#!/usr/bin/env python3
"""
listing_copy.py - generate Etsy copy (title, tags, description, personalization)
for each productised listing. SEO follows the shop's search-territory approach:
core + style + type + a rotating occasion angle, kept short and low-overlap.
"""
import hashlib
import listings

PRICE = "6.99"
SECTION = "Name Prints"

STYLE_DESC = {
    "name_hero": "Bold Arabic", "calligraphic": "Calligraphy", "serif_minimal": "Minimalist Serif",
    "min_diamond": "Minimalist", "nameonly_field": "Colour Block", "nameonly_botanical": "Boho Botanical",
    "nameonly_poster": "Modern Poster", "botanical_block": "Boho Botanical", "block_ink": "Colour Block",
    "block_reverse": "Bold Colour", "horizon": "Minimalist", "band": "Colour Band", "aura": "Aura Gradient",
    "framed_label": "Elegant Label", "poster_serif": "Serif Poster", "colorfield": "Colour Field",
    "monogram": "Monogram", "arc_block": "Bauhaus Arc", "fullbleed": "Bold Colour",
    "amara": "Boho Botanical", "botanical_sprig": "Boho Botanical", "stacked": "Modern",
    "celestial": "Celestial Moon", "verse_apart": "Name & Dua", "verse_set": "2-Piece Set",
}

# occasion angles rotated per listing so titles/tags don't all read the same
ANGLES = ["New Baby Gift", "Nursery Decor", "Eid Gift", "New Home Gift", "Ramadan Decor",
          "Wedding Gift", "Aqiqah Gift", "Birthday Gift"]

TYPE_LINE = {
    "name": "Arabic Name Wall Art",
    "meaning": "Arabic Name & Meaning Print",
    "dob": "Name, Date & Meaning Print",
    "verse": "Arabic Name & Dua Print",
}

# tag pools by role — pick a rotating slice per listing (Etsy: 13 tags, <=20 chars each)
CORE = ["islamic name print", "arabic name print", "personalised print", "muslim gift",
        "islamic wall art", "custom name print"]
AUDIENCE = ["new baby gift", "muslim baby gift", "nursery wall art", "eid gift",
            "new home gift", "ramadan decor", "islamic gift", "aqiqah gift"]
TYPE_TAGS = {
    "name": ["arabic calligraphy", "name sign"],
    "meaning": ["name meaning print", "arabic name gift"],
    "dob": ["birth print", "new baby print"],
    "verse": ["dua wall art", "ayah print"],
}


def _h(s):
    return int(hashlib.md5(s.encode()).hexdigest(), 16)


def angle_for(key):
    return ANGLES[_h(key) % len(ANGLES)]


def title(L):
    style = STYLE_DESC.get(L["key"], "Minimalist")
    t = (f"Personalised {TYPE_LINE[L['pers']]} | Islamic Name Print | "
         f"{style} | {angle_for(L['key'])} | Digital Download")
    return t[:140]


def tags(L):
    style = STYLE_DESC.get(L["key"], "minimalist").lower() + " print"
    rot = _h(L["key"])
    core = CORE[:4]
    aud = [AUDIENCE[(rot + i) % len(AUDIENCE)] for i in range(3)]
    typ = TYPE_TAGS[L["pers"]]
    extra = ["boho wall art", "muslim wall art", "arabic print", "personalized gift"]
    ex = [extra[(rot + i) % len(extra)] for i in range(4 - len(typ))]
    out, seen = [], set()
    for t in core + [style] + typ + aud + ex:
        t = t[:20]
        if t not in seen:
            seen.add(t); out.append(t)
    return out[:13]


def personalization(L):
    fields = listings.PERS_FIELDS[L["pers"]]
    cw = " / ".join(c for c, _ in L["colourways"])
    lines = ["Add your details in the Personalisation box:"]
    step = 1
    for f in fields:
        if f == "Colourway":
            lines.append(f"{step}) Colourway: {cw}")
        elif "Arabic" in f:
            lines.append(f"{step}) Name in Arabic — paste the exact spelling you want "
                         "(we place it exactly as sent; we never auto-translate)")
        elif "Date" in f:
            lines.append(f"{step}) Date to show (e.g. “15.05.2024” or “Est. 2024”) — optional")
        else:
            lines.append(f"{step}) Name in English (e.g. {L['sample'].title()})")
        step += 1
    return "\n".join(lines)


def description(L):
    style = STYLE_DESC.get(L["key"], "minimalist")
    meaning_note = ("The meaning shown is written by us for the name you choose. "
                    if L["pers"] == "meaning" else "")
    dua_note = ("A verified Arabic dua is included on the print. "
                if L["pers"] == "verse" else "")
    set_note = ("This is a coordinated 2-piece set (name + dua) designed to hang together. "
                if L["is_set"] else "")
    return (
        f"Personalised Islamic name print — a {style.lower()} design in warm, framable colours.\n"
        f"{set_note}Made to order with the name and spelling you provide.\n\n"
        f"{personalization(L)}\n\n"
        f"{meaning_note}{dua_note}Arabic is placed exactly as you send it — please paste the "
        "spelling you want.\n\n"
        "WHAT YOU GET (made-to-order digital files, delivered after we set your name):\n"
        "• 5 print ratios covering every common frame size — ISO A (A5–A1), 2:3, 3:4, 4:5, 5:7\n"
        "• 300 DPI print-ready PDF + PNG\n\n"
        "This is a DIGITAL download — no physical item is shipped. Colours may vary slightly by screen "
        "and printer. Frame not included. For personal use only.\n\n"
        f"Price ${PRICE}."
    )


def listing_copy(L):
    return {
        "key": L["key"], "price": PRICE, "section": SECTION,
        "personalization_type": L["pers"],
        "colourways": [c for c, _ in L["colourways"]],
        "title": title(L), "tags": tags(L),
        "personalization": personalization(L), "description": description(L),
    }


if __name__ == "__main__":
    import json
    out = {L["key"]: listing_copy(L) for L in listings.all_listings()}
    print(json.dumps(out, ensure_ascii=False, indent=2))
