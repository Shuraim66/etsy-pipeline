#!/usr/bin/env python3
"""Render the 18 wave-2 templates with sample verified names and lay them out in
a labelled contact sheet for review (reduced canvas for speed)."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import render

ROOT = Path(__file__).resolve().parent
OUT = Path("/tmp/claude-1000/-home-alpha-products-barakah-pipeline/"
           "21f40b72-608a-41f8-b087-efce93a039b1/scratchpad/wave2")
OUT.mkdir(parents=True, exist_ok=True)
DB = json.loads((ROOT / "data/names_db.json").read_text())

# (template, sample-name-key)
JOBS = [
    ("nw_name_hero_charcoal", "yusuf"), ("nw_name_hero_sage", "maryam"),
    ("nw_name_hero_terracotta", "zayd"),
    ("nw_calligraphic_ink", "ibrahim"), ("nw_calligraphic_rouge", "aisha"),
    ("nw_calligraphic_olive", "musa"),
    ("nw_serif_minimal_cream", "maryam"), ("nw_serif_minimal_sage", "noor"),
    ("nw_serif_minimal_clay", "hamza"),
    ("nw_celestial_cream", "ibrahim"), ("nw_celestial_navy", "yusuf"),
    ("nw_celestial_sage", "maryam"),
    ("nw_monogram_terracotta", "khadija"), ("nw_monogram_sage", "ali"),
    ("nw_monogram_charcoal", "zayd"),
    ("nw_arc_block_terracotta", "aisha"), ("nw_arc_block_emerald", "musa"),
    ("nw_arc_block_ochre", "noor"),
]


def row_for(key):
    d = DB[key]
    return {
        "name_latin": key.title(),
        "name_arabic": d.get("name_arabic", ""),
        "meaning": d.get("meaning", ""),
        "date": "15 · 05 · 2024",
    }


def main():
    thumbs = []
    for tpl, key in JOBS:
        r = render.render(row_for(key), tpl, out_dir=OUT, canvas=(1000, 1414), tag="p")
        thumbs.append((tpl, key, r["png"]))
        print("rendered", tpl, key, flush=True)

    # contact sheet: 6 cols x 3 rows
    cols, rows = 6, 3
    tw, th = 460, 650
    pad, lab = 24, 34
    cw, ch = tw + pad, th + pad + lab
    sheet = Image.new("RGB", (cols * cw + pad, rows * ch + pad), (250, 248, 244))
    draw = ImageDraw.Draw(sheet)
    try:
        f = ImageFont.truetype(str(ROOT / "fonts/EBGaramond[wght].ttf"), 20)
    except Exception:
        f = ImageFont.load_default()
    for i, (tpl, key, png) in enumerate(thumbs):
        c, r = i % cols, i // cols
        x, y = pad + c * cw, pad + r * ch
        im = Image.open(png).convert("RGB")
        im.thumbnail((tw, th))
        ox = x + (tw - im.width) // 2
        sheet.paste(im, (ox, y))
        label = tpl.replace("nw_", "")
        draw.text((x + tw // 2, y + th + 6), label, fill=(60, 55, 48), font=f, anchor="ma")
    sheet_path = OUT / "_contact_sheet.jpg"
    sheet.save(sheet_path, quality=90)
    print("SHEET", sheet_path)


if __name__ == "__main__":
    main()
