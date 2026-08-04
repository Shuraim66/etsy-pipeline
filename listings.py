#!/usr/bin/env python3
"""
listings.py - single source of truth for the productised name-print listings.
Each listing = one layout (grouping A) offering its colourways as a personalization
choice. Used by the catalog sheet, the photo-set builder and the copy generator.
"""

# personalization types -> the fields a buyer fills
PERS_FIELDS = {
    "name":    ["Name (Latin spelling)", "Arabic spelling to place", "Colourway"],
    "meaning": ["Name (Latin spelling)", "Arabic spelling to place", "Colourway"],
    "dob":     ["Name (Latin spelling)", "Date / “Est. 2024”", "Arabic spelling to place", "Colourway"],
    "verse":   ["Name (Latin spelling)", "Arabic spelling to place", "Colourway"],
}

# (listing_key, personalization, sample_name, [(colourway, template_stem), ...])
LISTINGS = {
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
        ("verse_set", "verse", "ibrahim", [("cream", "nw_verseset_cream"), ("navy", "nw_verseset_navy")]),  # 2-panel set (A/B)
    ],
}


def all_listings():
    """Flatten to a list of dicts."""
    out = []
    for cat, rows in LISTINGS.items():
        for key, pers, sample, cways in rows:
            out.append({"key": key, "category": cat, "pers": pers,
                        "sample": sample, "colourways": cways,
                        "is_set": key == "verse_set"})
    return out


def sample_row(sample_name, db, pers):
    d = db[sample_name]
    row = {"name_latin": sample_name.title(), "name_arabic": d.get("name_arabic", ""),
           "meaning": d.get("meaning", "")}
    if pers == "dob":
        row["date"] = "15 · 05 · 2024"
    return row
