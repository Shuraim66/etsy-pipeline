#!/usr/bin/env python3
"""
fix_draft_thumbs.py - make the square lead crop the PRIMARY photo on
Art Prints drafts.

Two Etsy behaviours drove the earlier failures:
  1. A listing must always keep >= 1 image, so "delete everything then
     re-upload" cannot work — the last delete 400s and the wipe loop stalls
     (my first attempt wiped listings down to a single stale image).
  2. Duplicate ranks are allowed; ties resolve by upload age, so an old
     rank-1 image kept winning the thumbnail slot.

Working approach: upload the new set FIRST (ranks 1..N), then delete the
leftovers. The listing never drops below one image, and the freshly uploaded
rank-1 lead crop ends up as the primary.
"""
from __future__ import annotations

import time
from pathlib import Path

import requests

import etsy_api
import etsy_publish_art as pub

ROOT = Path(__file__).resolve().parent
ART_SECTION = 59585273
API = "https://openapi.etsy.com/v3/application"


def images_of(client, lid):
    r = requests.get(f"{API}/listings/{lid}/images", headers=client._headers(), timeout=30)
    return r.json().get("results", []) if r.status_code == 200 else []


def delete_image(client, lid, iid):
    for _ in range(3):
        try:
            r = requests.delete(f"{API}/shops/{client.shop_id}/listings/{lid}/images/{iid}",
                                headers=client._headers(), timeout=60)
            return r.status_code in (200, 204, 404)
        except requests.exceptions.ConnectionError:
            time.sleep(4)
    return False


def asset_order(folder: Path, slug: str):
    order = [folder / f"{slug}_lead.jpg"]
    order += [folder / f"{slug}_scene{i}.jpg" for i in (1, 2, 3, 4)]
    order += [folder / f"{slug}_mock{i}.jpg" for i in (1, 2, 3)]
    order += [folder / f"{slug}_print.png"]
    return [p for p in order if p.exists()][:9]


def main():
    client = etsy_api.EtsyClient()
    res = client.get(f"/shops/{client.shop_id}/listings", state="draft", limit=100)
    drafts = [l for l in res.get("results", []) if l.get("shop_section_id") == ART_SECTION]

    folders = {}
    for root, line in ((ROOT / "output/staging_sd", "ai"),
                       (ROOT / "output/staging_pd_art", "pd")):
        if not root.exists():
            continue
        for folder in sorted(p for p in root.iterdir() if p.is_dir()):
            if not (folder / f"{folder.name}_print.png").exists():
                continue
            meta = pub.build_meta(folder, line)
            if meta:
                folders[meta["title"]] = folder

    good = 0
    for l in drafts:
        lid, title = l["listing_id"], l["title"]
        folder = folders.get(title)
        if folder is None:
            print(f"  no match: {title[:50]}", flush=True)
            continue
        slug = folder.name

        before = {im["listing_image_id"] for im in images_of(client, lid)}

        # 1) upload the intended set first (listing never drops below 1 image)
        for rank, p in enumerate(asset_order(folder, slug), start=1):
            client.upload_listing_image(lid, p, rank=rank)

        # 2) remove every pre-existing image
        for iid in before:
            delete_image(client, lid, iid)

        imgs = sorted(images_of(client, lid), key=lambda i: i.get("rank", 99))
        first = imgs[0] if imgs else {}
        ok = first.get("full_width") == 2000 and first.get("full_height") == 2000
        good += 1 if ok else 0
        print(f"{'ok ' if ok else 'BAD'} {slug}: {len(imgs)} imgs, "
              f"rank1={first.get('full_width')}x{first.get('full_height')}", flush=True)
        time.sleep(0.2)

    print(f"\n{good}/{len(drafts)} drafts lead with the 2000x2000 crop", flush=True)


if __name__ == "__main__":
    main()
