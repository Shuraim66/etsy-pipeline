#!/usr/bin/env python3
"""
refresh_photos.py - rebuild and re-upload the listing photo set for every
single-print listing in the shop.

WHY EVERY LISTING, NOT JUST THE 39: the flood-fill that mapped the frame
openings ran with a loose tolerance, so on any plate holding a white MAT it
grabbed mat+window as one blob. Every photo ever composited through those
plates put the art over the mat, hard against the moulding - and on the linen
flatlay it painted over the dried flower that overlaps the frame. The quads
were re-derived in verify_plates.py; every photo built before that is wrong.

Photo order (8, Etsy allows 10):
  1 lead        square crop, art dominates at thumbnail size
  2 room        the line's signature room
  3 detail      100% crop of the artwork
  4-7 rooms     the remaining four scenes
  8 sizes       the print-ratio card

Upload order matters: new images go up FIRST, then the old ones are deleted.
Etsy refuses to delete a listing's last image, so deleting first strands the
listing on a stale photo (this bit us once already).

Usage:
  python3 refresh_photos.py                 # dry run, builds assets only
  python3 refresh_photos.py --live          # build + push
  python3 refresh_photos.py --live --only 4532011229
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import requests

import etsy_api
import scene_set
import sizes_card

ROOT = Path(__file__).resolve().parent
API = "https://openapi.etsy.com/v3/application"
MAP = Path("/tmp/claude-1000/-home-alpha-products-barakah-pipeline/"
           "816bc583-a082-4ed0-829d-65c9a115ca14/scratchpad/final_map.json")

FOOTERS = {
    "name": "300 DPI · print-ready PDF · 5 ratios included",
    "geo":  "300 DPI · print-ready PDF · instant download",
    "art":  "300 DPI · print-ready PDF · instant download",
}


def images_of(client, lid):
    r = requests.get(f"{API}/listings/{lid}/images", headers=client._headers(), timeout=30)
    return r.json().get("results", []) if r.status_code == 200 else []


def delete_image(client, lid, iid):
    for _ in range(3):
        try:
            r = requests.delete(
                f"{API}/shops/{client.shop_id}/listings/{lid}/images/{iid}",
                headers=client._headers(), timeout=60)
            return r.status_code in (200, 204, 404)
        except requests.exceptions.ConnectionError:
            time.sleep(4)
    return False


def build_assets(folder: Path, slug: str, preset: str) -> list[Path]:
    print_png = folder / f"{slug}_print.png"
    paths = scene_set.build(print_png, folder, slug, preset=preset)
    lead, rooms, detail = paths[0], paths[1:-1], paths[-1]
    card = folder / f"{slug}_sizes.jpg"
    sizes_card.build(card, footer=FOOTERS.get(preset, FOOTERS["art"]))
    return [lead, rooms[0], detail, *rooms[1:], card]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--only", nargs="*", help="restrict to these listing ids")
    ap.add_argument("--preset", help="restrict to one line: name/geo/art")
    args = ap.parse_args(argv)

    mapping = json.loads(MAP.read_text())
    todo = {k: v for k, v in mapping.items() if v.get("preset") in FOOTERS}
    if args.only:
        todo = {k: v for k, v in todo.items() if k in set(args.only)}
    if args.preset:
        todo = {k: v for k, v in todo.items() if v["preset"] == args.preset}
    print(f"{len(todo)} listings to refresh"
          f"{'' if args.live else '  (DRY RUN - assets only)'}\n")

    client = etsy_api.EtsyClient() if args.live else None
    ok = bad = 0
    for lid, v in todo.items():
        folder = ROOT / v["path"]
        slug = folder.name
        try:
            assets = build_assets(folder, slug, v["preset"])
        except Exception as e:
            print(f"BUILD FAIL {slug}: {e}", flush=True)
            bad += 1
            continue
        if not args.live:
            print(f"built {slug}: {len(assets)} photos", flush=True)
            ok += 1
            continue

        before = {im["listing_image_id"] for im in images_of(client, lid)}
        for rank, p in enumerate(assets, start=1):
            client.upload_listing_image(lid, p, rank=rank)
        for iid in before:
            delete_image(client, lid, iid)

        imgs = sorted(images_of(client, lid), key=lambda i: i.get("rank", 99))
        first = imgs[0] if imgs else {}
        good = first.get("full_width") == 2000 and first.get("full_height") == 2000
        ok, bad = ok + int(good), bad + int(not good)
        print(f"{'ok ' if good else 'BAD'} {lid} {slug}: {len(imgs)} imgs, "
              f"rank1 {first.get('full_width')}x{first.get('full_height')}", flush=True)
        time.sleep(0.2)

    print(f"\n{ok} ok, {bad} problem")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
