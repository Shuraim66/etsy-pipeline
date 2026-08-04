#!/usr/bin/env python3
"""
create_review_drafts.py - create a few DRAFT Etsy listings for the new name-print
designs so the operator can review them before rolling out all 25.

DRAFTS ONLY (state defaults to draft) — never publishes. Per listing:
  render the 5-ratio deliverable pack (sample name) -> create draft ->
  set a short (<=120 char) personalization prompt -> upload files -> upload photos.

Usage: python create_review_drafts.py name_hero amara celestial
"""
from __future__ import annotations
import sys, json, time
from pathlib import Path
import requests
import etsy_api, render, listings

API = "https://openapi.etsy.com/v3/application"
# text-box instruction per personalization type (colourway is a separate dropdown)
TEXT_INSTR = {
    "name": "Name in English. Paste the Arabic spelling if you have it, or we will send the Arabic for you to approve first.",
    "meaning": "Name in English. Paste the Arabic spelling if you have it, or we will send the Arabic for you to approve first.",
    "dob": "Name in English + date. Paste the Arabic spelling, or we will send the Arabic for you to approve first.",
    "verse": "Name in English. Paste the Arabic spelling if you have it, or we will send the Arabic for you to approve first.",
}


def set_options(client, lid, L):
    """Two custom options: a text box (name/Arabic/date) + a Colourway DROPDOWN.
    (Etsy variations are unavailable for digital items; dropdown options must be
    {'label': ...} objects, and only text_input questions may carry instructions.)"""
    opts = [{"label": cw.title()} for cw, _ in L["colourways"]]
    payload = {"personalization_questions": [
        {"question_text": "Your details", "instructions": TEXT_INSTR[L["pers"]][:120],
         "question_type": "text_input", "required": True, "max_allowed_characters": 256},
        {"question_text": "Colourway", "question_type": "dropdown", "required": True, "options": opts},
    ]}
    r = requests.post(f"{API}/shops/{client.shop_id}/listings/{lid}/personalization",
                      headers={**client._headers(), "Content-Type": "application/json"},
                      data=json.dumps(payload), timeout=30)
    if r.status_code not in (200, 201):
        raise etsy_api.EtsyError(f"set_options -> {r.status_code}: {r.text[:200]}")
    return r.json()

ROOT = Path(__file__).resolve().parent
DB = json.loads((ROOT / "data/names_db.json").read_text())
COPY = json.loads((ROOT / "listings_out/_copy.json").read_text())
DEFAULTS = etsy_api.load_secrets().get("listing", {})

# print ratios (portrait, ~300 DPI, files stay well under Etsy's 20 MB limit)
RATIOS = {"iso_A": (2480, 3508), "ratio_2x3": (2400, 3600), "ratio_3x4": (2700, 3600),
          "ratio_4x5": (2880, 3600), "ratio_5x7": (2571, 3600)}


def short_pers(L):
    cw = " / ".join(c for c, _ in L["colourways"])
    if L["pers"] == "dob":
        s = f"Enter: Name (English) + date + exact Arabic spelling to place + colourway: {cw}"
    else:
        s = f"Enter: Name (English) + exact Arabic spelling to place + colourway: {cw}"
    return s[:120]


def render_files(L):
    stem = L["colourways"][0][1]                       # lead colourway
    if L["is_set"]:
        stem = stem + "_A"
    row = listings.sample_row(L["sample"], DB, L["pers"])
    files = []
    for tag, (w, h) in RATIOS.items():
        r = render.render(row, stem, out_dir=ROOT / "listings_out" / L["key"] / "_files",
                          canvas=(w, h), tag=tag)
        files.append(r["pdf"])
    return files


def photos(key):
    ims = sorted((ROOT / "listings_out" / key).glob(f"{key}_0*.jpg"))
    return [p for p in ims if not p.stem.endswith("_sq")][:10]


def create_one(client, key):
    L = next(x for x in listings.all_listings() if x["key"] == key)
    c = COPY[key]
    meta = {"title": c["title"], "description": c["description"], "price": c["price"],
            "tags": c["tags"], "currency_code": "USD"}
    files = render_files(L)
    imgs = photos(key)
    print(f"\n=== {key} ===\n  title: {meta['title']}\n  price: ${meta['price']} | "
          f"tags {len(meta['tags'])} | files {len(files)} | photos {len(imgs)}", flush=True)
    res = client.create_draft_listing(meta, DEFAULTS)
    lid = res.get("listing_id") or (res.get("results") or [{}])[0].get("listing_id")
    set_options(client, lid, L)                         # text box + Colourway dropdown
    for i, f in enumerate(files, 1):
        client.upload_listing_file(lid, f, rank=i); time.sleep(0.3)
    for i, im in enumerate(imgs, 1):
        client.upload_listing_image(lid, im, rank=i); time.sleep(0.3)
    print(f"  + DRAFT listing_id {lid}", flush=True)
    return lid


def main(argv):
    keys = argv or ["name_hero", "amara", "celestial"]
    client = etsy_api.EtsyClient()
    made = []
    for k in keys:
        try:
            made.append((k, create_one(client, k)))
        except Exception as e:
            import traceback; traceback.print_exc()
            print(f"  FAIL {k}: {e}", flush=True)
    print("\n=== DRAFTS CREATED ===")
    for k, lid in made:
        print(f"  {k:12s} listing {lid}  ->  https://www.etsy.com/your/shops/me/tools/listings")


if __name__ == "__main__":
    main(sys.argv[1:])
