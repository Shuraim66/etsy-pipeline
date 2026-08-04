#!/usr/bin/env python3
"""
migrate_mockups.py - convert the flat 4:5 frame set into the new self-contained
per-mockup asset directories the data-driven renderer consumes:

    mockups/<name>/
        background.webp
        config.json

These frames are single photographs (the moulding is already part of the
photo), so they carry no separate frame/shadow/glare layers - the renderer
skips those automatically. inner_quad is the traced opening; outer_quad is the
opening grown by a small margin to approximate the moulding's outer edge (used
only for perspective detection / future features here).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "assets/mockups/frames"
OUT = ROOT / "mockups"

# descriptive metadata only (never drives behaviour)
META = {
    "m1_black_hung":   ("hung", "black"),
    "m2_gold_lean":    ("lean", "gold"),
    "m3_brass_flatlay": ("flatlay", "brass"),
    "m4_gold_easel":   ("easel", "gold"),
}


def grow(quad, frac):
    q = np.array(quad, dtype=float)
    c = q.mean(axis=0)
    return [[round(float(x), 1), round(float(y), 1)] for x, y in (c + (q - c) * (1 + frac))]


def main():
    coords = json.loads((SRC / "coords.json").read_text())
    OUT.mkdir(exist_ok=True)
    for name, inner in coords.items():
        d = OUT / name
        d.mkdir(parents=True, exist_ok=True)
        img = Image.open(SRC / f"{name}.jpg").convert("RGB")
        w, h = img.size
        img.save(d / "background.webp", "WEBP", quality=92, method=6)

        style, color = META.get(name, ("flatlay", "wood" if name.startswith("px_") else "black"))
        config = {
            "version": 1,
            "canvas": {"width": w, "height": h},
            "frame": {"style": style, "color": color, "has_mat": False, "glass": True},
            "outer_quad": grow(inner, 0.05),
            "inner_quad": [[round(float(x), 1), round(float(y), 1)] for x, y in inner],
            "effects": {
                "shadow": {"enabled": False, "opacity": 0.45, "blend_mode": "multiply"},
                "glare": {"enabled": False, "opacity": 0.18, "blend_mode": "screen"},
            },
            "render": {"allow_crop": False, "default_padding": 8, "interpolation": "lanczos"},
        }
        (d / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
        print("wrote", d.name)
    print(f"\n{len(coords)} mockups -> {OUT}")


if __name__ == "__main__":
    main()
