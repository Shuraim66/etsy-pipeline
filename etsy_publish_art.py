#!/usr/bin/env python3
"""
etsy_publish_art.py - DRAFT Etsy listings for the non-personalized art lines
(AI painterly originals in staging_sd, public-domain masters in staging_pd_art).

Differences from the name-print flow (etsy_publish.py):
  * NO personalization -> buyers get INSTANT DOWNLOAD after purchase.
  * Listings go to a separate shop section ("Art Prints") — created on first
    --live run if art_section_id is not stored in etsy_secrets.json.
  * Prices: $8.99 AI originals, $5.99 public-domain reprints.
  * PD listings credit artist + museum from ATTRIBUTION.txt (never claimed as
    original work); AI listings are described honestly as artist-designed
    digital art prints.

DRY-RUN by default; --live creates DRAFTS only (review/publish in Shop Manager).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import etsy_api

ROOT = Path(__file__).resolve().parent
SIZE_TAGS = ("iso_A", "ratio_2x3", "ratio_3x4", "ratio_4x5", "ratio_5x7")
TITLE_MAX, TAG_MAX_LEN, TAG_MAX_COUNT = 140, 20, 13

ART_SECTION_TITLE = "Art Prints"
PRICE_AI, PRICE_PD = 6.99, 4.99   # list prices; run ~25-30% launch sale in Shop Manager

BASE_TAGS = ["printable wall art", "digital download", "instant download",
             "wall art print", "home decor", "gallery wall art"]

# slug -> (display title lead, niche tags, one-line description flavor)
AI_META = {
    "meadow_42": ("Wildflower Meadow Painting", ["wildflower print", "poppy wall art", "impressionist art", "meadow painting", "floral landscape"], "an impressionist wildflower meadow at golden hour, with poppies and daisies in warm evening light"),
    "botanical_101": ("Watercolor Eucalyptus Print", ["eucalyptus print", "watercolor leaves", "boho wall art", "sage green decor", "botanical print"], "delicate watercolor eucalyptus branches in soft sage tones on cream"),
    "coast_202": ("Abstract Gold Coastal Art", ["coastal wall art", "abstract seascape", "gold leaf art", "teal beach decor", "ocean abstract"], "an abstract seascape of soft teal waves with gold-leaf accents"),
    "moody_floral_303": ("Moody Peony Still Life", ["moody floral art", "dark botanical", "peony wall art", "vintage floral", "dark academia"], "dusty mauve peonies on a deep charcoal ground, painted in dramatic chiaroscuro light"),
    "mountains_404": ("Misty Mountains Ink Painting", ["mountain wall art", "japandi decor", "ink wash art", "zen wall art", "minimalist nature"], "misty layered ridgelines in a quiet Japanese ink-wash style"),
    "desert_boho_111": ("Boho Desert Sunset Print", ["desert wall art", "boho decor", "cactus print", "terracotta art", "southwestern art"], "a terracotta desert at dusk with saguaro silhouettes under a blush-pink sky"),
    "tropical_12": ("Tropical Monstera Painting", ["monstera print", "tropical decor", "jungle wall art", "palm leaf print", "green botanical"], "lush monstera and palm leaves in deep emerald gouache on cream"),
    "gold_abstract_313": ("Gold Fluid Abstract Art", ["fluid art print", "gold abstract", "marble wall art", "black gold decor", "modern abstract"], "flowing marbled paint in cream, charcoal and gold"),
    "goldjap_v964": ("Japandi Gold Abstract", ["japandi wall art", "neutral abstract", "gold line art", "beige wall decor", "organic abstract"], "calm organic curves in warm neutrals traced with gold"),
    "autumn_birch_14": ("Autumn Birch Forest Painting", ["birch tree print", "autumn wall art", "fall decor", "forest painting", "golden leaves art"], "white birch trunks under golden autumn leaves in soft morning light"),
    "ocean_wave_15": ("Ocean Wave Painting", ["ocean wall art", "wave painting", "coastal decor", "turquoise sea art", "surf wall art"], "a cresting turquoise wave with sunlit sea foam"),
    "lavender_16": ("Lavender Field at Sunset", ["lavender print", "provence wall art", "purple wall decor", "farmhouse art", "flower field print"], "rows of Provence lavender rolling toward a farmhouse in golden light"),
    "winter_forest_17": ("Winter Pine Forest Print", ["winter wall art", "snowy forest print", "scandinavian decor", "pine tree art", "hygge decor"], "snow-covered pines in soft blue dusk light"),
    "sunflowers_18": ("Sunflower Bouquet Painting", ["sunflower wall art", "farmhouse decor", "yellow floral print", "kitchen wall art", "impasto flowers"], "an expressive impasto bouquet of sunflowers in a ceramic vase"),
    "koi_inpaint2_8": ("Koi Fish Zen Art Print", ["koi fish art", "japanese wall art", "zen decor", "japandi print", "feng shui art"], "two koi circling in dark teal water with gold ring accents"),
    "celestial_20": ("Crescent Moon Celestial Art", ["celestial print", "moon wall art", "night sky print", "navy gold decor", "mystical art"], "a crescent moon and stars over a calm midnight ocean"),
    "brush_floral_51": ("Impasto Roses Painting", ["rose wall art", "impasto painting", "textured floral", "pink flower print", "cottage decor"], "wild roses painted with thick palette-knife strokes"),
    "brush_landscape_52": ("Palette Knife Landscape", ["textured landscape", "palette knife art", "sunset hills print", "modern landscape", "colorful wall art"], "rolling sunset hills built from bold slabs of paint"),
    "brushabs_v932": ("Bold Ink Abstract Print", ["bold abstract art", "ink brush art", "orange black art", "modern abstract", "gestural painting"], "a calligraphic diagonal sweep in charcoal, orange and cream"),
    "brushabs_v933": ("Modern Brushstroke Abstract", ["brushstroke art", "abstract wall art", "black white orange", "dynamic abstract", "statement art"], "bold crossing brushstrokes with a burst of burnt orange"),
    "brush_stilllife_regen_94": ("Peach Still Life Painting", ["still life print", "kitchen wall art", "peach painting", "old master style", "dining room art"], "a black pitcher and sunlit peaches in a warm painterly still life"),
}


def _clean_tag(t: str) -> str:
    t = "".join(c for c in t.strip().lower() if c.isalnum() or c in " -")
    return " ".join(t.split())[:TAG_MAX_LEN].strip()


def _tags(cands) -> list[str]:
    out = []
    for t in cands:
        ct = _clean_tag(t)
        if ct and ct not in out:
            out.append(ct)
        if len(out) >= TAG_MAX_COUNT:
            break
    return out


def _title(parts) -> str:
    parts = list(parts)
    while len(parts) > 2 and len(" | ".join(parts)) > TITLE_MAX:
        parts.pop()
    return " | ".join(parts)[:TITLE_MAX]


DESC_COMMON = (
    "\n\n★ INSTANT DIGITAL DOWNLOAD — no physical item is shipped, and no "
    "personalization is needed: your files are available the moment payment "
    "clears.\n\n"
    "WHAT YOU RECEIVE (5 high-resolution PDF files, 300 DPI):\n"
    "  • ISO A (prints A3 / A4 / A5)\n"
    "  • 2:3 ratio (4x6, 8x12, 12x18, 16x24, 20x30, 24x36)\n"
    "  • 3:4 ratio (6x8, 9x12, 12x16, 15x20, 18x24)\n"
    "  • 4:5 ratio (8x10, 11x14, 16x20)\n"
    "  • 5:7 ratio (5x7, 10x14)\n\n"
    "Print at home, at a local print shop, or through an online printing "
    "service. Frame not included.\n"
)


def _parse_attribution(folder: Path) -> dict:
    meta = {}
    att = folder / "ATTRIBUTION.txt"
    if att.exists():
        for line in att.read_text(encoding="utf-8").splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip().lower()] = v.strip()
    return meta


def build_meta(folder: Path, line: str) -> dict | None:
    slug = folder.name
    if line == "ai":
        if slug not in AI_META:
            print(f"  ! no AI_META entry for {slug}; skipping")
            return None
        lead, niche_tags, flavor = AI_META[slug]
        title = _title([lead, "Printable Wall Art", "Digital Download"])
        desc = (f"{lead} — {flavor}. An original digital art print designed in our "
                f"studio." + DESC_COMMON)
        tags = _tags(niche_tags + BASE_TAGS)
        price = PRICE_AI
    else:
        a = _parse_attribution(folder)
        artist, work = a.get("artist", "Unknown artist"), a.get("title", "Untitled")
        museum = a.get("museum", "")
        surname = artist.split()[-1] if artist else "Vintage"
        title = _title([f"{work} by {artist}", "Vintage Fine Art Print", "Digital Download"])
        desc = (f"“{work}” by {artist}"
                + (f" ({a['date']})" if a.get("date") else "")
                + f" — a museum-quality digital restoration of this public-domain "
                f"masterpiece, from the open-access collection of the {museum}. "
                f"Artwork is in the public domain; this listing is for a digitally "
                f"prepared print file." + DESC_COMMON)
        tags = _tags([f"{surname} print", f"{surname} wall art", "vintage art print",
                      "fine art print", "famous painting", "classic art",
                      "museum art print"] + BASE_TAGS)
        price = PRICE_PD
    return {"title": title, "description": desc, "tags": tags, "price": price,
            "currency_code": "USD"}


def gather_assets(folder: Path, slug: str):
    # lead: scene1 (real-interior, thumbnail-optimized), then remaining scenes,
    # then close-up frame mocks, then the flat print
    images = [folder / f"{slug}_scene{i}.jpg" for i in (1, 2, 3, 4)
              if (folder / f"{slug}_scene{i}.jpg").exists()]
    images += [folder / f"{slug}_mock{i}.jpg" for i in (1, 2, 3)
               if (folder / f"{slug}_mock{i}.jpg").exists()]
    if (folder / f"{slug}_print.png").exists():
        images.append(folder / f"{slug}_print.png")
    files = [folder / f"{slug}_{t}.pdf" for t in SIZE_TAGS
             if (folder / f"{slug}_{t}.pdf").exists()]
    return images[:10], files[:5]


def ensure_art_section(client: etsy_api.EtsyClient, secrets_all: dict) -> int:
    """Return the art shop-section id, creating the section if needed and
    persisting it into etsy_secrets.json."""
    listing = secrets_all.setdefault("listing", {})
    if listing.get("art_section_id"):
        return int(listing["art_section_id"])
    res = client.post_form(f"/shops/{client.shop_id}/sections",
                           {"title": ART_SECTION_TITLE})
    sid = res.get("shop_section_id")
    listing["art_section_id"] = sid
    (ROOT / "etsy_secrets.json").write_text(
        json.dumps(secrets_all, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"created shop section '{ART_SECTION_TITLE}' -> id {sid}")
    return int(sid)


def process_one(folder: Path, line: str, defaults: dict, live: bool,
                client=None, section_id=None):
    slug = folder.name
    meta = build_meta(folder, line)
    if meta is None:
        return
    images, files = gather_assets(folder, slug)

    print(f"\n=== [{line}] {slug} ===")
    print(f"  title : {meta['title']}")
    print(f"  price : {meta['price']} USD | instant download (no personalization)")
    print(f"  tags  ({len(meta['tags'])}): {', '.join(meta['tags'])}")
    print(f"  images({len(images)}): {', '.join(p.name for p in images)}")
    print(f"  files ({len(files)}): {', '.join(p.name for p in files)}")
    for f in files:
        mb = f.stat().st_size / 1e6
        if mb > 20:
            print(f"  ! WARNING: {f.name} is {mb:.1f} MB (> 20 MB Etsy limit)")

    if not live:
        print("  [dry-run] no API call")
        return
    if not files:
        print("  ! skipped: no digital files")
        return
    d = dict(defaults)
    d["shop_section_id"] = section_id
    d["is_personalizable"] = False           # -> instant download
    d["when_made"] = "2020_2026"             # finished digital design, not made-to-order
    res = client.create_draft_listing(meta, d)
    lid = res.get("listing_id") or (res.get("results") or [{}])[0].get("listing_id")
    for i, f in enumerate(files, 1):
        client.upload_listing_file(lid, f, rank=i)
    for i, im in enumerate(images, 1):
        client.upload_listing_image(lid, im, rank=i)
    print(f"  + DRAFT listing {lid} created")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Draft Etsy listings for art lines (dry-run default).")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--only", help="limit to one slug")
    args = ap.parse_args(argv)

    lines = [("ai", ROOT / "output" / "staging_sd"),
             ("pd", ROOT / "output" / "staging_pd_art")]

    client = section_id = None
    defaults = {}
    if args.live:
        secrets_all = etsy_api.load_secrets()
        defaults = dict(secrets_all.get("listing", {}))
        defaults.pop("personalization_instructions", None)
        client = etsy_api.EtsyClient()
        section_id = ensure_art_section(client, secrets_all)
    else:
        try:
            defaults = dict(etsy_api.load_secrets().get("listing", {}))
        except Exception:
            pass
        print("DRY-RUN — no API calls (add --live to create drafts)")

    n = 0
    for line, root in lines:
        if not root.exists():
            continue
        for folder in sorted(p for p in root.iterdir() if p.is_dir()):
            if args.only and folder.name != args.only:
                continue
            if not (folder / f"{folder.name}_print.png").exists():
                continue
            process_one(folder, line, defaults, args.live, client, section_id)
            n += 1
    print(f"\n{n} listings processed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
