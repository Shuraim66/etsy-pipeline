#!/usr/bin/env python3
"""
pinterest_api.py - minimal Pinterest REST API v5 client: OAuth token management
+ boards + pins.

CLI:
  python pinterest_api.py whoami    # confirm the authorized account
  python pinterest_api.py boards    # list your boards (id / privacy / name)

Reads pinterest_secrets.json (client_id/secret/api_base/board) and
pinterest_token.json (from pinterest_auth.py). Access tokens auto-refresh.
Token calls use HTTP Basic (confidential client); API calls use Bearer.
"""
from __future__ import annotations

import base64
import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
SECRETS = ROOT / "pinterest_secrets.json"
TOKEN = ROOT / "pinterest_token.json"


class PinterestError(RuntimeError):
    pass


def load_secrets() -> dict:
    if not SECRETS.exists():
        raise PinterestError(f"Missing {SECRETS.name}. Copy pinterest_secrets.example.json -> "
                             f"{SECRETS.name} and fill in client_id / client_secret.")
    return json.loads(SECRETS.read_text(encoding="utf-8"))


class PinterestClient:
    def __init__(self):
        self.s = load_secrets()
        self.client_id = self.s["client_id"]
        self.client_secret = self.s["client_secret"]
        self.base = self.s.get("api_base", "https://api.pinterest.com").rstrip("/")
        if not TOKEN.exists():
            raise PinterestError(f"Not authorized yet. Run `python pinterest_auth.py` to create {TOKEN.name}.")
        self.token = json.loads(TOKEN.read_text(encoding="utf-8"))

    # -- tokens --------------------------------------------------------------
    def _basic(self) -> str:
        return base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()

    def _save(self, tok: dict) -> None:
        tok.setdefault("refresh_token", self.token.get("refresh_token"))
        tok["obtained_at"] = int(time.time())
        TOKEN.write_text(json.dumps(tok, indent=2), encoding="utf-8")
        self.token = tok

    def _access(self) -> str:
        t = self.token
        if t.get("obtained_at", 0) + t.get("expires_in", 2592000) - 300 > time.time():
            return t["access_token"]
        r = requests.post(f"{self.base}/v5/oauth/token",
                          headers={"Authorization": f"Basic {self._basic()}",
                                   "Content-Type": "application/x-www-form-urlencoded"},
                          data={"grant_type": "refresh_token", "refresh_token": t["refresh_token"]},
                          timeout=30)
        if r.status_code != 200:
            raise PinterestError(f"Token refresh failed ({r.status_code}): {r.text}\n"
                                 f"Re-run `python pinterest_auth.py`.")
        self._save(r.json())
        return self.token["access_token"]

    def get(self, path, **params):
        r = requests.get(f"{self.base}{path}", headers={"Authorization": f"Bearer {self._access()}"},
                         params=params or None, timeout=30)
        if r.status_code != 200:
            raise PinterestError(f"GET {path} -> {r.status_code}: {r.text}")
        return r.json()

    def post(self, path, payload):
        r = requests.post(f"{self.base}{path}",
                          headers={"Authorization": f"Bearer {self._access()}",
                                   "Content-Type": "application/json"},
                          json=payload, timeout=60)
        if r.status_code not in (200, 201):
            raise PinterestError(f"POST {path} -> {r.status_code}: {r.text}")
        return r.json()

    # -- identity / boards / pins -------------------------------------------
    def whoami(self):
        return self.get("/v5/user_account")

    def list_boards(self):
        boards, bookmark = [], None
        while True:
            r = self.get("/v5/boards", page_size=100, **({"bookmark": bookmark} if bookmark else {}))
            boards += r.get("items", [])
            bookmark = r.get("bookmark")
            if not bookmark:
                return boards

    def create_board(self, name, description="", privacy="SECRET"):
        return self.post("/v5/boards", {"name": name[:50], "description": (description or "")[:500],
                                        "privacy": privacy})

    def find_or_create_board(self, name, description="", privacy="SECRET"):
        for b in self.list_boards():
            if b.get("name", "").strip().lower() == name.strip().lower():
                return b["id"]
        return self.create_board(name, description, privacy)["id"]

    def create_pin(self, board_id, image_path, title="", description="", link="", alt_text=""):
        path = Path(image_path)
        ct = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        payload = {
            "board_id": board_id,
            "media_source": {"source_type": "image_base64", "content_type": ct,
                             "data": base64.b64encode(path.read_bytes()).decode()},
            "title": (title or "")[:100],
            "description": (description or "")[:500],
        }
        if link:
            payload["link"] = link
        if alt_text:
            payload["alt_text"] = alt_text[:500]
        return self.post("/v5/pins", payload)


def _cmd_whoami() -> int:
    try:
        u = PinterestClient().whoami()
    except PinterestError as e:
        print(f"ERROR: {e}")
        return 1
    except requests.RequestException as e:
        print(f"NETWORK ERROR: {e}")
        return 1
    print("Authorized Pinterest account:")
    print(f"  username     : {u.get('username')}")
    print(f"  account type : {u.get('account_type')}")
    print(f"  business     : {u.get('business_name')}")
    print(f"  id           : {u.get('id')}")
    return 0


def _cmd_boards() -> int:
    try:
        boards = PinterestClient().list_boards()
    except PinterestError as e:
        print(f"ERROR: {e}")
        return 1
    except requests.RequestException as e:
        print(f"NETWORK ERROR: {e}")
        return 1
    print(f"{len(boards)} board(s):")
    for b in boards:
        print(f"  {b.get('id')}  {b.get('privacy', ''):9}  {b.get('name')}")
    return 0


def main(argv) -> int:
    cmd = argv[0] if argv else ""
    if cmd == "whoami":
        return _cmd_whoami()
    if cmd == "boards":
        return _cmd_boards()
    print("usage: python pinterest_api.py [whoami|boards]")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
