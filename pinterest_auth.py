#!/usr/bin/env python3
"""
pinterest_auth.py - one-time OAuth 2.0 authorization for Pinterest API v5.

Pinterest uses a confidential-client flow (no PKCE): the token call authenticates
with HTTP Basic (client_id:client_secret). Run this, open the printed URL, approve,
paste back the redirect URL (or just the code) -> saves pinterest_token.json.

  python pinterest_auth.py
"""
from __future__ import annotations

import base64
import json
import secrets as pysecrets
import sys
import time
import urllib.parse
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
SECRETS = ROOT / "pinterest_secrets.json"
TOKEN = ROOT / "pinterest_token.json"
AUTH_URL = "https://www.pinterest.com/oauth/"
# read account, read+write boards + pins (incl. secret-board variants for SECRET boards)
SCOPES = ["user_accounts:read", "boards:read", "boards:write", "boards:write_secret",
          "pins:read", "pins:write", "pins:write_secret"]


def _extract_code(pasted: str, expected_state: str) -> str:
    if pasted.startswith("http"):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(pasted).query)
        if expected_state and q.get("state", [None])[0] != expected_state:
            print("WARNING: state did not match (possible CSRF / wrong paste).")
        return q.get("code", [""])[0]
    return pasted.strip()


def main() -> int:
    if not SECRETS.exists():
        print(f"Missing {SECRETS.name}. Copy pinterest_secrets.example.json -> {SECRETS.name} first.")
        return 1
    s = json.loads(SECRETS.read_text(encoding="utf-8"))
    cid, secret, redirect = s["client_id"], s["client_secret"], s["redirect_uri"]
    base = s.get("api_base", "https://api.pinterest.com").rstrip("/")

    state = pysecrets.token_urlsafe(16)
    params = urllib.parse.urlencode({
        "client_id": cid, "redirect_uri": redirect, "response_type": "code",
        "scope": ",".join(SCOPES), "state": state,
    })
    print("STEP 1 — open this URL (logged into your Pinterest account) and approve:\n")
    print(f"  {AUTH_URL}?{params}\n")
    print("STEP 2 — Pinterest redirects to your redirect_uri with ?code=...&state=...")
    print("         (the page may fail to load — that's fine, copy the address bar)\n")
    pasted = input("STEP 3 — paste the full redirect URL (or just the code): ").strip()
    code = _extract_code(pasted, state)
    if not code:
        print("No code found.")
        return 1

    basic = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    r = requests.post(f"{base}/v5/oauth/token",
                      headers={"Authorization": f"Basic {basic}",
                               "Content-Type": "application/x-www-form-urlencoded"},
                      data={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect},
                      timeout=30)
    if r.status_code != 200:
        print(f"Token exchange failed ({r.status_code}): {r.text}")
        return 1
    tok = r.json()
    tok["obtained_at"] = int(time.time())
    TOKEN.write_text(json.dumps(tok, indent=2), encoding="utf-8")
    print(f"\nSaved {TOKEN.name}. Verify with:  python pinterest_api.py whoami")
    return 0


if __name__ == "__main__":
    sys.exit(main())
