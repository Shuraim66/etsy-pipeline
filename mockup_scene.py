#!/usr/bin/env python3
"""
mockup_scene.py - deterministic frame compositor over SD interior plates.

The SD scenes are ROOM PLATES (no usable frame in them). This module draws a
photoreal-enough frame directly onto the wall: molding with lit/shadow edges,
inner mat, soft drop shadow, then pastes the print into the opening. Because
we define the geometry, there is no corner-detection ambiguity and every
design fits perfectly.

SCENES maps each plate to a frame rect (in plate pixel coords, pre-upscale),
a frame style, and a light direction for the shadow.

Usage:
  from mockup_scene import scene_mockup
  scene_mockup("output/staging_sd/x/x_print.png", "livingroom", "out.jpg")
CLI:
  python3 mockup_scene.py <print.png> <scene> <out.jpg>
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent
PLATES = ROOT / "output" / "staging_sd"
OUT_LONG = 2000            # output long edge

# frame styles: (molding colours outer->inner, molding width frac, mat width frac)
STYLES = {
    "oak":   {"tones": [(176, 138, 92), (204, 168, 120), (156, 120, 78)], "mold": 0.030, "mat": 0.055},
    "black": {"tones": [(28, 28, 30), (58, 58, 62), (18, 18, 20)],        "mold": 0.026, "mat": 0.060},
    "gold":  {"tones": [(168, 132, 62), (214, 178, 104), (128, 96, 44)],  "mold": 0.028, "mat": 0.050},
    "white": {"tones": [(238, 236, 230), (250, 249, 245), (215, 212, 204)], "mold": 0.030, "mat": 0.0},
}

# scene -> plate file, frame QUAD (TL,TR,BR,BL in plate coords - follows the
# wall plane's perspective), style, light dir. Quads are hand-set per plate,
# sized ~0.4-0.5x the anchor furniture width at believable eye height.
SCENES = {
    # frontal blank-wall plates (plate_* series): flat rectangles are
    # geometrically correct, frames at ~1/3 wall width, believable hang height
    "livingroom": {
        "plate": "plate_livingroom.png",
        # 640x832 plate; wall spans full width, sofa top ~y=540
        # frame ~200px wide centered above sofa, bottom ~60px above sofa line
        "quad": [(220, 150), (420, 150), (420, 420), (220, 420)],
        "style": "black",
        "light": "left",
        "wall_lum": 238,
    },
    "dining": {
        "plate": "plate_dining.png",
        # blank wall between window and table; table top ~y=510
        "quad": [(190, 110), (410, 110), (410, 400), (190, 400)],
        "style": "black",
        "light": "left",
        "wall_lum": 238,
    },
    "reading": {
        "plate": "plate_reading.png",
        # beige wall above armchair; chair top ~y=380
        "quad": [(170, 90), (400, 90), (400, 400), (170, 400)],
        "style": "oak",
        "light": "left",
        "wall_lum": 210,
    },
    "sideboard": {
        "plate": "plate_sideboard.png",
        # wide cream wall between pampas and lamp
        "quad": [(150, 90), (400, 90), (400, 430), (150, 430)],
        "style": "black",
        "light": "right",
        "wall_lum": 215,
    },
    "green_lounge": {
        "plate": "plate_green_lounge.png",
        # sage wall right of window, above the potted trees
        "quad": [(395, 80), (595, 80), (595, 360), (395, 360)],
        "style": "oak",
        "light": "left",
        "wall_lum": 175,
    },
}


def _build_framed_flat(pr: Image.Image, style_key: str, light: str,
                       out_w: int = 1200) -> Image.Image:
    """Build the complete framed object FLAT (frame + mat + print + glass
    sheen) on a transparent canvas, to be perspective-warped into the scene."""
    st = STYLES[style_key]
    mold = int(out_w * st["mold"] * 1.6)
    mat = int(out_w * st["mat"] * 1.6)

    aspect = pr.height / pr.width
    open_w = out_w - 2 * (mold + mat)
    open_h = int(open_w * aspect)
    W = out_w
    H = open_h + 2 * (mold + mat)

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    outer, lit, dark = st["tones"]

    # molding
    d.rectangle([0, 0, W - 1, H - 1], fill=outer + (255,))
    bev = max(3, mold // 3)
    d.rectangle([0, 0, W, bev], fill=lit + (255,))
    d.rectangle([0, H - bev, W, H], fill=dark + (255,))
    if light == "left":
        d.rectangle([0, 0, bev, H], fill=lit + (255,))
        d.rectangle([W - bev, 0, W, H], fill=dark + (255,))
    else:
        d.rectangle([W - bev, 0, W, H], fill=lit + (255,))
        d.rectangle([0, 0, bev, H], fill=dark + (255,))

    # mat
    if mat > 0:
        d.rectangle([mold, mold, W - mold, H - mold], fill=(247, 244, 236, 255))

    # print
    x0, y0 = mold + mat, mold + mat
    pr_r = pr.resize((open_w, open_h), Image.LANCZOS)
    img.paste(pr_r, (x0, y0))
    if mat > 0:
        d.rectangle([x0 - 2, y0 - 2, x0 + open_w + 2, y0 + open_h + 2],
                    outline=(208, 203, 192, 255), width=2)

    # inner shadow (molding onto mat/print) + glass sheen
    inner = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    idr = ImageDraw.Draw(inner)
    idr.rectangle([mold, mold, W - mold, mold + bev], fill=(0, 0, 0, 70))
    idr.rectangle([mold, mold, mold + bev, H - mold], fill=(0, 0, 0, 45))
    img.alpha_composite(inner.filter(ImageFilter.GaussianBlur(3)))
    sheen = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sheen)
    sd.polygon([(x0, y0), (x0 + open_w * 0.42, y0), (x0, y0 + open_h * 0.5)],
               fill=(255, 255, 255, 22))
    img.alpha_composite(sheen.filter(ImageFilter.GaussianBlur(5)))
    return img


def _coeffs(dst, src):
    """8 perspective coefficients mapping dst->src for Image.transform."""
    A, b = [], []
    for (X, Y), (x, y) in zip(dst, src):
        A.append([X, Y, 1, 0, 0, 0, -x * X, -x * Y]); b.append(x)
        A.append([0, 0, 0, X, Y, 1, -y * X, -y * Y]); b.append(y)
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


def scene_mockup(print_png, scene_key: str, out_path) -> Path:
    cfg = SCENES[scene_key]
    plate = Image.open(PLATES / cfg["plate"]).convert("RGBA")
    scale = OUT_LONG / max(plate.size)
    plate = plate.resize((round(plate.width * scale), round(plate.height * scale)), Image.LANCZOS)
    quad = [(x * scale, y * scale) for x, y in cfg["quad"]]

    # crop print to the quad's average aspect
    pr = Image.open(print_png).convert("RGB")
    qw = (abs(quad[1][0] - quad[0][0]) + abs(quad[2][0] - quad[3][0])) / 2
    qh = (abs(quad[3][1] - quad[0][1]) + abs(quad[2][1] - quad[1][1]) ) / 2
    # frame adds molding+mat around the print; account for that in aspect
    st = STYLES[cfg["style"]]
    chrome = 2 * (st["mold"] + st["mat"]) * 1.6      # fraction of flat width
    open_ratio_w = 1 - chrome
    target = (qw * open_ratio_w) / (qh - qw * chrome)
    w, h = pr.size
    if w / h > target:
        nw = int(h * target)
        pr = pr.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(w / target)
        pr = pr.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))

    lum = cfg.get("wall_lum", 225)
    if lum < 220:
        pr = ImageEnhance.Brightness(pr).enhance(0.96)

    flat = _build_framed_flat(pr, cfg["style"], cfg["light"])

    # drop shadow: warped quad silhouette, offset down + away from light
    off = plate.width * 0.006
    ox = off if cfg["light"] == "left" else -off
    sh = Image.new("RGBA", plate.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).polygon([(x + ox, y + off * 1.6) for x, y in quad],
                               fill=(18, 16, 13, 115))
    plate.alpha_composite(sh.filter(ImageFilter.GaussianBlur(int(plate.width * 0.01))))

    # perspective-warp the flat framed object onto the quad
    coeffs = _coeffs(quad, [(0, 0), (flat.width, 0), (flat.width, flat.height), (0, flat.height)])
    warped = flat.transform(plate.size, Image.PERSPECTIVE, coeffs, Image.BICUBIC)
    plate.alpha_composite(warped)

    out_path = Path(out_path)
    plate.convert("RGB").save(out_path, quality=92)
    return out_path


def generate_for(print_png, folder, slug, scenes=("livingroom", "bedroom", "nursery")):
    """Write styled-interior mockups alongside the existing photo mockups."""
    out = []
    for i, sc in enumerate(scenes, 1):
        out.append(scene_mockup(print_png, sc, Path(folder) / f"{slug}_scene{i}.jpg"))
    return out


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        raise SystemExit("usage: mockup_scene.py <print.png> <scene> <out.jpg>")
    print(scene_mockup(sys.argv[1], sys.argv[2], sys.argv[3]))
