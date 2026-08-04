#!/usr/bin/env python3
"""
proof.py - low-res, watermarked proof image for sending to buyers before final.

Downscales the print and overlays a tiled diagonal watermark so the proof is
clearly not print-ready. Watermark uses a mid-grey so it reads on both the dark
(emerald) and light (black_geo) styles.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"


def make_proof(print_png, out_path, long_edge: int = 1400,
               text: str = "PROOF • NOT FOR PRINT") -> Path:
    img = Image.open(print_png).convert("RGBA")
    scale = long_edge / max(img.size)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)

    font = ImageFont.truetype(str(FONT_DIR / "Cinzel[wght].ttf"), int(img.width * 0.045))

    # build an oversized watermark layer, tile the text, rotate, crop to image
    big = Image.new("RGBA", (img.width * 2, img.height * 2), (0, 0, 0, 0))
    wd = ImageDraw.Draw(big)
    step_x, step_y = int(img.width * 0.62), int(img.height * 0.16)
    for yy in range(0, big.height, step_y):
        for xx in range(0, big.width, step_x):
            wd.text((xx, yy), text, font=font, fill=(128, 128, 128, 80))
    big = big.rotate(30, resample=Image.BICUBIC, center=(big.width // 2, big.height // 2))
    left, top = (big.width - img.width) // 2, (big.height - img.height) // 2
    img = Image.alpha_composite(img, big.crop((left, top, left + img.width, top + img.height)))

    out_path = Path(out_path)
    img.convert("RGB").save(out_path, "PNG")
    return out_path
