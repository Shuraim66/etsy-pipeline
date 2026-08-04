#!/usr/bin/env python3
"""
scene_set.py - build the STANDARD listing photo set for a print.

The shop was shipping the same two or three plates on every listing while ten
were prepared, so every product looked like it lived in the same room. This
module fixes the routing: one tight square lead plus a spread of real rooms.

Standard set (8 photos, Etsy allows 10):
  1 lead      tight square crop, art dominates at phone-thumbnail size
  2 bedroom   frame over bedding, soft drape
  3 nursery   frame over kids' chairs, pale wall        <- name prints live here
  4 living    frame over console with plant
  5 office    frame over a wooden desk, plant + books
  6 closeup   ornate frame leaning on a desk, shallow depth
  7 detail    100% crop of the artwork itself (texture / line quality)
  8 sizes     the ratio guide (built elsewhere, appended by the caller)

Plate aspect ratios all sit between 0.70 and 0.73 against our 0.707 print, so
the perspective warp stretches by under 3% - no visible distortion.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

import make_leads
import mockup_photo

ROOT = Path(__file__).resolve().parent
OPENINGS = json.loads((ROOT / "assets/mockups/pexels/OPENINGS.json").read_text())

for _pid, _quad in OPENINGS.items():
    mockup_photo.OPENINGS[f"px_{_pid}"] = [tuple(_pt) for _pt in _quad]

ROOMS = {
    "bedroom": "px_12486080",   # black frame + mat, bedding and drape
    "nursery": "px_8490259",    # black frame over two white kids' chairs
    "living":  "px_8490172",    # thin frame over console with greenery
    "office":  "px_8490187",    # black frame over a wooden desk
    "closeup": "px_8490229",    # heavy black frame leaning, pencils, plant
    "hall":    "px_20553171",   # sage wall, sideboard, coat stand
    "minimal": "px_8148588",    # taupe wall, pendant lamp
    "linen":   "px_12486418",   # linen flatlay with dried bloom
    "nook":    "px_8490186",    # white nook, plants and throw
    "flatlay": "px_12486417",   # linen flatlay, alternate crop
}

# Which rooms suit which line. Nursery is the point of the name prints (their
# titles literally say "Islamic Nursery Decor"); fine-art reproductions read
# better in a study than a kids' room.
PRESETS = {
    "name":  ["nursery", "bedroom", "living", "office", "closeup"],
    # no linen/flatlay here: the lead crop is already cut from the linen plate,
    # so including it makes photos 1 and 7 look like the same shot twice.
    "art":   ["living", "office", "bedroom", "closeup", "hall"],
    "geo":   ["living", "office", "hall", "bedroom", "closeup"],
    "sacred": ["living", "bedroom", "office", "hall", "closeup"],
}


def detail_crop(print_png: Path, out: Path, size: int = 2000) -> Path:
    """100% pixel crop from the centre of the art - shows real texture."""
    img = Image.open(print_png).convert("RGB")
    side = min(size, img.width, img.height)
    cx, cy = img.width // 2, int(img.height * 0.42)
    left = max(0, min(img.width - side, cx - side // 2))
    top = max(0, min(img.height - side, cy - side // 2))
    crop = img.crop((left, top, left + side, top + side))
    if crop.size != (size, size):
        crop = crop.resize((size, size), Image.LANCZOS)
    crop.save(out, "JPEG", quality=92)
    return out


def build(print_png: Path, folder: Path, slug: str, preset: str = "art",
          with_detail: bool = True) -> list[Path]:
    """Write the full photo set; returns paths in listing order."""
    folder.mkdir(parents=True, exist_ok=True)
    out = [make_leads.lead_for(print_png, folder, slug)]
    for room in PRESETS[preset]:
        dst = folder / f"{slug}_scene_{room}.jpg"
        mockup_photo.place(print_png, ROOMS[room], dst)
        out.append(dst)
    if with_detail:
        out.append(detail_crop(print_png, folder / f"{slug}_detail.jpg"))
    return out


if __name__ == "__main__":
    import sys
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        ROOT / "output/staging_geo/isfahan_geo_shamsa/isfahan_geo_shamsa_print.png")
    preset = sys.argv[2] if len(sys.argv) > 2 else "geo"
    slug = src.name[:-len("_print.png")]
    paths = build(src, src.parent, slug, preset=preset)
    for p in paths:
        print(" ", p.name)
