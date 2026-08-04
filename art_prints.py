#!/usr/bin/env python3
"""
art_prints.py - full-bleed generative wall-art prints (non-Islamic line).

Each piece is a complete composition drawn in code (no text, no external
assets, license-clean like ornaments.py). Rendered at A3 @ 300 DPI with 2x
supersampling + subtle print grain, exported as print.png + print.pdf into
output/staging_cool_art/<name>/.

Pieces (popular, searched Etsy categories - executed as cohesive designs):
  boho_arches     - nested terracotta arch bands + sun, warm neutrals
  sun_horizon     - big sun over layered wavy dunes, warm gradient sky
  mountain_layers - misty layered ridgelines, light-to-ink depth
  flow_ribbons    - flowing translucent ribbons on deep navy
  organic_shapes  - mid-century matisse-style cutout shapes + squiggles
  circle_stack    - bauhaus overlapping circles, off-center balance
"""
from __future__ import annotations

import gc
import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdfcanvas

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "staging_cool_art"
W0, H0 = 3508, 4961  # A3 @ 300 DPI
SS = 2               # supersample factor


# ------------------------------------------------------------------ helpers --
def hx(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def vgrad(w: int, h: int, c0, c1) -> Image.Image:
    col = Image.new("RGB", (1, h))
    px = col.load()
    for y in range(h):
        t = y / (h - 1)
        px[0, y] = tuple(round(c0[i] + (c1[i] - c0[i]) * t) for i in range(3))
    return col.resize((w, h))


def add_grain(img: Image.Image, strength: float = 0.05) -> Image.Image:
    """Subtle film-grain so flat fields read as printed art, not vector fill."""
    noise = Image.effect_noise(img.size, 22).convert("RGB")
    try:
        overlaid = ImageChops.overlay(img.convert("RGB"), noise)
    except Exception:
        overlaid = ImageChops.multiply(img.convert("RGB"), noise)
    return Image.blend(img.convert("RGB"), overlaid, strength)


def smooth_open(pts, samples=18):
    """Catmull-Rom through open point list."""
    if len(pts) < 3:
        return list(pts)
    ext = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for j in range(samples):
            t = j / samples
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t
                       + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                       + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t
                       + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                       + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    out.append(pts[-1])
    return out


def smooth_closed(pts, samples=16):
    """Catmull-Rom around a closed point loop -> organic blob outline."""
    n = len(pts)
    out = []
    for i in range(n):
        p0, p1, p2, p3 = pts[(i - 1) % n], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        for j in range(samples):
            t = j / samples
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t
                       + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                       + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t
                       + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                       + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    return out


def blob(cx, cy, r, wobble=0.22, n=12, seed=0):
    rnd = random.Random(seed)
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        rr = r * (1 + rnd.uniform(-wobble, wobble))
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return smooth_closed(pts)


# ------------------------------------------------------------------- pieces --
def boho_arches(W, H):
    bg = hx("#F4EDE3")
    img = Image.new("RGBA", (W, H), bg + (255,))
    d = ImageDraw.Draw(img)

    bands = ["#C67B5C", "#E3C099", "#A64B2A", "#DDA15E", "#8A9B6E", "#F4EDE3"]
    cx, base = W * 0.5, H * 0.66
    R = W * 0.38
    foot = H * 0.88

    for i, col in enumerate(bands):
        r = R * (1 - i * 0.155)
        c = hx(col)
        d.pieslice([cx - r, base - r, cx + r, base + r], 180, 360, fill=c)
        d.rectangle([cx - r, base, cx + r, foot], fill=c)

    # sun disc, offset high right
    sr = W * 0.085
    sx, sy = W * 0.76, H * 0.155
    d.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=hx("#A64B2A"))

    # dotted halo arc above the arch
    ink = hx("#4A3B2E")
    for k in range(11):
        a = math.pi * (0.15 + 0.7 * k / 10)
        rr = R * 1.14
        px, py = cx + rr * math.cos(math.pi + a * 0), base - rr * math.sin(a)
        px = cx + rr * math.cos(math.pi + (math.pi * (0.12 + 0.76 * k / 10)))
        py = base + rr * math.sin(math.pi + (math.pi * (0.12 + 0.76 * k / 10)))
        dr = W * 0.006
        d.ellipse([px - dr, py - dr, px + dr, py + dr], fill=ink)

    # grounding lines under the arch feet
    for j, wfrac in enumerate((0.56, 0.40)):
        y = foot + H * 0.025 + j * H * 0.022
        d.line([cx - W * wfrac / 2, y, cx + W * wfrac / 2, y], fill=ink, width=max(2, int(W * 0.0016)))
    return img


