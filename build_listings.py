#!/usr/bin/env python3
"""
build_listings.py - render the full Etsy photo set for each productised listing.

Per listing (8 images, all 4:5 / 2000x2500):
  01 hero          lead colourway in the oak lean frame (thumbnail)
  02 colourways    all colourways side-by-side, labelled
  03,04 colours    the remaining colourways in the oak frame
  05 glass         lead colourway under glass with a soft glare
  06,07 scenes     lead colourway in two varied styled rooms
  08 sizes         aspect-ratio / print-size card
verse_set is a 2-panel set: pair shots (name + dua) per colourway.

Writes into listings_out/<key>/<key>_NN.jpg. Local only; pushing is separate + gated.
"""
from __future__ import annotations
import sys, json
from pathlib import Path
from PIL import Image, ImageDraw
import render, sizes_card, listings
from mockup_render import render_mockup

ROOT = Path(__file__).resolve().parent
MK = ROOT / "mockups"
OUTROOT = ROOT / "listings_out"
DB = json.loads((ROOT / "data/names_db.json").read_text())

import hashlib
# hero/thumbnail frames: art-prominent (readable at thumbnail size) and framed against
# non-white backgrounds so even dark prints keep a visible frame edge. Rotated per listing
# by a hash of the key so the shop page reads varied — like the single-print rollout.
# EXCLUDED from hero: m1_black_hung (black moulding disappears on white wall behind dark
# prints -> reads as a frameless poster) and matted frames where the art shows too small.
# Match the existing shop: the same 6 proven hero frames the live listings rotate
# (m1_black_hung stays excluded — its black moulding vanishes on white walls behind dark prints).
HERO_POOL = ["px_8534228", "px_12486417", "px_12486418", "m2_gold_lean", "m3_brass_flatlay", "px_8490197"]
# scene frames for the 3 in-listing lifestyle shots (per listing we pick 3 that aren't its hero)
SCENE_POOL = ["px_8251251", "px_8490187", "px_8490197", "m3_brass_flatlay", "px_12486417", "m2_gold_lean"]


def _hash(s):
    return int(hashlib.md5(s.encode()).hexdigest(), 16)


def lead_for(key):
    return HERO_POOL[_hash(key) % len(HERO_POOL)]


def scenes_for(key, hero):
    off = _hash(key + "scn") % len(SCENE_POOL)
    rot = SCENE_POOL[off:] + SCENE_POOL[:off]
    return [f for f in rot if f != hero][:3]
CANVAS = (2000, 2828)
CW, CH = 2000, 2500
CREAM = (244, 241, 235)


def _print(stem, sample, pers):
    row = listings.sample_row(sample, DB, pers)
    r = render.render(row, stem, out_dir=OUTROOT / "_prints", canvas=CANVAS, tag="p")
    return r["png"]


def _mock(print_png, frame, out):
    return render_mockup(print_png, MK / frame, out)["jpg"]


def _copy_mood(out):
    import shutil
    shutil.copy(MOOD, out)
    return out


