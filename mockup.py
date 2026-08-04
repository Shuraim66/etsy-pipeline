#!/usr/bin/env python3
"""
mockup.py - composite a finished print into a framed wall scene (2000x2000).

Fully procedural and deterministic: a soft warm-wall gradient with a gentle
top light, a matted dark frame with a drop shadow, the print placed in the mat
opening (aspect preserved, never distorted), and a faint glass glare. No
external or photographic assets, so it is license-clean.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps

SIZE = 2000
SCENES = Path(__file__).resolve().parent / "assets" / "scenes"
# where the framed print sits on a scene's wall (fractions of the scene image)
SCENE_REGION = {"cx": 0.48, "bottom": 0.695, "width": 0.40, "frame": 0.011, "mat": 0.005}
# per-scene overrides so the frame always hangs clear on the wall (furniture
# lines differ between rooms). Keys are scene filenames; only the changed keys.
SCENE_REGIONS = {
    "room3_boho.png":  {"cx": 0.47, "bottom": 0.575, "width": 0.375},
    "room4_moody.png": {"cx": 0.585, "bottom": 0.625, "width": 0.355},
}


def _scenes():
    return (sorted(SCENES.glob("*.png")) + sorted(SCENES.glob("*.jpg"))) if SCENES.exists() else []


def _pick(key: str, n: int) -> int:
    # deterministic per output name, evenly distributed across scenes
    return int(hashlib.md5(str(key).encode()).hexdigest(), 16) % n if n else 0


def _scene_compose(print_png, scene_path, long_edge=1600, region=None) -> Image.Image:
    """Composite a framed print onto a photographic room scene."""
    region = {**SCENE_REGION, **(region or {})}
    scene = Image.open(scene_path).convert("RGB")
    scale = long_edge / max(scene.size)
    scene = scene.resize((round(scene.width * scale), round(scene.height * scale)),
                         Image.LANCZOS).convert("RGBA")
    W, H = scene.size
    m = min(W, H)
    print_img = Image.open(print_png).convert("RGB")
    ratio = print_img.height / print_img.width
    fr, mat = int(m * region["frame"]), int(m * region["mat"])
    outer_w = int(region["width"] * W)
    pw = outer_w - 2 * (fr + mat)
    ph = int(pw * ratio)
    outer_h = ph + 2 * (fr + mat)
    ox = int(region["cx"] * W - outer_w / 2)
    oy = int(region["bottom"] * H - outer_h)
    # soft drop shadow (scene light comes from the left -> shadow falls down-right)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    off = int(m * 0.008)
    ImageDraw.Draw(shadow).rectangle([ox + off, oy + off, ox + outer_w + off, oy + outer_h + off],
                                     fill=(0, 0, 0, 95))
    scene.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(m * 0.012)))
    d = ImageDraw.Draw(scene)
    lip = max(1, int(m * 0.0016))
    # natural light-oak frame with a soft top-down wood gradient + bevel lines
    frame_band = Image.new("RGB", (1, outer_h))
    fpx = frame_band.load()
    ftop, fbot = (214, 186, 140), (182, 150, 104)
    for y in range(outer_h):
        t = y / max(1, outer_h - 1)
        fpx[0, y] = tuple(round(ftop[i] + (fbot[i] - ftop[i]) * t) for i in range(3))
    scene.paste(frame_band.resize((outer_w, outer_h)), (ox, oy))
    d.rectangle([ox, oy, ox + outer_w, oy + outer_h], outline=(158, 128, 84, 255), width=lip)          # outer edge
    d.rectangle([ox + fr, oy + fr, ox + outer_w - fr, oy + outer_h - fr], fill=(250, 248, 243, 255))    # thin mat
    d.rectangle([ox + fr, oy + fr, ox + outer_w - fr, oy + outer_h - fr], outline=(150, 120, 78, 255), width=lip)  # inner bevel
    px0, py0 = ox + fr + mat, oy + fr + mat
    scene.paste(print_img.resize((pw, ph), Image.LANCZOS), (px0, py0))
    d.rectangle([px0 - 1, py0 - 1, px0 + pw + 1, py0 + ph + 1], outline=(210, 204, 194, 255), width=1)
    return scene.convert("RGB")


def _wall(w: int, h: int) -> Image.Image:
    top, bot = (226, 222, 214), (197, 191, 181)
    col = Image.new("RGB", (1, h))
    px = col.load()
    for y in range(h):
        t = y / (h - 1)
        px[0, y] = tuple(round(top[i] + (bot[i] - top[i]) * t) for i in range(3))
    wall = col.resize((w, h)).convert("RGBA")
    # soft light pooled near the top-centre
    light = Image.new("L", (w, h), 0)
    ImageDraw.Draw(light).ellipse([w * 0.10, -h * 0.25, w * 0.90, h * 0.62], fill=80)
    light = light.filter(ImageFilter.GaussianBlur(w * 0.12))
    glow = Image.new("RGBA", (w, h), (255, 250, 240, 255))
    return Image.composite(glow, wall, light)


def composite(print_png, out_path, size=None) -> Path:
    """Place the print in a room mockup. Uses a photographic scene from
    assets/scenes/ if any exist (framed on the wall); otherwise a procedural wall.

    `size`=(w,h) forces exact output dims (e.g. a 2:3 pin); None keeps the scene's
    aspect (a 2:3-ish room photo) for the listing hero image."""
    scenes = _scenes()
    if scenes:
        scene = scenes[_pick(Path(out_path).stem, len(scenes))]
        img = _scene_compose(print_png, scene, long_edge=(max(size) if size else 1600),
                             region=SCENE_REGIONS.get(scene.name))
        if size:
            img = ImageOps.fit(img, size, Image.LANCZOS)
        out_path = Path(out_path)
        img.save(out_path, "PNG")
        return out_path

    W, H = size or (SIZE, SIZE)
    m = min(W, H)
    print_img = Image.open(print_png).convert("RGB")
    ratio = print_img.height / print_img.width  # ~1.414 (A-series portrait)

    scene = _wall(W, H)
    draw = ImageDraw.Draw(scene)

    ph = int(H * 0.62)
    pw = int(ph / ratio)
    mat = int(m * 0.045)
    frame_w = int(m * 0.018)
    outer_w = pw + 2 * mat + 2 * frame_w
    outer_h = ph + 2 * mat + 2 * frame_w
    ox = (W - outer_w) // 2
    oy = int(H * 0.10)

    # drop shadow (offset + blurred)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    off = int(m * 0.010)
    ImageDraw.Draw(shadow).rectangle(
        [ox + off, oy + off, ox + outer_w + off, oy + outer_h + off], fill=(0, 0, 0, 120))
    scene.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(m * 0.012)))

    # frame (dark) -> mat (cream) -> print
    draw.rectangle([ox, oy, ox + outer_w, oy + outer_h], fill=(40, 33, 29, 255))
    draw.rectangle([ox + frame_w, oy + frame_w,
                    ox + outer_w - frame_w, oy + outer_h - frame_w], fill=(246, 243, 236, 255))
    px0, py0 = ox + frame_w + mat, oy + frame_w + mat
    scene.paste(print_img.resize((pw, ph), Image.LANCZOS), (px0, py0))
    draw.rectangle([px0 - 2, py0 - 2, px0 + pw + 2, py0 + ph + 2], outline=(208, 203, 194, 255), width=3)

    # subtle glass glare across the top-left of the glazing
    glare = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glare).polygon(
        [(px0, py0), (px0 + pw * 0.5, py0), (px0, py0 + ph * 0.6)], fill=(255, 255, 255, 24))
    scene.alpha_composite(glare)

    out_path = Path(out_path)
    scene.convert("RGB").save(out_path, "PNG")
    return out_path
