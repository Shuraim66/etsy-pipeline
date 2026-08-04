#!/usr/bin/env python3
"""
fetch_room_plates.py - pull empty-frame plates for the ROOM TYPES the listing
photo set is missing.

The current plate library skews living-room/flatlay: there is exactly one
bedroom, no nursery and no office. Nursery matters most - half the name-print
titles literally say "Islamic Nursery Decor" and none of the photos show one.

Candidates land in assets/mockups/pexels/candidates/ tagged with the room they
were fetched for; they still need reviewing at full size and their frame
opening corner-mapped into OPENINGS.json before use.

Usage: python3 fetch_room_plates.py [room ...]
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KEY = (ROOT / ".pexels_key").read_text().strip()
OUT = ROOT / "assets" / "mockups" / "pexels" / "candidates"
META = OUT.parent / "PLATES_rooms.json"

ROOMS = {
    "nursery": [
        "empty frame nursery wall",
        "blank poster frame kids room",
        "nursery wall decor frame crib",
        "baby room picture frame mockup",
    ],
    "office": [
        "empty frame above desk",
        "blank poster frame home office",
        "picture frame desk workspace mockup",
        "empty frame shelf books interior",
    ],
    "bedroom": [
        "empty frame above bed",
        "blank poster frame bedroom wall",
        "picture frame bedside table mockup",
    ],
    "living": [
        "empty frame above sofa living room",
        "blank poster frame couch interior",
    ],
    "closeup": [
        "empty picture frame close up detail",
        "blank frame corner texture macro",
    ],
}

MIN_W, MIN_H = 1800, 1800
PER_QUERY = 6


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


def main(rooms):
    OUT.mkdir(parents=True, exist_ok=True)
    meta = json.loads(META.read_text()) if META.exists() else {}
    seen = set(meta)
    total = 0
    for room in rooms:
        got = 0
        for q in ROOMS[room]:
            res = get("https://api.pexels.com/v1/search?query="
                      + urllib.parse.quote(q) + "&per_page=40&size=large")
            n = 0
            for p in res.get("photos", []):
                if n >= PER_QUERY:
                    break
                pid = str(p["id"])
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
                meta[pid] = {"room": room, "query": q,
                             "photographer": p["photographer"], "url": p["url"],
                             "alt": p.get("alt", ""), "w": p["width"], "h": p["height"]}
                n += 1
                got += 1
                total += 1
                time.sleep(0.15)
            print(f"  [{room}] {q!r} -> {n}")
        print(f"{room}: {got}")
    META.write_text(json.dumps(meta, indent=1))
    print(f"\n{total} new candidates -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:] or list(ROOMS)))
