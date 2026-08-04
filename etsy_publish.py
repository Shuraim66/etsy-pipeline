#!/usr/bin/env python3
"""
etsy_publish.py - create DRAFT Etsy digital-download listings from rendered
design folders.

SAFE BY DESIGN:
  * DRY-RUN is the default — prints the exact listing payload + the image/file
    assets, makes NO API calls. Add --live to actually create drafts.
  * Creates DRAFTS only — never publishes. You review + publish in Etsy.

Per Etsy v3: createDraftListing (type=download) → upload digital files (<=5,
<=20MB) → upload images (the mockup + pins). Listing title/description/tags come
from etsy_meta.py; price/taxonomy/who_made/when_made from etsy_secrets.json.

  python etsy_publish.py output/catalog                 # dry-run, all designs
  python etsy_publish.py output/catalog/ibrahim_hero --live
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import etsy_api
import etsy_meta
import render

ROOT = Path(__file__).resolve().parent
SIZE_TAGS = ("iso_A", "ratio_2x3", "ratio_3x4", "ratio_4x5", "ratio_5x7")
# Etsy listing photos: the room mockup, the flat print, and the "name meaning"
# graphic. Deliberately NOT the other pins — _pin_mockup duplicates the room
# mockup, and _pin_styles ("Choose Your Style") is misleading on a 1-design listing.
PIN_TAGS = ("_pin_text",)
# Shared, on-theme info cards appended to EVERY listing (how it works / what you
# receive / sizes) — same for all designs, so kept once in assets/listing/.
LISTING_ASSETS = ("asset_whatyouget.png", "asset_sizes.png", "asset_howitworks.png")


def _known_styles():
    return [p.stem for p in (ROOT / "templates").glob("*.json")]


def _split_slug(slug: str):
    """Split '<name>_<style>' into (name, style) using the known style names."""
    best = ""
    for s in _known_styles():
        if slug.endswith("_" + s) and len(s) > len(best):
            best = s
    if best:
        return slug[: -(len(best) + 1)].replace("_", " ").title(), best
    name, _, style = slug.rpartition("_")
    return (name or slug).replace("_", " ").title(), style


def _meaning(name: str) -> str:
    db_path = ROOT / "data" / "names_db.json"
    if not db_path.exists():
        return ""
    entry = json.loads(db_path.read_text(encoding="utf-8")).get(render.slugify(name))
    return entry.get("meaning", "") if entry and entry.get("verified") else ""


def gather_assets(folder: Path, slug: str):
    """(images, files): images = mockup + pins + print preview; files = the
    digital downloads (the ratio pack if present, else the print files)."""
    images = []
    for i in (1, 2, 3):                                  # real-photo frame mockups
        m = folder / f"{slug}_mock{i}.jpg"
        if m.exists():
            images.append(m)
    if not images and (folder / f"{slug}_mockup.png").exists():   # procedural fallback
        images.append(folder / f"{slug}_mockup.png")
    if (folder / f"{slug}_print.png").exists():          # the flat artwork
        images.append(folder / f"{slug}_print.png")
    for a in LISTING_ASSETS:                             # shared info cards
        p = ROOT / "assets" / "listing" / a
        if p.exists():
            images.append(p)

    files = [folder / f"{slug}_{t}.pdf" for t in SIZE_TAGS if (folder / f"{slug}_{t}.pdf").exists()]
    if not files:
        files = [folder / f"{slug}_print.{e}" for e in ("pdf", "png") if (folder / f"{slug}_print.{e}").exists()]
    return images[:10], files[:5]


def process_one(folder: Path, defaults: dict, live: bool):
    slug = folder.name
    name, style = _split_slug(slug)
    meta = etsy_meta.build_meta(name, style or "print", defaults, _meaning(name))
    images, files = gather_assets(folder, slug)

    print(f"\n=== {slug} ===")
    print(f"  title    : {meta['title']}")
    print(f"  price    : {meta['price']} {meta['currency_code']} | qty {defaults.get('quantity', 999)} "
          f"| type {defaults.get('type', 'download')} | taxonomy {defaults.get('taxonomy_id', '(unset)')}")
    print(f"  who/when : {defaults.get('who_made', 'i_did')} / {defaults.get('when_made', 'made_to_order')}")
    print(f"  tags ({len(meta['tags'])}): {', '.join(meta['tags'])}")
    print(f"  images ({len(images)}): {', '.join(p.name for p in images) or '(none)'}")
    print(f"  files  ({len(files)}): {', '.join(p.name for p in files) or '(none)'}")
    for f in files:
        mb = f.stat().st_size / 1e6
        if mb > 20:
            print(f"  ! WARNING: {f.name} is {mb:.1f} MB (> Etsy's 20 MB digital-file limit)")

    if not live:
        print("  [dry-run] no API call")
        return
    if not files:
        print("  ! skipped: a download listing needs >=1 digital file")
        return
    client = etsy_api.EtsyClient()
    res = client.create_draft_listing(meta, defaults)
    lid = res.get("listing_id") or (res.get("results") or [{}])[0].get("listing_id")
    if meta.get("is_personalizable", defaults.get("is_personalizable")):
        client.set_personalization(
            lid, defaults.get("personalization_instructions", ""),
            required=defaults.get("personalization_is_required", True),
            max_chars=defaults.get("personalization_char_count_max", 256))
    for i, f in enumerate(files, 1):
        client.upload_listing_file(lid, f, rank=i)
    for i, im in enumerate(images, 1):
        client.upload_listing_image(lid, im, rank=i)
    print(f"  + created DRAFT listing_id {lid} — review & publish in Etsy Shop Manager")


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Create DRAFT Etsy digital listings (dry-run by default; never publishes).")
    ap.add_argument("path", help="a design folder, or a parent directory of design folders")
    ap.add_argument("--live", action="store_true", help="actually create drafts (default: dry-run / preview)")
    args = ap.parse_args(argv)

    try:
        defaults = etsy_api.load_secrets().get("listing", {})
    except etsy_api.EtsyError as e:
        if args.live:
            print(f"ERROR: {e}")
            return 1
        defaults = {}   # dry-run can preview without credentials

    if args.live and not defaults.get("taxonomy_id"):
        print("ERROR: set listing.taxonomy_id in etsy_secrets.json before --live "
              "(find it via GET /v3/application/seller-taxonomy/nodes).")
        return 1

    path = Path(args.path)
    if (path / f"{path.name}_print.png").exists():
        folders = [path]
    else:
        folders = sorted(p for p in path.iterdir()
                         if p.is_dir() and (p / f"{p.name}_print.png").exists())
    if not folders:
        print(f"No design folders with a *_print.png found at {path}")
        return 1

    print("LIVE — creating DRAFTS" if args.live else "DRY-RUN — no API calls (add --live to create drafts)")
    for f in folders:
        process_one(f, defaults, args.live)
    if not args.live:
        print("\nDry-run complete. After `python etsy_auth.py`, re-run with --live to create the drafts.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
