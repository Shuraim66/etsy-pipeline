#!/usr/bin/env python3
"""
add_plates.py - map NEW room plates into OPENINGS.json without disturbing the
seven already-verified quads.

Rooms the library was missing: nursery, office, and a genuine close-up/detail
shot. Detection reuses map_pexels_plates.detect_opening (flood-fill the blank
opening from a hint point); every result is test-composited for review before
it is trusted.

Usage: python3 add_plates.py [--commit]
  without --commit it only writes test composites to the scratchpad.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from PIL import Image

import mockup_photo
from map_pexels_plates import detect_opening

ROOT = Path(__file__).resolve().parent
CAND = ROOT / "assets" / "mockups" / "pexels" / "candidates"
OPENINGS_JSON = ROOT / "assets" / "mockups" / "pexels" / "OPENINGS.json"
SCRATCH = Path("/tmp/claude-1000/-home-alpha-products-barakah-pipeline/"
               "816bc583-a082-4ed0-829d-65c9a115ca14/scratchpad")

# pid -> (room, hint_cx, hint_cy)
NEW = {
    "8490259":  ("nursery", 0.50, 0.31),   # black frame over two kids' chairs
    "8490187":  ("office",  0.53, 0.36),   # black frame over wooden desk
    "8490229":  ("closeup", 0.62, 0.51),   # ornate frame leaning on a desk
}

# 5726035 (oak frame / marble console) was rejected: the frame interior and the
# wall are the same white, so the flood fill leaks out and swallows 96% of the
# plate. It would need a hand-traced quad; we already have office coverage.

TEST_PRINT = ROOT / "output/staging_geo/isfahan_geo_shamsa/isfahan_geo_shamsa_print.png"


def main(commit=False):
    existing = json.loads(OPENINGS_JSON.read_text())
    added = {}
    for pid, (room, hx, hy) in NEW.items():
        src = CAND / f"pexels_{pid}.jpg"
        if not src.exists():
            print(f"{pid}: MISSING {src}")
            continue
        img = Image.open(src)
        box = detect_opening(img, (hx, hy))
        if not box:
            print(f"{pid}: DETECT FAILED")
            continue
        x0, y0, x1, y1 = box
        w, h = x1 - x0, y1 - y0
        frac = (w * h) / (img.width * img.height)
        print(f"{pid} [{room}]: opening {w}x{h}  ({frac:.1%} of plate, "
              f"aspect {w/h:.2f})")
        if frac < 0.015:
            print("   too small - skipped")
            continue
        quad = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
        added[pid] = quad

        dst = mockup_photo.MOCKS / f"px_{pid}.jpg"
        if not dst.exists():
            shutil.copy(src, dst)
        mockup_photo.OPENINGS[f"px_{pid}"] = [tuple(p) for p in quad]
        mockup_photo.place(TEST_PRINT, f"px_{pid}", SCRATCH / f"new_{pid}.jpg")
        print(f"   -> test composite new_{pid}.jpg")

    if commit:
        existing.update(added)
        OPENINGS_JSON.write_text(json.dumps(existing, indent=1))
        print(f"\ncommitted {len(added)} plates; OPENINGS.json now has "
              f"{len(existing)}")
    else:
        print(f"\n{len(added)} mapped (review the composites, then --commit)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main("--commit" in sys.argv))
