#!/usr/bin/env python3
"""
ornaments.py - procedural, code-drawn ornaments for the name prints.

Everything here is generated from geometry (no external/copyrighted art), so it
is license-clean and fully recolorable per style. All pieces render on a
transparent RGBA layer at a supersampled resolution and are downscaled with
LANCZOS for smooth, crisp gold lines.

Public pieces:
  medallion(size, color, ...)      -> circular Islamic geometric rosette (style #1 top)
  arch(w, h, color, ...)           -> pointed-arch frame ornament
  floral(size, color, ...)         -> symmetric vine/leaf sprig (geometric-leaning)
  corner_bracket(size, color, ...) -> L-shaped corner flourish (top-left orientation)
  divider(width, color, ...)       -> thin rule with a center diamond
  draw_border(canvas, color, ...)  -> draws the double-line frame onto a canvas
"""
from __future__ import annotations

import math

from PIL import Image, ImageDraw

RGBA = tuple
_SS = 4  # supersample factor for smooth edges


def _new(size_px: int):
    """Create a transparent supersampled canvas + draw handle; returns (img, draw, S)."""
    s = size_px * _SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img), s


def _down(img: Image.Image, size_px: int) -> Image.Image:
    return img.resize((size_px, size_px), Image.LANCZOS)


def _ring(draw, cx, cy, r, color, width):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=max(1, int(width)))


def _star_polygon(cx, cy, n, step, r, rot=-math.pi / 2):
    """Vertices for an {n/step} star polygon path (closed)."""
    pts = [(cx + r * math.cos(rot + 2 * math.pi * i / n),
            cy + r * math.sin(rot + 2 * math.pi * i / n)) for i in range(n)]
    path, idx = [], 0
    for _ in range(n + 1):
        path.append(pts[idx % n])
        idx += step
    return path


def _petal(d, c, a, r0, r1, halfw, color, width):
    """Draw one pointed lotus petal radiating outward along angle `a`."""
    ca, sa = math.cos(a), math.sin(a)
    pa = a + math.pi / 2
    cpa, spa = math.cos(pa), math.sin(pa)
    mr = (r0 + r1) / 2
    base = (c + r0 * ca, c + r0 * sa)
    tip = (c + r1 * ca, c + r1 * sa)
    left = (c + mr * ca + halfw * cpa, c + mr * sa + halfw * spa)
    right = (c + mr * ca - halfw * cpa, c + mr * sa - halfw * spa)
    d.polygon([base, left, tip, right], outline=color, width=max(1, int(width)))


def medallion(size: int, color, line: float = 0.0045) -> Image.Image:
    """A circular Islamic 'shamsa' rosette: a beaded rim, a crown of radiating
    pointed petals (with shorter petals interleaved), and overlaid star polygons
    around a central boss. Code-drawn and recolorable; an original, not a copy."""
    img, d, S = _new(size)
    c = S / 2
    R = S * 0.46
    lw = max(1.0, S * line)

    # beaded outer ring (small dots) + double rim
    for i in range(64):
        a = 2 * math.pi * i / 64
        bx, by = c + R * 1.02 * math.cos(a), c + R * 1.02 * math.sin(a)
        r = S * 0.006
        d.ellipse([bx - r, by - r, bx + r, by + r], fill=color)
    _ring(d, c, c, R, color, lw)
    _ring(d, c, c, R * 0.95, color, lw * 0.6)

    # crown of 16 long petals + 16 shorter petals interleaved for density
    N = 16
    for i in range(N):
        _petal(d, c, 2 * math.pi * i / N, R * 0.30, R * 0.93, R * 0.085, color, lw * 0.8)
        _petal(d, c, 2 * math.pi * (i + 0.5) / N, R * 0.30, R * 0.66, R * 0.05, color, lw * 0.7)

    # inner containing ring + overlaid star polygons (16-point + 8-point)
    _ring(d, c, c, R * 0.32, color, lw)
    d.line(_star_polygon(c, c, 16, 6, R * 0.30), fill=color, width=int(lw * 0.8), joint="curve")
    d.line(_star_polygon(c, c, 8, 3, R * 0.20), fill=color, width=int(lw), joint="curve")

    # center boss
    _ring(d, c, c, R * 0.12, color, lw)
    d.ellipse([c - S * 0.013, c - S * 0.013, c + S * 0.013, c + S * 0.013], fill=color)

    return _down(img, size)


