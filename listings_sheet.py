#!/usr/bin/env python3
"""Full catalog grouped BY LISTING (grouping A). Each listing = one layout that
offers 3 colourways as a personalization choice. For every listing we render its
3 colourways as styled mockups (px_8534228), label each with its colourway name,
and write the personalization fields the buyer fills. 4 sheets, one per
personalization type."""
import json
from pathlib import Path
from PIL import Image, ImageDraw
import render
from mockup_render import render_mockup

ROOT = Path(__file__).resolve().parent
OUT = Path("/tmp/claude-1000/-home-alpha-products-barakah-pipeline/"
           "21f40b72-608a-41f8-b087-efce93a039b1/scratchpad/catalog")
OUT.mkdir(parents=True, exist_ok=True)
DB = json.loads((ROOT / "data/names_db.json").read_text())
FRAME = ROOT / "mockups" / "px_8534228"

PERS = {
    "name": "Personalization — buyer fills:\n• Name (Latin spelling)\n• Arabic spelling to place\n• Colourway",
    "meaning": "Personalization — buyer fills:\n• Name (Latin spelling)\n• Arabic spelling to place\n• Colourway\n(meaning written by shop)",
    "dob": "Personalization — buyer fills:\n• Name (Latin spelling)\n• Date / “Est. 2024”\n• Arabic spelling to place\n• Colourway",
    "verse": "Personalization — buyer fills:\n• Name (Latin spelling)\n• Arabic spelling to place\n• Colourway\n(dua included, verified)",
}

# (label, pers_key, sample-name, [(colourway_name, template_stem), ...])
CATS = {
    "NAME ONLY": [
        ("name_hero", "name", "yusuf", [("charcoal", "nw_name_hero_charcoal"), ("sage", "nw_name_hero_sage"), ("terracotta", "nw_name_hero_terracotta")]),
        ("calligraphic", "name", "aisha", [("ink", "nw_calligraphic_ink"), ("rouge", "nw_calligraphic_rouge"), ("olive", "nw_calligraphic_olive")]),
        ("serif_minimal", "name", "maryam", [("cream", "nw_serif_minimal_cream"), ("sage", "nw_serif_minimal_sage"), ("clay", "nw_serif_minimal_clay")]),
        ("min_diamond", "name", "noor", [("cream", "nm_min_diamond_cream"), ("sage", "nm_min_diamond_sage"), ("blush", "nm_min_diamond_blush")]),
        ("nameonly_field", "name", "layla", [("sage", "nv_nameonly_field_sage"), ("blush", "nv_nameonly_field_blush"), ("sky", "nv_nameonly_field_sky")]),
        ("nameonly_botanical", "name", "noor", [("terracotta", "nv_nameonly_botanical_terracotta"), ("sage", "nv_nameonly_botanical_sage"), ("navy", "nv_nameonly_botanical_navy")]),
        ("nameonly_poster", "name", "yusuf", [("cream", "nv_nameonly_poster_cream"), ("sage", "nv_nameonly_poster_sage"), ("charcoal", "nv_nameonly_poster_charcoal")]),
    ],
    "NAME + MEANING": [
        ("botanical_block", "meaning", "maryam", [("terracotta", "nm_botanical_block_terracotta"), ("sage", "nm_botanical_block_sage"), ("ochre", "nm_botanical_block_ochre")]),
        ("block_ink", "meaning", "musa", [("charcoal", "nm_block_ink_charcoal"), ("emerald", "nm_block_ink_emerald"), ("navy", "nm_block_ink_navy")]),
        ("block_reverse", "meaning", "hamza", [("navy", "nm_block_reverse_navy"), ("emerald", "nm_block_reverse_emerald"), ("charcoal", "nm_block_reverse_charcoal")]),
        ("horizon", "meaning", "zayd", [("sage", "nm_horizon_sage"), ("clay", "nm_horizon_clay"), ("dusty", "nm_horizon_dusty")]),
        ("band", "meaning", "omar", [("terracotta", "nm_band_terracotta"), ("sage", "nm_band_sage"), ("ochre", "nm_band_ochre")]),
        ("aura", "meaning", "layla", [("blush", "nm_aura_blush"), ("sage", "nm_aura_sage"), ("lilac", "nm_aura_lilac")]),
        ("framed_label", "meaning", "ali", [("gold", "nm_framed_label_gold"), ("sage", "nm_framed_label_sage"), ("charcoal", "nm_framed_label_charcoal")]),
        ("poster_serif", "meaning", "bilal", [("cream", "nm_poster_serif_cream"), ("clay", "nm_poster_serif_clay"), ("ochre", "nm_poster_serif_ochre")]),
        ("colorfield", "meaning", "yasmin", [("sage", "nm_colorfield_sage"), ("blush", "nm_colorfield_blush"), ("dusty", "nm_colorfield_dusty")]),
        ("monogram", "meaning", "khadija", [("terracotta", "nw_monogram_terracotta"), ("sage", "nw_monogram_sage"), ("charcoal", "nw_monogram_charcoal")]),
        ("arc_block", "meaning", "aisha", [("terracotta", "nw_arc_block_terracotta"), ("emerald", "nw_arc_block_emerald"), ("ochre", "nw_arc_block_ochre")]),
        ("fullbleed", "meaning", "musa", [("terracotta", "nw_fullbleed_terracotta"), ("emerald", "nw_fullbleed_emerald"), ("navy", "nw_fullbleed_navy")]),
        ("amara", "meaning", "maryam", [("olive", "nw_amara_olive"), ("sage", "nw_amara_sage"), ("blush", "nw_amara_blush")]),
    ],
    "NAME + DOB": [
        ("botanical_sprig", "dob", "ibrahim", [("sage", "nm_botanical_sprig_sage"), ("clay", "nm_botanical_sprig_clay"), ("blush", "nm_botanical_sprig_blush")]),
        ("stacked", "dob", "yusuf", [("cream", "nm_stacked_cream"), ("terracotta", "nm_stacked_terracotta"), ("navy", "nm_stacked_navy")]),
        ("celestial", "dob", "maryam", [("cream", "nw_celestial_cream"), ("navy", "nw_celestial_navy"), ("sage", "nw_celestial_sage")]),
    ],
    "NAME + VERSE": [
        ("verse_apart", "verse", "ibrahim", [("cream", "nv_verseapart_cream"), ("sage", "nv_verseapart_sage"), ("navy", "nv_verseapart_navy")]),
        ("verse_set (2-panel)", "verse", "ibrahim", [("cream · name", "nw_verseset_cream_A"), ("cream · dua", "nw_verseset_cream_B"), ("navy · name", "nw_verseset_navy_A")]),
    ],
}


