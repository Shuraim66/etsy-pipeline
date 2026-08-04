#!/usr/bin/env python3
"""
verse_lux.py - luxury textured verse art: SD-generated painterly grounds
(no text in them) + verified Arabic composited on top via raqm.

Treatments:
  lux_circle  - gold ring medallion on the texture; verse disc-shaped inside a
                solid deep-tone cartouche for contrast; gold label.
  lux_full    - verse monumental across the texture with a soft darkening
                scrim behind the lettering zone for legibility.

Usage:
  python3 verse_lux.py <bg.png> <circle|full> <text_key> [gold|cream|ink]

Arabic: verified strings from data/sacred_texts.json placed verbatim.
"""
from __future__ import annotations

import gc
import json
import math
import sys
from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdfcanvas

import arabic_text
from verse_art2 import fit_verse_in_circle, latin_line, translation_block, hx

ROOT = Path(__file__).resolve().parent
FONTS = ROOT / "assets" / "fonts"
AMIRI = str(FONTS / "Amiri-Regular.ttf")
AMIRI_B = str(FONTS / "Amiri-Bold.ttf")
OUT = ROOT / "output" / "staging_sacred"
W0, H0 = 3508, 4961

INKS = {
    "gold":  {"main": hx("#D8B25F"), "label": hx("#D8B25F"), "trans": hx("#EFE6CF")},
    "cream": {"main": hx("#F3EAD3"), "label": hx("#D8B25F"), "trans": hx("#EFE6CF")},
    "ink":   {"main": hx("#2E2820"), "label": hx("#8C6D2F"), "trans": hx("#4A4235")},
}


def load_bg(path):
    bg = Image.open(path).convert("RGB").resize((W0, H0), Image.LANCZOS)
    return bg.convert("RGBA")


def save(img, slug):
    folder = OUT / slug
    folder.mkdir(parents=True, exist_ok=True)
    png = folder / f"{slug}_print.png"
    img.convert("RGB").save(png, "PNG")
    page = (W0 / 300.0 * 72.0, H0 / 300.0 * 72.0)
    c = pdfcanvas.Canvas(str(folder / f"{slug}_print.pdf"), pagesize=page)
    c.drawImage(ImageReader(img.convert("RGB")), 0, 0, width=page[0], height=page[1])
    c.showPage()
    c.save()
    del img
    gc.collect()
    return png


def avg_lum(img, box):
    区 = img.crop(box).convert("L").resize((24, 24))
    px = list(区.getdata())
    return sum(px) / len(px)


