#!/usr/bin/env python3
"""
make_leads.py - build the LEAD listing image: a tight square crop of the
scene mockup centered on the framed art, so the artwork dominates at phone
thumbnail size (the actual purchase surface).

Uses the known opening quads, padded ~35% around the frame, clamped to the
plate. Writes <slug>_lead.jpg (2000x2000) per piece.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image

import mockup_photo

ROOT = Path(__file__).resolve().parent
OPENINGS = json.loads((ROOT / "assets/mockups/pexels/OPENINGS.json").read_text())

# register pexels plates with mockup_photo (same as regen_mockups.py)
for _pid, _quad in OPENINGS.items():
    mockup_photo.OPENINGS[f"px_{_pid}"] = [tuple(_pt) for _pt in _quad]

# Lead plates, rotated by a stable hash of the slug. A single lead plate makes
# the whole shop grid look like one photograph repeated 50 times, which was the
# complaint that started this; rotating means neighbouring search results never
# share a prop. Dark/light routing is kept so dark art always lands somewhere
# pale enough for the frame to read.
LEAD_LIGHT = ["12486418", "8148588", "12486080", "8490229",
              "20553171", "12486417", "8490172"]
LEAD_DARK = ["8490186", "8490259", "8490187", "20553171", "8490172"]

# frame chrome beyond the opening (fraction of opening size) to include
FRAME_PAD = 0.10
CONTEXT = 0.14           # tight: art must dominate at 170px phone thumbnail


def lead_for(print_png: Path, folder: Path, slug: str) -> Path:
    pool = LEAD_DARK if mockup_photo._is_dark(print_png) else LEAD_LIGHT
    pid = pool[int(hashlib.md5(slug.encode()).hexdigest(), 16) % len(pool)]
    quad = OPENINGS[pid]
    xs = [pt[0] for pt in quad]; ys = [pt[1] for pt in quad]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    fw, fh = x1 - x0, y1 - y0

    # crop the PLATE to the lead square FIRST, upscale if the opening is small,
    # THEN composite — so the art renders at full lead resolution (small-opening
    # plates like the white nook otherwise yield a soft ~250px artwork).
    plate = Image.open(mockup_photo.MOCKS / f"px_{pid}.jpg")
    pad_x = fw * (FRAME_PAD + CONTEXT)
    pad_y = fh * (FRAME_PAD + CONTEXT)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    side = max(fw + 2 * pad_x, fh + 2 * pad_y)
    left = max(0, min(plate.width - side, cx - side / 2))
    top = max(0, min(plate.height - side, cy - side / 2))
    side = min(side, plate.width - left, plate.height - top)
    crop = plate.crop((int(left), int(top), int(left + side), int(top + side)))

    scale = 2000 / crop.width
    crop = crop.resize((2000, 2000), Image.LANCZOS)
    # opening coords inside the crop, scaled
    q = [((x - left) * scale, (y - top) * scale) for x, y in quad]

    key = f"lead_{pid}_{slug}"
    tmp_plate = mockup_photo.MOCKS / f"{key}.jpg"
    crop.save(tmp_plate, quality=95)
    mockup_photo.OPENINGS[key] = [(int(px), int(py)) for px, py in q]
    out = folder / f"{slug}_lead.jpg"
    mockup_photo.place(print_png, key, out)
    tmp_plate.unlink()
    del mockup_photo.OPENINGS[key]
    return out


if __name__ == "__main__":
    n = 0
    for root in (ROOT / "output/staging_sd", ROOT / "output/staging_pd_art"):
        if not root.exists():
            continue
        for folder in sorted(p for p in root.iterdir() if p.is_dir()):
            prints = list(folder.glob("*_print.png"))
            if not prints:
                continue
            slug = prints[0].name[:-len("_print.png")]
            lead_for(prints[0], folder, slug)
            n += 1
            print("ok", slug, flush=True)
    print(f"\n{n} leads")
