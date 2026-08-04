#!/usr/bin/env python3
"""
map_pexels_plates.py - auto-detect blank frame openings in the shortlisted
Pexels plates (flood-fill the bright empty opening, same trick as m1-m3),
then composite a test print into each for review.

Detection: scan from the estimated opening centre; grow a connected region of
near-uniform bright pixels; take its bounding box corners (near-frontal photos
-> rectangle is fine, the warp handles tiny skews via the quad).
"""
from __future__ import annotations

from collections import deque
from pathlib import Path

from PIL import Image

import mockup_photo  # reuse place()-style warp via OPENINGS dict

ROOT = Path(__file__).resolve().parent
CAND = ROOT / "assets" / "mockups" / "pexels" / "candidates"

# shortlist: pid -> (hint_cx, hint_cy) as fractions where the opening sits
SHORTLIST = {
    "8148588":  (0.28, 0.50),   # black frame, greige wall, frontal
    "8490186":  (0.60, 0.32),   # thin black frame, white wall, chair+plant
    "8490248":  (0.62, 0.35),   # portrait frame above eames chair
    "8490172":  (0.60, 0.42),   # thin frame, shelf with plant
    "12486080": (0.55, 0.42),   # black frame w/ mat, bedroom drape
    "4466652":  (0.42, 0.45),   # white frame lean, wood table, bouquet
    "5978718":  (0.35, 0.45),   # oak frame lean, vase of dried flowers
    "8947628":  (0.52, 0.55),   # white frame lean by window
}

TOL = 26          # brightness tolerance for region growing


def detect_opening(img: Image.Image, hint):
    """Flood-fill from hint; return (x0,y0,x1,y1) of the blank opening."""
    small = img.convert("L")
    scale = 900 / max(small.size)
    if scale < 1:
        small = small.resize((round(small.width * scale), round(small.height * scale)))
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
        if abs(px[x, y] - base) > TOL:
            continue
        xs.append(x); ys.append(y)
        q.extend(((x+1,y),(x-1,y),(x,y+1),(x,y-1)))
    if not xs:
        return None
    fx = img.width / W
    # trim 1% inward so the print tucks under the frame lip
    x0, x1 = min(xs) * fx, max(xs) * fx
    y0, y1 = min(ys) * fx, max(ys) * fx
    bw, bh = x1 - x0, y1 - y0
    return (int(x0 + bw*0.01), int(y0 + bh*0.01), int(x1 - bw*0.01), int(y1 - bh*0.01))


if __name__ == "__main__":
    S = Path("/tmp/claude-1000/-home-alpha-products-barakah-pipeline/816bc583-a082-4ed0-829d-65c9a115ca14/scratchpad")
    test_print = ROOT / "output/staging_sd/koi_inpaint2_8/koi_inpaint2_8_print.png"
    results = {}
    for pid, hint in SHORTLIST.items():
        f = CAND / f"pexels_{pid}.jpg"
        img = Image.open(f)
        box = detect_opening(img, hint)
        if not box:
            print(f"{pid}: DETECT FAILED")
            continue
        x0, y0, x1, y1 = box
        w, h = x1-x0, y1-y0
        frac = (w*h) / (img.width*img.height)
        print(f"{pid}: opening {w}x{h} ({frac:.1%} of plate)")
        if frac < 0.02:
            print(f"  too small; skip")
            continue
        results[pid] = box
        # test composite via mockup_photo.place with a temp OPENINGS entry
        quad = [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]
        mockup_photo.OPENINGS[f"px_{pid}"] = quad
        # place() reads from assets/mockups/<key>.jpg; temporarily copy
        dst = mockup_photo.MOCKS / f"px_{pid}.jpg"
        if not dst.exists():
            import shutil
            shutil.copy(f, dst)
        mockup_photo.place(test_print, f"px_{pid}", S / f"px_{pid}_test.jpg")
        print(f"  -> test composite written")
    import json
    (ROOT / "assets/mockups/pexels/OPENINGS.json").write_text(json.dumps(results, indent=1))
    print(f"\n{len(results)} plates mapped; OPENINGS.json saved")