def lux_circle(bg_path, entry, slug, palette="cream", r_frac=0.325, cy_frac=0.43):
    ink = INKS[palette]
    img = load_bg(bg_path)
    d = ImageDraw.Draw(img)
    cx, cy, R = W0 / 2, H0 * cy_frac, W0 * r_frac

    # dark translucent cartouche for text contrast; tone follows ground
    lum = avg_lum(img, (int(cx - R), int(cy - R), int(cx + R), int(cy + R)))
    dark_ground = lum < 120
    disc_fill = (12, 16, 14, 215) if dark_ground else (250, 246, 236, 232)
    text_col = ink["main"] if dark_ground else hx("#2E2820")

    glow = Image.new("RGBA", (W0, H0), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([cx - R * 1.22, cy - R * 1.22, cx + R * 1.22, cy + R * 1.22],
                                 fill=hx("#D8B25F") + (70,))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(int(W0 * 0.028))))

    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=disc_fill)
    for rr, w in ((R * 1.005, 0.0042), (R * 1.05, 0.0016)):
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                  outline=hx("#D8B25F"), width=max(2, int(W0 * w)))

    for li, y in fit_verse_in_circle(entry["arabic_uthmani"], R * 0.88, text_col):
        img.alpha_composite(li, (int(cx - li.width / 2), int(cy + y * R * 0.88 - li.height / 2)))

    lab = latin_line(entry["label"], int(H0 * 0.0148), ink["label"])
    lab_bg = Image.new("RGBA", (W0, H0), (0, 0, 0, 0))
    lb = ImageDraw.Draw(lab_bg)
    lx0 = int(cx - lab.width / 2) - int(W0 * 0.03)
    ly0 = int(H0 * 0.845) - int(H0 * 0.012)
    lb.rounded_rectangle([lx0, ly0, lx0 + lab.width + int(W0 * 0.06),
                          ly0 + lab.height + int(H0 * 0.024)],
                         radius=int(H0 * 0.02),
                         fill=((250, 246, 238, 70) if palette == "ink" else (8, 10, 12, 95)))
    img.alpha_composite(lab_bg.filter(ImageFilter.GaussianBlur(int(W0 * 0.012))))
    img.alpha_composite(lab, (int(cx - lab.width / 2), int(H0 * 0.845)))
    # translation with soft scrim if ground is busy
    tr = translation_block(entry["translation"], int(W0 * 0.64), int(H0 * 0.0126), ink["trans"] + (235,))
    band = Image.new("RGBA", (W0, H0), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    b_rgb = (250, 246, 238) if palette == "ink" else (10, 12, 10)
    b_top, b_bot = int(H0 * 0.84), int(H0 * 0.955)
    for yy in range(b_top, b_bot, 4):
        t = (yy - b_top) / max(1, b_bot - b_top)
        bd.rectangle([0, yy, W0, yy + 4], fill=b_rgb + (int(80 * math.sin(math.pi * t) ** 0.7),))
    img.alpha_composite(band.filter(ImageFilter.GaussianBlur(24)))
    img.alpha_composite(tr, (int(W0 / 2 - tr.width / 2), int(H0 * 0.882)))
    return save(img, slug)


def lux_full(bg_path, entry, slug, palette="gold"):
    ink = INKS[palette]
    img = load_bg(bg_path)

    margin = int(W0 * 0.085)
    target_h = int(H0 * 0.58)
    size = int(H0 * 0.05)
    body = None
    for _ in range(8):
        cand = arabic_text.render_arabic_paragraph(
            entry["arabic_uthmani"], AMIRI_B, color=ink["main"],
            max_width=W0 - 2 * margin, font_size=size, leading=1.62)
        if cand.height > target_h:
            break
        body = cand
        size = int(size * 1.2)
    if body is None:
        body = cand
    x0 = (W0 - body.width) // 2
    y0 = int(H0 * 0.09) + (target_h - body.height) // 2

    # legibility: FULL-BLEED vertical gradient (no rectangle edges to notice).
    # Dark inks get a light veil, light inks get a dark veil; strength fades
    # out top and bottom so the ground still reads as itself.
    lum = avg_lum(img, (x0, y0, x0 + body.width, y0 + body.height))
    veil_rgb = (250, 246, 238) if palette == "ink" else (8, 10, 12)
    peak = 96 if palette == "ink" else (86 if lum >= 110 else 110)
    veil = Image.new("RGBA", (W0, H0), (0, 0, 0, 0))
    vd = ImageDraw.Draw(veil)
    top, bot = y0 - int(H0 * 0.06), y0 + body.height + int(H0 * 0.06)
    span = max(1, bot - top)
    for yy in range(top, bot, 4):
        t = (yy - top) / span
        a = int(peak * math.sin(math.pi * t) ** 0.7)      # 0 -> peak -> 0
        vd.rectangle([0, yy, W0, yy + 4], fill=veil_rgb + (a,))
    img.alpha_composite(veil.filter(ImageFilter.GaussianBlur(int(W0 * 0.03))))
    img.alpha_composite(body, (x0, y0))

    lab = latin_line(entry["label"], int(H0 * 0.0148), ink["label"])
    img.alpha_composite(lab, (int(W0 / 2 - lab.width / 2), int(H0 * 0.845)))
    tr = translation_block(entry["translation"], int(W0 * 0.62), int(H0 * 0.0126), ink["trans"] + (235,))
    band = Image.new("RGBA", (W0, H0), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    b_rgb = (250, 246, 238) if palette == "ink" else (10, 12, 10)
    b_top, b_bot = int(H0 * 0.84), int(H0 * 0.955)
    for yy in range(b_top, b_bot, 4):
        t = (yy - b_top) / max(1, b_bot - b_top)
        bd.rectangle([0, yy, W0, yy + 4], fill=b_rgb + (int(80 * math.sin(math.pi * t) ** 0.7),))
    img.alpha_composite(band.filter(ImageFilter.GaussianBlur(24)))
    img.alpha_composite(tr, (int(W0 / 2 - tr.width / 2), int(H0 * 0.882)))
    return save(img, slug)


if __name__ == "__main__":
    data = json.loads((ROOT / "data" / "sacred_texts.json").read_text(encoding="utf-8"))
    combos = [
        # (bg file, treatment, text, palette, slug)
        ("bg_marble_gold",  "circle", "bismillah", "gold"),
        ("bg_navy_fleck",   "circle", "ikhlas_1",  "cream"),
        ("bg_plum_silk",    "circle", "bismillah", "cream"),
        ("bg_parchment",    "full",   "bismillah", "ink"),
        ("bg_sage_wash",    "full",   "ikhlas_1",  "ink"),
        ("bg_floral_corner","circle", "ikhlas_1",  "ink"),
        ("bg_navy_fleck",   "full",   "bismillah", "gold"),
        ("bg_marble_gold",  "full",   "ikhlas_1",  "gold"),
    ]
    made = []
    for bg, treat, key, pal in combos:
        e = data[key]
        assert e["verified"]
        bgp = ROOT / "output" / "staging_sd" / f"{bg}.png"
        if not bgp.exists():
            print("missing bg:", bgp)
            continue
        slug = f"{key}_{bg[3:]}_{treat}"
        fn = lux_circle if treat == "circle" else lux_full
        made.append(fn(bgp, e, slug, pal))
        print("ok", slug, flush=True)

    thumbs = [Image.open(p) for p in made]
    th, pad, cols = 640, 24, 4
    thumbs = [t.resize((int(t.width * th / t.height), th), Image.LANCZOS) for t in thumbs]
    tw = max(t.width for t in thumbs)
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (tw + pad) + pad, rows * (th + pad) + pad), (245, 243, 238))
    for i, t in enumerate(thumbs):
        r, c = divmod(i, cols)
        sheet.paste(t, (pad + c * (tw + pad) + (tw - t.width) // 2, pad + r * (th + pad)))
    sheet.save(OUT / "_REVIEW_lux.png")
    print("sheet:", OUT / "_REVIEW_lux.png")
