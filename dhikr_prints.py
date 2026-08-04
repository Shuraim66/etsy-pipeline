#!/usr/bin/env python3
"""
dhikr_prints.py - single-word dhikr prints.

Design brief comes from competitor research: the sellers in this niche run
MINIMAL — textured off-white paper, one large word, a small English caption.
So the differentiation is not louder backgrounds (that failed); it is
(a) genuinely calligraphic scripts, and (b) four restrained ground treatments.

Scripts (both SIL OFL, free for commercial use):
  ArefRuqaaInk  - real calligraphic modelling, thick/thin ductus
  Rakkas        - heavy display weight for poster-scale statements

Grounds:
  paper    warm off-white with fine fibre grain (the market standard, done well)
  linen    subtle woven texture, tone slightly deeper
  ink      near-black ground, cream word (the inverse nobody in the beige crowd runs)
  sand     warm greige with a soft horizon wash

Arabic policy: verified entries only from data/sacred_texts.json, placed
verbatim through raqm. Never generated, never edited.
"""
from __future__ import annotations

import gc
import json
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdfcanvas

import arabic_text

ROOT = Path(__file__).resolve().parent
F = ROOT / "assets" / "fonts"
RUQAA = str(F / "ArefRuqaaInk.ttf")
RAKKAS = str(F / "Rakkas.ttf")
CINZEL = str(F / "Cinzel[wght].ttf")
GARA = str(F / "EBGaramond[wght].ttf")
OUT = ROOT / "output" / "staging_dhikr"
W0, H0 = 3508, 4961

KEYS = ["dhikr_subhanallah", "dhikr_alhamdulillah", "dhikr_allahuakbar"]

GROUNDS = {
    "paper": {"bg": "#F4EFE6", "ink": "#241F1A", "cap": "#6E6153"},
    "linen": {"bg": "#E8E1D4", "ink": "#2B2620", "cap": "#6B6053"},
    "ink":   {"bg": "#1A1815", "ink": "#EFE7D8", "cap": "#A79781"},
    "sand":  {"bg": "#E3D8C6", "ink": "#33291F", "cap": "#6F6151"},
}


