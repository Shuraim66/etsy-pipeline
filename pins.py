#!/usr/bin/env python3
"""
pins.py - Pinterest pin generator.

For one rendered design folder, writes a `pins/` subfolder with four 1000x1500
(2:3 vertical) pins + a pins.csv of keyword-rich titles/descriptions/boards:

  1. _pin_mockup.png   framed-in-room, full bleed
  2. _pin_closeup.png  crop on the Arabic name + ornament
  3. _pin_text.png     design + headline overlay (design's own fonts/palette)
  4. _pin_styles.png   same name across the lead styles in one image

Text overlays reuse the design's resolved palette + fonts. Batch via
generate.py --pins.
"""
from __future__ import annotations

import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

import mockup
import mockup_photo
import render

ROOT = Path(__file__).resolve().parent
FONT_DIR = ROOT / "assets" / "fonts"
PIN = (1000, 1500)          # Pinterest 2:3
SS = 2                      # supersample for crisp overlay text
SHOWCASE = ["hero", "mihrab", "split_panel"]   # styles shown in the comparison pin
KW = ("Arabic Calligraphy Wall Art | Personalized Muslim Gift | "
      "Eid & Nikah Present | Islamic Nursery Decor | Digital Download")

_cmp_cache: dict = {}        # name -> [thumbnail Images]


def _hex(h):
    h = str(h).lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _lum(rgb):
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


def _font(file, size):
    return ImageFont.truetype(str(FONT_DIR / file), max(8, int(size)))


def _cover(img, w, h, fy=0.5):
    """Scale to cover w x h, crop centred horizontally and at vertical focus fy."""
    s = max(w / img.width, h / img.height)
    r = img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)
    x = (r.width - w) // 2
    y = max(0, min(int((r.height - h) * fy), r.height - h))
    return r.crop((x, y, x + w, y + h))


