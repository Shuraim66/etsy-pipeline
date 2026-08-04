#!/usr/bin/env python3
"""
etsy_publish_bundles.py - DRAFT Etsy listings for the SET/BUNDLE products.

Sets are the AOV play: one listing at $12.99-16.99 instead of three at $6.99.
Same instant-download mechanics as the singles (no personalization), filed in
the Art Prints section.

Photo order: gallery-wall lead (thumbnail), flat grid of all pieces, then the
per-piece framed interior scenes.

DRY-RUN by default; --live creates DRAFTS only.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import etsy_api
from build_bundles import BUNDLES

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "staging_bundles"
ART_SECTION = 59585273
TITLE_MAX, TAG_MAX_LEN, TAG_MAX_COUNT = 140, 20, 13

# per-bundle SEO: distinct search territory each (no tag overlap within group)
META = {
    "set_japandi_3": {
        "title": "Japandi Wall Art Set of 3 | Koi Fish, Misty Mountains & Gold Abstract | Printable Digital Download",
        "tags": ["japandi wall art", "set of 3 prints", "koi fish art", "zen wall decor",
                 "mountain print set", "neutral wall art", "gallery wall set",
                 "minimalist art set", "printable wall art", "digital download",
                 "instant download", "living room decor", "calm home decor"],
    },
    "set_coastal_3": {
        "title": "Coastal Wall Art Set of 3 | Ocean Wave, Gold Shoreline & Crescent Moon | Printable Digital Download",
        "tags": ["coastal wall art", "set of 3 prints", "ocean wave print", "beach house decor",
                 "gold coastal art", "celestial print", "gallery wall set", "sea wall art",
                 "printable wall art", "digital download", "instant download",
                 "bathroom wall art", "blue wall decor"],
    },
    "set_botanical_3": {
        "title": "Botanical Wall Art Set of 3 | Eucalyptus, Monstera & Lavender Field | Printable Digital Download",
        "tags": ["botanical print set", "set of 3 prints", "eucalyptus print", "monstera art",
                 "lavender field art", "green wall art", "gallery wall set", "plant wall art",
                 "printable wall art", "digital download", "instant download",
                 "kitchen wall decor", "boho botanical"],
    },
    "set_moody_florals_3": {
        "title": "Moody Floral Wall Art Set of 3 | Dark Peonies, Roses & Still Life | Printable Digital Download",
        "tags": ["moody floral art", "set of 3 prints", "dark botanical", "peony wall art",
                 "vintage floral set", "dark academia decor", "gallery wall set",
                 "dining room art", "printable wall art", "digital download",
                 "instant download", "bedroom wall art", "still life print"],
    },
    "set_masters_3": {
        "title": "Vintage Fine Art Set of 3 | Van Gogh, Renoir & Cezanne | Museum Prints Digital Download",
        "tags": ["van gogh print", "renoir print", "cezanne art", "vintage art set",
                 "set of 3 prints", "famous paintings", "museum art print", "classic wall art",
                 "gallery wall set", "printable wall art", "digital download",
                 "instant download", "fine art prints"],
    },
}

DESC_TAIL = (
    "\n\n★ INSTANT DIGITAL DOWNLOAD — nothing is shipped. Your files are "
    "available the moment payment clears; no personalization needed.\n\n"
    "WHAT YOU RECEIVE\n"
    "  • One high-resolution 300 DPI PDF per artwork in the set\n"
    "  • ISO A sizing — prints beautifully at A5, A4, A3 and larger\n\n"
    "Print at home, at a local print shop, or through an online printing "
    "service. Frames not included.\n\n"
    "Buying the set costs far less than the prints individually — designed to "
    "hang together as a gallery wall.\n"
)


def clean_tag(t):
    t = "".join(c for c in t.strip().lower() if c.isalnum() or c in " -")
    return " ".join(t.split())[:TAG_MAX_LEN].strip()


def assets(folder: Path, slug: str):
    images, files = [], []
    for name in [f"{slug}_lead.jpg", f"{slug}_grid.jpg",
                 f"{slug}_scene1.jpg", f"{slug}_scene2.jpg"]:
        p = folder / name
        if p.exists():
            images.append(p)
    for i in range(1, 6):
        p = folder / f"{slug}_file{i}.pdf"
        if p.exists():
            files.append(p)
    return images[:10], files[:5]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args(argv)

    secrets = etsy_api.load_secrets()
    defaults = dict(secrets.get("listing", {}))
    defaults.pop("personalization_instructions", None)
    defaults["is_personalizable"] = False
    defaults["when_made"] = "2020_2026"
    defaults["shop_section_id"] = ART_SECTION

    client = etsy_api.EtsyClient() if args.live else None
    if not args.live:
        print("DRY-RUN — no API calls (add --live to create drafts)\n")

    n = 0
    for b in BUNDLES:
        slug = b["slug"]
        folder = OUT / slug
        if not folder.exists():
            print(f"  missing folder: {slug}")
            continue
        m = META.get(slug)
        if not m:
            print(f"  no META for {slug}")
            continue
        images, files = assets(folder, slug)
        tags = []
        for t in m["tags"]:
            ct = clean_tag(t)
            if ct and ct not in tags:
                tags.append(ct)
        tags = tags[:TAG_MAX_COUNT]
        meta = {
            "title": m["title"][:TITLE_MAX],
            "description": f"{b['title']} — {b['blurb']}" + DESC_TAIL,
            "tags": tags,
            "price": b["price"],
            "currency_code": "USD",
        }

        print(f"=== {slug} ===")
        print(f"  title : {meta['title']}")
        print(f"  price : {meta['price']} USD | {len(b['pieces'])} pieces | instant download")
        print(f"  tags  ({len(tags)}): {', '.join(tags)}")
        print(f"  images({len(images)}): {', '.join(p.name for p in images)}")
        print(f"  files ({len(files)}): {', '.join(p.name for p in files)}")
        for f in files:
            mb = f.stat().st_size / 1e6
            if mb > 20:
                print(f"  ! {f.name} is {mb:.1f} MB (>20 MB Etsy limit)")

        if args.live:
            res = client.create_draft_listing(meta, defaults)
            lid = res.get("listing_id") or (res.get("results") or [{}])[0].get("listing_id")
            for i, f in enumerate(files, 1):
                client.upload_listing_file(lid, f, rank=i)
            for i, im in enumerate(images, 1):
                client.upload_listing_image(lid, im, rank=i)
            print(f"  + DRAFT listing {lid} created")
            time.sleep(0.3)
        n += 1
        print()
    print(f"{n} bundles processed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
