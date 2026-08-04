#!/usr/bin/env python3
"""
render.py - the rendering engine.

render(row, style) -> writes {name}_{style}_print.png and .pdf into an output
folder and returns the paths. Everything is built in Pillow at the style's
canvas size (A3 @ 300 DPI by default); the PDF is that high-res raster placed
on a correctly-sized vector page (print-perfect at A3/A4/A5).

Layout is a vertically-centred FLOW: the text stack (name -> latin -> date ->
divider -> meaning -> divider -> dua -> translation) is measured and centred in
a region, so omitting the date or the dua reflows cleanly with no gap. The
frame, corners and top medallion are absolute.

Arabic is delegated entirely to arabic_text.py (the only module that touches
Arabic). This engine never generates or transliterates Arabic.
"""
from __future__ import annotations

import argparse
import gc
import json
import re
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
from reportlab.lib.pagesizes import A3
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdfcanvas

try:
    import arabic_text
except ImportError:
    arabic_text = None  # Optional for non-Arabic templates
import ornaments

ROOT = Path(__file__).resolve().parent
FONT_DIR = ROOT / "assets" / "fonts"
TEMPLATE_DIR = ROOT / "templates"
ASSETS_DIR = ROOT / "assets"  # For image overlays


# ---------------------------------------------------------------- helpers ----
def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.strip().lower()).strip("_") or "name"


def load_style(style: str) -> dict:
    data = json.loads((TEMPLATE_DIR / f"{style}.json").read_text(encoding="utf-8"))
    if "extends" in data:  # variant SKU: inherit a base layout, override on top
        data = {**load_style(data["extends"]), **data}
    return data


_PALETTES = None


def load_palettes() -> dict:
    """Named role->colour palettes (palettes.json). Lets one layout recolour."""
    global _PALETTES
    if _PALETTES is None:
        p = ROOT / "palettes.json"
        _PALETTES = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    return _PALETTES


_CONFIG = None


def load_config() -> dict:
    global _CONFIG
    if _CONFIG is None:
        p = ROOT / "config.json"
        _CONFIG = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    return _CONFIG


def apply_defaults(row: dict) -> dict:
    """Fill a blank dua_arabic (and its translation) from config defaults.

    A row that supplies its own verified dua_arabic overrides the default. Only
    operator-verified Unicode (from config.json) is ever substituted here.
    """
    row = dict(row)
    defaults = load_config().get("defaults", {})
    # fill blank verified-Arabic + translation pairs from config (operator-set)
    for ar, tr in (("dua_arabic", "dua_translation"),
                   ("bismillah_arabic", "bismillah_translation")):
        if defaults.get(ar) and not str(row.get(ar, "") or "").strip():
            row[ar] = defaults[ar]
        if defaults.get(tr) and not str(row.get(tr, "") or "").strip():
            row[tr] = defaults[tr]
    return row


_FONT_CACHE: dict = {}


def load_font(spec: dict, size_px: int) -> ImageFont.FreeTypeFont:
    key = (spec["file"], size_px, spec.get("weight"))
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    font = ImageFont.truetype(str(FONT_DIR / spec["file"]), size_px)
    if "weight" in spec:
        try:
            font.set_variation_by_axes([spec["weight"]])
        except Exception:
            pass  # static font or no matching axis; default instance is fine
    _FONT_CACHE[key] = font
    return font


def make_gradient(w: int, h: int, c0, c1) -> Image.Image:
    """Vertical gradient from c0 (top) to c1 (bottom)."""
    col = Image.new("RGB", (1, h))
    px = col.load()
    for y in range(h):
        t = y / (h - 1)
        px[0, y] = tuple(round(c0[i] + (c1[i] - c0[i]) * t) for i in range(3))
    return col.resize((w, h))


def _apply_vignette(img: Image.Image, strength: float = 0.35) -> None:
    """Darken the edges with a soft radial falloff to add depth (in place)."""
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    mx, my = int(w * 0.06), int(h * 0.06)
    ImageDraw.Draw(mask).ellipse([mx, my, w - mx, h - my], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(int(min(w, h) * 0.13)))
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    overlay.putalpha(mask.point(lambda v: int((255 - v) * strength)))
    img.alpha_composite(overlay)


