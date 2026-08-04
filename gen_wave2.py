#!/usr/bin/env python3
"""
gen_wave2.py - emit the 6 new bestseller-inspired name-print layouts, each in 3
colourways (18 templates, templates/nw_*.json). Built purely on existing render.py
primitives (arabic/line/paragraph/divider blocks, panels/washes, watermark, and
the new crescent ornament). No Arabic is generated: the arabic_name/dua fields are
filled per order from operator-verified Unicode only.

Layouts (gap-fillers vs the market leaders):
  name_hero     big-Arabic hero + tiny Latin        (ArabesqDesigns "نوح")   name-only
  calligraphic  ornamental calligraphic Arabic       (EmeraldCrafts Etsy Pick) name-only
  serif_minimal large serif Latin + delicate Arabic  (SARAH / MARYAM $18)      name-only
  celestial     gold crescent + name + date          (AHMED, baby/aqiqah)      name + DOB
  monogram      ghosted giant name behind            (AYAAN 5*)                name + meaning
  arc_block     bold Bauhaus disc colour-block       (INAYA)                   name + meaning
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TPL = ROOT / "templates"
CANVAS = {"w": 3508, "h": 4961}

FONTS = {
    "amiri":       {"file": "Amiri-Regular.ttf"},
    "amiri_bold":  {"file": "Amiri-Bold.ttf"},
    "rakkas":      {"file": "Rakkas.ttf"},
    "arefruqaa":   {"file": "ArefRuqaa-Regular.ttf"},
    "katibeh":     {"file": "Katibeh.ttf"},
    "cinzel":      {"file": "Cinzel[wght].ttf", "weight": 500},
    "cinzel_lt":   {"file": "Cinzel[wght].ttf", "weight": 400},
    "body":        {"file": "EBGaramond[wght].ttf", "weight": 450},
    "italic":      {"file": "EBGaramond-Italic[wght].ttf", "weight": 450},
}


def base(name, ground, colors, extra_fonts):
    fonts = {k: FONTS[k] for k in extra_fonts}
    return {
        "name": name,
        "canvas": dict(CANVAS),
        "ornament": "none",
        "border": {"style": "none"},
        "corner": {"style": "none"},
        "divider_style": "none",
        "fonts": fonts,
        "background": {"from": ground, "to": ground},
        "colors": colors,
    }


TEMPLATES = {}


def add(t):
    TEMPLATES[t["name"]] = t


# ---- palettes -------------------------------------------------------------
CREAM = "#F1E8DD"
CREAM2 = "#F4EDE3"

# ======================================================================= 1
# name_hero: oversized Arabic hero, small Latin caps beneath. name-only.
for cw, ink, accent, ground in [
    ("charcoal", "#2B2823", "#9A6B4E", CREAM),
    ("sage",     "#4A5647", "#7C8768", "#ECEBE1"),
    ("terracotta", "#7A3B28", "#B5603F", "#F3E7DD"),
]:
    t = base(f"nw_name_hero_{cw}", ground,
             {"ink": ink, "soft": "#8A7F68", "accent": accent},
             ["amiri_bold", "cinzel"])
    t["flow"] = {"region": [0.30, 0.72], "valign": "center", "blocks": [
        {"id": "arabic_name", "field": "name_arabic", "type": "arabic",
         "font": "amiri_bold", "height": 0.155, "max_w": 0.82, "color": "ink"},
        {"id": "d", "type": "divider", "style": "rule", "width": 0.07,
         "color": "accent", "gap": 0.055},
        {"id": "latin_name", "field": "name_latin", "type": "line",
         "font": "cinzel", "size": 0.026, "tracking": 0.34, "upper": True,
         "color": "soft", "gap": 0.04},
    ]}
    add(t)

# ======================================================================= 2
# calligraphic: ornamental display-Arabic name, Latin in italic below. name-only.
for cw, afont, ink, ground in [
    ("ink",  "arefruqaa", "#25211C", CREAM),
    ("rouge", "rakkas",   "#7A2E2A", "#F4EBE1"),
    ("olive", "katibeh",  "#3E4A3A", "#EDEBDF"),
]:
    t = base(f"nw_calligraphic_{cw}", ground,
             {"ink": ink, "soft": "#8A7F68", "accent": "#B08D4F"},
             [afont, "italic"])
    h = 0.20 if afont == "katibeh" else (0.16 if afont == "rakkas" else 0.14)
    t["flow"] = {"region": [0.32, 0.70], "valign": "center", "blocks": [
        {"id": "arabic_name", "field": "name_arabic", "type": "arabic",
         "font": afont, "height": h, "max_w": 0.84, "color": "ink"},
        {"id": "latin_name", "field": "name_latin", "type": "line",
         "font": "italic", "size": 0.030, "tracking": 0.06, "upper": False,
         "color": "soft", "gap": 0.06},
    ]}
    add(t)

# ======================================================================= 3
# serif_minimal: large Cinzel Latin, thin rule, delicate Amiri Arabic. name-only.
for cw, ink, accent, ground in [
    ("cream",   "#2B2823", "#9A6B4E", CREAM2),
    ("sage",    "#46503F", "#7C8768", "#EAEAE0"),
    ("clay",    "#5E3A2C", "#A9654A", "#F2E7DE"),
]:
    t = base(f"nw_serif_minimal_{cw}", ground,
             {"ink": ink, "soft": "#8C8478", "accent": accent},
             ["cinzel_lt", "amiri", "italic"])
    t["flow"] = {"region": [0.34, 0.66], "valign": "center", "blocks": [
        {"id": "latin_name", "field": "name_latin", "type": "line",
         "font": "cinzel_lt", "size": 0.058, "tracking": 0.16, "upper": True,
         "color": "ink"},
        {"id": "d", "type": "divider", "style": "rule", "width": 0.09,
         "color": "accent", "gap": 0.05},
        {"id": "arabic_name", "field": "name_arabic", "type": "arabic",
         "font": "amiri", "height": 0.06, "max_w": 0.5, "color": "ink", "gap": 0.05},
    ]}
    add(t)

# ======================================================================= 4
# celestial: gold crescent + name + Arabic + date + meaning. name + DOB.
for cw, ground, ink, gold, soft in [
    ("cream", CREAM, "#2B2823", "#B08D4F", "#8A7F68"),
    ("navy",  "#243140", "#EDE6DA", "#C7A667", "#A9B0B8"),
    ("sage",  "#E9E9DF", "#3E4A3A", "#A98A4E", "#7C8163"),
]:
    t = base(f"nw_celestial_{cw}", ground,
             {"ink": ink, "soft": soft, "gold": gold},
             ["cinzel", "amiri", "italic"])
    t["ornament"] = "crescent"
    t["crest"] = {"size": 0.16, "cy": 0.205, "color": "gold"}
    t["zones"] = [
        {"region": [0.1, 0.40, 0.9, 0.50], "valign": "center", "blocks": [
            {"id": "latin_name", "field": "name_latin", "type": "line",
             "font": "cinzel", "size": 0.045, "tracking": 0.18, "upper": True,
             "color": "ink"}]},
        {"region": [0.2, 0.51, 0.8, 0.585], "valign": "center", "blocks": [
            {"id": "arabic_name", "field": "name_arabic", "type": "arabic",
             "font": "amiri", "height": 0.05, "max_w": 0.45, "color": "gold"}]},
        {"region": [0.3, 0.60, 0.7, 0.645], "valign": "center", "blocks": [
            {"id": "date", "field": "date", "type": "line", "font": "italic",
             "size": 0.020, "tracking": 0.24, "color": "soft"}]},
        {"region": [0.2, 0.67, 0.8, 0.80], "valign": "top", "blocks": [
            {"id": "meaning", "type": "paragraph", "font": "italic",
             "size": 0.0145, "leading": 1.7, "max_w": 0.5, "color": "soft"}]},
    ]
    add(t)

# ======================================================================= 5
# monogram: ghosted giant Arabic name behind the composed name block. name+meaning.
for cw, ground, ink, wm, accent in [
    ("terracotta", CREAM, "#2B2823", "#CFA982", "#B5603F"),
    ("sage",       "#EDEDE3", "#3E4A3A", "#B4C09A", "#7C8768"),
    ("charcoal",   "#EEEAE3", "#2A2723", "#C0B49A", "#6E5A48"),
]:
    t = base(f"nw_monogram_{cw}", ground,
             {"ink": ink, "soft": "#8A7F68", "accent": accent, "wm": wm},
             ["cinzel", "amiri", "body", "italic"])
    t["watermark"] = {"field": "name_arabic", "font": "amiri", "color": "wm",
                      "max_w": 0.9, "height": 0.5, "cy": 0.5, "alpha": 0.6}
    t["zones"] = [
        {"region": [0.1, 0.44, 0.9, 0.55], "valign": "center", "blocks": [
            {"id": "latin_name", "field": "name_latin", "type": "line",
             "font": "cinzel", "size": 0.05, "tracking": 0.16, "upper": True,
             "color": "ink"}]},
        {"region": [0.3, 0.56, 0.7, 0.60], "valign": "center", "blocks": [
            {"id": "d", "type": "divider", "style": "diamond", "width": 0.1,
             "color": "accent"}]},
        {"region": [0.18, 0.61, 0.82, 0.74], "valign": "top", "blocks": [
            {"id": "meaning", "type": "paragraph", "font": "italic",
             "size": 0.0145, "leading": 1.7, "max_w": 0.52, "color": "soft"}]},
    ]
    add(t)

# ======================================================================= 6
# arc_block: bold Bauhaus disc colour-block, name + Arabic + meaning. name+meaning.
for cw, disc, ground, ink in [
    ("terracotta", "#B5603F", CREAM, "#2B2823"),
    ("emerald",    "#2F5D50", "#F1EDE3", "#23201C"),
    ("ochre",      "#C08A3E", "#F3ECE0", "#2B2823"),
]:
    t = base(f"nw_arc_block_{cw}", ground,
             {"ink": ink, "soft": "#8A7F68", "disc": disc, "light": "#F4EEE4"},
             ["cinzel", "amiri", "italic"])
    t["background"]["washes"] = [
        {"cx": 0.5, "cy": 0.30, "rx": 0.29, "ry": 0.19, "color": "disc",
         "alpha": 0.95, "blur": 0.004}]
    t["zones"] = [
        # Arabic reversed out of the disc
        {"region": [0.30, 0.255, 0.70, 0.345], "valign": "center", "blocks": [
            {"id": "arabic_name", "field": "name_arabic", "type": "arabic",
             "font": "amiri", "height": 0.05, "max_w": 0.34, "color": "light"}]},
        {"region": [0.1, 0.53, 0.9, 0.62], "valign": "center", "blocks": [
            {"id": "latin_name", "field": "name_latin", "type": "line",
             "font": "cinzel", "size": 0.046, "tracking": 0.16, "upper": True,
             "color": "ink"}]},
        {"region": [0.18, 0.65, 0.82, 0.79], "valign": "top", "blocks": [
            {"id": "meaning", "type": "paragraph", "font": "italic",
             "size": 0.0145, "leading": 1.7, "max_w": 0.52, "color": "soft"}]},
    ]
    add(t)


def main():
    for name, t in TEMPLATES.items():
        (TPL / f"{name}.json").write_text(json.dumps(t, indent=2, ensure_ascii=False))
    print(f"wrote {len(TEMPLATES)} templates:")
    for n in sorted(TEMPLATES):
        print("  ", n)


if __name__ == "__main__":
    main()
