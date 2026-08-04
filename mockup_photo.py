#!/usr/bin/env python3
"""
mockup_photo.py - composite a print into a REAL photographic frame mockup by
perspective-warping the artwork into the frame's blank opening.

Real mockup photos live in assets/mockups/; OPENINGS holds the 4 corners
(TL, TR, BR, BL, in that photo's pixel coords) of each blank frame opening.
No numpy — the 8 perspective coefficients are solved with plain Gaussian
elimination. The print is centre-cropped to the opening's aspect first so the
Arabic never stretches.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

from PIL import Image

MOCKS = Path(__file__).resolve().parent / "assets" / "mockups"

# [top-left, top-right, bottom-right, bottom-left] of each blank opening (px)
OPENINGS = {
    # m1/m2/m3 auto-detected by flood-filling the blank white opening; m4 hand-set
    # (its opening connects to the wall so auto-detect leaks).
    # flood-detected white opening + ~1.5% bleed (thin frame -> small bleed so
    # the art tucks under the black edge without spilling onto the wall).
    "m1_black_hung":   [(2726, 688), (4652, 676), (4647, 3371), (2729, 3371)],
    "m2_gold_lean":    [(2005, 2714), (3634, 2704), (3665, 5041), (2005, 5031)],
    "m3_brass_flatlay":[(1553, 788), (2977, 806), (3020, 2985), (1549, 2972)],
    # opening detected from the paper, then bled outward ~5% so the art tucks
    # UNDER the gold frame lip (no thin grey glass-edge gap shows at the top).
    "m4_gold_easel":   [(1819, 1077), (3094, 1031), (3342, 3011), (2095, 3106)],
}


def _solve8(A, b):
    """Gaussian elimination for an 8x8 system; returns the 8 unknowns."""
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    n = 8
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        pv = M[c][c]
        M[c] = [v / pv for v in M[c]]
        for r in range(n):
            if r != c and M[r][c]:
                f = M[r][c]
                M[r] = [M[r][k] - f * M[c][k] for k in range(n + 1)]
    return [M[r][n] for r in range(n)]


def _coeffs(dst, src):
    """8 PERSPECTIVE coeffs mapping dst(output)->src(input) for Image.transform."""
    A, b = [], []
    for (X, Y), (x, y) in zip(dst, src):
        A.append([X, Y, 1, 0, 0, 0, -x * X, -x * Y]); b.append(x)
        A.append([0, 0, 0, X, Y, 1, -y * X, -y * Y]); b.append(y)
    return _solve8(A, b)


def _crop_aspect(img, aspect):
    """Centre-crop img to the given width/height aspect ratio."""
    w, h = img.size
    if w / h > aspect:                       # too wide -> trim sides
        nw = int(h * aspect)
        return img.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    nh = int(w / aspect)                     # too tall -> trim top/bottom
    return img.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def place(print_png, mock_key: str, out_path) -> Path:
    quad = OPENINGS[mock_key]
    mock = Image.open(MOCKS / f"{mock_key}.jpg").convert("RGBA")
    pr = Image.open(print_png).convert("RGBA")
    tl, tr, br, bl = quad
    wA = (_dist(tl, tr) + _dist(bl, br)) / 2
    hA = (_dist(tl, bl) + _dist(tr, br)) / 2
    pr = _crop_aspect(pr, wA / hA)
    w, h = pr.size
    coeffs = _coeffs(quad, [(0, 0), (w, 0), (w, h), (0, h)])
    warped = pr.transform(mock.size, Image.PERSPECTIVE, coeffs, Image.BICUBIC)
    mock.alpha_composite(warped)
    out_path = Path(out_path)
    mock.convert("RGB").save(out_path, quality=92)
    return out_path


# frame routing. m4_gold_easel is intentionally DROPPED: it is a thin, back-
# leaning glass easel with hard sun-glare and its own brass legs crossing the
# art, so warped prints read as "messed up" no matter how well they register.
# Only the three clean scenes are used: black wall-hung, gold lean, brass flatlay.
LIGHT_SET = ["m1_black_hung", "m2_gold_lean", "m3_brass_flatlay"]
DARK_SET = ["m2_gold_lean", "m3_brass_flatlay", "m1_black_hung"]


def _is_dark(print_png) -> bool:
    im = Image.open(print_png).convert("L").resize((40, 56))
    px = list(im.getdata())
    return (sum(px) / len(px)) < 110


def generate_for(print_png, folder, slug):
    """Write 3 real-photo mockups (slug_mock1..3.jpg) for a design folder.

    The frame set is rotated by a stable hash of the slug so that different
    designs LEAD with different scenes (the mock1 thumbnail varies across the
    shop) while every listing still gets 3 distinct frames. Dark/light routing
    is preserved so a dark print never lands in the black frame.
    """
    keys = list(DARK_SET if _is_dark(print_png) else LIGHT_SET)
    shift = int(hashlib.md5(slug.encode()).hexdigest(), 16) % len(keys)
    keys = keys[shift:] + keys[:shift]
    out = []
    for i, k in enumerate(keys, 1):
        out.append(place(print_png, k, Path(folder) / f"{slug}_mock{i}.jpg"))
    return out


if __name__ == "__main__":
    import sys
    print_png, key, out = sys.argv[1], sys.argv[2], sys.argv[3]
    place(print_png, key, out)
    print("wrote", out)
