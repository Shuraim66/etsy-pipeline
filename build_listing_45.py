#!/usr/bin/env python3
"""
build_listing_45.py - the finalized listing photo builder.

Every image is uniform 4:5 (2000x2500) so the Etsy mobile swipe carousel stays
clean. The print is composited into the operator-approved frame set (16 plates:
the 11 root-folder locked frames + the 5 candidates confirmed 2026-08-01), then
cropped 4:5 with the frame a MODERATE element in a warm styled scene (not a
tight crop of just the frame, not a giant poster).

Frame set and per-listing routing live here. The lead (thumbnail) rotates by a
hash of the slug so neighbouring shop results never share a scene.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image

import mockup_photo
import sizes_card

ROOT = Path(__file__).resolve().parent
FRAMES_DIR = ROOT / "assets/mockups/frames"      # 16 plates, pre-cropped to 4:5
mockup_photo.MOCKS = FRAMES_DIR
OPEN = json.loads((FRAMES_DIR / "coords.json").read_text())
for _key, _q in OPEN.items():
    mockup_photo.OPENINGS[_key] = [tuple(p) for p in _q]

# the 16 approved frames, warm/prominent-frame leads first
FRAMES = [
    "px_12486418", "px_12486417", "m2_gold_lean", "m3_brass_flatlay",
    "px_8534228", "px_8490197", "m1_black_hung", "px_8148588", "m4_gold_easel",
    "px_12486080", "px_8490172", "px_20553171", "px_8251251",
    "px_8490187", "px_8490186", "px_8947552",
]
FRAMES = [f for f in dict.fromkeys(FRAMES) if f in OPEN]


def bleed(quad, frac=0.05):
    """Expand the opening outward from its centroid so the print tucks UNDER the
    frame edge (a slightly-small/offset detected quad otherwise leaves a grey
    gap where the art falls short — see mockup-frames memory)."""
    cx = sum(p[0] for p in quad) / 4.0
    cy = sum(p[1] for p in quad) / 4.0
    return [(x + (x - cx) * frac, y + (y - cy) * frac) for x, y in quad]


def scene(print_png: Path, frame_key: str, out: Path, bias_x=0.0) -> Path:
    # plates are already 4:5, so this just composites the print into the opening
    # (bled outward so it tucks under the frame edge) — no crop needed.
    orig = mockup_photo.OPENINGS[frame_key]
    mockup_photo.OPENINGS[frame_key] = bleed(orig)
    try:
        mockup_photo.place(print_png, frame_key, out)
    finally:
        mockup_photo.OPENINGS[frame_key] = orig
    return out


def build(print_png: Path, folder: Path, slug: str, n=6) -> list[Path]:
    folder.mkdir(parents=True, exist_ok=True)
    # stable rotation of the frame set starting at a slug-hash offset
    off = int(hashlib.md5(slug.encode()).hexdigest(), 16) % len(FRAMES)
    order = FRAMES[off:] + FRAMES[:off]
    out = []
    for i, fk in enumerate(order[:n], 1):
        out.append(scene(print_png, fk, folder / f"{slug}_v{i}.jpg"))
    card = folder / f"{slug}_v{n+1}.jpg"
    c = sizes_card.build(folder / f"{slug}_sizes_sq.jpg")
    ci = Image.open(c).convert("RGB")
    canv = Image.new("RGB", (2000, 2500), (244, 241, 235))
    canv.paste(ci.resize((2000, 2000)), (0, 250))
    canv.save(card, quality=93)
    out.append(card)
    return out


if __name__ == "__main__":
    import sys
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        ROOT / "output/listings/maryam_aquarelle/maryam_aquarelle_print.png")
    slug = src.name[:-len("_print.png")]
    paths = build(src, src.parent, slug)
    for p in paths:
        print(" ", p.name)
