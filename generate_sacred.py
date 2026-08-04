#!/usr/bin/env python3
"""
generate_sacred.py - render the verified sacred texts through the new verse
layouts into output/staging_sacred/.

Text policy: Arabic comes ONLY from data/sacred_texts.json entries with
verified:true (canonical Uthmani, human-confirmed). This script never edits
Arabic. Layout labels/translations are the verified English from the same file.

Design set (2026-07 regeneration - replaces the rejected first batch):
  verse_gallery           sage colour-block editorial (bestseller look)
  verse_ivory_arch        ivory arch panel + gold rule (prayer room lead)
  verse_night             charcoal-navy + gold on star field (statement)
  verse_terracotta_block  bold terracotta block, cream verse (boho)

Per verse x style: print.png/pdf, then package_art.py adds ratios/proof/mockups.
"""
from __future__ import annotations

import gc
import json
from pathlib import Path

import render

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "staging_sacred"

STYLES = ["verse_gallery", "verse_ivory_arch", "verse_night", "verse_terracotta_block"]

# Which texts suit a poster (short enough to breathe at display size).
# Ayat al-Kursi is long: keep it to the two layouts with the largest text zones.
TEXTS = {
    "bismillah":     {"styles": STYLES},
    "ikhlas_1":      {"styles": STYLES},
    "sharh_5":       {"styles": STYLES},
    "sharh_6":       {"styles": STYLES},
    "ayat_al_kursi": {"styles": ["verse_night", "verse_ivory_arch"]},
}


def main():
    data = json.loads((ROOT / "data" / "sacred_texts.json").read_text(encoding="utf-8"))
    made = []
    for key, cfg in TEXTS.items():
        entry = data.get(key)
        if not entry or not entry.get("verified"):
            print(f"skip {key}: not verified")
            continue
        # unique display label per text (sharh_5/sharh_6 share a surah name,
        # so include the verse reference to keep slugs and posters distinct)
        label = entry["label"].split("·")[0].strip()
        ref = entry.get("verse_key", "")
        display = f"{label} {ref}" if label.lower().count("surah") and ref else label
        row = {
            "name_latin": display,
            "name_arabic": entry["arabic_uthmani"],               # verified Unicode, placed verbatim
            "meaning": entry["label"],                            # reference line
            "dua_translation": entry["translation"],
        }
        slug_base = key
        for style in cfg["styles"]:
            res = render.render(row, style, OUT)
            made.append(res["folder"])
            print(f"ok {slug_base} x {style}", flush=True)
            gc.collect()
    print(f"\n{len(made)} designs rendered to {OUT}")


if __name__ == "__main__":
    main()