def row_for(key):
    d = DB[key]
    return {"name_latin": key.title(), "name_arabic": d.get("name_arabic", ""),
            "meaning": d.get("meaning", ""), "date": "15 · 05 · 2024"}


def mockup_for(stem, key):
    """Render the design's print then warp into the catalog frame; cached."""
    jpg = OUT / f"mk_{stem}.jpg"
    if jpg.exists():
        return jpg
    r = render.render(row_for(key), stem, out_dir=OUT / "_prints", canvas=(1000, 1414), tag="p")
    render_mockup(r["png"], FRAME, jpg)
    return jpg


def build():
    lab = render.load_font({"file": "Cinzel[wght].ttf", "weight": 600}, 30)
    cw_font = render.load_font({"file": "Cinzel[wght].ttf", "weight": 500}, 22)
    body = render.load_font({"file": "EBGaramond[wght].ttf", "weight": 450}, 23)
    hdr = render.load_font({"file": "Cinzel[wght].ttf", "weight": 600}, 40)

    TW, TH = 300, 375
    GUT = 430
    pad, gap = 30, 18
    rowh = TH + 34 + gap

    for cat, listings in CATS.items():
        W = GUT + 3 * (TW + gap) + pad * 2
        H = pad * 2 + 80 + len(listings) * rowh
        sheet = Image.new("RGB", (W, H), (250, 248, 244))
        d = ImageDraw.Draw(sheet)
        d.text((pad, pad), cat, fill=(48, 42, 35), font=hdr)
        y = pad + 80
        for label, pkey, key, cways in listings:
            d.text((pad, y + 4), label, fill=(42, 37, 31), font=lab)
            d.multiline_text((pad, y + 46), PERS[pkey], fill=(120, 105, 85), font=body, spacing=7)
            for i, (cwname, stem) in enumerate(cways):
                jpg = mockup_for(stem, key)
                im = Image.open(jpg).convert("RGB"); im.thumbnail((TW, TH))
                x = pad + GUT + i * (TW + gap)
                sheet.paste(im, (x, y))
                d.text((x + im.width // 2, y + TH + 6), cwname, fill=(70, 62, 52), font=cw_font, anchor="ma")
            print("listing:", label, flush=True)
            y += rowh
        p = OUT / f"LISTINGS_{cat.replace(' ', '_').replace('+', 'and')}.jpg"
        sheet.save(p, quality=90)
        print("SHEET", p, flush=True)


if __name__ == "__main__":
    build()