def sun_horizon(W, H):
    img = vgrad(W, H, hx("#F6E7D3"), hx("#EFC9A0")).convert("RGBA")
    d = ImageDraw.Draw(img)

    # halo + sun
    scx, scy, sr = W * 0.5, H * 0.335, W * 0.235
    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse([scx - sr * 1.5, scy - sr * 1.5, scx + sr * 1.5, scy + sr * 1.5],
                                 fill=hx("#F2B279") + (90,))
    img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(int(W * 0.03))))
    d.ellipse([scx - sr, scy - sr, scx + sr, scy + sr], fill=hx("#E07A5F"))

    # layered dunes (wavy bands)
    bands = [("#F2E4CF", 0.545, 0.030), ("#D9B48A", 0.645, 0.038),
             ("#B07156", 0.745, 0.044), ("#5C3A2E", 0.850, 0.050)]
    rnd = random.Random(7)
    for col, yfrac, amp in bands:
        phase = rnd.uniform(0, 6.28)
        pts = []
        for x in range(0, W + 40, 40):
            y = H * yfrac + H * amp * (0.6 * math.sin(2.2 * math.pi * x / W + phase)
                                       + 0.4 * math.sin(4.7 * math.pi * x / W + phase * 1.7))
            pts.append((x, y))
        poly = pts + [(W, H), (0, H)]
        d.polygon(poly, fill=hx(col))
    return img


def mountain_layers(W, H):
    img = vgrad(W, H, hx("#EFE9E1"), hx("#E4DACC")).convert("RGBA")
    d = ImageDraw.Draw(img)

    # pale sun
    sr = W * 0.10
    sx, sy = W * 0.70, H * 0.185
    d.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=hx("#DDBE97"))

    ridges = [("#D8D2C4", 0.42, 0.020), ("#BFB6A4", 0.52, 0.028),
              ("#9A917F", 0.62, 0.034), ("#6E6A5E", 0.72, 0.040),
              ("#474A45", 0.82, 0.046), ("#2C3134", 0.92, 0.050)]
    rnd = random.Random(3)
    for col, yfrac, amp in ridges:
        p1, p2, p3 = (rnd.uniform(0, 6.28) for _ in range(3))
        pts = []
        for x in range(0, W + 30, 30):
            t = x / W
            y = H * yfrac + H * amp * (0.5 * math.sin(2 * math.pi * (1.3 * t) + p1)
                                       + 0.3 * math.sin(2 * math.pi * (2.9 * t) + p2)
                                       + 0.2 * math.sin(2 * math.pi * (5.3 * t) + p3))
            pts.append((x, y))
        # mist above each ridge for depth
        mist = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(mist).polygon(pts + [(W, H), (0, H)], fill=hx("#FFFFFF") + (26,))
        img.alpha_composite(mist.filter(ImageFilter.GaussianBlur(int(H * 0.008))))
        d.polygon(pts + [(W, H), (0, H)], fill=hx(col))
    return img


def flow_ribbons(W, H):
    img = vgrad(W, H, hx("#101A2E"), hx("#1D2C4C")).convert("RGBA")

    ribbons = [("#E9C46A", 0.24, 0.085, 215), ("#F4A261", 0.42, 0.070, 195),
               ("#9AC1B8", 0.60, 0.075, 185), ("#E76F51", 0.78, 0.090, 205)]
    rnd = random.Random(11)
    for col, yfrac, wfrac, alpha in ribbons:
        y0 = H * yfrac
        p0 = (-W * 0.05, y0 + rnd.uniform(-0.05, 0.05) * H)
        p1 = (W * rnd.uniform(0.20, 0.38), y0 + rnd.uniform(-0.16, 0.16) * H)
        p2 = (W * rnd.uniform(0.62, 0.80), y0 + rnd.uniform(-0.16, 0.16) * H)
        p3 = (W * 1.05, y0 + rnd.uniform(-0.05, 0.05) * H)
        n = 140
        center = []
        for i in range(n + 1):
            t = i / n
            u = 1 - t
            x = u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0]
            y = u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1]
            center.append((x, y))
        left, right = [], []
        wmax = W * wfrac
        for i, (x, y) in enumerate(center):
            if i == 0:
                dx, dy = center[1][0] - x, center[1][1] - y
            else:
                dx, dy = x - center[i - 1][0], y - center[i - 1][1]
            ln = math.hypot(dx, dy) or 1
            nx, ny = -dy / ln, dx / ln
            t = i / n
            wdt = wmax * (math.sin(math.pi * min(max(t, 0.02), 0.98)) ** 0.6) / 2
            left.append((x + nx * wdt, y + ny * wdt))
            right.append((x - nx * wdt, y - ny * wdt))
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(layer).polygon(left + right[::-1], fill=hx(col) + (alpha,))
        img.alpha_composite(layer)

    # sparse star dots
    d = ImageDraw.Draw(img)
    for _ in range(26):
        x, y = rnd.uniform(0.06, 0.94) * W, rnd.uniform(0.05, 0.95) * H
        r = rnd.uniform(0.0012, 0.0030) * W
        d.ellipse([x - r, y - r, x + r, y + r], fill=hx("#F2E9DC") + (rnd.randint(90, 200),))
    return img


