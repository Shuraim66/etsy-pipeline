#!/usr/bin/env python3
"""
fetch_mockup_plates.py - pull REAL empty-frame interior photos from Pexels
as mockup plates (the asset class that finally looks right).

Pexels license: free for commercial use incl. modification (compositing our
prints). We keep per-photo attribution (photographer + URL) as a courtesy
and record it in PLATES.json.

Flow:
  1. search several queries, portrait-orientation, large
  2. download candidates to assets/mockups/pexels/candidates/
  3. operator/agent reviews at full size; approved ones get their frame
     opening corner-mapped into OPENINGS (mockup_photo.py style)

Usage: python3 fetch_mockup_plates.py
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KEY = (ROOT / ".pexels_key").read_text().strip()
OUT = ROOT / "assets" / "mockups" / "pexels" / "candidates"

QUERIES = [
    ("empty picture frame wall interior", 8),
    ("blank poster frame mockup living room", 8),
    ("empty frame above sofa", 6),
    ("blank frame bedroom wall", 6),
    ("empty wooden frame interior plant", 6),
]

MIN_W, MIN_H = 2000, 2000       # need print-quality plates


def get(url):
    req = urllib.request.Request(url, headers={
        "Authorization": KEY,
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) barakah-mockups/1.0",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def fetch(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "barakah-mockups/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        dest.write_bytes(r.read())


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    seen, meta = set(), {}
    kept = 0
    for q, want in QUERIES:
        res = get("https://api.pexels.com/v1/search?query="
                  + urllib.parse.quote(q) + f"&per_page=30&size=large")
        n = 0
        for p in res.get("photos", []):
            if n >= want:
                break
            pid = p["id"]
            if pid in seen or p["width"] < MIN_W or p["height"] < MIN_H:
                continue
            seen.add(pid)
            dest = OUT / f"pexels_{pid}.jpg"
            if not dest.exists():
                try:
                    fetch(p["src"]["large2x"], dest)
                except Exception as e:
                    print("  dl fail", pid, e)
                    continue
            meta[str(pid)] = {
                "photographer": p["photographer"],
                "url": p["url"],
                "alt": p.get("alt", ""),
                "w": p["width"], "h": p["height"],
                "query": q,
            }
            n += 1
            kept += 1
            print(f"  ok {pid} {p['width']}x{p['height']} {p.get('alt','')[:50]}")
            time.sleep(0.2)
        print(f"[{q}] -> {n}")
    (OUT.parent / "PLATES.json").write_text(json.dumps(meta, indent=1))
    print(f"\n{kept} candidates in {OUT}")
