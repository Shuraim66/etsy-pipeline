#!/usr/bin/env python3
"""
verse_art2.py - RICH compositional verse art, five distinct structures
(none of them the panel/stack formula):

  illuminated  - Quran-frontispiece energy: star-field ground, central solid
                 cartouche disc + gold rings holding the verse, ornate border,
                 corner quarter-medallions.
  mihrab       - the verse steps down inside a true mihrab arch silhouette,
                 geometric band at the base, warm sandstone palette.
  hilye        - classic hilye structure: big central roundel + four small
                 corner roundels (crescent/star accents), parchment ground.
  radiant      - upgrade of the medallion: shamsa rays radiating behind the
                 text disc, tighter ring, jewel ground.
  duotone      - upgrade of monumental: giant verse across a two-tone split
                 ground, ink flips colour at the boundary via masking.

Arabic: verified Unicode from data/sacred_texts.json placed verbatim (raqm).
"""
from __future__ import annotations

import gc
import json
import math
from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdfcanvas

import arabic_text
import ornaments

ROOT = Path(__file__).resolve().parent
FONTS = ROOT / "assets" / "fonts"
AMIRI = str(FONTS / "Amiri-Regular.ttf")
AMIRI_B = str(FONTS / "Amiri-Bold.ttf")
CINZEL = str(FONTS / "Cinzel[wght].ttf")
GARA_I = str(FONTS / "EBGaramond-Italic[wght].ttf")
OUT = ROOT / "output" / "staging_sacred"
W0, H0 = 3508, 4961


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


