#!/usr/bin/env python3
"""
pinterest_publish.py - post a design's generated pins to Pinterest.

Reads each design's pins/pins.csv (from generate.py --pins) and creates one Pin
per row, using the CSV's pin_title / pin_description / suggested_board and the
listing_url as the Pin link (so pins drive traffic to your Etsy listing).

SAFE BY DESIGN:
  * DRY-RUN by default — prints what would be posted, NO API calls. --live posts.
  * Posts to a board with the privacy from pinterest_secrets.json (default
    SECRET) — Pinterest has no "draft", so a SECRET board is the safe equivalent
    (and new Trial apps are sandbox-only / private regardless).

  python pinterest_publish.py output/catalog                    # dry-run, all designs
  python pinterest_publish.py output/catalog/ibrahim_hero --live
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import pinterest_api


def read_pins(pins_dir: Path):
    f = pins_dir / "pins.csv"
    if not f.exists():
        return []
    with f.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def process_one(folder: Path, defaults: dict, client, live: bool, cache: dict) -> int:
    pins_dir = folder / "pins"
    rows = read_pins(pins_dir)
    print(f"\n=== {folder.name} ===")
    if not rows:
        print("  no pins/pins.csv — run `generate.py --pins` first; skipping")
        return 0
    posted = 0
    for r in rows:
        img = pins_dir / r["pin_image"]
        board_name = (r.get("suggested_board") or defaults.get("default_name") or "Pins").strip()
        link = (r.get("listing_url") or "").strip()
        print(f"  • {r['pin_image']}  ->  board '{board_name}'  link={link or '(none yet)'}")
        print(f"      {r['pin_title']}")
        if not img.exists():
            print("      ! image missing; skip")
            continue
        if not live:
            continue
        if board_name not in cache:
            cache[board_name] = client.find_or_create_board(
                board_name, defaults.get("description", ""), defaults.get("privacy", "SECRET"))
        client.create_pin(cache[board_name], img, title=r["pin_title"],
                          description=r["pin_description"], link=link, alt_text=r["pin_title"])
        posted += 1
        print("      + posted")
    return posted


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Post generated pins to Pinterest (dry-run by default).")
    ap.add_argument("path", help="a design folder, or a parent directory of design folders")
    ap.add_argument("--live", action="store_true", help="actually post pins (default: dry-run / preview)")
    args = ap.parse_args(argv)

    try:
        defaults = pinterest_api.load_secrets().get("board", {})
    except pinterest_api.PinterestError as e:
        if args.live:
            print(f"ERROR: {e}")
            return 1
        defaults = {}

    path = Path(args.path)
    if (path / "pins" / "pins.csv").exists():
        folders = [path]
    else:
        folders = sorted(p for p in path.iterdir() if p.is_dir() and (p / "pins" / "pins.csv").exists())
    if not folders:
        print(f"No design folders with pins/pins.csv at {path}")
        return 1

    if args.live:
        privacy = defaults.get("privacy", "SECRET")
        print(f"LIVE — posting pins to '{defaults.get('default_name', 'Pins')}' boards (privacy: {privacy})")
        if privacy != "SECRET":
            print(f"  NOTE: privacy is {privacy} — pins may be PUBLIC immediately (Standard-access apps).")
    else:
        print("DRY-RUN — no API calls (add --live to post)")

    client = pinterest_api.PinterestClient() if args.live else None
    cache: dict = {}
    total = sum(process_one(f, defaults, client, args.live, cache) for f in folders)
    if args.live:
        print(f"\nPosted {total} pin(s).")
    else:
        print("\nDry-run complete. After `python pinterest_auth.py`, re-run with --live to post.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
