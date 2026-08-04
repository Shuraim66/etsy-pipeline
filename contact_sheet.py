#!/usr/bin/env python3
"""
contact_sheet.py - render one name across many styles and tile a labeled grid
for side-by-side comparison.

Usage:
  python contact_sheet.py                       # default: the 6 design systems
  python contact_sheet.py style_a,style_b,...   # any subset of templates/
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import render

ROOT = Path(__file__).resolve().parent
FONT_DIR = ROOT / "assets" / "fonts"
DEFAULT_STYLES = [
    "hero", "hero_black", "hero_navy", "hero_ivory",
    "mihrab", "mihrab_black", "mihrab_navy", "mihrab_ivory",
    "split_panel", "split_panel_black", "split_panel_navy", "split_panel_ivory",
]


def build(styles, out_path, row=None, cols=3, thumb_w=720, pad=64, label_h=80,
          bg=(238, 236, 231)):
    row = row or render.SAMPLE_IBRAHIM
    tmp = ROOT / "output" / "_contact"
    thumbs = []
    for s in styles:
        paths = render.render(row, s, tmp)
        im = Image.open(paths["png"]).convert("RGB")
        h = int(im.height * thumb_w / im.width)
        thumbs.append((s, im.resize((thumb_w, h), Image.LANCZOS)))

    cell_img_h = thumbs[0][1].height
    rows = (len(thumbs) + cols - 1) // cols
    cw, ch = thumb_w + pad, cell_img_h + label_h + pad
    sheet = Image.new("RGB", (cols * cw + pad, rows * ch + pad), bg)
    d = ImageDraw.Draw(sheet)
    lf = ImageFont.truetype(str(FONT_DIR / "Cinzel[wght].ttf"), 38)

    for i, (name, im) in enumerate(thumbs):
        r, c = divmod(i, cols)
        x, y = pad + c * cw, pad + r * ch
        sheet.paste(im, (x, y))
        d.rectangle([x - 1, y - 1, x + im.width, y + im.height], outline=(198, 194, 186), width=2)
        d.text((x + im.width / 2, y + im.height + label_h / 2), name,
               font=lf, fill=(34, 34, 34), anchor="mm")

    sheet.save(out_path)
    return out_path


if __name__ == "__main__":
    styles = sys.argv[1].split(",") if len(sys.argv) > 1 else DEFAULT_STYLES
    out = ROOT / "output" / "contact_sheet.png"
    print("Rendering:", ", ".join(styles))
    build(styles, out, cols=4)
    print("wrote", out)
