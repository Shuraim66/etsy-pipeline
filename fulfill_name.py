#!/usr/bin/env python3
"""
fulfill_name.py — turn ONE personalized order into a delivery-ready print pack.

Given the design (a template, or a listing key + colourway) and the buyer's
details, renders the artwork in all 5 print ratios (PDF + PNG) into one folder,
ready to zip and send. Works for the new name-print listings AND the existing
ones (both render from templates via render.py).

HARD RULE — never generates Arabic: the Arabic must be supplied with --arabic, or
come from the operator-verified names_db. If neither is available it refuses to
render (source/verify the Arabic first, or send it to the buyer to approve).

Examples:
  # name in the verified db -> Arabic + meaning fill automatically
  python fulfill_name.py --template nm_botanical_block_terracotta --name Maryam

  # new listing by key + colourway, custom Arabic pasted by the buyer
  python fulfill_name.py --listing amara --colourway olive --name Zayd --arabic "زيد"

  # DOB design
  python fulfill_name.py --template nw_celestial_navy --name Yusuf --arabic "يوسف" --date "15.05.2024"

  # 2-panel verse set renders both panels
  python fulfill_name.py --listing verse_set --colourway navy --name Ibrahim --arabic "إبراهيم"
"""
from __future__ import annotations
import argparse
import json
import shutil
import sys
from pathlib import Path

from PIL import Image
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.utils import ImageReader

import render
import listings


def leanify(png_path: Path, w: int, h: int):
    """Replace render's huge lossless PNG+PDF with delivery-friendly files:
    a high-quality JPG (paper grain compresses well as JPEG) and a JPG-wrapped
    print-ready PDF at 300 DPI physical size. Returns (jpg, pdf)."""
    png_path = Path(png_path)
    im = Image.open(png_path).convert("RGB")
    jpg = png_path.with_suffix(".jpg")
    im.save(jpg, quality=92, optimize=True, progressive=True)
    pdf = png_path.with_suffix(".pdf")
    page = (w / 300.0 * 72.0, h / 300.0 * 72.0)              # inches -> points @300 DPI
    c = pdfcanvas.Canvas(str(pdf), pagesize=page)
    c.drawImage(ImageReader(str(jpg)), 0, 0, width=page[0], height=page[1])
    c.showPage(); c.save()
    png_path.unlink(missing_ok=True)                          # drop the bulky PNG
    return jpg, pdf

ROOT = Path(__file__).resolve().parent
DB = json.loads((ROOT / "data/names_db.json").read_text())

# print-ready ratios (portrait), long side 5400 px = 18" @ 300 DPI; prints scale down cleanly
RATIOS = {
    "iso_A":     (3820, 5400),   # ISO A (A5..A2)
    "ratio_2x3": (3600, 5400),   # 4x6 .. 20x30"
    "ratio_3x4": (4050, 5400),   # 6x8 .. 18x24"
    "ratio_4x5": (4320, 5400),   # 8x10 .. 16x20"
    "ratio_5x7": (3857, 5400),   # 5x7 .. 10x14"
}


def resolve_templates(args):
    """Return the list of template stems to render (2 for a verse set)."""
    if args.template:
        if not (ROOT / "templates" / f"{args.template}.json").exists():
            sys.exit(f"ERROR: template '{args.template}' not found in templates/")
        return [args.template]
    L = next((x for x in listings.all_listings() if x["key"] == args.listing), None)
    if not L:
        sys.exit(f"ERROR: unknown listing '{args.listing}'. Use --template, or a valid --listing key.")
    if not args.colourway:
        opts = ", ".join(cw for cw, _ in L["colourways"])
        sys.exit(f"ERROR: --colourway required for listing '{args.listing}'. Options: {opts}")
    stem = next((s for cw, s in L["colourways"] if cw == args.colourway), None)
    if not stem:
        opts = ", ".join(cw for cw, _ in L["colourways"])
        sys.exit(f"ERROR: colourway '{args.colourway}' not in '{args.listing}'. Options: {opts}")
    return [stem + "_A", stem + "_B"] if L["is_set"] else [stem]


