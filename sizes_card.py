#!/usr/bin/env python3
"""
sizes_card.py - the "what sizes do I get" listing graphic.

Buyers of digital prints ask this before anything else, and a square card that
answers it belongs in the photo strip rather than buried in the description.
Deliberately plain: it is an information card, not artwork.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
F = ROOT / "assets" / "fonts"

RATIOS = [
    ("ISO A", "A5 · A4 · A3 · A2 · A1"),
    ("2:3", '4x6 · 8x12 · 12x18 · 16x24 · 20x30 · 24x36"'),
    ("3:4", '6x8 · 9x12 · 12x16 · 15x20 · 18x24"'),
    ("4:5", '8x10 · 11x14 · 16x20"'),
    ("5:7", '5x7 · 10x14"'),
]

BG = (244, 241, 235)
INK = (43, 38, 32)
SOFT = (122, 110, 95)
RULE = (206, 194, 176)


def _font(name, size, weight=None):
    f = ImageFont.truetype(str(F / name), size)
    if weight:
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
    return f


def build(out: Path, size: int = 2000,
          footer: str = "300 DPI · print-ready PDF + PNG · made to order") -> Path:
    img = Image.new("RGB", (size, size), BG)
    d = ImageDraw.Draw(img)
    s = size / 2000.0

    title = _font("Cinzel[wght].ttf", int(78 * s), 600)
    sub = _font("EBGaramond[wght].ttf", int(46 * s), 450)
    lab = _font("Cinzel[wght].ttf", int(58 * s), 600)
    body = _font("EBGaramond[wght].ttf", int(42 * s), 450)

    def centre(text, font, y, fill):
        w = d.textlength(text, font=font)
        d.text(((size - w) / 2, y), text, font=font, fill=fill)

    centre("5 PRINT RATIOS", title, int(170 * s), INK)
    centre("one purchase — every common frame size", sub, int(285 * s), SOFT)
    d.line([size * 0.40, int(390 * s), size * 0.60, int(390 * s)], fill=RULE,
           width=max(1, int(3 * s)))

    y = int(500 * s)
    for name, sizes in RATIOS:
        d.text((int(210 * s), y), name, font=lab, fill=INK)
        d.text((int(210 * s), y + int(74 * s)), sizes, font=body, fill=SOFT)
        y += int(120 * s)
        d.line([int(210 * s), y + int(28 * s), size - int(210 * s), y + int(28 * s)],
               fill=RULE, width=max(1, int(2 * s)))
        y += int(96 * s)

    centre(footer, body, int(1760 * s), SOFT)
    img.save(out, "JPEG", quality=93)
    return out


if __name__ == "__main__":
    p = build(Path("/tmp/claude-1000/-home-alpha-products-barakah-pipeline/"
                   "816bc583-a082-4ed0-829d-65c9a115ca14/scratchpad/sizes_card.jpg"))
    print(p)
