#!/usr/bin/env python3
"""
package_art.py - packaging pass for RASTER art lines (SD originals + public-
domain masters). Brings each piece's folder up to the draft-ready layout used
by the Islamic listings:

  <slug>_print.png/pdf      (already present - A3 master, 3508x4961)
  <slug>_iso_A.png/pdf      (4242x6000 - same 1:sqrt2 aspect, pure resize)
  <slug>_ratio_2x3.png/pdf  (4000x6000 - centre crop)
  <slug>_ratio_3x4.png/pdf  (4500x6000 - centre crop)
  <slug>_ratio_4x5.png/pdf  (4800x6000 - centre crop)
  <slug>_ratio_5x7.png/pdf  (4286x6000 - centre crop)
  <slug>_proof.png          (watermarked low-res)
  <slug>_mock1..3.jpg       (real-photo frame mockups)
  SIZES.txt

Unlike the JSON-template line (sizes.py re-renders and text reflows), raster
art is centre-cropped per ratio. iso_A matches the master's aspect exactly, so
nothing is lost there; the worst crop (4x5) trims ~12% off the height.
"""
from __future__ import annotations

import gc
import sys
from pathlib import Path

from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdfcanvas

import mockup_photo
import proof as proofmod

ROOT = Path(__file__).resolve().parent

RATIOS = [
    ("iso_A",     4242, 6000, "A3 / A4 / A5 (ISO A)"),
    ("ratio_2x3", 4000, 6000, "4x6, 8x12, 12x18, 16x24, 20x30, 24x36"),
    ("ratio_3x4", 4500, 6000, "6x8, 9x12, 12x16, 15x20, 18x24"),
    ("ratio_4x5", 4800, 6000, "8x10, 11x14, 16x20"),
    ("ratio_5x7", 4286, 6000, "5x7, 10x14"),
]


def _center_crop_resize(img: Image.Image, w: int, h: int) -> Image.Image:
    target = w / h
    iw, ih = img.size
    if iw / ih > target:
        nw = int(ih * target)
        img = img.crop(((iw - nw) // 2, 0, (iw - nw) // 2 + nw, ih))
    else:
        nh = int(iw / target)
        img = img.crop((0, (ih - nh) // 2, iw, (ih - nh) // 2 + nh))
    return img.resize((w, h), Image.LANCZOS)


def _save_pair(img: Image.Image, base: Path):
    img.save(base.with_suffix(".png"), "PNG")
    _save_pdf_jpeg(img, base.with_suffix(".pdf"))


def _save_pdf_jpeg(img: Image.Image, pdf_path: Path, quality: int = 92):
    """PDF with JPEG-compressed image data (photographic art in a lossless PDF
    blows past Etsy's 20 MB digital-file cap; q92 JPEG is print-transparent)."""
    import io
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality, subsampling=0)
    buf.seek(0)
    page = (img.width / 300.0 * 72.0, img.height / 300.0 * 72.0)
    c = pdfcanvas.Canvas(str(pdf_path), pagesize=page)
    c.drawImage(ImageReader(buf), 0, 0, width=page[0], height=page[1])
    c.showPage()
    c.save()


def package_folder(folder: Path) -> bool:
    """Package one piece folder containing <slug>_print.png. Returns True if done."""
    prints = list(folder.glob("*_print.png"))
    if not prints:
        return False
    print_png = prints[0]
    slug = print_png.name[:-len("_print.png")]

    master = Image.open(print_png).convert("RGB")

    for tag, w, h, _ in RATIOS:
        out_base = folder / f"{slug}_{tag}"
        if not out_base.with_suffix(".png").exists():
            _save_pair(_center_crop_resize(master, w, h), out_base)

    proof_path = folder / f"{slug}_proof.png"
    if not proof_path.exists():
        proofmod.make_proof(print_png, proof_path)

    if not (folder / f"{slug}_mock1.jpg").exists():
        mockup_photo.generate_for(print_png, folder, slug)

    guide = "Each file is a print ratio; print it at any size in its family:\n\n"
    for tag, w, h, covers in RATIOS:
        guide += f"  {tag:11} ({w}x{h}px, 300 DPI)  ->  {covers}\n"
    (folder / "SIZES.txt").write_text(guide, encoding="utf-8")

    del master
    gc.collect()
    return True


def main(roots: list[str]):
    done = failed = 0
    for root in roots:
        rootp = ROOT / root if not Path(root).is_absolute() else Path(root)
        for folder in sorted(p for p in rootp.iterdir() if p.is_dir()):
            try:
                if package_folder(folder):
                    done += 1
                    print(f"ok   {folder.name}", flush=True)
            except Exception as e:
                failed += 1
                print(f"FAIL {folder.name}: {e}", flush=True)
    print(f"\npackaged {done} pieces, {failed} failures")


if __name__ == "__main__":
    roots = sys.argv[1:] or ["output/staging_sd", "output/staging_pd_art"]
    main(roots)
