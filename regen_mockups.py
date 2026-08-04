#!/usr/bin/env python3
"""
regen_mockups.py - shop-wide mockup regeneration with the approved real-photo
plate set:

  px_8148588  greige wall + black frame + pendant  (moody editorial)
  px_8490186  white wall + reading nook            (bright airy)
  px_8490172  shelf + eucalyptus vase              (styled shelf)
  px_12486080 bedroom drape                        (soft intimate)
  + the 3 original frames via mockup_photo (m1 black hung, m2 gold lean,
    m3 brass flatlay)

Per piece: writes <slug>_scene1..4.jpg (pexels plates) alongside the existing
<slug>_mock1..3.jpg. Lead-image guidance: scene1 (greige/black) for dark art,
nook for light art - recorded in LEADS.txt per staging dir.

Dark/light routing mirrors mockup_photo: dark prints avoid the dark greige
plate as lead, light prints lead with it (contrast wins thumbnails).
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

import mockup_photo

ROOT = Path(__file__).resolve().parent
OPENINGS = json.loads((ROOT / "assets/mockups/pexels/OPENINGS.json").read_text())

# register pexels plates with mockup_photo's warp machinery
for pid, quad in OPENINGS.items():
    # registry stores true 4-corner quads (tilt-aware)
    mockup_photo.OPENINGS[f"px_{pid}"] = [tuple(pt) for pt in quad]

# 12486417 = linen drape + dark frame (boho, warm) | 8101038 = sunlit shadow
# 20553171 = scandi sideboard | originals: greige/nook/shelf/bedroom
PLATE_ORDER_LIGHT = ["px_12486418", "px_8148588", "px_12486417", "px_20553171",
                     "px_8490172", "px_12486080"]
PLATE_ORDER_DARK = ["px_8490186", "px_12486417", "px_20553171", "px_12486418",
                    "px_8490172", "px_12486080"]


def regen_folder(folder: Path) -> bool:
    prints = list(folder.glob("*_print.png"))
    if not prints:
        return False
    print_png = prints[0]
    slug = print_png.name[:-len("_print.png")]
    order = PLATE_ORDER_DARK if mockup_photo._is_dark(print_png) else PLATE_ORDER_LIGHT
    for i, key in enumerate(order[:4], 1):
        out = folder / f"{slug}_scene{i}.jpg"
        mockup_photo.place(print_png, key, out)   # overwrite: plate set changed
    return True


if __name__ == "__main__":
    roots = [ROOT / "output" / "staging_sd", ROOT / "output" / "staging_pd_art"]
    n = 0
    for root in roots:
        if not root.exists():
            continue
        for folder in sorted(p for p in root.iterdir() if p.is_dir()):
            try:
                if regen_folder(folder):
                    n += 1
                    print(f"ok {folder.name}", flush=True)
            except Exception as e:
                print(f"FAIL {folder.name}: {e}", flush=True)
    print(f"\n{n} pieces got scene mockups")
