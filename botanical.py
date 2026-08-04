#!/usr/bin/env python3
"""
botanical.py - load the Figma-authored botanical line-art (assets/botanical/*.png,
black on transparent) and tint it to any colourway using its own alpha as the
shape mask. These replace the old geometric procedural ornaments; the vectors are
original (drawn by us in Figma) and license-clean for resale.
"""
from pathlib import Path
from PIL import Image

ASSET = Path(__file__).resolve().parent / "assets" / "botanical"
NAMES = ("eucalyptus", "olive", "wildflower", "laurel")

_CACHE: dict = {}


def tinted(name: str, target_w: int, color: tuple) -> Image.Image:
    """Return the motif recoloured to `color` (r,g,b), scaled to `target_w` px wide.
    The source art is dark on transparent; we keep only its alpha and fill with the
    target colour, so anti-aliased edges stay clean and it recolours per colourway."""
    key = (name, int(target_w), tuple(color))
    if key in _CACHE:
        return _CACHE[key]
    # Figma exports the art dark-on-light with an OPAQUE background, so the shape
    # lives in luminance, not alpha. Derive the mask from brightness: dark art ->
    # opaque, light ground -> transparent. Level it so the ~cream ground goes fully
    # clear (no haze) and the near-black art goes fully opaque.
    src = Image.open(ASSET / f"{name}.png").convert("L")
    mask = src.point(lambda v: 0 if v >= 232 else min(255, int((232 - v) * 255 / 200)))
    solid = Image.new("RGBA", src.size, tuple(color) + (0,))
    solid.putalpha(mask)
    h = max(1, round(src.height * target_w / src.width))
    out = solid.resize((int(target_w), h), Image.LANCZOS)
    _CACHE[key] = out
    return out
