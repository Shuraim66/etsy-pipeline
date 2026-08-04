#!/usr/bin/env python3
"""Split the 3 name-only styles into standalone listings, each with 3 colourways
(replacing the old single 'pick your style' bundle)."""
import json, copy
from pathlib import Path

TPL = Path(__file__).resolve().parent / "templates"


def load(n): return json.loads((TPL / f"{n}.json").read_text())
def save(t): (TPL / f"{t['name']}.json").write_text(json.dumps(t, indent=2, ensure_ascii=False))


# ---- field: full-bleed colour field, dark ink text ----
base = load("nv_nameonly_field")
for cw, ground, ink, soft in [
    ("sage",  "#C9D3C0", "#2E362A", "#5E6754"),
    ("blush", "#EAD4CC", "#5E3A2C", "#8A6152"),
    ("sky",   "#C7D5DC", "#2B3A42", "#556A73"),
]:
    t = copy.deepcopy(base); t["name"] = f"nv_nameonly_field_{cw}"
    t["background"] = {"from": ground, "to": ground}
    t["colors"] = {"ink": ink, "soft": soft}
    save(t)

# ---- botanical: colour panel + wildflower, name on cream below ----
base = load("nv_nameonly_botanical")
for cw, panel in [("terracotta", "#B5603F"), ("sage", "#7C8768"), ("navy", "#2A3A48")]:
    t = copy.deepcopy(base); t["name"] = f"nv_nameonly_botanical_{cw}"
    t["background"]["panels"][0]["color"] = panel
    save(t)

# ---- poster: minimal, big serif Latin + rule + Arabic ----
base = load("nv_nameonly_poster")
for cw, ground, ink, accent in [
    ("cream",    "#F0E7DD", "#2B2823", "#9A6B4E"),
    ("sage",     "#E9EBE1", "#3B463A", "#6E7A5C"),
    ("charcoal", "#33302B", "#ECE5D7", "#B08D4F"),
]:
    t = copy.deepcopy(base); t["name"] = f"nv_nameonly_poster_{cw}"
    t["background"] = {"from": ground, "to": ground}
    t["colors"] = {"ink": ink, "soft": "#8A7F68", "accent": accent}
    save(t)

# remove the old single-style bundle templates
for old in ("nv_nameonly_field", "nv_nameonly_botanical", "nv_nameonly_poster"):
    p = TPL / f"{old}.json"
    if p.exists(): p.unlink()

print("generated 9 name-only colourway templates; removed 3 bundle originals")