def _wrap(draw, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = f"{cur} {w}".strip()
        if cur and draw.textlength(t, font=font) > maxw:
            lines.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def _draw_centred(draw, lines, font, cx, y, fill, gap):
    asc, desc = font.getmetrics()
    for ln in lines:
        draw.text((cx - draw.textlength(ln, font=font) / 2, y), ln, font=font, fill=fill)
        y += asc + desc + gap
    return y


def _overlay_colors(style):
    """A guaranteed-legible (dark band, light text) pair tinted by the palette."""
    colors = style.get("colors", {})
    band = _hex(colors.get("banner") or colors.get("bgFrom") or style.get("background", {}).get("from", "#10362A"))
    if _lum(band) > 120:                         # light palette -> darken to a bar
        band = tuple(int(c * 0.40) for c in band)
    text = _hex(colors.get("accent") or colors.get("gold") or "#EAD9B0")
    if _lum(text) < 150:                          # ensure light text on the dark bar
        text = _hex(colors.get("bannerText") or "#F2ECDE")
    return band, text


def _comparison_thumbs(row, tmp_parent):
    key = render.slugify(row.get("name_latin", "name"))
    if key in _cmp_cache:
        return _cmp_cache[key]
    tmp = Path(tmp_parent) / "_pin_tmp"
    thumbs = []
    for s in SHOWCASE:
        p = render.render(row, s, tmp, canvas=(900, 1273), tag="cmp")
        thumbs.append(Image.open(p["png"]).convert("RGB"))
    _cmp_cache[key] = thumbs
    return thumbs


def build(row: dict, style_name: str, folder, out_dir=None) -> Path:
    """Generate the 4 pins + pins.csv for one rendered design folder."""
    folder = Path(folder)
    slug = folder.name
    print_png = folder / f"{slug}_print.png"
    pins_dir = folder / "pins"
    pins_dir.mkdir(exist_ok=True)

    style = render.resolve_style(style_name)
    name = row.get("name_latin", "Name")
    disp_file = style["fonts"].get("latin_name", {}).get("file", "Cinzel[wght].ttf")
    body_file = style["fonts"].get("body", {}).get("file", "EBGaramond-Italic[wght].ttf")
    band_c, text_c = _overlay_colors(style)
    W, H, sw, sh = PIN[0], PIN[1], PIN[0] * SS, PIN[1] * SS

    # 1. mockup pin — REAL photo frame (gold-lean, true 2:3), fit to the pin ----
    if (mockup_photo.MOCKS / "m2_gold_lean.jpg").exists():
        _tmp = pins_dir / f"{slug}_pin_mockup_tmp.jpg"
        mockup_photo.place(print_png, "m2_gold_lean", _tmp)
        ImageOps.fit(Image.open(_tmp).convert("RGB"), PIN, Image.LANCZOS).save(
            pins_dir / f"{slug}_pin_mockup.png")
        _tmp.unlink()
    else:
        mockup.composite(print_png, pins_dir / f"{slug}_pin_mockup.png", size=PIN)

    # 2. close-up on the name + ornament (upper-centre crop) -------------------
    src = Image.open(print_png).convert("RGB")
    cw = int(src.width * 0.66)
    ch = int(cw * 1.5)
    cx = (src.width - cw) // 2
    cy = max(0, min(int(src.height * 0.05), src.height - ch))
    src.crop((cx, cy, cx + cw, cy + ch)).resize(PIN, Image.LANCZOS).save(pins_dir / f"{slug}_pin_closeup.png")

    # 3. text-overlay pin ------------------------------------------------------
    base = _cover(src, sw, sh, fy=0.40).convert("RGBA")
    d = ImageDraw.Draw(base, "RGBA")
    bandh = int(sh * 0.27)
    d.rectangle([0, sh - bandh, sw, sh], fill=band_c + (235,))
    head_font = _font(disp_file, sw * 0.050)
    sub_font = _font(body_file, sw * 0.028)
    head_lines = _wrap(d, "What your name means in Arabic", head_font, sw * 0.86)
    block_h = len(head_lines) * (sum(head_font.getmetrics()) + int(sw * 0.012))
    y = sh - bandh + (bandh - block_h - sum(sub_font.getmetrics())) / 2
    y = _draw_centred(d, head_lines, head_font, sw / 2, y, text_c, int(sw * 0.012))
    sub = f"{name} · Personalized Islamic Name Print"
    d.text((sw / 2 - d.textlength(sub, font=sub_font) / 2, y + int(sw * 0.006)), sub, font=sub_font, fill=text_c)
    base.convert("RGB").resize(PIN, Image.LANCZOS).save(pins_dir / f"{slug}_pin_text.png")

    # 4. style-comparison pin --------------------------------------------------
    thumbs = _comparison_thumbs(row, out_dir or folder.parent)
    cmp = Image.new("RGB", (sw, sh), band_c)
    cd = ImageDraw.Draw(cmp)
    title_font = _font(disp_file, sw * 0.060)
    kicker_font = _font(disp_file, sw * 0.022)
    cd.text((sw / 2 - cd.textlength(name.upper(), font=title_font) / 2, int(sh * 0.07)),
            name.upper(), font=title_font, fill=text_c)
    kicker = "C H O O S E   Y O U R   S T Y L E"
    cd.text((sw / 2 - cd.textlength(kicker, font=kicker_font) / 2, int(sh * 0.155)),
            kicker, font=kicker_font, fill=text_c)
    tw = int(sw * 0.285)
    th = int(tw * (1273 / 900))
    gap = int(sw * 0.035)
    x0 = (sw - (len(thumbs) * tw + (len(thumbs) - 1) * gap)) // 2
    ty = int(sh * 0.40)
    for i, t in enumerate(thumbs):
        x = x0 + i * (tw + gap)
        cmp.paste(t.resize((tw, th), Image.LANCZOS), (x, ty))
        cd.rectangle([x, ty, x + tw, ty + th], outline=text_c, width=3)
    foot_font = _font(body_file, sw * 0.028)
    foot = "Personalized Islamic Name Print"
    cd.text((sw / 2 - cd.textlength(foot, font=foot_font) / 2, int(sh * 0.85)),
            foot, font=foot_font, fill=text_c)
    cmp.resize(PIN, Image.LANCZOS).save(pins_dir / f"{slug}_pin_styles.png")

    _write_csv(pins_dir, slug, name)
    return pins_dir


def _write_csv(pins_dir: Path, slug: str, name: str) -> None:
    rows = [
        (f"{slug}_pin_mockup.png",
         f"Personalized Islamic Name Print – {name} in Arabic",
         f"{name} in elegant Arabic calligraphy, framed for any room. {KW}",
         "Islamic Wall Art & Decor"),
        (f"{slug}_pin_closeup.png",
         f"{name} in Arabic Calligraphy | Custom Name Art",
         f"A close look at {name} written in Arabic calligraphy. {KW}",
         "Arabic Calligraphy Art"),
        (f"{slug}_pin_text.png",
         f"What Your Name Means in Arabic | {name}",
         f"Discover what {name} means in Arabic — a personalized keepsake print. {KW}",
         "Muslim Gift Ideas"),
        (f"{slug}_pin_styles.png",
         f"Islamic Name Print – Choose Your Style | {name}",
         f"{name} in multiple calligraphy styles and colours. {KW}",
         "Islamic Nursery & Home Decor"),
    ]
    with (pins_dir / "pins.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pin_image", "pin_title", "pin_description", "suggested_board", "listing_url"])
        for img, title, desc, board in rows:
            w.writerow([img, title, desc, board, ""])


if __name__ == "__main__":
    import sys
    style = sys.argv[1] if len(sys.argv) > 1 else "hero"
    out = ROOT / "output" / "_pins_demo"
    paths = render.render(render.SAMPLE_IBRAHIM, style, out)
    print("pins ->", build(render.SAMPLE_IBRAHIM, style, paths["folder"], out))
