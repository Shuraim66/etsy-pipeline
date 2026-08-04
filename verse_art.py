#!/usr/bin/env python3
"""
verse_art.py - compositional verse art (NOT the panel/stack template formula).

A: medallion   - the verse inside a large gold-ringed circular medallion on a
                 deep emerald ground; text lines width-shaped to fill the disc.
B: monumental  - the verse at enormous scale on warm raw ground; tight margins,
                 one ink, zero furniture. The type IS the design.

Arabic policy: places verified Unicode from data/sacred_texts.json verbatim
(raqm/HarfBuzz). Never generates or alters Arabic. Text is never clipped or
cropped - scale is computed so the full verse always fits.
"""
from __future__ import annotations

import gc
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdfcanvas

import arabic_text

ROOT = Path(__file__).resolve().parent
FONT = str(ROOT / "assets" / "fonts" / "Amiri-Regular.ttf")
FONT_LATIN = str(ROOT / "assets" / "fonts" / "Cinzel[wght].ttf")
OUT = ROOT / "output" / "staging_sacred"
W0, H0 = 3508, 4961


def hx(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def save(img: Image.Image, folder: Path, slug: str):
    folder.mkdir(parents=True, exist_ok=True)
    png = folder / f"{slug}_print.png"
    img.convert("RGB").save(png, "PNG")
    page = (W0 / 300.0 * 72.0, H0 / 300.0 * 72.0)
    c = pdfcanvas.Canvas(str(folder / f"{slug}_print.pdf"), pagesize=page)
    c.drawImage(ImageReader(img.convert("RGB")), 0, 0, width=page[0], height=page[1])
    c.showPage()
    c.save()
    return png


def _latin(text, size, color, tracking=0.30):
    from PIL import ImageFont
    f = ImageFont.truetype(FONT_LATIN, size)
    try:
        f.set_variation_by_axes([500])
    except Exception:
        pass
    text = text.upper()
    widths = [f.getlength(ch) for ch in text]
    tr = tracking * size
    total = sum(widths) + tr * max(0, len(text) - 1)
    asc, desc = f.getmetrics()
    img = Image.new("RGBA", (int(total) + 20, asc + desc + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = 10
    for ch, w in zip(text, widths):
        d.text((x, 10), ch, font=f, fill=color)
        x += w + tr
    bbox = img.getbbox()
    return img.crop(bbox) if bbox else img


# --------------------------------------------------------------- A: medallion
def words_of(s: str):
    return [w for w in s.split() if w.strip()]


def medallion(verse: str, label: str, translation: str, slug: str,
              ground="#14352B", ring="#CBA24C", ink="#EFE6CF"):
    img = Image.new("RGBA", (W0, H0), hx(ground) + (255,))
    d = ImageDraw.Draw(img)
    cx, cy = W0 / 2, H0 * 0.44
    R = W0 * 0.365                     # medallion radius

    # shape verse lines to the circle: chord width at each line's height
    words = words_of(verse)
    # choose line count by text length (bismillah short -> 3, kursi long -> many)
    nlines = max(3, min(11, round(len(words) / 3.2)))
    # distribute words so each line's share matches its chord width
    ys = [(-1 + 2 * (i + 0.5) / nlines) for i in range(nlines)]   # -1..1
    chords = [math.sqrt(max(0.05, 1 - y * y)) for y in ys]
    total_chord = sum(chords)
    lines, wi = [], 0
    for i, ch in enumerate(chords):
        take = round(len(words) * ch / total_chord)
        take = max(1, take)
        if i == nlines - 1:
            line = words[wi:]
        else:
            line = words[wi:wi + take]
        wi += len(line)
        if line:
            lines.append(" ".join(line))
        if wi >= len(words):
            break
    lines = [l for l in lines if l.strip()]
    n = len(lines)

    # render each line fitted to its chord
    usable = R * 0.86
    line_h = (usable * 2 * 0.86) / n
    rendered = []
    for i, line in enumerate(lines):
        y = (-1 + 2 * (i + 0.5) / n) * 0.82
        chord = math.sqrt(max(0.08, 1 - y * y)) * usable * 1.9
        li = arabic_text.render_arabic_fitted(
            line, FONT, color=hx(ink), max_width=int(chord),
            target_height=int(line_h * 0.62))
        rendered.append((li, y))
    for li, y in rendered:
        img.alpha_composite(li, (int(cx - li.width / 2),
                                 int(cy + y * usable - li.height / 2)))

    # rings
    for rr, w in ((R * 1.045, 0.006), (R * 1.085, 0.0022)):
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                  outline=hx(ring), width=max(2, int(W0 * w)))
    # 8 small diamond studs on the outer ring
    rr = R * 1.085
    for k in range(8):
        a = math.pi / 4 * k
        px, py = cx + rr * math.cos(a), cy + rr * math.sin(a)
        s = W0 * 0.008
        d.polygon([(px, py - s), (px + s, py), (px, py + s), (px - s, py)], fill=hx(ring))

    # label + translation beneath
    lab = _latin(label, int(H0 * 0.016), hx(ring))
    img.alpha_composite(lab, (int(cx - lab.width / 2), int(H0 * 0.845)))
    # translation: wrap to ~64 chars
    from textwrap import wrap
    from PIL import ImageFont
    tf = ImageFont.truetype(str(ROOT / "assets" / "fonts" / "EBGaramond-Italic[wght].ttf"),
                            int(H0 * 0.0135))
    tl = Image.new("RGBA", (W0, int(H0 * 0.10)), (0, 0, 0, 0))
    td = ImageDraw.Draw(tl)
    yy = 0
    for ln in wrap(translation, 74)[:3]:
        wpx = td.textlength(ln, font=tf)
        td.text(((W0 - wpx) / 2, yy), ln, font=tf, fill=hx(ink) + (215,))
        yy += int(H0 * 0.0135 * 1.65)
    img.alpha_composite(tl, (0, int(H0 * 0.885)))

    return save(img, OUT / f"{slug}_medallion", f"{slug}_medallion")


# -------------------------------------------------------------- B: monumental
def monumental(verse: str, label: str, translation: str, slug: str,
               ground="#F2EBDD", ink="#221F1A", accent="#B0623A"):
    img = Image.new("RGBA", (W0, H0), hx(ground) + (255,))

    # the verse fills the frame: iterate font size upward until the text block
    # genuinely occupies the target area, then centre it vertically
    margin = int(W0 * 0.07)
    target_h = int(H0 * 0.62)
    body = None
    size = int(H0 * 0.06)
    for _ in range(8):
        cand = arabic_text.render_arabic_paragraph(
            verse, FONT, color=hx(ink), max_width=W0 - 2 * margin,
            font_size=size, leading=1.55)
        if cand.height > target_h:
            break
        body = cand
        size = int(size * 1.22)
    if body is None:
        body = cand
    y0 = int(H0 * 0.075) + (target_h - body.height) // 2
    img.alpha_composite(body, ((W0 - body.width) // 2, y0))

    # one small accent: a short terracotta rule + label, low left
    d = ImageDraw.Draw(img)
    lx, ly = margin, int(H0 * 0.875)
    d.rectangle([lx, ly, lx + int(W0 * 0.10), ly + int(H0 * 0.0035)], fill=hx(accent))
    lab = _latin(label, int(H0 * 0.015), hx(ink), tracking=0.34)
    img.alpha_composite(lab, (lx, ly + int(H0 * 0.014)))
    # translation, small, left-aligned under label
    from textwrap import wrap
    from PIL import ImageFont
    tf = ImageFont.truetype(str(ROOT / "assets" / "fonts" / "EBGaramond-Italic[wght].ttf"),
                            int(H0 * 0.0125))
    td = ImageDraw.Draw(img)
    yy = ly + int(H0 * 0.014) + lab.height + int(H0 * 0.012)
    for ln in wrap(translation, 88)[:2]:
        td.text((lx, yy), ln, font=tf, fill=hx(ink) + (200,))
        yy += int(H0 * 0.0125 * 1.6)

    return save(img, OUT / f"{slug}_monumental", f"{slug}_monumental")


if __name__ == "__main__":
    data = json.loads((ROOT / "data" / "sacred_texts.json").read_text(encoding="utf-8"))
    bis = data["bismillah"]
    assert bis["verified"]
    label = "Bismillah · 1:1"
    made = []
    made.append(medallion(bis["arabic_uthmani"], label, bis["translation"], "bismillah"))
    made.append(monumental(bis["arabic_uthmani"], label, bis["translation"], "bismillah"))
    for p in made:
        print("ok", p)
    gc.collect()