def build_row(args):
    """Assemble the render row and ENFORCE the verified-Arabic rule."""
    row = {"name_latin": args.name, "name_arabic": args.arabic or "",
           "meaning": args.meaning or "", "date": args.date or ""}
    entry = DB.get(render.slugify(args.name))
    verified = entry if (entry and entry.get("verified")) else None
    if not row["name_arabic"]:
        if verified:
            row["name_arabic"] = verified["name_arabic"]
            print(f"  Arabic: auto from verified db ({row['name_arabic']})")
        else:
            sys.exit(f"ERROR: no verified Arabic for '{args.name}'. Pass --arabic \"…\" with the "
                     f"operator-verified spelling. Arabic is NEVER auto-generated.")
    if not row["meaning"] and verified:
        row["meaning"] = verified.get("meaning", "")
    if args.dua:
        row["dua_arabic"] = args.dua
    if args.dua_translation:
        row["dua_translation"] = args.dua_translation
    return row


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render one order's 5-ratio print pack (PDF+PNG).")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--template", help="template stem, e.g. nw_amara_olive / nm_botanical_block_sage")
    g.add_argument("--listing", help="new-listing key, e.g. amara (use with --colourway)")
    ap.add_argument("--colourway", help="colourway for --listing, e.g. olive")
    ap.add_argument("--name", required=True, help="buyer's name in Latin, e.g. Zayd")
    ap.add_argument("--arabic", help="verified Arabic Unicode (required unless the name is in names_db)")
    ap.add_argument("--meaning", help="override meaning (else auto from db for db names)")
    ap.add_argument("--date", help="date to show on DOB designs, e.g. 15.05.2024")
    ap.add_argument("--dua", help="override dua Arabic (verse designs; else verified default)")
    ap.add_argument("--dua-translation", dest="dua_translation", help="override dua translation")
    ap.add_argument("--out", default=str(ROOT / "fulfilled"), help="output root dir")
    ap.add_argument("--zip", action="store_true", help="also make a .zip of the pack per design")
    args = ap.parse_args(argv)

    templates = resolve_templates(args)
    print(f"Order: {args.name}  |  designs: {', '.join(templates)}")
    row = build_row(args)
    outroot = Path(args.out)

    packs = []
    for stem in templates:
        slug = f"{render.slugify(args.name)}_{stem}"
        folder = outroot / slug
        made = []
        for tag, (w, h) in RATIOS.items():
            r = render.render(row, stem, out_dir=outroot, canvas=(w, h), tag=tag)
            jpg, pdf = leanify(r["png"], w, h)                # PNG+PDF -> lean JPG+PDF
            made += [jpg, pdf]
        # warn on empty content that the design expects
        style = render.resolve_style(stem)
        block_ids = _block_ids(style)
        if "meaning" in block_ids and not row["meaning"]:
            print(f"  ! WARNING: '{stem}' shows a meaning but none was provided/derived")
        if "date" in block_ids and not row["date"]:
            print(f"  ! WARNING: '{stem}' shows a date but --date was not provided")
        pack_dir = folder
        print(f"  ✓ {stem}: 5 ratios (PDF+PNG) -> {pack_dir}")
        if args.zip:
            z = shutil.make_archive(str(outroot / slug), "zip", root_dir=pack_dir)
            print(f"    zip -> {z}")
            packs.append(z)
        else:
            packs.append(str(pack_dir))

    print("\nDELIVER:")
    for p in packs:
        print(" ", p)


def _block_ids(style):
    ids = set()
    blocks = []
    if "flow" in style:
        blocks = style["flow"]["blocks"]
    for z in style.get("zones", []):
        blocks += z["blocks"]
    for b in blocks:
        ids.add(b.get("id", "")); ids.add(b.get("field", ""))
    return ids


if __name__ == "__main__":
    main()
