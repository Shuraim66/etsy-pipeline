#!/usr/bin/env python3
"""
family_prints.py - PREMIUM personalized family/couple name pieces.

Why this line exists: instant-download singles are a $3 race. A made-to-order
personalized piece at $17.99-24.99 requires real per-order work (the Arabic
name must be supplied/verified per customer), which is exactly why bulk
template sellers cannot follow us here.

Three content models:
  family    "THE AHMED FAMILY" + Arabic family name + est. year
  couple    two names + Arabic + nikah/wedding date
  home      family name + Arabic + "established" line + city

Three layouts:
  stack     big Arabic centred, Latin tracked beneath (calm, boho)
  side      Arabic and Latin balanced across a hairline rule
  banner    Latin leads at poster scale, Arabic sits as an accent line

ARABIC POLICY (hard rule): the Arabic string is supplied per order by the
customer or the operator and passed in verbatim. This module NEVER generates,
transliterates or guesses Arabic. If name_arabic is blank the piece renders
Latin-only rather than inventing script.
"""
from __future__ import annotations

import gc
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdfcanvas

import arabic_text

ROOT = Path(__file__).resolve().parent
F = ROOT / "assets" / "fonts"
RUQAA = str(F / "ArefRuqaaInk.ttf")     # best free calligraphic script we have
AMIRI = str(F / "Amiri-Bold.ttf")
CINZEL = str(F / "Cinzel[wght].ttf")
GARA = str(F / "EBGaramond[wght].ttf")
GARA_I = str(F / "EBGaramond-Italic[wght].ttf")
OUT = ROOT / "output" / "staging_family"
W0, H0 = 3508, 4961