def _quad_point(p0, p1, p2, t):
    u = 1 - t
    return (u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
            u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1])


def _quad(p0, p1, p2, n=28):
    """Sample a quadratic Bezier into a polyline (Pillow has no native curves)."""
    return [_quad_point(p0, p1, p2, i / (n - 1)) for i in range(n)]


def floral_crest(width: int, height: int, color, line: float = 0.020) -> Image.Image:
    """A horizontal, symmetric floral spray for the top slot: a small center
    diamond with two mirrored leafy vines ending in buds. A delicate accent."""
    s = _SS
    W, H = width * s, height * s
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    lw = max(2, int(H * line))
    cx, cy = W / 2, H * 0.56
    dd = H * 0.16
    d.polygon([(cx, cy - dd), (cx + dd * 0.62, cy), (cx, cy + dd), (cx - dd * 0.62, cy)],
              outline=color, width=lw)
    d.ellipse([cx - H * 0.045, cy - H * 0.045, cx + H * 0.045, cy + H * 0.045], fill=color)
    for sgn in (-1, 1):
        p0 = (cx + sgn * dd * 0.62, cy)
        p1 = (cx + sgn * W * 0.20, cy - H * 0.34)
        p2 = (cx + sgn * W * 0.45, cy - H * 0.02)
        d.line(_quad(p0, p1, p2), fill=color, width=lw, joint="curve")
        for t, lr in ((0.45, H * 0.13), (0.72, H * 0.10)):  # leaves as little V strokes
            lx, ly = _quad_point(p0, p1, p2, t)
            d.line([lx, ly, lx + sgn * lr * 0.25, ly - lr], fill=color, width=max(1, int(lw * 0.7)))
            d.line([lx, ly, lx + sgn * lr, ly - lr * 0.3], fill=color, width=max(1, int(lw * 0.7)))
        bx, by = p2  # terminal bud
        d.ellipse([bx - H * 0.05, by - H * 0.05, bx + H * 0.05, by + H * 0.05],
                  outline=color, width=lw)
    return img.resize((width, height), Image.LANCZOS)


def arch_frame(width: int, height: int, color, line: float = 0.010,
               crown_ratio: float = 0.55) -> Image.Image:
    """A double-line pointed-arch frame (mihrab-style), open at the bottom, sized
    to wrap a title placed inside it. `crown_ratio` is crown height / opening."""
    s = _SS
    W, H = width * s, height * s
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    lw = max(2, int(W * line))
    inset = int(lw * 1.2)
    x_l, x_r = inset, W - inset
    cx = (x_l + x_r) / 2
    opening = x_r - x_l
    crown = opening * crown_ratio
    y_apex, y_spring = inset, inset + crown

    def arch_path(xl, xr, ya, ys, shrink=0.10):
        c = (xl + xr) / 2
        op = xr - xl
        left = _quad((xl, ys), (xl + op * shrink, ya + (ys - ya) * 0.18), (c, ya), 30)
        right = _quad((c, ya), (xr - op * shrink, ya + (ys - ya) * 0.18), (xr, ys), 30)
        return left + right

    # outer arch + jambs
    d.line(arch_path(x_l, x_r, y_apex, y_spring), fill=color, width=lw, joint="curve")
    d.line([x_l, y_spring, x_l, H - inset], fill=color, width=lw)
    d.line([x_r, y_spring, x_r, H - inset], fill=color, width=lw)
    # inner parallel line
    g = int(opening * 0.020) + lw
    li = max(1, int(lw * 0.6))
    d.line(arch_path(x_l + g, x_r - g, y_apex + g * 1.3, y_spring), fill=color, width=li, joint="curve")
    d.line([x_l + g, y_spring, x_l + g, H - inset], fill=color, width=li)
    d.line([x_r - g, y_spring, x_r - g, H - inset], fill=color, width=li)
    # apex finial
    d.ellipse([cx - lw * 1.6, y_apex - lw * 1.6, cx + lw * 1.6, y_apex + lw * 1.6], fill=color)
    return img.resize((width, height), Image.LANCZOS)


