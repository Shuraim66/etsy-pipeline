#!/usr/bin/env python3
"""
canva_family.py - fulfilment notes + downstream packaging for the PREMIUM
personalized family/couple line (the $17.99-24.99 made-to-order tier).

WHY CANVA: six rounds of Pillow-composed layouts were rejected as "too basic".
Canva produces genuine ornamental design (gold Islamic lattice corners, real
display typography, paper texture). This file does NOT design anything - it
packages what Canva exports and records the per-order procedure.

MASTER DESIGNS (Canva, owner account):
  DAHQ-NwAfZM   family master  - cream ground, navy serif, gold lattice corners
  DAHQ-KB8o4Y   emerald variant example (Siddiqui, Birmingham, est. 2019)
  DAHQ-Pf50-g   nikah/couple master - two names + Hijri & Gregorian dates
                (known issue: names sit high, lower third empty - fix before use)

PER-ORDER PROCEDURE (about a minute per order):
  1. copy-design from the relevant master
  2. read-design with open_transaction:true -> locator_ids
  3. replace_text on: surname, EST. line, city line
     (couple: name1, name2, hijri date, gregorian date)
  4. optional format_text colour swap for the colourway the buyer picked:
        cream/navy #253138 (default) | emerald #12362E
        charcoal #2B2620 | terracotta #8C3F23
  5. commit, then export-design png (width 3508 = A3 @ 300 DPI) + pdf
  6. run package_order() below -> ratio variants + mockups + zip-ready folder

ARABIC: if the buyer wants their name in Arabic they must supply the exact
string; it is placed verbatim. Never generated here or in Canva.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdfcanvas

import mockup_photo

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "staging_canva"
W0, H0 = 3508, 4961

MASTERS = {
    "family": "DAHQ-NwAfZM",
    "family_emerald": "DAHQ-KB8o4Y",
    "nikah": "DAHQ-Pf50-g",
}

COLOURWAYS = {
    "cream_navy": "#253138",
    "emerald": "#12362E",
    "charcoal": "#2B2620",
    "terracotta": "#8C3F23",
}

RATIOS = [
    ("iso_A", 4242, 6000, "A3 / A4 / A5 (ISO A)"),
    ("ratio_2x3", 4000, 6000, "4x6, 8x12, 12x18, 16x24, 20x30, 24x36"),
    ("ratio_3x4", 4500, 6000, "6x8, 9x12, 12x16, 15x20, 18x24"),
    ("ratio_4x5", 4800, 6000, "8x10, 11x14, 16x20"),
    ("ratio_5x7", 4286, 6000, "5x7, 10x14"),
]


def _crop_resize(img: Image.Image, w: int, h: int) -> Image.Image:
    target = w / h
    iw, ih = img.size
    if iw / ih > target:
        nw = int(ih * target)
        img = img.crop(((iw - nw) // 2, 0, (iw - nw) // 2 + nw, ih))
    else:
        nh = int(iw / target)
        img = img.crop((0, (ih - nh) // 2, iw, (ih - nh) // 2 + nh))
    return img.resize((w, h), Image.LANCZOS)


def _pdf(img: Image.Image, path: Path, quality: int = 92):
    import io
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality, subsampling=0)
    buf.seek(0)
    page = (img.width / 300.0 * 72.0, img.height / 300.0 * 72.0)
    c = pdfcanvas.Canvas(str(path), pagesize=page)
    c.drawImage(ImageReader(buf), 0, 0, width=page[0], height=page[1])
    c.showPage()
    c.save()


def package_order(canva_png: Path, slug: str, with_mockups: bool = True) -> Path:
    """Take a Canva export and produce the full deliverable folder."""
    folder = OUT / slug
    folder.mkdir(parents=True, exist_ok=True)

    master = Image.open(canva_png).convert("RGB")
    if master.width < W0:
        master = master.resize((W0, int(master.height * W0 / master.width)), Image.LANCZOS)

    print_img = _crop_resize(master, W0, H0)
    print_png = folder / f"{slug}_print.png"
    print_img.save(print_png, "PNG")
    _pdf(print_img, folder / f"{slug}_print.pdf")

    for tag, w, h, _covers in RATIOS:
        img = _crop_resize(master, w, h)
        img.save(folder / f"{slug}_{tag}.png", "PNG")
        _pdf(img, folder / f"{slug}_{tag}.pdf")

    guide = "Each file is a print ratio; print it at any size in its family:\n\n"
    for tag, w, h, covers in RATIOS:
        guide += f"  {tag:11} ({w}x{h}px, 300 DPI)  ->  {covers}\n"
    (folder / "SIZES.txt").write_text(guide, encoding="utf-8")

    if with_mockups:
        import json
        openings = json.loads((ROOT / "assets/mockups/pexels/OPENINGS.json").read_text())
        for pid, quad in openings.items():
            mockup_photo.OPENINGS[f"px_{pid}"] = [tuple(p) for p in quad]
        for i, key in enumerate(("px_12486418", "px_8148588", "px_20553171"), 1):
            mockup_photo.place(print_png, key, folder / f"{slug}_scene{i}.jpg")
        mockup_photo.generate_for(print_png, folder, slug)

    return folder


if __name__ == "__main__":
    src = OUT / "family_emerald_siddiqui.png"
    if src.exists():
        f = package_order(src, "family_emerald_siddiqui")
        print("packaged ->", f)
        for p in sorted(f.iterdir()):
            print("   ", p.name)
    else:
        print("missing", src)
