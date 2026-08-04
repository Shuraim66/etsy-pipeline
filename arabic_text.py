#!/usr/bin/env python3
"""
arabic_text.py - the ONE place this pipeline touches Arabic.

CORE RULE (do not violate): this module PLACES pre-verified Arabic Unicode.
It never generates, transliterates, romanizes, guesses, or "corrects" Arabic.
Every Arabic string must be operator-verified Unicode supplied via the data row.

How the text is laid out (chosen for *correctness*, verified empirically):
  * PREFERRED - Pillow built with libraqm (HarfBuzz): pass the RAW verified
    Unicode and let HarfBuzz do shaping + bidi + GPOS mark positioning. This is
    the only path that renders harakat (vowel marks, e.g. in a dua) correctly.
  * FALLBACK  - no libraqm: arabic-reshaper + python-bidi + the BASIC engine
    (the method named in the spec). Connected letterforms are correct, but
    combining harakat are not GPOS-positioned, so vowel marks degrade.

Either way we render exactly the supplied string - only the layout engine
differs. Everything is drawn onto an oversized transparent layer and cropped to
the inked bbox so tall diacritics / final swashes are never clipped.
"""
from __future__ import annotations

import warnings

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:          # fallback-only deps; raqm path doesn't need them
    arabic_reshaper = None
    get_display = None
from PIL import Image, ImageDraw, ImageFont, features

_HAS_RAQM = features.check("raqm")
_RAQM = ImageFont.Layout.RAQM
_BASIC = ImageFont.Layout.BASIC
_LAYOUT = _RAQM if _HAS_RAQM else _BASIC
_TRANSPARENT = (0, 0, 0, 0)

if not _HAS_RAQM:
    # Policy: prefer raqm, warn loudly on fallback (operator's choice).
    warnings.warn(
        "ARABIC FALLBACK: libraqm (HarfBuzz) not found. Falling back to "
        "arabic-reshaper + python-bidi (BASIC engine): connected letterforms "
        "render, but HARAKAT (vowel marks, e.g. in a dua) may be DROPPED or "
        "mispositioned. Install libraqm for fully correct Arabic.",
        RuntimeWarning, stacklevel=2)

# Fallback-only reshaper (used when libraqm is unavailable). Keep any harakat
# the operator supplied; render exactly what was given.
_RESHAPER = arabic_reshaper.ArabicReshaper(configuration={
    "delete_harakat": False,
    "support_ligatures": True,
}) if arabic_reshaper is not None else None

if not _HAS_RAQM and arabic_reshaper is None:
    raise ImportError("Neither libraqm nor arabic-reshaper available - cannot "
                      "render Arabic correctly. Install libraqm-enabled Pillow.")


def has_raqm() -> bool:
    """True if HarfBuzz complex-text layout is available (preferred path)."""
    return _HAS_RAQM


def _glyph_source(text: str) -> str:
    """The exact string handed to the renderer for the active engine.

    With raqm, HarfBuzz consumes the raw logical-order Unicode directly. Without
    raqm, we pre-shape (reshaper) and pre-order (bidi) for the BASIC engine.
    Neither path alters letter identity - it is pure presentation prep.
    """
    if _HAS_RAQM:
        return text
    return get_display(_RESHAPER.reshape(text))


def shape(text: str) -> str:
    """Public accessor for the reshaper+bidi form (fallback engine's input)."""
    return get_display(_RESHAPER.reshape(text))


def render_arabic(text: str, font_path: str, font_size: int, color) -> Image.Image:
    """Render verified Arabic to a tightly-trimmed RGBA image.

    Draws onto an oversized transparent canvas (generous margins so nothing
    clips), then crops to the real inked bounding box. Blank input yields a
    1x1 transparent image so callers can treat "no dua" uniformly.
    """
    if not text or not text.strip():
        return Image.new("RGBA", (1, 1), _TRANSPARENT)

    source = _glyph_source(text)
    font = ImageFont.truetype(font_path, font_size, layout_engine=_LAYOUT)
    pad = font_size  # a full em of margin on every side catches marks & swashes

    # measure (raqm gives the shaped advance) and build an oversized canvas
    draw_kwargs = {"direction": "rtl"} if _HAS_RAQM else {}
    advance = font.getlength(source, **({"direction": "rtl"} if _HAS_RAQM else {}))
    canvas = Image.new("RGBA", (int(advance + pad * 2), int(font_size * 3 + pad * 2)), _TRANSPARENT)
    draw = ImageDraw.Draw(canvas)
    # middle anchor + oversized canvas => order/direction is engine-driven and
    # nothing clips regardless of RTL layout; we crop to ink afterwards.
    draw.text((canvas.width // 2, canvas.height // 2), source,
              font=font, fill=color, anchor="mm", **draw_kwargs)

    bbox = canvas.getbbox()  # actual inked pixels, diacritics included
    if bbox is None:
        return Image.new("RGBA", (1, 1), _TRANSPARENT)
    return canvas.crop(bbox)


def render_arabic_paragraph(text: str, font_path: str, color, max_width: int,
                            font_size: int, leading: float = 1.65,
                            align: str = "center") -> Image.Image:
    """Render verified Arabic that wraps across multiple lines (e.g. a full verse).

    Words are greedily packed into lines no wider than `max_width` at the given
    `font_size`, each line is shaped/rendered independently (Arabic joins within
    a word, never across the space breaks, so per-line shaping stays correct),
    then the lines are stacked right-to-left-agnostic and aligned. Never invents
    or reshapes letters — pure line breaking of the exact input text.
    """
    if not text or not text.strip():
        return Image.new("RGBA", (1, 1), _TRANSPARENT)
    font = ImageFont.truetype(font_path, font_size, layout_engine=_LAYOUT)
    rtl = {"direction": "rtl"} if _HAS_RAQM else {}

    def measure(s: str) -> float:
        return font.getlength(_glyph_source(s), **rtl)

    lines, cur = [], []
    for w in text.split():
        if cur and measure(" ".join(cur + [w])) > max_width:
            lines.append(" ".join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(" ".join(cur))

    imgs = [render_arabic(ln, font_path, font_size, color) for ln in lines]
    step = int(font_size * leading)
    H = step * len(imgs) + font_size
    canvas = Image.new("RGBA", (max_width, H), _TRANSPARENT)
    y = int(font_size * 0.5)
    for im in imgs:
        x = (max_width - im.width) // 2 if align == "center" else (max_width - im.width if align == "right" else 0)
        canvas.alpha_composite(im, (x, y))
        y += step
    return canvas.crop(canvas.getbbox() or (0, 0, 1, 1))


def render_arabic_fitted(text: str, font_path: str, color,
                         max_width: int, target_height: int) -> Image.Image:
    """Render verified Arabic, then scale to target_height (capped at max_width).

    Renders at a high base size for crisp downscaling, then resizes to the
    requested glyph height; if that would exceed max_width, scales to fit width
    instead (preserving aspect). Crisp, and never clips.
    """
    if not text or not text.strip():
        return Image.new("RGBA", (1, 1), _TRANSPARENT)

    base = render_arabic(text, font_path, font_size=max(target_height * 2, 64), color=color)
    scale = target_height / base.height
    if base.width * scale > max_width:
        scale = max_width / base.width
    return base.resize((max(1, round(base.width * scale)), max(1, round(base.height * scale))),
                       Image.LANCZOS)
