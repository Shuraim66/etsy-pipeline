#!/usr/bin/env python3
"""
etsy_api.py - minimal Etsy Open API v3 client: OAuth token management + shop ops.

CLI:
  python etsy_api.py whoami     # confirm which (existing) shop the app is wired to

Reads etsy_secrets.json (client_id/secret/shop_id) and etsy_token.json (OAuth
tokens from etsy_auth.py). Access tokens are auto-refreshed. Every request sends
the required `x-api-key` + `Authorization: Bearer` headers.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
SECRETS = ROOT / "etsy_secrets.json"
TOKEN = ROOT / "etsy_token.json"
API = "https://openapi.etsy.com/v3/application"
# api.etsy.com fails DNS on some networks; openapi.etsy.com serves the same
# oauth token endpoint (both front the v3 public token path).
TOKEN_URL = "https://openapi.etsy.com/v3/public/oauth/token"


class EtsyError(RuntimeError):
    pass


def load_secrets() -> dict:
    if not SECRETS.exists():
        raise EtsyError(f"Missing {SECRETS.name}. Copy etsy_secrets.example.json -> "
                        f"{SECRETS.name} and fill in client_id / client_secret / shop_id.")
    return json.loads(SECRETS.read_text(encoding="utf-8"))


class EtsyClient:
    def __init__(self):
        self.secrets = load_secrets()
        self.client_id = self.secrets["client_id"]
        self.client_secret = self.secrets.get("client_secret", "")
        if not TOKEN.exists():
            raise EtsyError(f"Not authorized yet. Run `python etsy_auth.py` to create {TOKEN.name}.")
        self.token = json.loads(TOKEN.read_text(encoding="utf-8"))

    # -- tokens --------------------------------------------------------------
    def _save_token(self, tok: dict) -> None:
        tok.setdefault("refresh_token", self.token.get("refresh_token"))  # keep if omitted
        tok["obtained_at"] = int(time.time())
        TOKEN.write_text(json.dumps(tok, indent=2), encoding="utf-8")
        self.token = tok

    def _access_token(self) -> str:
        t = self.token
        if t.get("obtained_at", 0) + t.get("expires_in", 3600) - 60 > time.time():
            return t["access_token"]
        r = requests.post(TOKEN_URL, data={
            "grant_type": "refresh_token", "client_id": self.client_id,
            "refresh_token": t["refresh_token"]}, timeout=30)
        if r.status_code != 200:
            raise EtsyError(f"Token refresh failed ({r.status_code}): {r.text}\n"
                            f"Re-run `python etsy_auth.py` to re-authorize.")
        self._save_token(r.json())
        return self.token["access_token"]

    def _api_key(self) -> str:
        # Etsy requires "<keystring>:<shared_secret>" in x-api-key for this app;
        # a bare keystring returns 403 "Shared secret is required in x-api-key header."
        return f"{self.client_id}:{self.client_secret}" if self.client_secret else self.client_id

    def _headers(self) -> dict:
        return {"x-api-key": self._api_key(), "Authorization": f"Bearer {self._access_token()}"}

    def get(self, path: str, **params):
        r = requests.get(f"{API}{path}", headers=self._headers(), params=params or None, timeout=30)
        if r.status_code != 200:
            raise EtsyError(f"GET {path} -> {r.status_code}: {r.text}")
        return r.json()

    def post_form(self, path: str, data: dict):
        r = self._post_retry(f"{API}{path}", data=data)
        if r.status_code not in (200, 201):
            raise EtsyError(f"POST {path} -> {r.status_code}: {r.text}")
        return r.json()

    def _post_retry(self, url: str, retries: int = 4, **kw):
        """POST with retries on transient network errors (this box's DNS
        intermittently fails to resolve openapi.etsy.com)."""
        import time as _t
        last = None
        for attempt in range(retries):
            try:
                return requests.post(url, headers=self._headers(), timeout=120, **kw)
            except requests.exceptions.ConnectionError as e:
                last = e
                wait = 5 * (attempt + 1)
                print(f"    (network error, retry {attempt + 1}/{retries} in {wait}s)", flush=True)
                _t.sleep(wait)
        raise last

    def post_multipart(self, path: str, files: dict, data: dict | None = None):
        r = self._post_retry(f"{API}{path}", files=files, data=data)
        if r.status_code not in (200, 201):
            raise EtsyError(f"POST {path} -> {r.status_code}: {r.text}")
        return r.json()

    # -- listing creation (drafts only) -------------------------------------
    def create_draft_listing(self, meta: dict, defaults: dict) -> dict:
        """Create a DRAFT digital-download listing. Returns the listing object."""
        body = {
            "quantity": int(defaults.get("quantity", 999)),
            "title": meta["title"],
            "description": meta["description"],
            "price": f'{float(meta["price"]):.2f}',
            "who_made": defaults.get("who_made", "i_did"),
            "when_made": defaults.get("when_made", "made_to_order"),
            "taxonomy_id": int(defaults["taxonomy_id"]),
            "type": defaults.get("type", "download"),
            # Etsy form-encoded arrays are COMMA-separated; a Python list becomes
            # repeated fields and Etsy then keeps only ONE tag.
            "tags": ",".join(meta.get("tags", [])),
        }
        if defaults.get("shop_section_id"):
            body["shop_section_id"] = int(defaults["shop_section_id"])
        # NOTE: personalization is NOT set here — the legacy listing fields
        # (is_personalizable, ...) are deprecated and 400 the whole request.
        # Call set_personalization() after creation instead.
        return self.post_form(f"/shops/{self.shop_id}/listings", body)

    def set_personalization(self, listing_id, instructions, required=True, max_chars=256) -> dict:
        """Enable a single text personalization question via Etsy's dedicated
        personalization endpoint (the legacy listing fields are deprecated)."""
        payload = {"personalization_questions": [{
            "question_text": "Personalization",
            "instructions": (instructions or "")[:120],   # Etsy hard-caps at 120
            "question_type": "text_input",
            "required": bool(required),
            "max_allowed_characters": int(max_chars),
        }]}
        r = requests.post(f"{API}/shops/{self.shop_id}/listings/{listing_id}/personalization",
                          headers={**self._headers(), "Content-Type": "application/json"},
                          data=json.dumps(payload), timeout=30)
        if r.status_code not in (200, 201):
            raise EtsyError(f"set_personalization -> {r.status_code}: {r.text}")
        return r.json()

    def upload_listing_file(self, listing_id, path, name=None, rank=1) -> dict:
        path = Path(path)
        # Etsy rejects a file part with no Content-Type ("An error occurred while
        # uploading your file") — always send an explicit MIME type.
        # Pass BYTES (not a handle): _post_retry may resend, and a consumed
        # handle uploads empty -> Etsy 400 "File not uploaded".
        ctype = "application/pdf" if path.suffix.lower() == ".pdf" else "application/octet-stream"
        return self.post_multipart(
            f"/shops/{self.shop_id}/listings/{listing_id}/files",
            files={"file": (path.name, path.read_bytes(), ctype)},
            data={"name": name or path.name, "rank": rank})

    def upload_listing_image(self, listing_id, path, rank=1) -> dict:
        path = Path(path)
        return self.post_multipart(
                f"/shops/{self.shop_id}/listings/{listing_id}/images",
                files={"image": (path.name, path.read_bytes(), "image/png")},
                data={"rank": rank})

    # -- identity / shop -----------------------------------------------------
    @property
    def user_id(self) -> str:
        # Etsy access tokens are prefixed with the user id: "<user_id>.<rest>"
        return str(self.token.get("access_token", "")).split(".")[0]

    @property
    def shop_id(self):
        return self.secrets.get("shop_id") or 0

    def whoami(self):
        """Return (user_id, shop) for the authorized account's EXISTING shop.

        Etsy v3 has no /users/me: the user id is the access-token prefix, and the
        shop is fetched by id (from secrets) or resolved from the owner."""
        uid = self.user_id
        if self.shop_id:
            shop = self.get(f"/shops/{self.shop_id}")
        else:
            shop = self.get(f"/users/{uid}/shops")  # getShopByOwnerUserId -> Shop
        return uid, shop


def ping() -> dict:
    """Validate the API key only (no OAuth). GET /openapi-ping."""
    s = load_secrets()
    key = f'{s["client_id"]}:{s["client_secret"]}' if s.get("client_secret") else s["client_id"]
    r = requests.get(f"{API}/openapi-ping", headers={"x-api-key": key}, timeout=30)
    if r.status_code != 200:
        raise EtsyError(f"ping -> {r.status_code}: {r.text}")
    return r.json()


def _cmd_ping() -> int:
    try:
        print("API key OK:", ping())
        return 0
    except EtsyError as e:
        print(f"ERROR: {e}")
    except requests.RequestException as e:
        print(f"NETWORK ERROR: {e}")
    return 1


def _cmd_whoami() -> int:
    try:
        uid, shop = EtsyClient().whoami()
    except EtsyError as e:
        print(f"ERROR: {e}")
        return 1
    except requests.RequestException as e:
        print(f"NETWORK ERROR: {e}")
        return 1
    print("Authorized — talking to your existing shop:\n")
    print(f"  shop name       : {shop.get('shop_name')}")
    print(f"  shop id         : {shop.get('shop_id')}")
    print(f"  user id         : {uid}")
    print(f"  currency        : {shop.get('currency_code')}")
    print(f"  active listings : {shop.get('listing_active_count')}")
    print(f"  digital listings: {shop.get('digital_listing_count')}")
    print(f"  url             : {shop.get('url')}")
    print("\nLooks right? Drafts the pipeline creates will land in THIS shop's Drafts.")
    return 0


def main(argv) -> int:
    cmd = argv[0] if argv else ""
    if cmd == "whoami":
        return _cmd_whoami()
    if cmd == "ping":
        return _cmd_ping()
    print("usage: python etsy_api.py [ping|whoami]")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
