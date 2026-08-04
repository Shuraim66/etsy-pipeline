#!/usr/bin/env python3
"""
etsy_meta.py - build Etsy listing metadata (title, description, tags) for a
design. Pure/local; no network. The Etsy client assembles the API payload from
this + the listing defaults in etsy_secrets.json.
"""
from __future__ import annotations

TITLE_MAX = 140       # Etsy listing title hard limit
TAG_MAX_LEN = 20      # per-tag character limit
TAG_MAX_COUNT = 13    # max tags per listing


def _title(name: str) -> str:
    parts = [name, "Personalized Islamic Name Print", "Arabic Calligraphy Wall Art",
             "Eid & Nikah Gift", "Digital Download"]
    while len(parts) > 2 and len(" | ".join(parts)) > TITLE_MAX:
        parts.pop()
    return " | ".join(parts)[:TITLE_MAX]


def _clean_tag(t: str) -> str:
    # Etsy tags: <= 20 chars; letters, numbers, spaces and hyphens only.
    t = "".join(c for c in t.strip().lower() if c.isalnum() or c in " -")
    return " ".join(t.split())[:TAG_MAX_LEN].strip()


def _tags(name: str, style: str, base_tags) -> list[str]:
    candidates = [f"{name} arabic", f"{name} print", f"{style.replace('_', ' ')} print"]
    candidates += list(base_tags or [])
    out: list[str] = []
    for t in candidates:
        ct = _clean_tag(t)
        if ct and ct not in out:
            out.append(ct)
        if len(out) >= TAG_MAX_COUNT:
            break
    return out


GEO_TAGS = [
    "islamic geometric", "geometric wall art", "islamic wall art", "arabesque print",
    "moroccan pattern", "gold geometric art", "islamic art print", "arabic wall decor",
    "printable wall art", "digital download", "ramadan decor", "mosque art print",
    "star pattern art",
]


def _geo_title(name: str) -> str:
    parts = [name, "Islamic Geometric Wall Art", "Arabesque Pattern Print", "Digital Download"]
    while len(parts) > 2 and len(" | ".join(parts)) > TITLE_MAX:
        parts.pop()
    return " | ".join(parts)[:TITLE_MAX]


def _geo_meta(name: str, listing_defaults: dict) -> dict:
    description = (
        f"{name} — an original Islamic geometric wall art print. An intricate arabesque "
        "pattern drawn from traditional Islamic geometry, in a clean, modern palette.\n\n"
        "★ INSTANT DIGITAL DOWNLOAD — no physical item is shipped.\n"
        "★ Multiple print ratios included (ISO A3/A4/A5, plus 2:3, 3:4, 4:5, 5:7) so you can print at\n"
        "  A-sizes, 8x10, 11x14, 16x20, 18x24, 24x36 and more.\n"
        "★ High-resolution 300 DPI files (PNG + PDF).\n\n"
        "Perfect for Ramadan & Eid, a modern Muslim home, prayer room, or office — and a gift that suits any decor.\n\n"
        "HOW IT WORKS: purchase → download the files → print at home, a local shop, or online.\n"
        "Colours may vary slightly between screens and printers. For personal use; not for resale."
    )
    out = [t for t in (_clean_tag(x) for x in GEO_TAGS) if t][:TAG_MAX_COUNT]
    return {
        "title": _geo_title(name), "description": description, "tags": out,
        "price": float(listing_defaults.get("price", 9.99)),
        "currency_code": listing_defaults.get("currency_code", "USD"),
        "is_personalizable": False,
    }


def build_meta(name: str, style: str, listing_defaults: dict, meaning: str = "") -> dict:
    """Return {title, description, tags, price, currency_code} for one design."""
    name = (name or "Name").strip()
    if str(style).startswith("geo_"):
        return _geo_meta(name, listing_defaults)
    intro = (f"{name} — a personalized Islamic name print in elegant Arabic calligraphy."
             + (f"\n\n{meaning.strip()}" if meaning and meaning.strip() else ""))
    description = intro + (
        "\n\n"
        "★ INSTANT DIGITAL DOWNLOAD — no physical item is shipped.\n"
        "★ Multiple print ratios included (ISO A3/A4/A5, plus 2:3, 3:4, 4:5, 5:7) so you can print at\n"
        "  A-sizes, 8x10, 11x14, 16x20, 18x24, 24x36 and more.\n"
        "★ High-resolution 300 DPI files (PNG + PDF).\n"
        "★ Personalized with the name in verified Arabic calligraphy.\n\n"
        "Perfect for Eid, Ramadan, weddings & nikah, a new baby or nursery, or a thoughtful Muslim gift.\n\n"
        "HOW IT WORKS: purchase → download the files → print at home, a local shop, or online.\n"
        "Colours may vary slightly between screens and printers. For personal use; not for resale."
    )
    return {
        "title": _title(name),
        "description": description,
        "tags": _tags(name, style, listing_defaults.get("base_tags", [])),
        "price": float(listing_defaults.get("price", 9.99)),
        "currency_code": listing_defaults.get("currency_code", "USD"),
        "is_personalizable": True,
    }


if __name__ == "__main__":
    import json
    m = build_meta("Ibrahim", "hero", {"price": 9.99, "currency_code": "USD",
                                        "base_tags": ["islamic wall art", "muslim gift", "eid gift"]},
                   meaning="Father of many nations.")
    print(json.dumps(m, indent=2, ensure_ascii=False))
    print("title len:", len(m["title"]), "| tags:", len(m["tags"]))