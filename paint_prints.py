#!/usr/bin/env python3
"""
paint_prints.py - painterly nature wall-art prints (non-Islamic line).

Simulated paint: every piece is built from thousands of individual brush dabs
and strokes with per-dab colour/size/angle jitter, watercolor blob washes with
edge bleed, and canvas grain. No text, no external assets - license-clean.

Niches (validated against Etsy bestsellers + 2026 trend reports):
  meadow_poppies       - impressionist wildflower meadow (poppies/daisies)
  watercolor_botanical - soft eucalyptus stems, watercolor
  moody_blooms         - dark moody florals, oil-paint look
  abstract_coast       - painterly ocean + foam
  mountain_gold        - textured abstract landscape, warm sun
  forest_mist          - misty pine forest, layered atmosphere

Output: output/staging_cool_art/<name>/<name>_print.png + .pdf (A3 @ 300 DPI).
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
W0, H0 = 3508, 4961
SS = 2


# ------------------------------------------------------------------ helpers --
def hx(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def jit(rnd, c, amt=14):
    """Jitter a colour +-amt per channel — makes flat fields read as paint."""
    return tuple(max(0, min(255, v + rnd.randint(-amt, amt))) for v in c)


def vgrad(w, h, stops):
    """Vertical multi-stop gradient. stops: [(t, (r,g,b)), ...] sorted by t."""
    col = Image.new("RGB", (1, h))
    px = col.load()
    for y in range(h):
        t = y / (h - 1)
        for i in range(len(stops) - 1):
            t0, c0 = stops[i]
            t1, c1 = stops[i + 1]
            if t0 <= t <= t1:
                f = (t - t0) / (t1 - t0) if t1 > t0 else 0
                px[0, y] = tuple(round(c0[k] + (c1[k] - c0[k]) * f) for k in range(3))
                break
        else:
            px[0, y] = stops[-1][1]
    return col.resize((w, h))


def dab(d, x, y, r, color, angle, elong=2.2, alpha=255):
    """One elliptical brush dab (rotated ellipse approximated by a thick line)."""
    dx, dy = math.cos(angle) * r * elong / 2, math.sin(angle) * r * elong / 2
    d.line([x - dx, y - dy, x + dx, y + dy], fill=color + (alpha,), width=max(1, int(r)))


def stroke(d, pts, color, width, alpha=255):
    d.line(pts, fill=color + (alpha,), width=max(1, int(width)), joint="curve")


def smooth_open(pts, samples=14):
    """Catmull-Rom spline through an open point list -> gestural curve."""
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


def canvas_texture(img, strength=0.06):
    """Fine noise + a faint weave so flats look like primed canvas."""
    noise = Image.effect_noise(img.size, 26).convert("RGB")
    out = Image.blend(img.convert("RGB"), ImageChops.overlay(img.convert("RGB"), noise), strength)
    return out


def wash(img, cx, cy, rx, ry, color, alpha=40, blur=0.05, rim=1.35, seed=0):
    """Watercolor blob: soft fill + slightly darker irregular rim (edge bleed)."""
    W, H = img.size
    rnd = random.Random(seed)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    pts = []
    n = 16
    for i in range(n):
        a = 2 * math.pi * i / n
        rr = 1 + rnd.uniform(-0.18, 0.18)
        pts.append((cx + rx * rr * math.cos(a), cy + ry * rr * math.sin(a)))
    ld.polygon(pts, fill=color + (alpha,))
    rim_c = tuple(int(v * 0.82) for v in color)
    ld.line(pts + [pts[0]], fill=rim_c + (int(alpha * rim),), width=max(2, int(min(rx, ry) * 0.045)))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(int(min(W, H) * blur))))


# ------------------------------------------------------------------- pieces --
def meadow_poppies(W, H):
    rnd = random.Random(42)
    # hazy warm sky into pale field
    img = vgrad(W, H, [(0.0, hx("#F3E9D5")), (0.42, hx("#EDE3C8")),
                       (0.55, hx("#CFCB9B")), (1.0, hx("#77854A"))]).convert("RGBA")
    d = ImageDraw.Draw(img, "RGBA")

    horizon = 0.46 * H
    # meadow underpainting: broad horizontal strokes darkening toward viewer
    for _ in range(1800):
        y = horizon + (rnd.random() ** 1.4) * (H - horizon)
        depth = (y - horizon) / (H - horizon)
        base = (hx("#B4B575") if depth < 0.3 else
                hx("#8D9A55") if depth < 0.65 else hx("#5F7038"))
        c = jit(rnd, base, 20)
        r = (6 + 26 * depth) * W / 3508
        dab(d, rnd.uniform(-0.02, 1.02) * W, y, r, c,
            rnd.uniform(-0.10, 0.10), elong=rnd.uniform(4, 7), alpha=rnd.randint(100, 190))

    # grass blades: gestural curved strokes, denser + taller near the bottom
    for _ in range(700):
        depth = rnd.random() ** 1.3
        y0 = horizon + depth * (H - horizon) * 1.02
        x0 = rnd.uniform(-0.02, 1.02) * W
        hgt = H * (0.015 + 0.14 * depth ** 1.7) * rnd.uniform(0.6, 1.3)
        lean = rnd.uniform(-0.45, 0.45) * hgt
        pts = [(x0, y0), (x0 + lean * 0.4, y0 - hgt * 0.55), (x0 + lean, y0 - hgt)]
        c = jit(rnd, hx("#55663A") if depth > 0.5 else hx("#7E8F4E"), 20)
        stroke(d, smooth_open_pts(pts), c, (1.5 + 6 * depth) * W / 3508,
               alpha=rnd.randint(120, 210))

    def poppy(x, y, R, seed):
        r = random.Random(seed)
        col = jit(r, hx("#C7402D"), 20)
        # 4-5 big ragged petals: overlapping fat dabs around centre
        n = r.randint(4, 5)
        for i in range(n):
            a = 2 * math.pi * i / n + r.uniform(-0.25, 0.25)
            px, py = x + R * 0.52 * math.cos(a), y + R * 0.52 * math.sin(a) * 0.85
            pc = tuple(max(0, min(255, v + r.randint(-24, 18))) for v in col)
            dab(d, px, py, R * 0.55, pc, a + r.uniform(-0.3, 0.3),
                elong=1.6, alpha=r.randint(200, 240))
        # petal highlight
        dab(d, x - R * 0.2, y - R * 0.25, R * 0.35, jit(r, hx("#E06048"), 12),
            r.uniform(0, 3), 1.5, 160)
        # dark centre + tiny stamen dots
        d.ellipse([x - R * 0.16, y - R * 0.14, x + R * 0.16, y + R * 0.14],
                  fill=hx("#241F1B") + (235,))
        for _ in range(6):
            aa = r.uniform(0, 2 * math.pi)
            sx, sy = x + R * 0.20 * math.cos(aa), y + R * 0.19 * math.sin(aa)
            rr = R * 0.03
            d.ellipse([sx - rr, sy - rr, sx + rr, sy + rr], fill=hx("#3B342C") + (220,))

    def daisy(x, y, R, seed):
        r = random.Random(seed)
        for i in range(r.randint(8, 10)):
            a = 2 * math.pi * i / 9 + r.uniform(-0.15, 0.15)
            px, py = x + R * 0.5 * math.cos(a), y + R * 0.5 * math.sin(a) * 0.9
            dab(d, px, py, R * 0.30, jit(r, hx("#EFEADB"), 8), a,
                elong=2.6, alpha=r.randint(200, 245))
        d.ellipse([x - R * 0.16, y - R * 0.15, x + R * 0.16, y + R * 0.15],
                  fill=jit(r, hx("#D9A441"), 12) + (240,))

    def cornflower(x, y, R, seed):
        r = random.Random(seed)
        for i in range(6):
            a = 2 * math.pi * i / 6 + r.uniform(-0.2, 0.2)
            px, py = x + R * 0.42 * math.cos(a), y + R * 0.42 * math.sin(a)
            dab(d, px, py, R * 0.34, jit(r, hx("#5B6FA8"), 18), a, 1.8, r.randint(190, 235))
        d.ellipse([x - R * 0.1, y - R * 0.1, x + R * 0.1, y + R * 0.1],
                  fill=hx("#2C3557") + (230,))

    # distant flower speckle (small, sparse, above mid)
    for _ in range(420):
        depth = rnd.uniform(0.08, 0.45)
        y = horizon + depth * (H - horizon)
        x = rnd.uniform(0, W)
        col = rnd.choice([hx("#C7402D"), hx("#E8E4D8"), hx("#5B6FA8"), hx("#D9A441")])
        r = (2 + 6 * depth) * W / 3508
        dab(d, x, y, r, jit(rnd, col, 14), rnd.uniform(0, 3), 1.3, rnd.randint(150, 220))

    # mid + foreground blooms with stems (big, the hook of the piece)
    blooms = []
    for i in range(46):
        depth = 0.45 + 0.55 * (rnd.random() ** 0.8)
        y = horizon + depth * (H - horizon)
        x = rnd.uniform(0.02, 0.98) * W
        R = W * (0.008 + 0.040 * (depth - 0.45) / 0.55) * rnd.uniform(0.75, 1.3)
        blooms.append((y, x, R, i))
    blooms.sort()          # paint back to front
    for y, x, R, i in blooms:
        # stem
        sway = rnd.uniform(-0.3, 0.3) * R * 3
        pts = [(x, y + R * 3.2), (x + sway * 0.5, y + R * 1.6), (x + sway * 0.2, y)]
        stroke(d, smooth_open_pts(pts), jit(rnd, hx("#4E5F33"), 14),
               max(2, R * 0.10), alpha=200)
        kind = rnd.random()
        if kind < 0.55:
            poppy(x, y, R, 500 + i)
        elif kind < 0.8:
            daisy(x, y, R * 0.9, 700 + i)
        else:
            cornflower(x, y, R * 0.8, 900 + i)
    return img


def smooth_open_pts(pts, samples=14):
    return smooth_open(pts, samples)


def watercolor_botanical(W, H):
    rnd = random.Random(9)
    img = Image.new("RGBA", (W, H), hx("#FBF9F3") + (255,))

    # faint background washes — one soft layer, blurred together (no ring artifacts)
    washes = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    wd = ImageDraw.Draw(washes)
    for cx, cy, rx, ry, col, a in [
            (0.30, 0.28, 0.34, 0.26, "#DFE7D3", 90), (0.72, 0.60, 0.30, 0.26, "#EAE3CB", 80),
            (0.52, 0.82, 0.30, 0.20, "#DCE4D0", 70)]:
        wd.ellipse([W * cx - W * rx, H * cy - H * ry, W * cx + W * rx, H * cy + H * ry],
                   fill=hx(col) + (a,))
    img.alpha_composite(washes.filter(ImageFilter.GaussianBlur(int(W * 0.10))))

    d = ImageDraw.Draw(img, "RGBA")
    greens = [hx("#7C8F6D"), hx("#93A585"), hx("#5F7355"), hx("#A9B896"), hx("#86977A")]

    def leaf_shape(cx, cy, L, Wd, ang, col, alpha):
        """Pointed-oval watercolor leaf with layered fill, rim + centre vein."""
        ca, sa = math.cos(ang), math.sin(ang)
        px, py = -sa, ca
        tip = (cx + ca * L, cy + sa * L)
        base = (cx - ca * L * 0.12, cy - sa * L * 0.12)
        # two mirrored quadratic sides -> leaf outline
        side1 = _quad(base, (cx + ca * L * 0.42 + px * Wd, cy + sa * L * 0.42 + py * Wd), tip, 20)
        side2 = _quad(tip, (cx + ca * L * 0.42 - px * Wd, cy + sa * L * 0.42 - py * Wd), base, 20)
        outline = side1 + side2
        # layered translucent fills (watercolor build-up)
        for fa, shrink in ((alpha, 1.0), (int(alpha * 0.6), 0.8)):
            pts = [(base[0] + (x - base[0]) * shrink, base[1] + (y - base[1]) * shrink)
                   for x, y in outline]
            d.polygon(pts, fill=col + (fa,))
        # darker rim + vein
        rim = tuple(int(v * 0.78) for v in col)
        d.line(outline + [outline[0]], fill=rim + (min(255, alpha + 60),),
               width=max(2, int(W * 0.0012)))
        d.line([base, tip], fill=rim + (min(255, alpha + 40),), width=max(2, int(W * 0.0012)))

    def eucalyptus(x0, y0, x1, y1, nleaf, scale, seed):
        r = random.Random(seed)
        n = 60
        pts = []
        for i in range(n + 1):
            t = i / n
            x = x0 + (x1 - x0) * t + math.sin(t * 3.1) * W * 0.02 * r.uniform(0.6, 1.4)
            y = y0 + (y1 - y0) * t
            pts.append((x, y))
        stroke(d, pts, jit(r, hx("#6B7C5E"), 8), W * 0.0028, 210)
        stem_ang = math.atan2(y1 - y0, x1 - x0)
        for i in range(nleaf):
            t = 0.10 + 0.88 * i / nleaf
            px, py = pts[int(t * n)]
            side = -1 if i % 2 == 0 else 1
            L = W * scale * r.uniform(0.9, 1.25) * (1 - 0.30 * t)
            ang = stem_ang + side * r.uniform(0.55, 1.05)
            col = jit(r, greens[i % len(greens)], 14)
            # short petiole then the leaf
            ax, ay = px + math.cos(ang) * L * 0.16, py + math.sin(ang) * L * 0.16
            stroke(d, [(px, py), (ax, ay)], jit(r, hx("#6B7C5E"), 10), W * 0.0018, 180)
            leaf_shape(ax, ay, L, L * 0.34, ang, col, r.randint(95, 130))

    eucalyptus(W * 0.26, H * 0.94, W * 0.40, H * 0.08, 13, 0.085, 11)
    eucalyptus(W * 0.55, H * 0.97, W * 0.70, H * 0.20, 11, 0.075, 22)
    eucalyptus(W * 0.47, H * 0.95, W * 0.34, H * 0.30, 9, 0.062, 33)
    eucalyptus(W * 0.68, H * 0.96, W * 0.82, H * 0.42, 7, 0.055, 44)

    # scattered seed dots
    for _ in range(24):
        x, y = rnd.uniform(0.12, 0.88) * W, rnd.uniform(0.12, 0.9) * H
        r = W * rnd.uniform(0.003, 0.006)
        d.ellipse([x - r, y - r, x + r, y + r], fill=jit(rnd, hx("#A98F63"), 20) + (rnd.randint(50, 110),))
    return img


def _quad(p0, p1, p2, n=20):
    out = []
    for i in range(n):
        t = i / (n - 1)
        u = 1 - t
        out.append((u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
                    u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]))
    return out


def moody_blooms(W, H):
    rnd = random.Random(5)
    img = vgrad(W, H, [(0.0, hx("#131A19")), (0.6, hx("#18211F")), (1.0, hx("#0D1211"))]).convert("RGBA")
    d = ImageDraw.Draw(img, "RGBA")

    def petal(cx, cy, ang, L, Wd, col, alpha):
        """One painted petal: rounded teardrop polygon from centre outward."""
        ca, sa = math.cos(ang), math.sin(ang)
        px, py = -sa, ca
        tip = (cx + ca * L, cy + sa * L)
        base = (cx + ca * L * 0.08, cy + sa * L * 0.08)
        s1 = _quad(base, (cx + ca * L * 0.5 + px * Wd, cy + sa * L * 0.5 + py * Wd), tip, 16)
        s2 = _quad(tip, (cx + ca * L * 0.5 - px * Wd, cy + sa * L * 0.5 - py * Wd), base, 16)
        d.polygon(s1 + s2, fill=col + (alpha,))

    def bloom(cx, cy, R, base, seed):
        r = random.Random(seed)
        # outer ring of big shadowed petals, then two inner rings lighter
        for ring, (rr, wd, n, shade) in enumerate((
                (1.00, 0.42, 8, 0.60), (0.68, 0.36, 6, 0.88), (0.40, 0.30, 5, 1.15))):
            off = r.uniform(0, 2 * math.pi)
            for i in range(n):
                a = off + 2 * math.pi * i / n + r.uniform(-0.10, 0.10)
                c = tuple(max(0, min(255, int(v * shade + r.randint(-12, 12)))) for v in base)
                petal(cx, cy, a, R * rr * r.uniform(0.9, 1.08),
                      R * wd * r.uniform(0.85, 1.1), c, r.randint(215, 245))
        # soft glowing heart
        for rr, col, a in ((0.15, hx("#E5C989"), 120), (0.09, hx("#E8D3A0"), 200),
                           (0.045, hx("#8A6B33"), 220)):
            d.ellipse([cx - R * rr, cy - R * rr * 0.9, cx + R * rr, cy + R * rr * 0.9],
                      fill=jit(r, col, 8) + (a,))

    # stems + leaves first (behind blooms)
    for sx, sy, ex, ey, sd in [(0.30, 1.0, 0.36, 0.42, 1), (0.62, 1.0, 0.55, 0.30, 2),
                               (0.78, 1.0, 0.72, 0.55, 3)]:
        pts = [(W * (sx + (ex - sx) * t + 0.015 * math.sin(4 * t)),
                H * (sy + (ey - sy) * t)) for t in [i / 30 for i in range(31)]]
        stroke(d, pts, hx("#26362E"), W * 0.004, 210)
        for t in (0.35, 0.6):
            px, py = pts[int(t * 30)]
            lr = W * 0.06
            ang = -1.2 if sd % 2 else -1.9
            tip = (px + lr * math.cos(ang), py + lr * math.sin(ang))
            d.polygon([(px, py), (px + lr * 0.45 * math.cos(ang - 0.7), py + lr * 0.45 * math.sin(ang - 0.7)),
                       tip,
                       (px + lr * 0.45 * math.cos(ang + 0.7), py + lr * 0.45 * math.sin(ang + 0.7))],
                      fill=jit(random.Random(sd), hx("#2E4438"), 12) + (200,))

    bloom(W * 0.36, H * 0.38, W * 0.145, hx("#8C4A52"), 7)     # dusty rose
    bloom(W * 0.55, H * 0.26, W * 0.115, hx("#4E6E6A"), 8)     # teal
    bloom(W * 0.72, H * 0.52, W * 0.125, hx("#7A5E74"), 9)     # mauve
    bloom(W * 0.25, H * 0.66, W * 0.085, hx("#9C7C4E"), 10)    # ochre bud

    # falling petals — small teardrops drifting
    for i in range(14):
        x, y = rnd.uniform(0.1, 0.9) * W, rnd.uniform(0.1, 0.95) * H
        c = jit(rnd, rnd.choice([hx("#8C4A52"), hx("#7A5E74")]), 14)
        petal(x, y, rnd.uniform(0, 2 * math.pi), W * rnd.uniform(0.012, 0.022),
              W * rnd.uniform(0.005, 0.009), c, rnd.randint(80, 150))
    return img


def abstract_coast(W, H):
    rnd = random.Random(17)
    img = vgrad(W, H, [(0.0, hx("#E9E3D3")), (0.40, hx("#CFD8D2")),
                       (0.62, hx("#7FA3A1")), (0.80, hx("#3E6D74")), (1.0, hx("#2B4E57"))]).convert("RGBA")
    d = ImageDraw.Draw(img, "RGBA")

    # sky strokes
    for _ in range(900):
        y = rnd.uniform(0, 0.38) * H
        c = jit(rnd, hx("#EAE4D3"), 8)
        dab(d, rnd.uniform(0, W), y, rnd.uniform(5, 14) * W / 3508, c,
            rnd.uniform(-0.05, 0.05), 7, rnd.randint(25, 60))

    # sea: long horizontal strokes, deeper colour with depth + light band at horizon
    for _ in range(3600):
        t = rnd.random() ** 1.3
        y = H * (0.40 + 0.60 * t)
        base = (hx("#BFD4CB") if t < 0.12 else hx("#8FB4AE") if t < 0.35 else
                hx("#537E82") if t < 0.65 else hx("#33565E"))
        c = jit(rnd, base, 14)
        dab(d, rnd.uniform(-0.03, 1.03) * W, y, (3 + 10 * t) * W / 3508, c,
            rnd.uniform(-0.04, 0.04), rnd.uniform(5, 9), rnd.randint(90, 190))

    # foam: soft blended crests painted with overlapping pale dabs (no hard lines)
    for k in range(8):
        yf = H * (0.60 + 0.050 * k) + rnd.uniform(-0.012, 0.012) * H
        x0 = rnd.uniform(-0.10, 0.22) * W
        x1 = x0 + rnd.uniform(0.55, 1.0) * W
        n = 120
        for i in range(n):
            t = i / (n - 1)
            x = x0 + (x1 - x0) * t
            y = yf + math.sin(t * math.pi) * rnd.uniform(-0.015, 0.004) * H \
                + math.sin(t * 8 + k * 1.7) * 0.004 * H
            fade = math.sin(math.pi * t) ** 0.7          # taper at both ends
            r = rnd.uniform(3, 9) * W / 3508 * (0.7 + 0.6 * fade)
            dab(d, x, y, r, jit(rnd, hx("#F2EFE4"), 6),
                rnd.uniform(-0.06, 0.06), rnd.uniform(2.5, 4.5),
                int(rnd.randint(60, 130) * fade))
        # sparse speckle drift below the crest
        for _ in range(40):
            t = rnd.random()
            x = x0 + (x1 - x0) * t
            y = yf + rnd.uniform(0.002, 0.03) * H
            r = W * rnd.uniform(0.0010, 0.0028)
            d.ellipse([x - r, y - r, x + r, y + r],
                      fill=hx("#F2EFE4") + (rnd.randint(40, 100),))

    # pale sun: blurred halo + soft disc painted over the sky strokes
    gx, gy = W * 0.68, H * 0.185
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([gx - W * 0.16, gy - W * 0.16, gx + W * 0.16, gy + W * 0.16],
               fill=hx("#F4E9C8") + (150,))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(int(W * 0.06))))
    disc = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(disc).ellipse([gx - W * 0.055, gy - W * 0.055, gx + W * 0.055, gy + W * 0.055],
                                 fill=hx("#F7EDD2") + (235,))
    img.alpha_composite(disc.filter(ImageFilter.GaussianBlur(int(W * 0.008))))
    # light path shimmer on the water under the sun
    for _ in range(500):
        t = rnd.random()
        y = H * (0.42 + 0.55 * t)
        x = gx + rnd.gauss(0, W * 0.05 * (0.5 + t))
        r = W * rnd.uniform(0.001, 0.004) * (0.6 + t)
        d.ellipse([x - r * 3, y - r * 0.7, x + r * 3, y + r * 0.7],
                  fill=hx("#F2E7C6") + (rnd.randint(40, 110),))
    return img


def mountain_gold(W, H):
    rnd = random.Random(23)
    img = vgrad(W, H, [(0.0, hx("#F0E3CC")), (0.45, hx("#E8CFA4")), (1.0, hx("#D8B183"))]).convert("RGBA")
    d = ImageDraw.Draw(img, "RGBA")

    # big low sun
    sr = W * 0.16
    sx, sy = W * 0.5, H * 0.335
    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse([sx - sr * 1.7, sy - sr * 1.7, sx + sr * 1.7, sy + sr * 1.7],
                                 fill=hx("#EFB973") + (100,))
    img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(int(W * 0.04))))
    d.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=hx("#D98E4A"))

    # ridge silhouettes built from angular strokes (palette-knife feel)
    ridges = [("#B98A5C", 0.47, 0.030), ("#96684A", 0.56, 0.036),
              ("#6E4A3A", 0.66, 0.042), ("#4A332E", 0.77, 0.050), ("#33241F", 0.89, 0.055)]
    for col, yf, amp in ridges:
        p1, p2 = rnd.uniform(0, 6), rnd.uniform(0, 6)
        pts = []
        for x in range(0, W + 25, 25):
            t = x / W
            y = H * yf + H * amp * (0.55 * math.sin(2 * math.pi * 1.1 * t + p1)
                                    + 0.45 * abs(math.sin(2 * math.pi * 2.3 * t + p2)) * -1)
            pts.append((x, y))
        d.polygon(pts + [(W, H), (0, H)], fill=hx(col))
        # knife strokes along each ridge top
        for _ in range(240):
            i = rnd.randint(1, len(pts) - 2)
            x, y = pts[i]
            c = jit(rnd, hx(col), 18)
            c = tuple(min(255, int(v * 1.25)) for v in c)
            dab(d, x, y + rnd.uniform(0, 0.02) * H, rnd.uniform(4, 10) * W / 3508, c,
                rnd.uniform(-0.25, 0.25), rnd.uniform(3, 6), rnd.randint(70, 150))

    # birds
    for _ in range(5):
        bx, by = rnd.uniform(0.2, 0.8) * W, rnd.uniform(0.12, 0.26) * H
        bw = W * rnd.uniform(0.010, 0.020)
        stroke(d, [(bx - bw, by), (bx, by - bw * 0.45), (bx + bw, by)], hx("#3A2C26"),
               W * 0.0018, 200)
    return img


def forest_mist(W, H):
    rnd = random.Random(31)
    img = vgrad(W, H, [(0.0, hx("#E8EAE4")), (0.5, hx("#CBD4CC")), (1.0, hx("#A9B8AC"))]).convert("RGBA")

    def pine(d, x, base_y, h, col, alpha):
        """Solid layered-triangle spruce silhouette — reads as a full tree."""
        wby = h * 0.30
        stroke(d, [(x, base_y), (x, base_y - h * 0.25)], col, max(2, h * 0.030), alpha)
        tiers = 5
        for i in range(tiers):
            t = i / (tiers - 1)                      # 0 bottom -> 1 top
            yb = base_y - h * (0.16 + 0.60 * t)      # tier base
            yt = yb - h * 0.30                        # tier apex
            span = wby * (1 - 0.62 * t) * rnd.uniform(0.9, 1.1)
            sag = span * 0.18                         # drooping branch edges
            d.polygon([(x - span, yb + sag), (x, yt), (x + span, yb + sag),
                       (x + span * 0.55, yb), (x, yb - h * 0.04), (x - span * 0.55, yb)],
                      fill=col + (alpha,))

    # back to front: lighter, smaller, mistier -> darker, larger, crisper
    layers = [("#B9C4B7", 0.40, 0.06, 26, 120), ("#96A594", 0.52, 0.09, 20, 150),
              ("#6F8371", 0.66, 0.13, 15, 185), ("#4A5F4E", 0.82, 0.18, 12, 215),
              ("#2F4235", 1.00, 0.24, 9, 235)]
    for col, yf, hf, n, alpha in layers:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer, "RGBA")
        for _ in range(n):
            x = rnd.uniform(-0.02, 1.02) * W
            hh = H * hf * rnd.uniform(0.7, 1.25)
            pine(ld, x, H * yf + rnd.uniform(-0.01, 0.02) * H, hh, jit(rnd, hx(col), 10), alpha)
        img.alpha_composite(layer)
        # mist band between layers
        mist = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(mist).rectangle([0, H * (yf - 0.10), W, H * yf], fill=hx("#EDEFE8") + (70,))
        img.alpha_composite(mist.filter(ImageFilter.GaussianBlur(int(H * 0.03))))

    # faint sun disc high left
    d = ImageDraw.Draw(img, "RGBA")
    sr = W * 0.075
    d.ellipse([W * 0.26 - sr, H * 0.14 - sr, W * 0.26 + sr, H * 0.14 + sr],
              fill=hx("#F5F2E4") + (170,))
    return img


# -------------------------------------------------------------------- runner --
PIECES = {
    "meadow_poppies": meadow_poppies,
    "watercolor_botanical": watercolor_botanical,
    "moody_blooms": moody_blooms,
    "abstract_coast": abstract_coast,
    "mountain_gold": mountain_gold,
    "forest_mist": forest_mist,
}


def export(name, fn):
    Wss, Hss = W0 * SS, H0 * SS
    art = fn(Wss, Hss)
    art = art.resize((W0, H0), Image.LANCZOS)
    art = canvas_texture(art, 0.06)

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
    out = OUT / "_REVIEW_paint.png"
    sheet.save(out, "PNG")
    return out


if __name__ == "__main__":
    made = []
    for name, fn in PIECES.items():
        print(f"painting {name} ...", flush=True)
        made.append(export(name, fn))
        print(f"  done: {made[-1]}")
    print(f"review sheet: {contact_sheet(made)}")