def corner_bracket(size: int, color, line: float = 0.05) -> Image.Image:
    """An L-shaped double-line corner flourish in TOP-LEFT orientation.
    The caller rotates/flips it for the other three corners."""
    img, d, S = _new(size)
    lw = max(1, int(S * line * 0.18))
    inset, gap, run = S * 0.10, S * 0.10, S * 0.92
    # outer L
    d.line([inset, inset, inset + run, inset], fill=color, width=lw)
    d.line([inset, inset, inset, inset + run], fill=color, width=lw)
    # inner L (parallel)
    d.line([inset + gap, inset + gap, inset + run * 0.7, inset + gap], fill=color, width=int(lw * 0.7))
    d.line([inset + gap, inset + gap, inset + gap, inset + run * 0.7], fill=color, width=int(lw * 0.7))
    # small stepped flourish + diamond at the elbow
    e = inset + gap
    d.line([e, S * 0.42, S * 0.20, S * 0.42, S * 0.20, e], fill=color, width=int(lw * 0.7))
    dd = S * 0.05
    d.polygon([(e, e - dd), (e + dd, e), (e, e + dd), (e - dd, e)], outline=color, width=int(lw * 0.7))
    # tiny terminal ticks
    d.line([inset + run, inset, inset + run, inset + S * 0.06], fill=color, width=lw)
    d.line([inset, inset + run, inset + S * 0.06, inset + run], fill=color, width=lw)
    return _down(img, size)


def corner_floral(size: int, color, line: float = 0.02) -> Image.Image:
    """A small floral sprig growing inward from a corner (top-left orientation)."""
    img, d, S = _new(size)
    lw = max(2, int(S * line * 0.30))
    p0, p1, p2 = (S * 0.09, S * 0.09), (S * 0.52, S * 0.16), (S * 0.60, S * 0.56)
    d.line(_quad(p0, p1, p2, 26), fill=color, width=lw, joint="curve")
    for t, lr in ((0.42, S * 0.11), (0.72, S * 0.085)):
        lx, ly = _quad_point(p0, p1, p2, t)
        d.line([lx, ly, lx + lr, ly - lr * 0.4], fill=color, width=max(1, int(lw * 0.8)))
        d.line([lx, ly, lx + lr * 0.4, ly - lr], fill=color, width=max(1, int(lw * 0.8)))
    d.ellipse([p2[0] - S * 0.03, p2[1] - S * 0.03, p2[0] + S * 0.03, p2[1] + S * 0.03],
              outline=color, width=lw)
    d.ellipse([S * 0.06, S * 0.06, S * 0.11, S * 0.11], fill=color)
    return _down(img, size)


