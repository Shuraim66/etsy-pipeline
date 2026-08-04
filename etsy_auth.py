#!/usr/bin/env python3
"""
etsy_auth.py - one-time OAuth 2.0 (PKCE) authorization for your existing Etsy shop.

Run it, open the printed URL in your browser (logged into your Etsy account),
approve access, then paste back the redirect URL (or just the `code`). It
exchanges the code for tokens and saves etsy_token.json. No local server needed
-- the redirect page failing to load is fine; we only read the `code` from the
address bar.

  python etsy_auth.py
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets as pysecrets
import sys
import time
import urllib.parse
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
SECRETS = ROOT / "etsy_secrets.json"
TOKEN = ROOT / "etsy_token.json"
AUTH_URL = "https://www.etsy.com/oauth/connect"
TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"
# read shop, read + write listings (write also covers image/file uploads)
SCOPES = ["shops_r", "shops_w", "listings_r", "listings_w", "listings_d"]


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _extract_code(pasted: str, expected_state: str) -> str:
    if pasted.startswith("http"):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(pasted).query)
        if expected_state and q.get("state", [None])[0] != expected_state:
            print("WARNING: state did not match (possible CSRF / wrong paste).")
        return q.get("code", [""])[0]
    return pasted.strip()


def main() -> int:
    if not SECRETS.exists():
        print(f"Missing {SECRETS.name}. Copy etsy_secrets.example.json -> {SECRETS.name} first.")
        return 1
    s = json.loads(SECRETS.read_text(encoding="utf-8"))
    client_id, redirect = s["client_id"], s["redirect_uri"]

    verifier = _b64url(os.urandom(40))                       # 43-128 char PKCE preimage
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    state = pysecrets.token_urlsafe(16)
    params = urllib.parse.urlencode({
        "response_type": "code", "client_id": client_id, "redirect_uri": redirect,
        "scope": " ".join(SCOPES), "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256",
    })

    print("STEP 1 — open this URL (logged into your Etsy account) and approve:\n")
    print(f"  {AUTH_URL}?{params}\n")
    print("STEP 2 — Etsy redirects to your redirect_uri with ?code=...&state=...")
    print("         (the page may fail to load — that's fine, just copy the address bar)\n")
    pasted = input("STEP 3 — paste the full redirect URL (or just the code): ").strip()
    code = _extract_code(pasted, state)
    if not code:
        print("No code found.")
        return 1

    r = requests.post(TOKEN_URL, data={
        "grant_type": "authorization_code", "client_id": client_id,
        "redirect_uri": redirect, "code": code, "code_verifier": verifier}, timeout=30)
    if r.status_code != 200:
        print(f"Token exchange failed ({r.status_code}): {r.text}")
        return 1
    tok = r.json()
    tok["obtained_at"] = int(time.time())
    TOKEN.write_text(json.dumps(tok, indent=2), encoding="utf-8")
    print(f"\nSaved {TOKEN.name}. Verify with:  python etsy_api.py whoami")
    return 0


if __name__ == "__main__":
    sys.exit(main())