def render_line(text: str, font: ImageFont.FreeTypeFont, color,
                tracking_px: float = 0.0, upper: bool = False) -> Image.Image:
    """A single line of Latin text, optionally upper-cased and letter-spaced,
    trimmed to its inked bbox on a transparent layer."""
    if not text or not text.strip():
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    if upper:
        text = text.upper()
    ascent, descent = font.getmetrics()
    widths = [font.getlength(ch) for ch in text]
    total = sum(widths) + tracking_px * max(0, len(text) - 1)
    pad = int((ascent + descent) * 0.6)
    layer = Image.new("RGBA", (int(total + pad * 2), ascent + descent + pad * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    x = pad
    for ch, w in zip(text, widths):
        draw.text((x, pad), ch, font=font, fill=color, anchor="la")
        x += w + tracking_px
    bbox = layer.getbbox()
    return layer.crop(bbox) if bbox else layer


def render_paragraph(text: str, font: ImageFont.FreeTypeFont, color,
                     max_w: int, leading: float, align: str = "center") -> Image.Image:
    """Word-wrapped multi-line paragraph (align: left|center|right), trimmed."""
    if not text or not text.strip():
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if cur and font.getlength(trial) > max_w:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)

    ascent, descent = font.getmetrics()
    line_h = int((ascent + descent) * leading)
    layer = Image.new("RGBA", (max_w, line_h * len(lines) + line_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for i, ln in enumerate(lines):
        lw = font.getlength(ln)
        x = 0 if align == "left" else (max_w - lw if align == "right" else (max_w - lw) / 2)
        draw.text((x, i * line_h), ln, font=font, fill=color, anchor="la")
    bbox = layer.getbbox()
    return layer.crop(bbox) if bbox else layer


# --------------------------------------------------------------- rendering ---
def _build_block(b: dict, row: dict, style: dict, W: int, H: int):
    """Return an RGBA image for one flow block, or None if it has no content."""
    fonts = style["fonts"]
    colors = style["colors"]

    def color_of(key):
        return hex_to_rgb(colors[key]) if key in colors else hex_to_rgb(key)

    col = color_of(b["color"]) if "color" in b else (255, 255, 255)
    t = b["type"]
    field = b.get("field", b["id"])  # data-row key may differ from the layout id

    if t == "arabic":
        text = row.get(field, "")
        if not text or not str(text).strip():
            return None
        if arabic_text is None:
            raise ImportError("arabic_text module required for Arabic text rendering")
        return arabic_text.render_arabic_fitted(
            str(text), str(FONT_DIR / fonts[b["font"]]["file"]),
            color=col, max_width=int(b["max_w"] * W), target_height=int(b["height"] * H))

    if t == "arabic_para":                    # multi-line verse (wraps by width)
        text = row.get(field, "")
        if not text or not str(text).strip():
            return None
        if arabic_text is None:
            raise ImportError("arabic_text module required for Arabic text rendering")
        return arabic_text.render_arabic_paragraph(
            str(text), str(FONT_DIR / fonts[b["font"]]["file"]), color=col,
            max_width=int(b["max_w"] * W), font_size=int(b["size"] * H),
            leading=b.get("leading", 1.65))

    if t == "line":
        text = b.get("text", row.get(field, ""))  # literal label (Latin) or row field
        if not text or not str(text).strip():
            return None
        font = load_font(fonts[b["font"]], int(b["size"] * H))
        return render_line(str(text), font, col,
                           tracking_px=b.get("tracking", 0.0) * b["size"] * H,
                           upper=b.get("upper", False))

    if t == "paragraph":
        text = b.get("text", row.get(field, ""))  # literal copy (Latin) or row field
        if not text or not str(text).strip():
            return None
        font = load_font(fonts[b["font"]], int(b["size"] * H))
        para_align = b.get("align", style.get("flow", {}).get("align", "center"))
        return render_paragraph(str(text), font, col, int(b["max_w"] * W),
                                b.get("leading", 1.4), align=para_align)

    if t == "divider":
        return ornaments.divider(int(b["width"] * W), col,
                                 style=b.get("style", style.get("divider_style", "diamond")))

    return None


def _layout_blocks(img, blocks, region, align_default, valign, margin_px, row, style, W, H):
    """Stack `blocks` vertically inside region (x0,y0,x1,y1 in px), aligned and
    vertically positioned (top|center|bottom). Returns {block_id: (x,y,w,h)}.
    Includes the shrink-to-fit safety net so a zone can never overflow."""
    x0, y0, x1, y1 = region
    region_w, region_h = x1 - x0, y1 - y0
    built = []
    for b in blocks:
        bi = _build_block(b, row, style, W, H)
        if bi is None:
            continue
        if b.get("rotate"):  # e.g. a vertical Arabic name column
            bi = bi.rotate(b["rotate"], expand=True, resample=Image.BICUBIC)
        built.append((bi, b.get("gap", 0.0) * H, b["id"], b.get("align", align_default)))
    if not built:
        return {}
    total = sum(im.height for im, _, _, _ in built) + sum(g for _, g, _, _ in built[1:])
    fit = min(1.0, region_h / total) if total > 0 else 1.0
    if fit < 1.0:
        built = [(im.resize((max(1, round(im.width * fit)), max(1, round(im.height * fit))),
                            Image.LANCZOS), g * fit, bid, al) for im, g, bid, al in built]
        total = sum(im.height for im, _, _, _ in built) + sum(g for _, g, _, _ in built[1:])
    if valign == "top":
        y = y0
    elif valign == "bottom":
        y = y1 - total
    else:
        y = y0 + (region_h - total) / 2
    placed = {}
    for i, (im, gap, bid, al) in enumerate(built):
        if i > 0:
            y += gap
        if al == "left":
            x = x0 + margin_px
        elif al == "right":
            x = x1 - margin_px - im.width
        else:
            x = x0 + (region_w - im.width) / 2
        img.alpha_composite(im, (int(x), int(y)))
        placed[bid] = (int(x), int(y), im.width, im.height)
        y += im.height
    return placed


_SCRIPTS = {
    "naskh": ("Amiri-Bold.ttf", "Amiri-Regular.ttf"),
    "kufic": ("ReemKufi[wght].ttf", "ReemKufi[wght].ttf"),
    "ruqaa": ("ArefRuqaa-Bold.ttf", "ArefRuqaa-Regular.ttf"),
}


def _apply_script(style: dict) -> dict:
    """Swap the Arabic fonts to a calligraphy script (naskh | kufic | ruqaa)."""
    sc = style.get("script")
    if sc not in _SCRIPTS:
        return style
    name_f, dua_f = _SCRIPTS[sc]
    fonts = {k: dict(v) for k, v in style.get("fonts", {}).items()}
    if "arabic_name" in fonts:
        fonts["arabic_name"]["file"] = name_f
    if "arabic_dua" in fonts:
        fonts["arabic_dua"]["file"] = dua_f
    return {**style, "fonts": fonts}


def resolve_style(style_name: str) -> dict:
    """Load a style with its palette merged + script applied -- the resolved form
    the renderer and the pin/asset tools both consume (colours + fonts ready)."""
    style = load_style(style_name)
    if "palette" in style:
        pal = load_palettes().get(style["palette"], {})
        roles = {k: v for k, v in pal.items() if isinstance(v, str)}
        style = {**style, "colors": {**roles, **style.get("colors", {})}, "_palette": pal}
    return _apply_script(style)


def render(row: dict, style_name: str, out_dir: Path | str = ROOT / "output",
           canvas: tuple | None = None, tag: str = "print") -> dict:
    """Render one verified row in one style -> PNG + PDF. Returns paths.

    `canvas=(w,h)` overrides the template size (the fraction-based layout reflows
    to any aspect ratio); `tag` names the output files (e.g. a size label).
    """
    row = apply_defaults(row)
    style = resolve_style(style_name)
    W, H = canvas if canvas else (style["canvas"]["w"], style["canvas"]["h"])
    colors = style.get("colors", {})

    def color_of(key):
        return hex_to_rgb(colors[key]) if key in colors else hex_to_rgb(key)

    # background gradient (from/to may be hex or palette role keys)
    bgc = style.get("background", {})
    img = make_gradient(W, H, color_of(bgc.get("from", "#FFFFFF")),
                        color_of(bgc.get("to", bgc.get("from", "#FFFFFF")))).convert("RGBA")
    vg = bgc.get("vignette")
    if vg == "palette":
        vg = style.get("_palette", {}).get("vignette", 0)
    if vg:
        _apply_vignette(img, float(vg))

    # image-based background (e.g. watercolor texture, photo)
    bg_image = bgc.get("image")
    if bg_image:
        img_path = ASSETS_DIR / "overlays" / bg_image
        if img_path.exists():
            bg = Image.open(img_path).convert("RGBA")
            bg = bg.resize((W, H), Image.LANCZOS)
            alpha = bgc.get("image_alpha", 1.0)
            if alpha < 1.0:
                bg.putalpha(bg.split()[3].point(lambda v: int(v * alpha)))
            img.alpha_composite(bg, (0, 0))

    # background colour panels (e.g. a top banner band for a split layout)
    for p in style.get("background", {}).get("panels", []):
        r = p["region"]
        ImageDraw.Draw(img).rectangle(
            [int(r[0] * W), int(r[1] * H), int(r[2] * W), int(r[3] * H)], fill=color_of(p["color"]))

    # soft watercolour wash blooms (blurred, translucent colour)
    for wsh in style.get("background", {}).get("washes", []):
        blob = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        cx, cy, rx, ry = wsh["cx"] * W, wsh["cy"] * H, wsh["rx"] * W, wsh["ry"] * H
        r_, g_, b_ = color_of(wsh["color"])
        ImageDraw.Draw(blob).ellipse([cx - rx, cy - ry, cx + rx, cy + ry],
                                     fill=(r_, g_, b_, int(255 * wsh.get("alpha", 0.22))))
        img.alpha_composite(blob.filter(ImageFilter.GaussianBlur(wsh.get("blur", 0.07) * min(W, H))))

    # fine paper grain over the whole background (colour panels + washes) for a
    # warm, tactile, non-digital feel — matches premium riso/paper name prints.
    # Applied by default; set background.texture to 0 to disable, or higher for
    # more tooth. Drawn BEFORE text/ornaments so they stay crisp on top.
    tex = float(style.get("background", {}).get("texture", 0.055))
    if tex > 0:
        rgb = img.convert("RGB")
        grain = Image.effect_noise((W, H), 22).convert("RGB")
        img = Image.blend(rgb, ImageChops.overlay(rgb, grain), tex).convert("RGBA")

    # oversized faded watermark of the verified name, behind everything
    wm = style.get("watermark")
    if wm and arabic_text is not None:
        wtext = str(row.get(wm.get("field", "name_arabic"), "") or "")
        if wtext.strip():
            wimg = arabic_text.render_arabic_fitted(
                wtext, str(FONT_DIR / style["fonts"][wm.get("font", "arabic_name")]["file"]),
                color=color_of(wm["color"]), max_width=int(wm.get("max_w", 0.92) * W),
                target_height=int(wm.get("height", 0.06) * H))
            faded = wimg.split()[3].point(lambda v: int(v * wm.get("alpha", 0.10)))
            wimg.putalpha(faded)
            img.alpha_composite(wimg, (int(wm.get("cx", 0.5) * W - wimg.width / 2),
                                       int(wm.get("cy", 0.5) * H - wimg.height / 2)))

    # full-field geometric pattern (pure-pattern posters: star tiling / flower
    # lattice / octagon grid). Tiled across `region` (default full bleed) and
    # composited under the border + any crest. No text -> no correctness risk.
    pat = style.get("pattern")
    if pat:
        pr = pat.get("region", [0.0, 0.0, 1.0, 1.0])
        px0, py0, px1, py1 = int(pr[0] * W), int(pr[1] * H), int(pr[2] * W), int(pr[3] * H)
        pw, ph = max(2, px1 - px0), max(2, py1 - py0)
        fn = getattr(ornaments, pat["kind"])
        kw = {k: pat[k] for k in ("cells", "line", "inner", "r_k") if k in pat}
        art = fn(pw, ph, color_of(pat["color"]), **kw)
        if pat.get("alpha", 1.0) < 1.0:
            a = art.split()[3].point(lambda v: int(v * pat["alpha"]))
            art.putalpha(a)
        img.alpha_composite(art, (px0, py0))

    # overlays (e.g. light leaks, textures, film grain)
    for ovr in style.get("overlays", []):
        ovr_path = ASSETS_DIR / "overlays" / ovr["file"]
        if ovr_path.exists():
            overlay = Image.open(ovr_path).convert("RGBA")
            overlay = overlay.resize((W, H), Image.LANCZOS)
            alpha = ovr.get("alpha", 1.0)
            if alpha < 1.0:
                overlay.putalpha(overlay.split()[3].point(lambda v: int(v * alpha)))
            if ovr.get("mode", "add") == "multiply":
                # Multiply blend mode for light leak effects
                base = img.convert("RGBA")
                overlay_rgba = overlay
                result = Image.new("RGBA", (W, H))
                for y in range(H):
                    for x in range(W):
                        b = base.getpixel((x, y))
                        o = overlay_rgba.getpixel((x, y))
                        if len(o) == 4 and o[3] < 255:
                            # Alpha composite for transparency
                            result.putpixel((x, y), o)
                        else:
                            # Multiply blend
                            br, bg, bb, ba = b
                            or_, og, ob, oa = o
                            rr = int((br * or_ / 255) if or_ > 0 else 0)
                            rg = int((bg * og / 255) if og > 0 else 0)
                            rb = int((bb * ob / 255) if ob > 0 else 0)
                            result.putpixel((x, y), (rr, rg, rb, ba))
                img = result
            else:
                img.alpha_composite(overlay, (0, 0))

    # frame (style: none | single | double)
    bd = style.get("border", {})
    if bd and bd.get("style", "double") != "none":
        ornaments.draw_border(img, color_of(bd["color"]),
                              inset=int(bd.get("inset", 0.03) * W), gap=int(bd.get("gap", 0.012) * W),
                              width=max(1, int(bd.get("line", 0.0015) * W)),
                              style=bd.get("style", "double"))

    # corner flourishes (style: none | bracket | deco)
    cn = style.get("corner", {})
    cstyle = cn.get("style", "bracket") if cn else "none"
    if cstyle != "none":
        csize = int(cn["size"] * W)
        ccolor = color_of(cn["color"])
        if cstyle == "deco":
            base = ornaments.deco_corner(csize, ccolor)
        elif cstyle == "floral":
            base = ornaments.corner_floral(csize, ccolor)
        else:
            base = ornaments.corner_bracket(csize, ccolor)
        margin = int(bd.get("inset", 0.03) * W)
        for flip_x, pos in [
            (False, (margin, margin)),
            (True, (W - margin - csize, margin)),
            (False, (margin, H - margin - csize)),
            (True, (W - margin - csize, H - margin - csize)),
        ]:
            tile = base
            if pos[1] != margin:  # bottom row -> flip vertically
                tile = tile.transpose(Image.FLIP_TOP_BOTTOM)
            if flip_x:
                tile = tile.transpose(Image.FLIP_LEFT_RIGHT)
            img.alpha_composite(tile, pos)

    # central cartouche: a clean disc (+ concentric ring) so a medallion reads as
    # a focal point over a busy geometric field (illuminated-frontispiece look).
    cart = style.get("cartouche")
    if cart:
        ccx, ccy, cr = int(cart.get("cx", 0.5) * W), int(cart["cy"] * H), int(cart["r"] * W)
        a = int(255 * cart.get("alpha", 1.0))
        ImageDraw.Draw(img, "RGBA").ellipse(
            [ccx - cr, ccy - cr, ccx + cr, ccy + cr], fill=color_of(cart["fill"]) + (a,))
        if cart.get("ring"):
            for mult, lw in ((1.0, 1.0), (0.955, 0.55)):
                rr = int(cr * mult)
                ImageDraw.Draw(img).ellipse(
                    [ccx - rr, ccy - rr, ccx + rr, ccy + rr], outline=color_of(cart["ring"]),
                    width=max(1, int(cart.get("ring_line", 0.0015) * W * mult * lw / mult)))

    # ---- top crest ornament (medallion / floral). 'arch' is drawn after flow. ----
    ornament = style.get("ornament", "medallion")
    crest = style.get("crest") or style.get("medallion")
    if crest and ornament in ("medallion", "geometric"):
        size = int(crest["size"])  # absolute pixel value, NOT multiplied by canvas size
        fn = ornaments.geometric if ornament == "geometric" else ornaments.medallion
        art = fn(size, color_of(crest["color"]))
        img.alpha_composite(art, ((W - size) // 2, int(crest["cy"] * H - size / 2)))
    elif crest and ornament in ("floral", "deco_fan"):
        rw, rh = (1.7, 0.72) if ornament == "floral" else (1.5, 0.85)
        fw, fh = int(crest["size"] * rw), int(crest["size"] * rh)  # use absolute size
        fn = ornaments.floral_crest if ornament == "floral" else ornaments.deco_fan
        art = fn(fw, fh, color_of(crest["color"]))
        img.alpha_composite(art, ((W - fw) // 2, int(crest["cy"] * H - fh / 2)))
    elif crest and ornament in ("sprig", "line_flower"):
        sw = int(crest["size"])
        sh = int(crest.get("size_h", crest["size"] * 1.5))
        fn = ornaments.line_flower if ornament == "line_flower" else ornaments.sprig
        art = fn(sw, sh, color_of(crest["color"]))
        img.alpha_composite(art, ((W - sw) // 2, int(crest["cy"] * H - sh / 2)))
    elif crest and ornament == "crescent":
        cs = crest["size"]
        size = int(cs * W) if cs <= 1 else int(cs)
        art = ornaments.crescent(size, color_of(crest["color"]))
        img.alpha_composite(art, ((W - size) // 2, int(crest["cy"] * H - size / 2)))
    elif crest and ornament == "botanical":
        import botanical
        # size is a FRACTION of canvas width (scales to any canvas); absolute px
        # (value > 1) kept as a fallback for older configs.
        cs = crest["size"]
        w_px = int(cs * W) if cs <= 1 else int(cs)
        art = botanical.tinted(crest.get("art", "wildflower"), w_px, color_of(crest["color"]))
        img.alpha_composite(art, ((W - art.width) // 2, int(crest["cy"] * H - art.height / 2)))
    # ornament "none" draws no crest; "arch" is drawn after the flow (below)

    # encircling wreath (the name sits inside it)
    wr = style.get("wreath")
    if wr:
        ws = int(wr["size"] * W)
        img.alpha_composite(ornaments.wreath(ws, color_of(wr["color"])),
                            (int(wr.get("cx", 0.5) * W - ws / 2), int(wr["cy"] * H - ws / 2)))

    # large architectural arch (mihrab) framing the upper zone
    ab = style.get("arch_big")
    if ab:
        r = ab["region"]
        aw, ah = int((r[2] - r[0]) * W), int((r[3] - r[1]) * H)
        img.alpha_composite(
            ornaments.arch_frame(aw, ah, color_of(ab["color"]),
                                 line=ab.get("line", 0.006), crown_ratio=ab.get("crown", 0.5)),
            (int(r[0] * W), int(r[1] * H)))

    # ---- layout: zones (multiple positioned stacks) or a single centred flow ----
    placed = {}
    if "zones" in style:
        for z in style["zones"]:
            r = z["region"]
            placed.update(_layout_blocks(
                img, z["blocks"], [r[0] * W, r[1] * H, r[2] * W, r[3] * H],
                z.get("align", "center"), z.get("valign", "center"),
                int(z.get("margin", 0.10) * W), row, style, W, H))
    else:
        flow = style["flow"]
        placed = _layout_blocks(
            img, flow["blocks"], [0, flow["region"][0] * H, W, flow["region"][1] * H],
            flow.get("align", "center"), flow.get("valign", "center"),
            int(flow.get("margin", 0.12) * W), row, style, W, H)

    # ---- arch ornament: a pointed frame wrapping the title (name/date) group ----
    if ornament == "arch":
        acfg = style.get("arch", {})
        ids = [i for i in ("arabic_name", "latin_name", "date") if i in placed]
        if ids:
            tx = min(placed[i][0] for i in ids)
            ty = min(placed[i][1] for i in ids)
            right = max(placed[i][0] + placed[i][2] for i in ids)
            bottom = max(placed[i][1] + placed[i][3] for i in ids)
            pad_x = int(W * 0.055)
            opening = (right - tx) + 2 * pad_x
            crown_ratio = acfg.get("crown", 0.55)
            crown = int(opening * crown_ratio)
            arch_img = ornaments.arch_frame(
                opening, crown + (bottom - ty) + int(H * 0.03),
                color_of(acfg.get("color", "black")),
                line=acfg.get("line", 0.010), crown_ratio=crown_ratio)
            img.alpha_composite(arch_img, (int(tx - pad_x), max(0, int(ty - crown - H * 0.005))))

    # ---- export ----
    out_dir = Path(out_dir)
    slug = f"{slugify(row.get('name_latin', 'name'))}_{style_name}"
    folder = out_dir / slug
    folder.mkdir(parents=True, exist_ok=True)

    rgb = img.convert("RGB")
    png_path = folder / f"{slug}_{tag}.png"
    rgb.save(png_path, "PNG")

    page = (W / 300.0 * 72.0, H / 300.0 * 72.0)  # physical size at 300 DPI, in points
    pdf_path = folder / f"{slug}_{tag}.pdf"
    c = pdfcanvas.Canvas(str(pdf_path), pagesize=page)
    c.drawImage(ImageReader(rgb), 0, 0, width=page[0], height=page[1])
    c.showPage()
    c.save()

    # free memory before returning
    del rgb
    del img
    gc.collect()

    return {"png": png_path, "pdf": pdf_path, "folder": folder}


# ----------------------------------------------------------------- preview ---
# Step-1 sample. Arabic name is the spec's verified example. The English meaning
# + translation are read from the reference (not Arabic). dua_arabic is left
# blank pending the operator's verified Unicode -> its block omits and reflows.
SAMPLE_IBRAHIM = {
    "name_latin": "Ibrahim",
    "name_arabic": "إبراهيم",
    "date": "15 / 05 / 2020",
    "meaning": ("The name Ibrahim, meaning “father of many nations,” belongs to one "
                "of the most revered prophets in Islam. Prophet Ibrahim (Abraham) is "
                "mentioned 69 times across 25 chapters of the Quran, and the 14th Surah "
                "bears his name — a symbol of unwavering faith, devotion, and leadership."),
    "dua_arabic": "",  # <-- supply verified Unicode to enable the dua line
    "dua_translation": "O Allah, I seek Your forgiveness and well-being in this world and the Hereafter.",
    "time": "08:42",
    "weight": "3.40 KG",
    "place": "London, United Kingdom",
}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Render the step-1 Ibrahim sample.")
    ap.add_argument("--style", default="emerald_gold")
    ap.add_argument("--out", default=str(ROOT / "output" / "_preview"))
    args = ap.parse_args()
    paths = render(SAMPLE_IBRAHIM, args.style, args.out)
    print("Wrote:")
    for k, v in paths.items():
        print(f"  {k}: {v}")
