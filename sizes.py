#!/usr/bin/env python3
"""
sizes.py - export one design at the standard print aspect ratios.

Because the layout is fraction-based, each ratio is a real re-render (the design
reflows), not a crop. One file per ratio covers a whole family of physical print
sizes -- the way Etsy digital-download prints are sold.
"""
from __future__ import annotations

from pathlib import Path

import render

# (tag, w_px, h_px, physical sizes covered)  -- ~300 DPI, 6000px long edge
RATIOS = [
    ("iso_A",     4242, 6000, "A3 / A4 / A5 (ISO A)"),
    ("ratio_2x3", 4000, 6000, "4x6, 8x12, 12x18, 16x24, 20x30, 24x36"),
    ("ratio_3x4", 4500, 6000, "6x8, 9x12, 12x16, 15x20, 18x24"),
    ("ratio_4x5", 4800, 6000, "8x10, 11x14, 16x20"),
    ("ratio_5x7", 4286, 6000, "5x7, 10x14"),
]


def export(row: dict, style_name: str, out_dir) -> Path:
    """Render `row` in `style_name` at every print ratio + write a SIZES guide."""
    folder = None
    for tag, w, h, _covers in RATIOS:
        folder = render.render(row, style_name, out_dir, canvas=(w, h), tag=tag)["folder"]
    guide = "Each file is a print ratio; print it at any size in its family:\n\n"
    for tag, w, h, covers in RATIOS:
        guide += f"  {tag:11} ({w}x{h}px, 300 DPI)  ->  {covers}\n"
    (folder / "SIZES.txt").write_text(guide, encoding="utf-8")
    return folder


if __name__ == "__main__":
    import sys
    style = sys.argv[1] if len(sys.argv) > 1 else "hero"
    out = Path(__file__).resolve().parent / "output" / "_sizes"
    print("size pack ->", export(render.SAMPLE_IBRAHIM, style, out))