PALETTES = {
    "oatmeal":   {"bg": "#F1EBDF", "ink": "#2C2620", "soft": "#7C6F5E", "rule": "#B9A88E"},
    "emerald":   {"bg": "#12362E", "ink": "#F0E7D4", "soft": "#B9C6B4", "rule": "#CBA24C"},
    "terracotta":{"bg": "#B5603F", "ink": "#F8EFE1", "soft": "#F0D9C4", "rule": "#F3E3CE"},
    "sage":      {"bg": "#D7DBCB", "ink": "#2F362B", "soft": "#6E7562", "rule": "#8C9679"},
    "ink":       {"bg": "#1B1A18", "ink": "#EFE7D8", "soft": "#A2957F", "rule": "#CBA24C"},
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


def latin(text, size, color, tracking=0.40, weight=500, font=CINZEL):
    f = ImageFont.truetype(font, size)
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


def italic(text, size, color):
    f = ImageFont.truetype(GARA_I, size)
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


def ground(pal_key):
    p = PALETTES[pal_key]
    img = Image.new("RGB", (W0, H0), hx(p["bg"]))
    grain = Image.effect_noise((W0, H0), 15).convert("RGB")
    img = Image.blend(img, ImageChops.overlay(img, grain), 0.09)
    return img.convert("RGBA")


def arabic_or_none(text, color, max_w, target_h, font=RUQAA):
    """Render supplied Arabic verbatim; return None when nothing was given."""
    if not text or not str(text).strip():
        return None
    return arabic_text.render_arabic_fitted(str(text), font, color=color,
                                            max_width=max_w, target_height=target_h)


# --------------------------------------------------------------- layouts ----
def layout_stack(row, pal_key, slug):
    p = PALETTES[pal_key]
    ink, soft, rule = hx(p["ink"]), hx(p["soft"]), hx(p["rule"])
    img = ground(pal_key)
    d = ImageDraw.Draw(img)

    ar = arabic_or_none(row.get("name_arabic"), ink, int(W0 * 0.70), int(H0 * 0.20))
    y = int(H0 * 0.24)
    if ar:
        img.alpha_composite(ar, ((W0 - ar.width) // 2, y))
        y += ar.height + int(H0 * 0.045)

    lat = latin(row["name_latin"], int(H0 * 0.030), ink, tracking=0.44, weight=600)
    img.alpha_composite(lat, ((W0 - lat.width) // 2, y))
    y += lat.height + int(H0 * 0.038)

    d.line([W0 * 0.40, y, W0 * 0.60, y], fill=rule, width=max(2, int(W0 * 0.0010)))
    y += int(H0 * 0.030)

    if row.get("subline"):
        sub = latin(row["subline"], int(H0 * 0.0155), soft, tracking=0.50)
        img.alpha_composite(sub, ((W0 - sub.width) // 2, y))
        y += sub.height + int(H0 * 0.024)
    if row.get("detail"):
        det = italic(row["detail"], int(H0 * 0.0165), soft + (235,))
        img.alpha_composite(det, ((W0 - det.width) // 2, y))
    return save(img, slug)


def layout_side(row, pal_key, slug):
    p = PALETTES[pal_key]
    ink, soft, rule = hx(p["ink"]), hx(p["soft"]), hx(p["rule"])
    img = ground(pal_key)
    d = ImageDraw.Draw(img)

    cy = int(H0 * 0.42)
    ar = arabic_or_none(row.get("name_arabic"), ink, int(W0 * 0.66), int(H0 * 0.155))
    if ar:
        img.alpha_composite(ar, ((W0 - ar.width) // 2, cy - ar.height - int(H0 * 0.035)))

    d.line([W0 * 0.30, cy, W0 * 0.70, cy], fill=rule, width=max(2, int(W0 * 0.0009)))
    # small diamond on the rule
    s = int(W0 * 0.008)
    d.polygon([(W0/2, cy - s), (W0/2 + s, cy), (W0/2, cy + s), (W0/2 - s, cy)], fill=rule)

    lat = latin(row["name_latin"], int(H0 * 0.026), ink, tracking=0.46, weight=600)
    img.alpha_composite(lat, ((W0 - lat.width) // 2, cy + int(H0 * 0.040)))

    y = cy + int(H0 * 0.040) + lat.height + int(H0 * 0.030)
    if row.get("subline"):
        sub = latin(row["subline"], int(H0 * 0.0150), soft, tracking=0.52)
        img.alpha_composite(sub, ((W0 - sub.width) // 2, y))
        y += sub.height + int(H0 * 0.022)
    if row.get("detail"):
        det = italic(row["detail"], int(H0 * 0.0160), soft + (235,))
        img.alpha_composite(det, ((W0 - det.width) // 2, y))
    return save(img, slug)


def layout_banner(row, pal_key, slug):
    p = PALETTES[pal_key]
    ink, soft, rule = hx(p["ink"]), hx(p["soft"]), hx(p["rule"])
    img = ground(pal_key)
    d = ImageDraw.Draw(img)

    # Latin at poster scale, wrapped to two lines if long
    words = row["name_latin"].split()
    if len(words) > 2:
        l1, l2 = " ".join(words[:-1]), words[-1]
    else:
        l1, l2 = (words[0], " ".join(words[1:])) if len(words) == 2 else (words[0], "")

    y = int(H0 * 0.22)
    for part in (l1, l2):
        if not part:
            continue
        lp = latin(part, int(H0 * 0.052), ink, tracking=0.16, weight=700)
        if lp.width > W0 * 0.82:
            k = (W0 * 0.82) / lp.width
            lp = lp.resize((int(lp.width * k), int(lp.height * k)), Image.LANCZOS)
        img.alpha_composite(lp, ((W0 - lp.width) // 2, y))
        y += lp.height + int(H0 * 0.012)

    y += int(H0 * 0.022)
    d.line([W0 * 0.36, y, W0 * 0.64, y], fill=rule, width=max(2, int(W0 * 0.0010)))
    y += int(H0 * 0.034)

    ar = arabic_or_none(row.get("name_arabic"), ink, int(W0 * 0.56), int(H0 * 0.105))
    if ar:
        img.alpha_composite(ar, ((W0 - ar.width) // 2, y))
        y += ar.height + int(H0 * 0.036)

    if row.get("subline"):
        sub = latin(row["subline"], int(H0 * 0.0150), soft, tracking=0.52)
        img.alpha_composite(sub, ((W0 - sub.width) // 2, y))
        y += sub.height + int(H0 * 0.022)
    if row.get("detail"):
        det = italic(row["detail"], int(H0 * 0.0160), soft + (235,))
        img.alpha_composite(det, ((W0 - det.width) // 2, y))
    return save(img, slug)


LAYOUTS = {"stack": layout_stack, "side": layout_side, "banner": layout_banner}

# demo rows only - real orders supply their own verified Arabic
SAMPLES = {
    "family": {
        "name_latin": "The Rahman Family",
        "name_arabic": "",            # operator/customer supplies per order
        "subline": "Est. 2016",
        "detail": "Manchester, United Kingdom",
    },
    "couple": {
        "name_latin": "Yusuf & Maryam",
        "name_arabic": "",
        "subline": "Nikah",
        "detail": "12 Rabi al-Awwal 1447  ·  5 September 2025",
    },
    "home": {
        "name_latin": "The Siddiqui Home",
        "name_arabic": "",
        "subline": "Bismillah",
        "detail": "A house built on love and faith",
    },
}

if __name__ == "__main__":
    made = []
    for kind, row in SAMPLES.items():
        for layout in LAYOUTS:
            pal = {"family": "oatmeal", "couple": "emerald", "home": "sage"}[kind]
            slug = f"{kind}_{layout}_{pal}"
            made.append(LAYOUTS[layout](row, pal, slug))
            print("ok", slug, flush=True)
    # colourway spread on the strongest layout
    for pal in ("terracotta", "ink"):
        slug = f"family_stack_{pal}"
        made.append(layout_stack(SAMPLES["family"], pal, slug))
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
    sheet.save(OUT / "_REVIEW_family.png")
    print("sheet:", OUT / "_REVIEW_family.png")
