#!/usr/bin/env python3
"""
verify_plates.py - re-detect and audit every mockup plate opening.

THE BUG THIS FIXES: the original detector flood-filled with a loose tolerance
(26), so on any plate where the frame holds a white MAT it grabbed mat+window
as one bright blob. Compositing into that quad wiped the mat, jammed the art
against the frame moulding, and on the linen flatlay pushed the bottom-left
corner out over the dried flower that overlaps the frame in the photo.

THE FIX: sweep the tolerance and keep the region whose aspect ratio is closest
to the print's own 0.707 - a real A-series print window matches it almost
exactly, a mat does not. Everything is then rendered as an overlay plus a live
composite so each plate is checked by eye before it is trusted.

Usage:
  python3 verify_plates.py            # audit, write overlays + composites
  python3 verify_plates.py --commit   # also rewrite OPENINGS.json
"""
from __future__ import annotations

import json
import sys
from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw

import mockup_photo

ROOT = Path(__file__).resolve().parent
OPENINGS_JSON = ROOT / "assets" / "mockups" / "pexels" / "OPENINGS.json"
SCRATCH = Path("/tmp/claude-1000/-home-alpha-products-barakah-pipeline/"
               "816bc583-a082-4ed0-829d-65c9a115ca14/scratchpad/plates")

PRINT_ASPECT = 3508 / 4961          # 0.7071 - every print we sell
TEST_PRINT = ROOT / "output/staging_geo/isfahan_geo_shamsa/isfahan_geo_shamsa_print.png"

# hint point inside each opening, as a fraction of the plate
HINTS = {
    "8148588":  (0.60, 0.50),
    "8490186":  (0.50, 0.30),
    "8490172":  (0.65, 0.48),
    "12486080": (0.50, 0.50),
    "12486417": (0.50, 0.55),
    "12486418": (0.50, 0.50),
    "20553171": (0.50, 0.42),
    "8490259":  (0.50, 0.31),
    "8490187":  (0.53, 0.36),
    "8490229":  (0.62, 0.51),
}


def _flood(img: Image.Image, hint, tol: int):
    small = img.convert("L")
    sc = 900 / max(small.size)
    if sc < 1:
        small = small.resize((round(small.width * sc), round(small.height * sc)))
    W, H = small.size
    px = small.load()
    sx, sy = int(hint[0] * W), int(hint[1] * H)
    base = px[sx, sy]
    seen = bytearray(W * H)
    q = deque([(sx, sy)])
    xs, ys = [], []
    while q:
        x, y = q.popleft()
        if x < 0 or y < 0 or x >= W or y >= H or seen[y * W + x]:
            continue
        seen[y * W + x] = 1
        if abs(px[x, y] - base) > tol:
            continue
        xs.append(x)
        ys.append(y)
        q.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    if not xs:
        return None
    f = img.width / W
    return (int(min(xs) * f), int(min(ys) * f), int(max(xs) * f), int(max(ys) * f))


def detect_window(img: Image.Image, hint):
    """Return the box whose aspect best matches a real print window."""
    best = None
    for tol in range(2, 31):
        b = _flood(img, hint, tol)
        if not b:
            continue
        w, h = b[2] - b[0], b[3] - b[1]
        if w < 40 or h < 40:
            continue
        if (w * h) / (img.width * img.height) > 0.55:   # leaked onto the wall
            continue
        err = abs((w / h) - PRINT_ASPECT)
        if best is None or err < best[0] - 1e-6:
            best = (err, b, tol)
    return best


def main(commit=False):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    old = json.loads(OPENINGS_JSON.read_text())
    new = {}
    for pid, hint in HINTS.items():
        src = mockup_photo.MOCKS / f"px_{pid}.jpg"
        img = Image.open(src)
        got = detect_window(img, hint)
        if not got:
            print(f"{pid}: DETECT FAILED")
            continue
        err, (x0, y0, x1, y1), tol = got
        w, h = x1 - x0, y1 - y0
        quad = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
        note = ""
        if pid in old:
            xs = [p[0] for p in old[pid]]
            ys = [p[1] for p in old[pid]]
            ow, oh = max(xs) - min(xs), max(ys) - min(ys)
            # 8148588's opening merges into the wall tone, so the sweep finds a
            # tall bogus region; its hand-traced quad is already correct. Keep
            # whichever quad is closer to the print aspect.
            if abs(ow / oh - PRINT_ASPECT) < err:
                quad = [list(p) for p in old[pid]]
                note = f"  KEPT hand-traced ({ow}x{oh}, {ow/oh:.3f})"
            note = (f"   was {ow}x{oh} aspect {ow/oh:.3f}" + note)
        print(f"{pid}: {w}x{h} aspect {w/h:.3f} (tol {tol}){note}")
        new[pid] = quad

        ov = img.convert("RGB").copy()
        d = ImageDraw.Draw(ov)
        if pid in old:
            d.polygon([tuple(p) for p in old[pid]], outline=(255, 60, 60))
        d.polygon([tuple(p) for p in quad], outline=(0, 220, 90))
        k = 900 / max(ov.size)
        ov.resize((int(ov.width * k), int(ov.height * k)), Image.LANCZOS) \
          .save(SCRATCH / f"ov_{pid}.jpg", quality=92)

        mockup_photo.OPENINGS[f"px_{pid}"] = [tuple(p) for p in quad]
        mockup_photo.place(TEST_PRINT, f"px_{pid}", SCRATCH / f"cmp_{pid}.jpg")

    if commit:
        OPENINGS_JSON.write_text(json.dumps(new, indent=1))
        print(f"\ncommitted {len(new)} plates")
    else:
        print(f"\n{len(new)} audited -> {SCRATCH} (review, then --commit)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main("--commit" in sys.argv))
