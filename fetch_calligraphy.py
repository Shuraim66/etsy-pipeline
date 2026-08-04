#!/usr/bin/env python3
"""
fetch_calligraphy.py - pull open-access ISLAMIC CALLIGRAPHY from Met + AIC
into output/staging_calligraphy/ (reuses fetch_pd_art helpers).

Every piece is a real historical work (levha, tughra, Quran folio, hilye...)
so the Arabic is authentic master calligraphy - no generation, no correctness
risk from us. ATTRIBUTION.txt per piece; the operator confirms content before
listing (museum metadata titles are recorded verbatim to aid that check).
"""
from __future__ import annotations

import io
import time
from pathlib import Path

from PIL import Image

import fetch_pd_art as pd

OUT = Path(__file__).resolve().parent / "output" / "staging_calligraphy"

NICHES = [
    ("levha_panel",   "calligraphy panel",     3),
    ("tughra",        "tughra",                2),
    ("quran_folio",   "quran folio",           4),
    ("nastaliq",      "nastaliq calligraphy",  2),
    ("album_leaf",    "calligraphy album",     3),
]

# a piece must mention one of these in its title to count as calligraphy art
TITLE_MUST = ("calligraph", "qur", "koran", "tughra", "folio", "levha",
              "album", "panel", "basmala", "hilye", "script")


def met_search_islamic(query: str, want: int, seen: set) -> list[dict]:
    """Met search constrained to the Islamic Art department (id 14)."""
    import urllib.parse
    q = urllib.parse.quote(query)
    try:
        res = pd.get_json("https://collectionapi.metmuseum.org/public/collection/v1/"
                          f"search?q={q}&hasImages=true&departmentIds=14")
    except Exception:
        return []
    picks = []
    for oid in (res.get("objectIDs") or [])[:80]:
        if len(picks) >= want:
            break
        key = f"met:{oid}"
        if key in seen:
            continue
        try:
            obj = pd.get_json(f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{oid}")
        except Exception:
            continue
        title = (obj.get("title") or "").lower()
        if not obj.get("isPublicDomain") or not obj.get("primaryImage"):
            continue
        if not any(k in title for k in TITLE_MUST):
            continue
        picks.append({
            "source": "The Metropolitan Museum of Art",
            "license": "CC0 / Open Access (Met isPublicDomain=true)",
            "id": key,
            "title": obj.get("title") or "Untitled",
            "artist": obj.get("artistDisplayName") or "Unknown calligrapher",
            "date": obj.get("objectDate") or "",
            "img_url": obj["primaryImage"],
        })
        seen.add(key)
        import time as _t
        _t.sleep(0.2)
    return picks

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    pd.OUT = OUT                       # redirect exports
    seen: set = set()
    made, catalog = [], []

    for niche, query, want in NICHES:
        print(f"[{niche}] {query}")
        picks = met_search_islamic(query, want, seen)
        for meta in picks:
            try:
                raw = pd.get_bytes(meta["img_url"])
                img = Image.open(io.BytesIO(raw))
                img.load()
            except Exception as e:
                print(f"  skip (download): {meta['title'][:40]} - {e}")
                continue
            if img.width < pd.MIN_SRC_W:
                print(f"  skip (small {img.width}px): {meta['title'][:40]}")
                continue
            png = pd.export(meta, img)
            made.append(png)
            catalog.append(f"{niche:12s} {meta['artist'][:26]:26s} {meta['title'][:50]:50s} {meta['source']}")
            print(f"  ok: {meta['title'][:60]} ({img.width}px)")
            time.sleep(0.3)

    (OUT / "CATALOG.txt").write_text(
        "Open-access Islamic calligraphy (CC0). OPERATOR MUST VERIFY each piece's\n"
        "content/title before listing - list with accurate description only.\n\n"
        + "\n".join(catalog) + "\n", encoding="utf-8")
    print(f"\n{len(made)} pieces")
    if made:
        print("review sheet:", pd.contact_sheet(made))
