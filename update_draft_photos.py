#!/usr/bin/env python3
"""
update_draft_photos.py - replace the photo set on Art Prints DRAFT listings.

Fixes vs the earlier attempt:
  * reads existing images from /listings/{id}/images (the shop-scoped path
    404s), so the delete step actually runs — otherwise uploads hit Etsy's
    20-image cap and the run dies
  * deletes ALL existing images before uploading the new set
  * order: lead crop, 4 scene mockups, 3 close-up frames, flat print (max 10)

Safe: only touches listings whose state is draft in the Art Prints section.
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


def list_images(client, lid):
    r = requests.get(f"{API}/listings/{lid}/images", headers=client._headers(), timeout=30)
    if r.status_code != 200:
        return []
    return r.json().get("results", [])


def delete_image(client, lid, image_id, shop_id):
    for _ in range(3):
        try:
            r = requests.delete(f"{API}/shops/{shop_id}/listings/{lid}/images/{image_id}",
                                headers=client._headers(), timeout=60)
            if r.status_code in (200, 204, 404):
                return True
        except requests.exceptions.ConnectionError:
            time.sleep(5)
    return False


def main():
    client = etsy_api.EtsyClient()
    res = client.get(f"/shops/{client.shop_id}/listings", state="draft", limit=100)
    drafts = [l for l in res.get("results", []) if l.get("shop_section_id") == ART_SECTION]
    print(f"{len(drafts)} drafts in Art Prints section", flush=True)

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

    updated = skipped = 0
    for l in drafts:
        lid, title = l["listing_id"], l["title"]
        folder = folders.get(title)
        if folder is None:
            skipped += 1
            print(f"  no folder match: {title[:60]}", flush=True)
            continue
        slug = folder.name

        existing = list_images(client, lid)
        for im in existing:
            delete_image(client, lid, im["listing_image_id"], client.shop_id)

        order = [folder / f"{slug}_lead.jpg"]
        order += [folder / f"{slug}_scene{i}.jpg" for i in (1, 2, 3, 4)]
        order += [folder / f"{slug}_mock{i}.jpg" for i in (1, 2, 3)]
        order += [folder / f"{slug}_print.png"]

        rank = 1
        for p in order:
            if not p.exists() or rank > 10:
                continue
            client.upload_listing_image(lid, p, rank=rank)
            rank += 1
        updated += 1
        print(f"ok {slug} (deleted {len(existing)}, uploaded {rank-1})", flush=True)
        time.sleep(0.2)

    print(f"\n{updated} drafts updated, {skipped} unmatched", flush=True)


if __name__ == "__main__":
    main()
