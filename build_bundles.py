#!/usr/bin/env python3
"""
build_bundles.py - assemble SET/BUNDLE products from finished pieces.

Why: single $3-tier digital files are a race to the bottom (see the business
strategy memo). A curated set of 3 at $12.99-16.99, or a 6-piece Islamic set
at $12-15, multiplies AOV using art that already exists.

Per bundle it writes into output/staging_bundles/<slug>/:
  <slug>_lead.jpg        square gallery-wall preview (the thumbnail)
  <slug>_grid.jpg        flat trio/six-up of the artworks
  <slug>_scene1..2.jpg   each piece shown framed in a real interior
  <slug>_file1..N.pdf    the print files (A-series), <=5 per Etsy listing
  SIZES.txt / CONTENTS.txt

Etsy caps digital listings at 5 files, so a 6-piece set ships as
5 PDFs where the last one is a combined multi-page document.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdfcanvas

import mockup_photo

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "staging_bundles"
SD = ROOT / "output" / "staging_sd"
PD = ROOT / "output" / "staging_pd_art"
FONT = str(ROOT / "assets" / "fonts" / "EBGaramond[wght].ttf")

# register the verified pexels plates
OPENINGS = json.loads((ROOT / "assets/mockups/pexels/OPENINGS.json").read_text())
for _pid, _quad in OPENINGS.items():
    mockup_photo.OPENINGS[f"px_{_pid}"] = [tuple(p) for p in _quad]

LIGHT_PLATE = "px_12486418"   # linen + strawflower
DARK_PLATE = "px_8490186"     # white nook

# One plate per tile in the gallery lead, so no prop repeats across the trio.
# CLEAN-WALL PLATES ONLY: the gallery lead crops tight to each frame, and the
# linen flatlays have a dried strawflower resting against the moulding, which
# survives the crop as an unexplained orange blob beside the artwork.
LEAD_PLATES = ["px_8148588", "px_20553171", "px_8490187", "px_8490259"]

BUNDLES = [
    {
        "slug": "set_japandi_3",
        "title": "Japandi Wall Art Set of 3",
        "pieces": [(SD, "koi_inpaint2_8"), (SD, "mountains_404"), (SD, "goldjap_v964")],
        "price": 16.99,
        "blurb": "A calm japandi trio — circling koi, misty ink-wash mountains, "
                 "and a soft gold-veined abstract.",
    },
    {
        "slug": "set_coastal_3",
        "title": "Coastal Wall Art Set of 3",
        "pieces": [(SD, "ocean_wave_15"), (SD, "coast_202"), (SD, "celestial_20")],
        "price": 16.99,
        "blurb": "Three coastal pieces — a cresting turquoise wave, an abstract "
                 "gold-leaf shoreline, and a crescent moon over midnight water.",
    },
    {
        "slug": "set_botanical_3",
        "title": "Botanical Wall Art Set of 3",
        "pieces": [(SD, "botanical_101"), (SD, "tropical_12"), (SD, "lavender_16")],
        "price": 16.99,
        "blurb": "Watercolor eucalyptus, emerald monstera, and a Provence "
                 "lavender field at sunset.",
    },
    {
        "slug": "set_moody_florals_3",
        "title": "Moody Floral Wall Art Set of 3",
        "pieces": [(SD, "moody_floral_303"), (SD, "brush_floral_51"),
                   (SD, "brush_stilllife_regen_94")],
        "price": 16.99,
        "blurb": "Dark romantic florals — dusty peonies, impasto wild roses, "
                 "and a candlelit peach still life.",
    },
    {
        "slug": "set_masters_3",
        "title": "Vintage Fine Art Set of 3",
        "pieces": [(PD, "gogh_wheat_field_with_cypresses"),
                   (PD, "renoir_in_the_meadow"),
                   (PD, "c_zanne_still_life_with_apples_and_a_pot_of_primroses")],
        "price": 12.99,
        "blurb": "Three public-domain masterpieces restored for print — Van Gogh, "
                 "Renoir and Cezanne.",
    },
]


def piece_print(root: Path, slug: str) -> Path:
    return root / slug / f"{slug}_print.png"


def grid_image(paths, out_path, cols=3, pad_frac=0.05, bg=(247, 244, 238)):
    """Flat side-by-side of the artworks on a warm paper ground."""
    th = 1600
    ims = []
    for p in paths:
        im = Image.open(p).convert("RGB")
        w = int(im.width * th / im.height)
        ims.append(im.resize((w, th), Image.LANCZOS))
    pad = int(th * pad_frac)
    rows = (len(ims) + cols - 1) // cols
    tw = max(i.width for i in ims)
    W = cols * tw + pad * (cols + 1)
    H = rows * th + pad * (rows + 1)
    sheet = Image.new("RGB", (W, H), bg)
    for i, im in enumerate(ims):
        r, c = divmod(i, cols)
        x = pad + c * (tw + pad) + (tw - im.width) // 2
        y = pad + r * (th + pad)
        # thin shadow so the prints read as paper
        sheet.paste(im, (x, y))
    sheet.save(out_path, quality=93)
    return out_path


def gallery_lead(paths, out_path, size=2000):
    """Square gallery-wall lead: pieces framed on one wall, thumbnail-optimised."""
    n = len(paths)
    tiles = []
    for idx, p in enumerate(paths):
        plate_key = LEAD_PLATES[idx % len(LEAD_PLATES)]
        tmp = out_path.parent / f"_tmp_{Path(p).stem}.jpg"
        mockup_photo.place(p, plate_key, tmp)
        im = Image.open(tmp)
        # crop tight around the frame using the plate quad
        quad = OPENINGS[plate_key.replace("px_", "")]
        xs = [q[0] for q in quad]; ys = [q[1] for q in quad]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
        fw, fh = x1 - x0, y1 - y0
        # enough to keep the whole moulding: cropping to the opening alone left
        # the art looking unframed, with a hairline where the frame should be
        padx, pady = fw * 0.10, fh * 0.075
        crop = im.crop((max(0, int(x0 - padx)), max(0, int(y0 - pady)),
                        min(im.width, int(x1 + padx)), min(im.height, int(y1 + pady))))
        tiles.append(crop)
        tmp.unlink()

    hh = int(size * 0.86)
    scaled = [t.resize((int(t.width * hh / t.height), hh), Image.LANCZOS) for t in tiles]
    gap = int(size * 0.014)
    total_w = sum(s.width for s in scaled) + gap * (n - 1)
    scale = min(1.0, (size - int(size * 0.06)) / total_w)
    if scale < 1.0:
        scaled = [s.resize((int(s.width * scale), int(s.height * scale)), Image.LANCZOS)
                  for s in scaled]
        total_w = sum(s.width for s in scaled) + gap * (n - 1)

    # Stagger the frames like a real gallery wall. Three portrait frames side by
    # side are width-limited, so a flat row leaves dead bands top and bottom;
    # alternating the hang height puts that space to work.
    stagger = int(scaled[0].height * 0.11)
    offsets = [(-1 if i % 2 == 0 else 1) * stagger // 2 for i in range(n)]
    span = scaled[0].height + stagger

    sheet = Image.new("RGB", (size, size), (243, 239, 232))
    x = (size - total_w) // 2
    y0 = (size - span) // 2 + stagger // 2
    for s, dy in zip(scaled, offsets):
        sheet.paste(s, (x, y0 + dy))
        x += s.width + gap
    sheet.save(out_path, quality=93)
    return out_path


def combined_pdf(pdf_paths, out_path):
    """One multi-page PDF holding several prints (Etsy caps files at 5)."""
    from PIL import Image as I
    pages = []
    for p in pdf_paths:
        png = Path(str(p).replace(".pdf", ".png"))
        if png.exists():
            pages.append(png)
    if not pages:
        return None
    c = None
    for png in pages:
        im = I.open(png).convert("RGB")
        page = (im.width / 300.0 * 72.0, im.height / 300.0 * 72.0)
        if c is None:
            c = pdfcanvas.Canvas(str(out_path), pagesize=page)
        else:
            c.setPageSize(page)
        c.drawImage(ImageReader(im), 0, 0, width=page[0], height=page[1])
        c.showPage()
    c.save()
    return out_path


def build(bundle):
    slug = bundle["slug"]
    folder = OUT / slug
    folder.mkdir(parents=True, exist_ok=True)
    prints = [piece_print(root, s) for root, s in bundle["pieces"]]
    missing = [p for p in prints if not p.exists()]
    if missing:
        print(f"  SKIP {slug}: missing {[m.name for m in missing]}")
        return None

    grid_image(prints, folder / f"{slug}_grid.jpg", cols=min(3, len(prints)))
    gallery_lead(prints, folder / f"{slug}_lead.jpg")

    # per-piece framed scenes (first two pieces, alternating plates)
    for i, p in enumerate(prints[:2], start=1):
        key = LIGHT_PLATE if i % 2 else DARK_PLATE
        mockup_photo.place(p, key, folder / f"{slug}_scene{i}.jpg")

    # files: one A-series PDF per piece (<=5); if more, last file combines rest
    src_pdfs = [Path(str(p).replace("_print.png", "_iso_A.pdf")) for p in prints]
    src_pdfs = [p if p.exists() else Path(str(p).replace("_iso_A.pdf", "_print.pdf"))
                for p in src_pdfs]
    out_files = []
    if len(src_pdfs) <= 5:
        for i, p in enumerate(src_pdfs, start=1):
            dst = folder / f"{slug}_file{i}.pdf"
            shutil.copy(p, dst)
            out_files.append(dst)
    else:
        for i, p in enumerate(src_pdfs[:4], start=1):
            dst = folder / f"{slug}_file{i}.pdf"
            shutil.copy(p, dst)
            out_files.append(dst)
        combined = combined_pdf([str(p).replace("_iso_A.pdf", "_print.pdf")
                                 for p in src_pdfs[4:]], folder / f"{slug}_file5.pdf")
        if combined:
            out_files.append(combined)

    names = ", ".join(s for _, s in bundle["pieces"])
    (folder / "CONTENTS.txt").write_text(
        f"{bundle['title']}  (${bundle['price']})\n\n{bundle['blurb']}\n\n"
        f"Pieces ({len(prints)}): {names}\n"
        f"Files: {len(out_files)} print-ready PDFs, 300 DPI, ISO A series\n",
        encoding="utf-8")
    print(f"  ok {slug}: {len(prints)} pieces, {len(out_files)} files")
    return folder


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    made = 0
    for b in BUNDLES:
        if build(b):
            made += 1
    print(f"\n{made}/{len(BUNDLES)} bundles built -> {OUT}")