def divider(width: int, color, height: int | None = None, style: str = "diamond") -> Image.Image:
    """A horizontal divider.
    Styles: none | rule | bar | double | diamond | dot | deco | chevron | leaf."""
    h = height or max(8, width // 16)
    s = _SS
    W, H = width * s, h * s
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cy = H / 2
    lw = max(1, int(H * 0.05))

    if style == "none":
        return img.resize((width, h), Image.LANCZOS)
    if style == "rule":
        d.line([W * 0.06, cy, W * 0.94, cy], fill=color, width=lw)
        return img.resize((width, h), Image.LANCZOS)
    if style == "bar":  # bold solid block
        bh = H * 0.46
        d.rectangle([W * 0.02, cy - bh / 2, W * 0.98, cy + bh / 2], fill=color)
        return img.resize((width, h), Image.LANCZOS)
    if style == "double":  # two parallel rules
        d.line([W * 0.06, cy - H * 0.20, W * 0.94, cy - H * 0.20], fill=color, width=lw)
        d.line([W * 0.06, cy + H * 0.20, W * 0.94, cy + H * 0.20], fill=color, width=lw)
        return img.resize((width, h), Image.LANCZOS)

    m = H * 0.34  # half-size of the center motif; side hairlines flank it
    cx = W * 0.5
    d.line([W * 0.06, cy, cx - m * 1.7, cy], fill=color, width=lw)
    d.line([cx + m * 1.7, cy, W * 0.94, cy], fill=color, width=lw)
    if style == "diamond":
        d.polygon([(cx, cy - m), (cx + m, cy), (cx, cy + m), (cx - m, cy)], outline=color, width=lw)
    elif style == "dot":
        d.ellipse([cx - m * 0.55, cy - m * 0.55, cx + m * 0.55, cy + m * 0.55], fill=color)
    elif style == "deco":
        d.rectangle([cx - m * 0.7, cy - m * 0.7, cx + m * 0.7, cy + m * 0.7], outline=color, width=lw)
        d.line([cx - m * 1.5, cy, cx - m * 0.85, cy], fill=color, width=lw)
        d.line([cx + m * 0.85, cy, cx + m * 1.5, cy], fill=color, width=lw)
    elif style == "chevron":
        d.line([(cx - m, cy + m * 0.6), (cx, cy - m * 0.6), (cx + m, cy + m * 0.6)],
               fill=color, width=lw, joint="curve")
    elif style == "leaf":
        for sgn in (-1, 1):
            d.line([cx, cy, cx + sgn * m * 1.1, cy - m * 0.8], fill=color, width=max(1, int(lw * 0.8)))
        d.ellipse([cx - m * 0.22, cy - m * 0.22, cx + m * 0.22, cy + m * 0.22], fill=color)
    for x in (W * 0.06, W * 0.94):
        d.ellipse([x - lw, cy - lw, x + lw, cy + lw], fill=color)
    return img.resize((width, h), Image.LANCZOS)


def deco_corner(size: int, color, line: float = 0.035) -> Image.Image:
    """An angular, stepped Art-Deco corner flourish (top-left orientation)."""
    img, d, S = _new(size)
    lw = max(2, int(S * line * 0.28))
    d.line([(S * 0.06, S * 0.48), (S * 0.06, S * 0.06), (S * 0.48, S * 0.06)],
           fill=color, width=lw, joint="curve")
    d.line([(S * 0.15, S * 0.36), (S * 0.15, S * 0.15), (S * 0.36, S * 0.15)],
           fill=color, width=max(1, int(lw * 0.8)), joint="curve")
    d.line([(S * 0.06, S * 0.22), (S * 0.22, S * 0.06)], fill=color, width=max(1, int(lw * 0.8)))
    d.rectangle([S * 0.085, S * 0.085, S * 0.115, S * 0.115], fill=color)
    return _down(img, size)


def geometric(size: int, color, line: float = 0.011) -> Image.Image:
    """A bold, sharp, monochrome emblem: overlaid rotated squares (an 8-point
    star) with a smaller diamond and a solid center. Modern + angular."""
    img, d, S = _new(size)
    c = S / 2
    R = S * 0.46
    lw = max(2, int(S * line))

    def sq(rr, rot, w):
        pts = [(c + rr * math.cos(rot + math.pi / 2 * k), c + rr * math.sin(rot + math.pi / 2 * k))
               for k in range(4)]
        d.polygon(pts, outline=color, width=w)

    sq(R, math.pi / 4, lw)        # diamond
    sq(R * 0.72, 0.0, lw)         # axis-aligned square -> 8-point overlap
    sq(R * 0.44, math.pi / 4, lw)  # inner diamond
    cs = R * 0.13
    d.rectangle([c - cs, c - cs, c + cs, c + cs], fill=color)
    for k in range(4):            # short radial ticks
        a = math.pi / 2 * k
        d.line([c + R * math.cos(a), c + R * math.sin(a),
                c + R * 1.12 * math.cos(a), c + R * 1.12 * math.sin(a)], fill=color, width=lw)
    return _down(img, size)


def deco_fan(width: int, height: int, color, line: float = 0.009) -> Image.Image:
    """An Art-Deco sunburst fan: straight rays in an upper semicircle with two
    concentric arcs and a small stepped base."""
    s = _SS
    W, H = width * s, height * s
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    lw = max(2, int(min(W, H) * line))
    cx, cy = W / 2, H * 0.92
    R = H * 0.82
    n = 15

    def ang(t):
        return math.radians(12 + 156 * t)

    for i in range(n):
        a = ang(i / (n - 1))
        d.line([cx, cy, cx + R * math.cos(a), cy - R * math.sin(a)],
               fill=color, width=lw if i % 2 == 0 else max(1, int(lw * 0.55)))
    for rr in (R * 0.55, R * 0.82):
        pts = [(cx + rr * math.cos(ang(j / 40)), cy - rr * math.sin(ang(j / 40))) for j in range(41)]
        d.line(pts, fill=color, width=max(1, int(lw * 0.7)), joint="curve")
    for k, wd in enumerate((0.09, 0.14, 0.19)):
        yb = cy + s * 3 + k * H * 0.018
        d.line([cx - W * wd, yb, cx + W * wd, yb], fill=color, width=max(1, int(lw * 0.8)))
    d.ellipse([cx - lw * 1.4, cy - lw * 1.4, cx + lw * 1.4, cy + lw * 1.4], fill=color)
    return img.resize((width, height), Image.LANCZOS)


def wreath(size: int, color, line: float = 0.009) -> Image.Image:
    """A circular botanical ring (small leaves around a thin guide circle) sized
    to encircle a name. Code-drawn and original."""
    img, d, S = _new(size)
    c = S / 2
    R = S * 0.40
    lw = max(2, int(S * line))
    d.ellipse([c - R * 0.80, c - R * 0.80, c + R * 0.80, c + R * 0.80],
              outline=color, width=max(1, int(lw * 0.55)))
    n = 34
    for i in range(n):
        a = 2 * math.pi * i / n
        bx, by = c + R * 0.84 * math.cos(a), c + R * 0.84 * math.sin(a)
        ox, oy = math.cos(a), math.sin(a)
        tip = (bx + ox * S * 0.085, by + oy * S * 0.085)
        ta = a + math.pi / 2
        wd = S * 0.022
        left = (bx + wd * math.cos(ta), by + wd * math.sin(ta))
        right = (bx - wd * math.cos(ta), by - wd * math.sin(ta))
        d.polygon([(bx, by), left, tip, right], outline=color, width=max(1, int(lw * 0.6)))
    return _down(img, size)


def sprig(width: int, height: int, color, line: float = 0.012) -> Image.Image:
    """A delicate botanical sprig: a slender curved stem with a few small leaf
    pairs and a bud at the tip. Fine continuous line-art; original, recolorable."""
    SS = 4
    W, H = max(2, width) * SS, max(2, height) * SS
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    lw = max(1, int(min(W, H) * line))
    cx = W / 2
    stem = []
    for i in range(49):
        t = i / 48
        stem.append((cx + math.sin(t * math.pi) * (W * 0.05), H * (0.97 - 0.92 * t)))
    d.line(stem, fill=color, width=lw, joint="curve")

    def pt(t):
        return stem[max(0, min(len(stem) - 1, int(round(t * (len(stem) - 1)))))]

    def leaf(base, ang, length, halfw):
        dx, dy = math.cos(ang), math.sin(ang)
        px, py = -dy, dx
        tip = (base[0] + length * dx, base[1] + length * dy)
        mid = (base[0] + length * 0.5 * dx, base[1] + length * 0.5 * dy)
        c1 = (mid[0] + halfw * px, mid[1] + halfw * py)
        c2 = (mid[0] - halfw * px, mid[1] - halfw * py)
        d.line(_quad(base, c1, tip, 18), fill=color, width=max(1, int(lw * 0.8)), joint="curve")
        d.line(_quad(base, c2, tip, 18), fill=color, width=max(1, int(lw * 0.8)), joint="curve")

    up = -math.pi / 2
    for t, spread, ln in ((0.34, 1.0, 0.30), (0.55, 0.9, 0.25), (0.74, 0.8, 0.19)):
        leaf(pt(t), up - spread, H * ln, W * 0.05)
        leaf(pt(t), up + spread, H * ln, W * 0.05)
    leaf(pt(1.0), up, H * 0.14, W * 0.04)               # tip bud
    return img.resize((max(2, width), max(2, height)), Image.LANCZOS)


def line_flower(width: int, height: int, color, line: float = 0.011) -> Image.Image:
    """A single continuous-line flower: a slim stem with one leaf rising into a
    five-petal bloom drawn as connected loops. Delicate, editorial; original."""
    SS = 4
    W, H = max(2, width) * SS, max(2, height) * SS
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    lw = max(1, int(min(W, H) * line))
    cx = W / 2
    fcx, fcy = cx, H * 0.34               # flower centre
    R = W * 0.30                          # petal reach
    # stem: gentle curve from the base up to the flower
    d.line(_quad((cx, H * 0.97), (cx + W * 0.04, H * 0.66), (fcx, fcy + R * 0.55), 26),
           fill=color, width=lw, joint="curve")
    # one leaf on the stem
    base = (cx + W * 0.012, H * 0.70)
    ang = -math.pi / 2 - 0.9
    tip = (base[0] + H * 0.16 * math.cos(ang), base[1] + H * 0.16 * math.sin(ang))
    mid = ((base[0] + tip[0]) / 2, (base[1] + tip[1]) / 2)
    pxp, pyp = -math.sin(ang), math.cos(ang)
    d.line(_quad(base, (mid[0] + W * 0.05 * pxp, mid[1] + H * 0.03 * pyp), tip, 16),
           fill=color, width=max(1, int(lw * 0.8)), joint="curve")
    d.line(_quad(base, (mid[0] - W * 0.05 * pxp, mid[1] - H * 0.03 * pyp), tip, 16),
           fill=color, width=max(1, int(lw * 0.8)), joint="curve")
    # five petals as loops radiating from the centre (one continuous feel)
    N = 5
    for i in range(N):
        a = -math.pi / 2 + 2 * math.pi * i / N
        tip = (fcx + R * math.cos(a), fcy + R * math.sin(a))
        pa = a + math.pi / 2
        hw = R * 0.55
        m = (fcx + R * 0.5 * math.cos(a), fcy + R * 0.5 * math.sin(a))
        c1 = (m[0] + hw * math.cos(pa), m[1] + hw * math.sin(pa))
        c2 = (m[0] - hw * math.cos(pa), m[1] - hw * math.sin(pa))
        d.line(_quad((fcx, fcy), c1, tip, 16), fill=color, width=lw, joint="curve")
        d.line(_quad(tip, c2, (fcx, fcy), 16), fill=color, width=lw, joint="curve")
    r = R * 0.12
    d.ellipse([fcx - r, fcy - r, fcx + r, fcy + r], outline=color, width=max(1, int(lw * 0.9)))
    return img.resize((max(2, width), max(2, height)), Image.LANCZOS)


def draw_border(canvas: Image.Image, color, inset: int, gap: int, width: int,
                style: str = "double") -> None:
    """Draw a frame onto `canvas`.
    Styles: none | single | double | rules_tb (top+bottom only) | stepped (deco)."""
    if style == "none":
        return
    d = ImageDraw.Draw(canvas)
    w, h = canvas.size
    lw = max(1, width)
    if style in ("single", "double"):
        offs = [inset] if style == "single" else [inset, inset + gap]
        for off in offs:
            d.rectangle([off, off, w - 1 - off, h - 1 - off], outline=color, width=lw)
    elif style == "rules_tb":  # editorial: full-width rules top and bottom only
        for yy in (inset, h - 1 - inset):
            d.line([inset, yy, w - 1 - inset, yy], fill=color, width=lw)
    elif style == "stepped":  # deco: double frame with bevelled corners
        o1, o2 = inset, inset + gap * 2
        d.rectangle([o1, o1, w - 1 - o1, h - 1 - o1], outline=color, width=lw)
        d.rectangle([o2, o2, w - 1 - o2, h - 1 - o2], outline=color, width=max(1, int(lw * 0.7)))
        n = int(min(w, h) * 0.028)
        for cx, cy, sx, sy in [(o1, o1, 1, 1), (w - 1 - o1, o1, -1, 1),
                               (o1, h - 1 - o1, 1, -1), (w - 1 - o1, h - 1 - o1, -1, -1)]:
            d.line([cx + sx * n, cy, cx, cy + sy * n], fill=color, width=lw)


# ---------------------------------------------------------------------------
# Full-field geometric patterns (for the pure-pattern "Islamic geometric"
# posters — zero text, so no correctness risk). All tile past the given w x h
# so the caller can composite/clip them into any region. Recolorable.
# ---------------------------------------------------------------------------
def star_tiling(w: int, h: int, color, cells: float = 6.0,
                line: float = 0.006, inner: float = 0.40, r_k: float = 0.5):
    """Classic 8-pointed star-and-cross ('khatam') tessellation. Stars sit on a
    square lattice; their concave notches form the interstitial crosses."""
    s = _SS
    W, H = w * s, h * s
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    lw = max(1, int(min(W, H) * line))
    u = W / cells
    R = u * r_k
    ri = R * inner

    def star8(cx, cy):
        pts = []
        for k in range(16):
            a = math.pi / 8 * k
            rr = R if k % 2 == 0 else ri
            pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        d.line(pts + [pts[0]], fill=color, width=lw, joint="curve")

    y = 0.0
    while y <= H + u:
        x = 0.0
        while x <= W + u:
            star8(x, y)
            x += u
        y += u
    return img.resize((max(2, w), max(2, h)), Image.LANCZOS)


def interlaced_circles(w: int, h: int, color, cells: float = 5.0, line: float = 0.006):
    """A 'flower of life' arabesque lattice: equal circles on a triangular
    lattice, each passing through its neighbours' centres, forming petal rosettes."""
    s = _SS
    W, H = w * s, h * s
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    lw = max(1, int(min(W, H) * line))
    r = W / cells
    rh = r * math.sqrt(3) / 2
    j = 0
    y = -r
    while y <= H + r:
        off = (r / 2) if (j % 2) else 0
        x = -r + off
        while x <= W + r:
            d.ellipse([x - r, y - r, x + r, y + r], outline=color, width=lw)
            x += r
        y += rh
        j += 1
    return img.resize((max(2, w), max(2, h)), Image.LANCZOS)


def eightfold_rosette_grid(w: int, h: int, color, cells: float = 4.0, line: float = 0.006):
    """An octagon + inscribed 8-point star (two squares) on a square lattice —
    an architectural zellige-style geometric field."""
    s = _SS
    W, H = w * s, h * s
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    lw = max(1, int(min(W, H) * line))
    u = W / cells
    R = u * 0.5

    def node(cx, cy):
        d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=color, width=lw)
        for rot in (0.0, math.pi / 4):
            pts = [(cx + R * math.cos(rot + math.pi / 2 * k),
                    cy + R * math.sin(rot + math.pi / 2 * k)) for k in range(4)]
            d.line(pts + [pts[0]], fill=color, width=lw)

    y = 0.0
    while y <= H + u:
        x = 0.0
        while x <= W + u:
            node(x, y)
            x += u
        y += u
    return img.resize((max(2, w), max(2, h)), Image.LANCZOS)