def organic_shapes(W, H):
    img = Image.new("RGBA", (W, H), hx("#F5F0E6") + (255,))
    d = ImageDraw.Draw(img)
    ink = hx("#26323B")

    palette = ["#E76F51", "#2A9D8F", "#E9C46A", "#264653", "#C67B5C", "#8A9B6E", "#D5896F"]
    rnd = random.Random(21)
    cells = [(cx, cy) for cy in (0.20, 0.50, 0.80) for cx in (0.25, 0.75)]
    rnd.shuffle(cells)
    for i, (cx, cy) in enumerate(cells):
        col = palette[i % len(palette)]
        r = W * rnd.uniform(0.11, 0.165)
        x = (cx + rnd.uniform(-0.05, 0.05)) * W
        y = (cy + rnd.uniform(-0.04, 0.04)) * H
        d.polygon(blob(x, y, r, wobble=0.24, n=11, seed=100 + i), fill=hx(col))

    # two ink squiggles across gaps
    for k, yf in enumerate((0.36, 0.66)):
        pts = [(W * (0.10 + 0.16 * j + rnd.uniform(-0.02, 0.02)),
                H * (yf + rnd.uniform(-0.045, 0.045))) for j in range(6)]
        d.line(smooth_open(pts), fill=ink, width=max(3, int(W * 0.0035)), joint="curve")

    # small hollow circles as accents
    for _ in range(5):
        x, y = rnd.uniform(0.08, 0.92) * W, rnd.uniform(0.06, 0.94) * H
        r = W * rnd.uniform(0.014, 0.026)
        d.ellipse([x - r, y - r, x + r, y + r], outline=ink, width=max(3, int(W * 0.0028)))
    return img


def circle_stack(W, H):
    img = Image.new("RGBA", (W, H), hx("#F2E9DC") + (255,))

    def disc(cx, cy, r, col, alpha=235):
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(layer).ellipse([cx - r, cy - r, cx + r, cy + r], fill=hx(col) + (alpha,))
        img.alpha_composite(layer)

    disc(W * 0.40, H * 0.335, W * 0.315, "#264653")
    disc(W * 0.635, H * 0.520, W * 0.235, "#E76F51", 225)
    disc(W * 0.455, H * 0.665, W * 0.165, "#E9C46A", 235)
    disc(W * 0.30, H * 0.56, W * 0.085, "#2A9D8F", 235)

    d = ImageDraw.Draw(img)
    d.ellipse([W * 0.66 - W * 0.125, H * 0.245 - W * 0.125, W * 0.66 + W * 0.125, H * 0.245 + W * 0.125],
              outline=hx("#26323B"), width=max(4, int(W * 0.005)))
    r = W * 0.022
    d.ellipse([W * 0.755 - r, H * 0.73 - r, W * 0.755 + r, H * 0.73 + r], fill=hx("#26323B"))
    # baseline rule for grounding
    d.line([W * 0.16, H * 0.875, W * 0.84, H * 0.875], fill=hx("#26323B"), width=max(3, int(W * 0.0022)))
    return img


# -------------------------------------------------------------------- runner --
PIECES = {
    "boho_arches": boho_arches,
    "sun_horizon": sun_horizon,
    "mountain_layers": mountain_layers,
    "flow_ribbons": flow_ribbons,
    "organic_shapes": organic_shapes,
    "circle_stack": circle_stack,
}


def export(name: str, fn) -> Path:
    Wss, Hss = W0 * SS, H0 * SS
    art = fn(Wss, Hss)
    art = art.resize((W0, H0), Image.LANCZOS)
    art = add_grain(art, 0.05)

    folder = OUT / name
    folder.mkdir(parents=True, exist_ok=True)
    png = folder / f"{name}_print.png"
    art.save(png, "PNG")

    page = (W0 / 300.0 * 72.0, H0 / 300.0 * 72.0)
    pdf = folder / f"{name}_print.pdf"
    c = pdfcanvas.Canvas(str(pdf), pagesize=page)
    c.drawImage(ImageReader(art), 0, 0, width=page[0], height=page[1])
    c.showPage()
    c.save()

    del art
    gc.collect()
    return png


def contact_sheet(paths, cols=3, thumb_h=900):
    thumbs = []
    for p in paths:
        im = Image.open(p)
        w = int(im.width * thumb_h / im.height)
        thumbs.append(im.resize((w, thumb_h), Image.LANCZOS))
    tw = max(t.width for t in thumbs)
    pad = 40
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (tw + pad) + pad, rows * (thumb_h + pad) + pad), (245, 243, 238))
    for i, t in enumerate(thumbs):
        r, c = divmod(i, cols)
        sheet.paste(t, (pad + c * (tw + pad) + (tw - t.width) // 2, pad + r * (thumb_h + pad)))
    out = OUT / "_REVIEW_prints.png"
    sheet.save(out, "PNG")
    return out


if __name__ == "__main__":
    made = []
    for name, fn in PIECES.items():
        print(f"rendering {name} ...", flush=True)
        made.append(export(name, fn))
        print(f"  done: {made[-1]}")
    sheet = contact_sheet(made)
    print(f"review sheet: {sheet}")