def hx(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


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


def latin(text, size, color, tracking=0.40, weight=500):
    f = ImageFont.truetype(CINZEL, size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    text = text.upper()
    widths = [f.getlength(ch) for ch in text]
    tr = tracking * size
    total = sum(widths) + tr * max(0, len(text) - 1)
    asc, desc = f.getmetrics()
    img = Image.new("RGBA", (int(total) + 24, asc + desc + 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = 12
    for ch, w in zip(text, widths):
        d.text((x, 12), ch, font=f, fill=color)
        x += w + tr
    b = img.getbbox()
    return img.crop(b) if b else img


def caption(text, size, color):
    f = ImageFont.truetype(GARA, size)
    try:
        f.set_variation_by_axes([450])
    except Exception:
        pass
    img = Image.new("RGBA", (W0, int(size * 2.2)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = d.textlength(text, font=f)
    d.text(((W0 - w) / 2, 0), text, font=f, fill=color)
    b = img.getbbox()
    return img.crop(b) if b else img


def paper_ground(base, kind):
    """Textured ground: fibre grain everywhere, plus a treatment per kind."""
    img = Image.new("RGB", (W0, H0), base)
    rnd = random.Random(11)

    if kind == "linen":
        weave = Image.new("L", (W0, H0), 128)
        wd = ImageDraw.Draw(weave)
        step = 7
        for x in range(0, W0, step):
            wd.line([x, 0, x, H0], fill=138, width=1)
        for y in range(0, H0, step):
            wd.line([0, y, W0, y], fill=118, width=1)
        img = ImageChops.overlay(img, weave.convert("RGB"))
    elif kind == "sand":
        wash = Image.new("RGBA", (W0, H0), (0, 0, 0, 0))
        ImageDraw.Draw(wash).ellipse(
            [-W0 * 0.2, H0 * 0.45, W0 * 1.2, H0 * 1.35],
            fill=tuple(max(0, c - 16) for c in base) + (120,))
        img = Image.alpha_composite(img.convert("RGBA"),
                                    wash.filter(ImageFilter.GaussianBlur(int(W0 * 0.12)))).convert("RGB")
    elif kind == "ink":
        glow = Image.new("RGBA", (W0, H0), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse(
            [W0 * 0.08, H0 * 0.18, W0 * 0.92, H0 * 0.72],
            fill=tuple(min(255, c + 18) for c in base) + (150,))
        img = Image.alpha_composite(img.convert("RGBA"),
                                    glow.filter(ImageFilter.GaussianBlur(int(W0 * 0.14)))).convert("RGB")

    # fine paper fibre on everything
    grain = Image.effect_noise((W0, H0), 16).convert("RGB")
    img = Image.blend(img, ImageChops.overlay(img, grain), 0.10)
    # a few faint fibres
    d = ImageDraw.Draw(img)
    for _ in range(240):
        x, y = rnd.uniform(0, W0), rnd.uniform(0, H0)
        ln = rnd.uniform(8, 46)
        shade = tuple(max(0, min(255, c + rnd.choice((-10, 10)))) for c in base)
        d.line([x, y, x + rnd.uniform(-ln, ln), y + rnd.uniform(-4, 4)], fill=shade, width=1)
    return img.convert("RGBA")


def design(entry, slug, ground_key, font_path, word_h=0.235, word_w=0.72):
    g = GROUNDS[ground_key]
    img = paper_ground(hx(g["bg"]), ground_key)

    word = arabic_text.render_arabic_fitted(
        entry["arabic_uthmani"], font_path, color=hx(g["ink"]),
        max_width=int(W0 * word_w), target_height=int(H0 * word_h))
    img.alpha_composite(word, ((W0 - word.width) // 2, int(H0 * 0.30)))

    # hairline rule, then transliteration, then the meaning - small and quiet
    d = ImageDraw.Draw(img)
    y = int(H0 * 0.645)
    d.line([W0 * 0.42, y, W0 * 0.58, y], fill=hx(g["cap"]), width=max(1, int(W0 * 0.0007)))

    lab = latin(entry["label"], int(H0 * 0.0165), hx(g["cap"]), tracking=0.46)
    img.alpha_composite(lab, ((W0 - lab.width) // 2, int(H0 * 0.678)))
    cap = caption(entry["translation"], int(H0 * 0.0145), hx(g["cap"]) + (230,))
    img.alpha_composite(cap, ((W0 - cap.width) // 2, int(H0 * 0.722)))
    return save(img, slug)


if __name__ == "__main__":
    data = json.loads((ROOT / "data" / "sacred_texts.json").read_text(encoding="utf-8"))
    made = []
    plan = [
        ("paper", RUQAA, 0.235),
        ("linen", RUQAA, 0.235),
        ("ink",   RAKKAS, 0.205),
        ("sand",  RAKKAS, 0.205),
    ]
    for key in KEYS:
        e = data[key]
        assert e.get("verified"), key
        short = key.replace("dhikr_", "")
        for gk, fp, wh in plan:
            script = "ruqaa" if fp == RUQAA else "rakkas"
            slug = f"{short}_{gk}_{script}"
            made.append(design(e, slug, gk, fp, word_h=wh))
            print("ok", slug, flush=True)

    th, pad, cols = 560, 18, 4
    thumbs = [Image.open(p) for p in made]
    thumbs = [t.resize((int(t.width * th / t.height), th), Image.LANCZOS) for t in thumbs]
    tw = max(t.width for t in thumbs)
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (tw + pad) + pad, rows * (th + pad) + pad), (245, 243, 238))
    for i, t in enumerate(thumbs):
        r, c = divmod(i, cols)
        sheet.paste(t, (pad + c * (tw + pad) + (tw - t.width) // 2, pad + r * (th + pad)))
    sheet.save(OUT / "_REVIEW_dhikr2.png")
    print("sheet:", OUT / "_REVIEW_dhikr2.png")
