#!/usr/bin/env python3
"""
gen_wave3.py - the 3 ArabesqDesigns-inspired layouts approved after the shop
review: full-bleed colourfield, botanical_side (AMARA), and a name+verse pairing.
Full-bleed + AMARA are single-panel listings; the verse pairing is a 2-panel set
(bundle-style) rendered as coordinated posters.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TPL = ROOT / "templates"
CANVAS = {"w": 3508, "h": 4961}
FONTS = {
    "amiri": {"file": "Amiri-Regular.ttf"}, "amiri_bold": {"file": "Amiri-Bold.ttf"},
    "cinzel": {"file": "Cinzel[wght].ttf", "weight": 500},
    "cinzel_lt": {"file": "Cinzel[wght].ttf", "weight": 400},
    "body": {"file": "EBGaramond[wght].ttf", "weight": 450},
    "italic": {"file": "EBGaramond-Italic[wght].ttf", "weight": 450},
}


def base(name, ground, colors, fkeys):
    return {"name": name, "canvas": dict(CANVAS), "ornament": "none",
            "border": {"style": "none"}, "corner": {"style": "none"},
            "divider_style": "none", "fonts": {k: FONTS[k] for k in fkeys},
            "background": {"from": ground, "to": ground}, "colors": colors}


T = {}
def add(t): T[t["name"]] = t

# ============================================================ full-bleed colourfield
# whole poster is the colour; big Arabic reversed out, Latin + meaning in light ink.
for cw, ground, light, soft in [
    ("terracotta", "#B15A3C", "#F4E9DD", "#E4C9B7"),
    ("emerald",    "#2F5A4E", "#EDE7D8", "#B9C6BB"),
    ("navy",       "#26333F", "#ECE5D7", "#AAB4BC"),
]:
    t = base(f"nw_fullbleed_{cw}", ground, {"light": light, "soft": soft},
             ["amiri_bold", "cinzel", "italic"])
    t["zones"] = [
        {"region": [0.14, 0.24, 0.86, 0.44], "valign": "center", "blocks": [
            {"id": "arabic_name", "field": "name_arabic", "type": "arabic",
             "font": "amiri_bold", "height": 0.135, "max_w": 0.74, "color": "light"}]},
        {"region": [0.1, 0.50, 0.9, 0.58], "valign": "center", "blocks": [
            {"id": "latin_name", "field": "name_latin", "type": "line", "font": "cinzel",
             "size": 0.032, "tracking": 0.28, "upper": True, "color": "light"}]},
        {"region": [0.2, 0.62, 0.8, 0.75], "valign": "top", "blocks": [
            {"id": "meaning", "type": "paragraph", "font": "italic", "size": 0.0142,
             "leading": 1.7, "max_w": 0.5, "color": "soft"}]},
    ]
    add(t)

# ============================================================ botanical_side (AMARA)
# cream ground, a botanical sprig up top, a LARGE serif name lower, arabic + meaning.
for cw, ground, ink, accent, art in [
    ("olive",  "#F1E8DD", "#2B2823", "#8A6A44", "olive"),
    ("sage",   "#E9EBE1", "#3B463A", "#6E7A5C", "eucalyptus"),
    ("blush",  "#F3E7E1", "#5E3A2C", "#B08161", "wildflower"),
]:
    t = base(f"nw_amara_{cw}", ground, {"ink": ink, "soft": "#8A7F68", "accent": accent},
             ["cinzel_lt", "amiri", "italic"])
    t["ornament"] = "botanical"
    t["crest"] = {"art": art, "size": 470, "cy": 0.24, "color": "accent"}
    t["zones"] = [
        {"region": [0.1, 0.46, 0.9, 0.57], "valign": "center", "blocks": [
            {"id": "latin_name", "field": "name_latin", "type": "line", "font": "cinzel_lt",
             "size": 0.062, "tracking": 0.1, "upper": True, "color": "ink"}]},
        {"region": [0.25, 0.585, 0.75, 0.65], "valign": "center", "blocks": [
            {"id": "arabic_name", "field": "name_arabic", "type": "arabic", "font": "amiri",
             "height": 0.038, "max_w": 0.4, "color": "accent"}]},
        {"region": [0.2, 0.68, 0.8, 0.8], "valign": "top", "blocks": [
            {"id": "meaning", "type": "paragraph", "font": "italic", "size": 0.0142,
             "leading": 1.7, "max_w": 0.5, "color": "soft"}]},
    ]
    add(t)

# ============================================================ name+verse SET (2 panels)
# a coordinated pair sold together: panel A = name, panel B = the dua/verse.
# same ground + type so they hang as a set. (bundle-style listing.)
for cw, ground, ink, accent in [
    ("cream", "#F1E8DD", "#2B2823", "#9A6B4E"),
    ("navy",  "#26333F", "#ECE5D7", "#C7A667"),
]:
    # panel A — name
    a = base(f"nw_verseset_{cw}_A", ground, {"ink": ink, "soft": "#8A7F68", "accent": accent},
             ["cinzel", "amiri", "italic"])
    a["ornament"] = "botanical"; a["crest"] = {"art": "laurel", "size": 620, "cy": 0.26, "color": "accent"}
    a["zones"] = [
        {"region": [0.1, 0.44, 0.9, 0.54], "valign": "center", "blocks": [
            {"id": "latin_name", "field": "name_latin", "type": "line", "font": "cinzel",
             "size": 0.05, "tracking": 0.14, "upper": True, "color": "ink"}]},
        {"region": [0.25, 0.55, 0.75, 0.62], "valign": "center", "blocks": [
            {"id": "arabic_name", "field": "name_arabic", "type": "arabic", "font": "amiri",
             "height": 0.05, "max_w": 0.45, "color": "accent"}]},
        {"region": [0.2, 0.66, 0.8, 0.78], "valign": "top", "blocks": [
            {"id": "meaning", "type": "paragraph", "font": "italic", "size": 0.0142,
             "leading": 1.7, "max_w": 0.5, "color": "soft"}]},
    ]
    add(a)
    # panel B — dua/verse (Arabic paragraph + translation), filled from verified config
    b = base(f"nw_verseset_{cw}_B", ground, {"ink": ink, "soft": "#8A7F68", "accent": accent},
             ["cinzel", "amiri", "italic"])
    b["fonts"]["arabic_dua"] = FONTS["amiri"]
    b["zones"] = [
        {"region": [0.14, 0.30, 0.86, 0.52], "valign": "center", "blocks": [
            {"id": "dua_arabic", "field": "dua_arabic", "type": "arabic_para", "font": "arabic_dua",
             "size": 0.03, "leading": 1.7, "max_w": 0.72, "color": "ink"}]},
        {"region": [0.2, 0.58, 0.8, 0.72], "valign": "top", "blocks": [
            {"id": "dua_translation", "type": "paragraph", "field": "dua_translation", "font": "italic",
             "size": 0.016, "leading": 1.7, "max_w": 0.56, "color": "soft"}]},
    ]
    add(b)


def main():
    for name, t in T.items():
        (TPL / f"{name}.json").write_text(json.dumps(t, indent=2, ensure_ascii=False))
    print(f"wrote {len(T)} templates:")
    for n in sorted(T): print("  ", n)


if __name__ == "__main__":
    main()
