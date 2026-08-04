#!/usr/bin/env python3
"""
push_shop.py - push the newly built 4:5 photo sets to their live/draft listings.

Reads rollout.json (listing_id, folder, print_path). For each listing uploads
<slug>_v1..v7.jpg at ranks 1..7 FIRST, then deletes the previous images
(upload-first-then-delete keeps the listing >= 1 image at all times). Verifies
rank-1 is 2000x2500. Idempotent-ish and resumable: pass --skip <id> ... to omit
already-done listings.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import requests

import etsy_api

API = "https://openapi.etsy.com/v3/application"
ROLLOUT = Path("/tmp/claude-1000/-home-alpha-products-barakah-pipeline/"
               "816bc583-a082-4ed0-829d-65c9a115ca14/scratchpad/rollout.json")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=[])
    ap.add_argument("--skip", nargs="*", default=[])
    args = ap.parse_args(argv)

    c = etsy_api.EtsyClient()
    rollout = json.loads(ROLLOUT.read_text())
    skip = set(args.skip)
    only = set(args.only)

    def images_of(lid):
        r = requests.get(f"{API}/listings/{lid}/images", headers=c._headers(), timeout=30)
        return r.json().get("results", []) if r.status_code == 200 else []

    def delete_image(lid, iid):
        for _ in range(3):
            try:
                r = requests.delete(f"{API}/shops/{c.shop_id}/listings/{lid}/images/{iid}",
                                    headers=c._headers(), timeout=60)
                if r.status_code in (200, 204, 404):
                    return True
            except requests.exceptions.ConnectionError:
                time.sleep(4)
        return False

    ok = bad = 0
    total = len(rollout)
    for n, (lid, folder_name, print_path) in enumerate(rollout, 1):
        if str(lid) in skip or (only and str(lid) not in only):
            continue
        pp = Path(print_path)
        folder = pp.parent
        slug = pp.name[:-len("_print.png")]
        imgs = [folder / f"{slug}_v{i}.jpg" for i in range(1, 8)]
        imgs = [p for p in imgs if p.exists()]
        if not imgs:
            print(f"[{n}/{total}] {lid} {slug}: NO IMAGES BUILT — skipped", flush=True)
            bad += 1
            continue
        try:
            before = {im["listing_image_id"] for im in images_of(lid)}
            for rank, p in enumerate(imgs, 1):
                c.upload_listing_image(lid, p, rank=rank)
            for iid in before:
                delete_image(lid, iid)
            final = sorted(images_of(lid), key=lambda x: x.get("rank", 99))
            first = final[0] if final else {}
            good = first.get("full_width") == 2000 and first.get("full_height") == 2500
            ok += 1 if good else 0
            bad += 0 if good else 1
            print(f"[{n}/{total}] {'ok ' if good else 'BAD'} {lid} {slug}: "
                  f"{len(final)} imgs, rank1 {first.get('full_width')}x{first.get('full_height')}", flush=True)
            time.sleep(0.2)
        except Exception as e:
            bad += 1
            print(f"[{n}/{total}] FAIL {lid} {slug}: {e}", flush=True)

    print(f"\npushed ok={ok} problems={bad}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
