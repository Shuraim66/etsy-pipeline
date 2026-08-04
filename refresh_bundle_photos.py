#!/usr/bin/env python3
"""
refresh_bundle_photos.py - push the rebuilt set/bundle photos.

The five set listings were composited through the same broken frame quads as
everything else (see refresh_photos.py), so their gallery leads put the art
over the mat. build_bundles.py has since been rerun against the corrected
quads and now composes the lead from clean-wall plates only.

Photo order: gallery lead, flat grid, the individual pieces, two room scenes,
then the print-ratio card.

Same upload-first-then-delete order as everywhere else: Etsy refuses to delete
a listing's last image.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import etsy_api
import sizes_card
from refresh_photos import delete_image, images_of

ROOT = Path(__file__).resolve().parent
B = ROOT / "output" / "staging_bundles"
MAP = Path("/tmp/claude-1000/-home-alpha-products-barakah-pipeline/"
           "816bc583-a082-4ed0-829d-65c9a115ca14/scratchpad/final_map.json")


def assets(folder: Path, slug: str):
    card = folder / f"{slug}_sizes.jpg"
    sizes_card.build(card)
    order = [folder / f"{slug}_lead.jpg", folder / f"{slug}_grid.jpg"]
    order += [folder / f"{slug}_piece{i}.jpg" for i in (1, 2, 3)]
    order += [folder / f"{slug}_scene{i}.jpg" for i in (1, 2)]
    order += [card]
    return [p for p in order if p.exists()][:10]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args(argv)

    mapping = json.loads(MAP.read_text())
    todo = {k: v for k, v in mapping.items()
            if v.get("folder", "").startswith("set_")}
    print(f"{len(todo)} bundle listings"
          f"{'' if args.live else '  (DRY RUN)'}\n")

    client = etsy_api.EtsyClient() if args.live else None
    for lid, v in todo.items():
        folder = B / v["folder"]
        paths = assets(folder, v["folder"])
        if not args.live:
            print(f"{lid} {v['folder']}: {len(paths)} photos "
                  f"({', '.join(p.name.replace(v['folder'] + '_', '') for p in paths)})")
            continue
        before = {im["listing_image_id"] for im in images_of(client, lid)}
        for rank, p in enumerate(paths, start=1):
            client.upload_listing_image(lid, p, rank=rank)
        for iid in before:
            delete_image(client, lid, iid)
        imgs = sorted(images_of(client, lid), key=lambda i: i.get("rank", 99))
        first = imgs[0] if imgs else {}
        good = first.get("full_width") == 2000 and first.get("full_height") == 2000
        print(f"{'ok ' if good else 'BAD'} {lid} {v['folder']}: {len(imgs)} imgs, "
              f"rank1 {first.get('full_width')}x{first.get('full_height')}", flush=True)
        time.sleep(0.2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