def crescent(size: int, color, line: float = 0.0) -> Image.Image:
    """A filled Islamic crescent (hilal) with a small five-point star nestled in
    its opening. Carved from two offset discs; the star sits to the concave side.
    Code-drawn and recolorable — a celestial motif for baby / aqiqah name prints."""
    img, d, S = _new(size)
    r = S * 0.40
    cx, cy = S * 0.42, S * 0.50
    # outer disc
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    # carve an equal-radius inner disc with a small offset -> a slim crescent sliver
    off = S * 0.13
    ir = r
    icx = cx + off
    hole = Image.new("L", (S, S), 0)
    ImageDraw.Draw(hole).ellipse([icx - ir, cy - ir, icx + ir, cy + ir], fill=255)
    from PIL import ImageChops
    img.putalpha(ImageChops.subtract(img.split()[3], hole))
    # small five-point star in the crescent's opening
    sr = S * 0.10
    scx, scy = cx + off + r * 0.30, cy - r * 0.42
    pts = []
    for i in range(10):
        rr = sr if i % 2 == 0 else sr * 0.42
        a = -math.pi / 2 + i * math.pi / 5
        pts.append((scx + rr * math.cos(a), scy + rr * math.sin(a)))
    d.polygon(pts, fill=color)
    return _down(img, size)