def latin_line(text, size, color, tracking=0.32, weight=500):
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
    img = Image.new("RGBA", (int(total) + 20, asc + desc + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = 10
    for ch, w in zip(text, widths):
        d.text((x, 10), ch, font=f, fill=color)
        x += w + tr
    b = img.getbbox()
    return img.crop(b) if b else img


def translation_block(text, width_px, size, color, align="center", max_lines=3):
    tf = ImageFont.truetype(GARA_I, size)
    try:
        tf.set_variation_by_axes([450])
    except Exception:
        pass
    lines = wrap(text, max(30, int(width_px / (size * 0.47))))[:max_lines]
    lh = int(size * 1.65)
    img = Image.new("RGBA", (width_px, lh * len(lines) + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, ln in enumerate(lines):
        wpx = d.textlength(ln, font=tf)
        x = 0 if align == "left" else (width_px - wpx) / 2
        d.text((x, i * lh), ln, font=tf, fill=color)
    b = img.getbbox()
    return img.crop(b) if b else img


def fit_verse_in_circle(verse, R_px, color, font=AMIRI, fill=0.80):
    """Shape verse lines so the block genuinely fills a disc of radius R."""
    words = [w for w in verse.split() if w.strip()]
    best = None
    for nlines in range(2, 14):
        ys = [(-1 + 2 * (i + 0.5) / nlines) * fill for i in range(nlines)]
        chords = [math.sqrt(max(0.04, 1 - y * y)) for y in ys]
        tot = sum(chords)
        lines, wi = [], 0
        ok = True
        for i, ch in enumerate(chords):
            take = max(1, round(len(words) * ch / tot))
            line = words[wi:] if i == nlines - 1 else words[wi:wi + take]
            if not line:
                ok = False
                break
            lines.append(" ".join(line))
            wi += len(line)
        if not ok or wi < len(words):
            continue
        line_h = (2 * R_px * fill) / nlines
        rendered = []
        overflow = False
        for i, line in enumerate(lines):
            y = ys[i]
            chord_px = math.sqrt(max(0.06, 1 - (y / fill) ** 2 * fill * fill)) * 2 * R_px * 0.92
            chord_px = math.sqrt(max(0.06, 1 - y * y)) * 2 * R_px * 0.92
            li = arabic_text.render_arabic_fitted(
                line, font, color=color, max_width=int(chord_px),
                target_height=int(line_h * 0.60))
            if li.width > chord_px * 1.02:
                overflow = True
            rendered.append((li, y))
        if overflow:
            continue
        density = sum(li.width * li.height for li, _ in rendered) / (math.pi * R_px * R_px)
        if best is None or density > best[0]:
            best = (density, rendered)
    return best[1] if best else []


# ------------------------------------------------------------- illuminated --
def illuminated(verse, label, translation, slug):
    NAVY, GOLD, CREAM, LINE = hx("#101C2E"), hx("#C6A14E"), hx("#F1E8D2"), hx("#22304A")
    img = Image.new("RGBA", (W0, H0), NAVY + (255,))

    field = ornaments.star_tiling(W0, H0, LINE, cells=6.0, line=0.004)
    img.alpha_composite(field)

    cx, cy, R = W0 / 2, H0 * 0.42, W0 * 0.335
    d = ImageDraw.Draw(img)
    # halo glow then solid cartouche
    glow = Image.new("RGBA", (W0, H0), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([cx - R * 1.25, cy - R * 1.25, cx + R * 1.25, cy + R * 1.25],
                                 fill=GOLD + (60,))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(int(W0 * 0.03))))
    d.ellipse([cx - R * 1.02, cy - R * 1.02, cx + R * 1.02, cy + R * 1.02], fill=GOLD + (255,))
    d.ellipse([cx - R * 0.985, cy - R * 0.985, cx + R * 0.985, cy + R * 0.985], fill=hx("#15243A") + (255,))
    d.ellipse([cx - R * 0.92, cy - R * 0.92, cx + R * 0.92, cy + R * 0.92], fill=CREAM + (255,))

    for li, y in fit_verse_in_circle(verse, R * 0.88, hx("#1E2A38")):
        img.alpha_composite(li, (int(cx - li.width / 2), int(cy + y * R * 0.88 - li.height / 2)))

    # ornate double border + corner quarter-medallions
    ornaments.draw_border(img, GOLD, inset=int(W0 * 0.035), gap=int(W0 * 0.010),
                          width=max(2, int(W0 * 0.0016)), style="double")
    med = ornaments.medallion(int(W0 * 0.30), GOLD)
    for (px, py) in [(-0.15, -0.15), (0.85, -0.15), (-0.15, 0.85), (0.85, 0.85)]:
        img.alpha_composite(med, (int(px * W0 * 0.30 + (0 if px < 0 else W0 - W0 * 0.30 * 0.85 - W0 * 0.30 * 0.15)),
                                  int(py * W0 * 0.30 + (0 if py < 0 else H0 - W0 * 0.30 * 0.85 - W0 * 0.30 * 0.15))))
    # (quarter medallions peeking from corners)

    lab = latin_line(label, int(H0 * 0.015), GOLD)
    img.alpha_composite(lab, (int(cx - lab.width / 2), int(H0 * 0.845)))
    tr = translation_block(translation, int(W0 * 0.64), int(H0 * 0.013), CREAM + (220,))
    img.alpha_composite(tr, (int(cx - tr.width / 2), int(H0 * 0.885)))
    return save(img, slug)


# ------------------------------------------------------------------ mihrab --
def mihrab(verse, label, translation, slug):
    SAND, DEEP, GOLD, INK = hx("#E8DCC4"), hx("#9C5B33"), hx("#B98A2E"), hx("#33291D")
    img = Image.new("RGBA", (W0, H0), SAND + (255,))
    d = ImageDraw.Draw(img)

    # mihrab niche: filled arch shape
    ax0, ax1 = W0 * 0.14, W0 * 0.86
    ay_apex, ay_spring, ay_base = H0 * 0.075, H0 * 0.30, H0 * 0.72
    cxm = (ax0 + ax1) / 2

    def arch_pts(x0, x1, ya, ys, yb, n=60):
        c = (x0 + x1) / 2
        pts = [(x0, yb), (x0, ys)]
        for i in range(n + 1):
            t = i / n
            xx = x0 + (c - x0) * t
            yy = ys - (ys - ya) * math.sin(t * math.pi / 2) ** 1.15
            pts.append((xx, yy))
        for i in range(n + 1):
            t = i / n
            xx = c + (x1 - c) * t
            yy = ya + (ys - ya) * (1 - math.cos(t * math.pi / 2) ** 1.15)
            pts.append((xx, yy))
        pts += [(x1, yb)]
        return pts

    d.polygon(arch_pts(ax0, ax1, ay_apex, ay_spring, ay_base), fill=DEEP + (255,))
    inset = W0 * 0.016
    d.polygon(arch_pts(ax0 + inset, ax1 - inset, ay_apex + inset * 1.6,
                       ay_spring + inset * 0.4, ay_base - inset * 0.5), fill=hx("#8A4E2B") + (255,))

    # verse inside the niche: lines step to the arch (narrow top, wide below)
    words = [w for w in verse.split() if w.strip()]
    n = max(3, min(10, round(len(words) / 3.0)))
    zone_top, zone_bot = ay_apex + H0 * 0.06, ay_base - H0 * 0.05
    zh = (zone_bot - zone_top) / n
    wi = 0
    weights = [0.34 + 0.66 * math.sin(math.pi / 2 * min(1, (i + 0.6) / (n * 0.62))) for i in range(n)]
    tot = sum(weights)
    for i in range(n):
        take = max(1, round(len(words) * weights[i] / tot))
        line = words[wi:] if i == n - 1 else words[wi:wi + take]
        wi += len(line)
        if not line:
            break
        maxw = (ax1 - ax0) * (0.30 + 0.52 * math.sin(math.pi / 2 * min(1, (i + 0.8) / (n * 0.7))))
        li = arabic_text.render_arabic_fitted(
            " ".join(line), AMIRI, color=hx("#F5E9D0"),
            max_width=int(maxw), target_height=int(zh * 0.56))
        img.alpha_composite(li, (int(cxm - li.width / 2), int(zone_top + i * zh + (zh - li.height) / 2)))
        if wi >= len(words):
            break

    band = ornaments.eightfold_rosette_grid(int(W0 * 0.72), int(H0 * 0.045), GOLD, cells=8.0, line=0.010)
    img.alpha_composite(band, (int(W0 * 0.14), int(H0 * 0.755)))

    lab = latin_line(label, int(H0 * 0.0155), hx("#7A4526"))
    img.alpha_composite(lab, (int(W0 / 2 - lab.width / 2), int(H0 * 0.845)))
    tr = translation_block(translation, int(W0 * 0.62), int(H0 * 0.0128), INK + (225,))
    img.alpha_composite(tr, (int(W0 / 2 - tr.width / 2), int(H0 * 0.885)))
    return save(img, slug)


# ------------------------------------------------------------------- hilye --
def hilye(verse, label, translation, slug):
    PARCH, GOLD, INK, ACC = hx("#F3EBD9"), hx("#B08D3C"), hx("#2E2A22"), hx("#20574F")
    img = Image.new("RGBA", (W0, H0), PARCH + (255,))
    d = ImageDraw.Draw(img)

    ornaments.draw_border(img, GOLD, inset=int(W0 * 0.04), gap=int(W0 * 0.012),
                          width=max(2, int(W0 * 0.0014)), style="double")

    cx, cy, R = W0 / 2, H0 * 0.40, W0 * 0.30
    # corner roundels (top pair between border and disc)
    for (fx, fy) in [(0.16, 0.13), (0.84, 0.13), (0.16, 0.67), (0.84, 0.67)]:
        rr = W0 * 0.075
        px, py = W0 * fx, H0 * fy
        d.ellipse([px - rr, py - rr, px + rr, py + rr], fill=ACC + (255,))
        d.ellipse([px - rr * 0.86, py - rr * 0.86, px + rr * 0.86, py + rr * 0.86],
                  outline=GOLD, width=max(2, int(W0 * 0.0016)))
        star = ornaments.geometric(int(rr * 0.9), GOLD)
        img.alpha_composite(star, (int(px - rr * 0.45), int(py - rr * 0.45)))

    d.ellipse([cx - R * 1.03, cy - R * 1.03, cx + R * 1.03, cy + R * 1.03], fill=GOLD + (255,))
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=hx("#FBF6EA") + (255,))
    for li, y in fit_verse_in_circle(verse, R * 0.90, INK):
        img.alpha_composite(li, (int(cx - li.width / 2), int(cy + y * R * 0.90 - li.height / 2)))

    lab = latin_line(label, int(H0 * 0.015), ACC)
    img.alpha_composite(lab, (int(cx - lab.width / 2), int(H0 * 0.80)))
    tr = translation_block(translation, int(W0 * 0.60), int(H0 * 0.0128), INK + (230,))
    img.alpha_composite(tr, (int(cx - tr.width / 2), int(H0 * 0.845)))
    return save(img, slug)


# ------------------------------------------------------------------ radiant --
def radiant(verse, label, translation, slug):
    PLUM, GOLD, CREAM = hx("#3A1E33"), hx("#D3A94F"), hx("#F4EAD5")
    img = Image.new("RGBA", (W0, H0), PLUM + (255,))
    d = ImageDraw.Draw(img)
    cx, cy, R = W0 / 2, H0 * 0.42, W0 * 0.30

    # rays
    ray = Image.new("RGBA", (W0, H0), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ray)
    for k in range(48):
        a = 2 * math.pi * k / 48
        r0, r1 = R * 1.10, R * (1.55 if k % 2 == 0 else 1.34)
        w = W0 * (0.006 if k % 2 == 0 else 0.003)
        x0, y0 = cx + r0 * math.cos(a), cy + r0 * math.sin(a)
        x1, y1 = cx + r1 * math.cos(a), cy + r1 * math.sin(a)
        rd.line([x0, y0, x1, y1], fill=GOLD + (200 if k % 2 == 0 else 130,), width=int(w))
    img.alpha_composite(ray)

    d.ellipse([cx - R * 1.05, cy - R * 1.05, cx + R * 1.05, cy + R * 1.05], fill=GOLD + (255,))
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=CREAM + (255,))
    for li, y in fit_verse_in_circle(verse, R * 0.90, hx("#2C2418")):
        img.alpha_composite(li, (int(cx - li.width / 2), int(cy + y * R * 0.90 - li.height / 2)))

    lab = latin_line(label, int(H0 * 0.015), GOLD)
    img.alpha_composite(lab, (int(cx - lab.width / 2), int(H0 * 0.85)))
    tr = translation_block(translation, int(W0 * 0.62), int(H0 * 0.0128), CREAM + (225,))
    img.alpha_composite(tr, (int(cx - tr.width / 2), int(H0 * 0.888)))
    return save(img, slug)


# ------------------------------------------------------------------ duotone --
def duotone(verse, label, translation, slug):
    TOP, BOT = hx("#EFE6D3"), hx("#1F3A33")
    INK_ON_TOP, INK_ON_BOT = hx("#1F3A33"), hx("#EFE6D3")
    split = 0.52
    img = Image.new("RGBA", (W0, H0), TOP + (255,))
    d = ImageDraw.Draw(img)
    d.rectangle([0, int(H0 * split), W0, H0], fill=BOT + (255,))

    margin = int(W0 * 0.08)
    target_h = int(H0 * 0.60)
    size = int(H0 * 0.055)
    body = None
    for _ in range(8):
        cand_dark = arabic_text.render_arabic_paragraph(
            verse, AMIRI_B, color=INK_ON_TOP, max_width=W0 - 2 * margin,
            font_size=size, leading=1.5)
        if cand_dark.height > target_h:
            break
        body = (cand_dark, size)
        size = int(size * 1.2)
    body_dark = body[0]
    body_light = arabic_text.render_arabic_paragraph(
        verse, AMIRI_B, color=INK_ON_BOT, max_width=W0 - 2 * margin,
        font_size=body[1], leading=1.5)

    x0 = (W0 - body_dark.width) // 2
    y0 = int(H0 * 0.09) + (target_h - body_dark.height) // 2
    ysplit = int(H0 * split)

    top_part = body_dark.crop((0, 0, body_dark.width, max(0, min(body_dark.height, ysplit - y0))))
    img.alpha_composite(top_part, (x0, y0))
    if y0 + body_light.height > ysplit:
        cut = max(0, ysplit - y0)
        bot_part = body_light.crop((0, cut, body_light.width, body_light.height))
        img.alpha_composite(bot_part, (x0, y0 + cut))

    lab = latin_line(label, int(H0 * 0.015), INK_ON_BOT)
    img.alpha_composite(lab, (margin, int(H0 * 0.875)))
    tr = translation_block(translation, int(W0 * 0.55), int(H0 * 0.0125),
                           INK_ON_BOT + (215,), align="left", max_lines=2)
    img.alpha_composite(tr, (margin, int(H0 * 0.905)))
    return save(img, slug)


DESIGNS = {
    "illuminated": illuminated,
    "mihrab": mihrab,
    "hilye": hilye,
    "radiant": radiant,
    "duotone": duotone,
}

if __name__ == "__main__":
    data = json.loads((ROOT / "data" / "sacred_texts.json").read_text(encoding="utf-8"))
    made = []
    for key in ("bismillah", "ikhlas_1"):
        e = data[key]
        assert e["verified"]
        label = e["label"]
        for name, fn in DESIGNS.items():
            slug = f"{key}_{name}"
            made.append(fn(e["arabic_uthmani"], label, e["translation"], slug))
            print("ok", slug, flush=True)

    thumbs = [Image.open(p) for p in made]
    th, pad, cols = 640, 24, 5
    thumbs = [t.resize((int(t.width * th / t.height), th), Image.LANCZOS) for t in thumbs]
    tw = max(t.width for t in thumbs)
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (tw + pad) + pad, rows * (th + pad) + pad), (245, 243, 238))
    for i, t in enumerate(thumbs):
        r, c = divmod(i, cols)
        sheet.paste(t, (pad + c * (tw + pad) + (tw - t.width) // 2, pad + r * (th + pad)))
    sheet.save(OUT / "_REVIEW_verse2.png")
    print("sheet:", OUT / "_REVIEW_verse2.png")
