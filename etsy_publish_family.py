#!/usr/bin/env python3
"""
etsy_publish_family.py - DRAFT the PREMIUM personalized family-name listing.

This is the moat product (see the business strategy memo): made-to-order,
personalization REQUIRED, $17.99. Unlike the instant-download lines, Etsy does
not auto-deliver — the operator renders the buyer's piece in Canva (see
canva_family.py for the per-order procedure) and sends the files.

Photos: styled-interior lead (square, thumbnail-optimised), colourway strip,
then the four samples framed in real photos.

DRY-RUN by default; --live creates a DRAFT only.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import etsy_api

ROOT = Path(__file__).resolve().parent
S = ROOT / "output" / "staging_canva"
NAME_SECTION = 58839805          # "Name Prints" — this is a personalized piece
PRICE = 17.99

TITLE = ("Personalized Family Name Print | Islamic Wall Art with Est. Year & City | "
         "Custom Muslim Home Gift | Digital Download")

TAGS = ["family name print", "personalized gift", "islamic wall art",
        "muslim home decor", "custom family sign", "new home gift",
        "housewarming muslim", "family established", "arabic home decor",
        "nikah gift", "eid gift for family", "custom name art",
        "digital download"]

DESC = """Personalized Family Name Print — designed individually for your family.

Your family name is set in an elegant display serif, framed by hand-placed
gold geometric corner ornaments drawn from traditional Islamic lattice work,
on a warm textured paper ground. Choose your colourway, and we design your
piece by hand and send the print-ready files.

★ WHAT WE NEED FROM YOU (add at checkout)
  1. Family name — e.g. "Rahman"
  2. Established year — e.g. "Est. 2016" (optional)
  3. City & country — e.g. "Manchester, United Kingdom" (optional)
  4. Colourway — Cream & Navy · Emerald · Charcoal · Terracotta
  Optional: if you would like your name in Arabic as well, paste the exact
  Arabic spelling you want and we will place it exactly as written.

★ WHAT YOU RECEIVE (within 24 hours, 5 high-resolution 300 DPI PDFs)
  • ISO A — prints A5 / A4 / A3 and larger
  • 2:3 ratio — 4x6, 8x12, 12x18, 16x24, 20x30, 24x36
  • 3:4 ratio — 6x8, 9x12, 12x16, 15x20, 18x24
  • 4:5 ratio — 8x10, 11x14, 16x20
  • 5:7 ratio — 5x7, 10x14

This is a made-to-order digital design, not an instant download — each piece
is set up by hand for your family. Nothing is shipped; frames not included.

Perfect for a new home, a nikah or wedding gift, Eid, or a family milestone.
"""


def assets():
    imgs = [S / "LISTING_lead.jpg", S / "LISTING_colourways.jpg"]
    for slug in ("family_cream_rahman", "family_emerald_siddiqui",
                 "family_charcoal_khan", "family_terracotta_hussain"):
        p = S / slug / f"{slug}_scene1.jpg"
        if p.exists():
            imgs.append(p)
    p = S / "family_cream_rahman" / "family_cream_rahman_print.png"
    if p.exists():
        imgs.append(p)
    return [i for i in imgs if i.exists()][:10]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args(argv)

    secrets = etsy_api.load_secrets()
    d = dict(secrets.get("listing", {}))
    d["shop_section_id"] = NAME_SECTION
    d["when_made"] = "made_to_order"          # genuinely made per order
    d["is_personalizable"] = True
    d["personalization_is_required"] = True
    d["personalization_char_count_max"] = 256
    d["personalization_instructions"] = (
        "Family name; Est. year (optional); City & country (optional); "
        "colourway: cream/emerald/charcoal/terracotta.")

    meta = {"title": TITLE[:140], "description": DESC, "tags": TAGS[:13],
            "price": PRICE, "currency_code": "USD"}
    imgs = assets()

    print(f"title : {meta['title']}")
    print(f"price : ${PRICE} | made-to-order | personalization REQUIRED")
    print(f"tags  ({len(meta['tags'])}): {', '.join(meta['tags'])}")
    print(f"images({len(imgs)}): {', '.join(p.name for p in imgs)}")
    print("files : none at listing level (delivered per order)")

    if not args.live:
        print("\nDRY-RUN — add --live to create the draft")
        return 0

    client = etsy_api.EtsyClient()
    res = client.create_draft_listing(meta, d)
    lid = res.get("listing_id") or (res.get("results") or [{}])[0].get("listing_id")
    client.set_personalization(lid, d["personalization_instructions"],
                               required=True, max_chars=256)
    for i, im in enumerate(imgs, 1):
        client.upload_listing_image(lid, im, rank=i)
    print(f"\n+ DRAFT listing {lid} created")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