def _label(canvas, text, y):
    d = ImageDraw.Draw(canvas)
    f = render.load_font({"file": "Cinzel[wght].ttf", "weight": 500}, 46)
    d.text((canvas.width // 2, y), text, fill=(70, 62, 52), font=f, anchor="ma")


def colourway_card(prints, cways, out, lead):
    """All colourways in the listing's lead frame, side by side, vertically centred."""
    canvas = Image.new("RGB", (CW, CH), CREAM)
    d = ImageDraw.Draw(canvas)
    n = len(cways)
    slotw = CW // n
    mocks = []
    for cwname, stem in cways:
        m = Image.open(_mock(prints[stem], lead, OUTROOT / "_tmp" / f"cw_{lead}_{stem}.jpg")).convert("RGB")
        m.thumbnail((slotw - 40, int(CH * 0.66)))
        mocks.append((cwname, m))
    rowh = max(m.height for _, m in mocks)
    top = (CH - rowh) // 2 + 30
    _label(canvas, f"{n} COLOURWAYS — CHOOSE YOURS", top - 130)
    fl = render.load_font({"file": "Cinzel[wght].ttf", "weight": 500}, 42)
    for i, (cwname, m) in enumerate(mocks):
        x = i * slotw + (slotw - m.width) // 2
        canvas.paste(m, (x, top + (rowh - m.height) // 2))
        d.text((i * slotw + slotw // 2, top + rowh + 26), cwname.upper(),
               fill=(90, 80, 68), font=fl, anchor="ma")
    fc = render.load_font({"file": "EBGaramond-Italic[wght].ttf", "weight": 450}, 40)
    d.text((CW // 2, CH - 150), "your name & chosen colour — personalised at checkout",
           fill=(140, 122, 100), font=fc, anchor="ma")
    canvas.save(out, quality=92)
    return out


def sizes_45(out):
    sq = sizes_card.build(out.with_name(out.stem + "_sq.jpg"))
    ci = Image.open(sq).convert("RGB")
    canv = Image.new("RGB", (CW, CH), CREAM)
    canv.paste(ci.resize((CW, CW)), (0, (CH - CW) // 2))
    canv.save(out, quality=94)
    return out


def build_normal(L):
    key, sample, pers, cways = L["key"], L["sample"], L["pers"], L["colourways"]
    folder = OUTROOT / key
    (folder).mkdir(parents=True, exist_ok=True)
    prints = {stem: _print(stem, sample, pers) for _, stem in cways}
    lead_stem = cways[0][1]
    lead = lead_for(key)                                                           # varied hero frame
    imgs = []
    imgs.append(_mock(prints[lead_stem], lead, folder / f"{key}_01.jpg"))          # hero
    imgs.append(colourway_card(prints, cways, folder / f"{key}_02.jpg", lead))     # colourways
    for i, (_, stem) in enumerate(cways[1:], start=3):                             # other colours
        imgs.append(_mock(prints[stem], lead, folder / f"{key}_{i:02d}.jpg"))
    n = len(cways) + 1                                                            # =4 for 3 colourways
    scenes = scenes_for(key, lead)                                                # 3 varied scenes, != hero
    for j, sc in enumerate(scenes):
        imgs.append(_mock(prints[lead_stem], sc, folder / f"{key}_{n+1+j:02d}.jpg"))
    imgs.append(sizes_45(folder / f"{key}_{n+1+len(scenes):02d}.jpg"))            # sizes
    return imgs


def build_set(L):
    """verse_set: coordinated 2-panel pairs (name + dua) per colourway."""
    key, sample = L["key"], L["sample"]
    folder = OUTROOT / key; folder.mkdir(parents=True, exist_ok=True)
    lead = lead_for(key)
    row = listings.sample_row(sample, DB, "verse")
    imgs = []
    idx = 1
    for cwname, base in L["colourways"]:          # base e.g. nw_verseset_cream
        pa = render.render(row, base + "_A", out_dir=OUTROOT / "_prints", canvas=CANVAS, tag="p")["png"]
        pb = render.render(row, base + "_B", out_dir=OUTROOT / "_prints", canvas=CANVAS, tag="p")["png"]
        ma = Image.open(_mock(pa, lead, OUTROOT / "_tmp" / f"{base}_A.jpg")).convert("RGB")
        mb = Image.open(_mock(pb, lead, OUTROOT / "_tmp" / f"{base}_B.jpg")).convert("RGB")
        # diptych on one 4:5 card
        canvas = Image.new("RGB", (CW, CH), CREAM)
        _label(canvas, f"2-PIECE SET · {cwname.upper()}", 110)
        for k, m in enumerate((ma, mb)):
            mm = m.copy(); mm.thumbnail((CW // 2 - 120, CH - 420))
            x = k * (CW // 2) + (CW // 2 - mm.width) // 2
            canvas.paste(mm, (x, 300))
        p = folder / f"{key}_{idx:02d}.jpg"; canvas.save(p, quality=92); imgs.append(p); idx += 1
        # single-panel styled scene of the name panel
        imgs.append(_mock(pa, lead, folder / f"{key}_{idx:02d}.jpg")); idx += 1
    imgs.append(sizes_45(folder / f"{key}_{idx:02d}.jpg"))
    return imgs


def build_one(L):
    (OUTROOT / "_tmp").mkdir(parents=True, exist_ok=True)
    return build_set(L) if L["is_set"] else build_normal(L)


def main(argv):
    only = set(argv)
    items = [l for l in listings.all_listings() if not only or l["key"] in only]
    for n, L in enumerate(items, 1):
        try:
            imgs = build_one(L)
            print(f"[{n}/{len(items)}] {L['key']}: {len(imgs)} images", flush=True)
        except Exception as e:
            import traceback; traceback.print_exc()
            print(f"[{n}/{len(items)}] FAIL {L['key']}: {e}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
