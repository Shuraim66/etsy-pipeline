#!/usr/bin/env python3
"""
fetch_pd_art.py - public-domain fine-art print pipeline.

Pulls open-access (CC0 / public-domain) paintings from museum APIs:
  - The Met (metmuseum.org, isPublicDomain=true, full-res primaryImage)
  - Art Institute of Chicago (api.artic.edu, is_public_domain=true, IIIF)

For each curated niche it downloads candidates, keeps only images big
enough for quality printing, crops to the A3 ratio (portrait), applies a
gentle print grade (contrast + saturation), and writes:

  output/staging_pd_art/<slug>/<slug>_print.png  (3508x4961, A3 @ 300 DPI)
  output/staging_pd_art/<slug>/<slug>_print.pdf
  output/staging_pd_art/<slug>/ATTRIBUTION.txt   (artist, title, date, museum, license)
  output/staging_pd_art/_REVIEW_pd.png           (contact sheet)
  output/staging_pd_art/CATALOG.txt              (one line per piece)

Only museum-flagged public-domain works are accepted; the license line is
recorded per piece. Listings must credit artist + museum and never claim
original authorship.
"""
from __future__ import annotations

import io
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageEnhance
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdfcanvas

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "staging_pd_art"
W0, H0 = 3508, 4961          # A3 @ 300 DPI, portrait
MIN_SRC_W = 1600             # reject smaller sources (would upscale too far)
UA = {"User-Agent": "BarakahDecor-print-pipeline/1.0 (contact: shop owner)"}

# niche -> (query, museum preference, max pieces)
NICHES = [
    ("meadow_impressionist", "wildflowers meadow landscape impressionism", 2),
    ("monet_waterlilies",    "monet water lilies",                          1),
    ("van_gogh",             "van gogh",                                    2),
    ("japanese_woodblock",   "hokusai wave woodblock",                      2),
    ("vintage_botanical",    "botanical flowers still life painting",       2),
    ("moody_floral",         "floral still life dark",                      2),
]


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def get_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:60] or "artwork"


# ------------------------------------------------------------------ sources --
def met_search(query: str, want: int, seen_ids: set) -> list[dict]:
    """The Met: full-res primaryImage, isPublicDomain flag."""
    q = urllib.parse.quote(query)
    try:
        res = get_json(f"https://collectionapi.metmuseum.org/public/collection/v1/"
                       f"search?q={q}&hasImages=true&medium=Paintings")
    except Exception:
        return []
    picks = []
    for oid in (res.get("objectIDs") or [])[:60]:
        if len(picks) >= want:
            break
        key = f"met:{oid}"
        if key in seen_ids:
            continue
        try:
            obj = get_json(f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{oid}")
        except Exception:
            continue
        if not obj.get("isPublicDomain") or not obj.get("primaryImage"):
            continue
        picks.append({
            "source": "The Metropolitan Museum of Art",
            "license": "CC0 / Open Access (Met isPublicDomain=true)",
            "id": key,
            "title": obj.get("title") or "Untitled",
            "artist": obj.get("artistDisplayName") or "Unknown artist",
            "date": obj.get("objectDate") or "",
            "img_url": obj["primaryImage"],
        })
        seen_ids.add(key)
        time.sleep(0.2)      # gentle on the free API
    return picks


def aic_search(query: str, want: int, seen_ids: set) -> list[dict]:
    """Art Institute of Chicago: IIIF, is_public_domain flag, max 1686px wide."""
    q = urllib.parse.quote(query)
    url = (f"https://api.artic.edu/api/v1/artworks/search?q={q}"
           f"&query%5Bterm%5D%5Bis_public_domain%5D=true&limit=25"
           f"&fields=id,title,artist_title,date_display,image_id,is_public_domain")
    try:
        res = get_json(url)
    except Exception:
        return []
    picks = []
    for a in res.get("data", []):
        if len(picks) >= want:
            break
        key = f"aic:{a['id']}"
        if key in seen_ids or not a.get("image_id") or not a.get("is_public_domain"):
            continue
        picks.append({
            "source": "Art Institute of Chicago",
            "license": "CC0 / Public Domain (AIC is_public_domain=true)",
            "id": key,
            "title": a.get("title") or "Untitled",
            "artist": a.get("artist_title") or "Unknown artist",
            "date": a.get("date_display") or "",
            "img_url": f"https://www.artic.edu/iiif/2/{a['image_id']}/full/1686,/0/default.jpg",
        })
        seen_ids.add(key)
    return picks


# ------------------------------------------------------------------- output --
def print_grade(img: Image.Image) -> Image.Image:
    """Gentle grade for print: slight contrast + saturation lift."""
    img = ImageEnhance.Contrast(img).enhance(1.05)
    img = ImageEnhance.Color(img).enhance(1.06)
    return img


def to_a3_portrait(img: Image.Image) -> Image.Image:
    """Trim scan edges, center-crop to A3 portrait ratio, resize to 3508x4961."""
    # 2% inset on all sides removes black scan borders / frame slivers
    w, h = img.size
    tx, ty = int(w * 0.02), int(h * 0.02)
    img = img.crop((tx, ty, w - tx, h - ty))

    target = W0 / H0
    w, h = img.size
    if w / h > target:                       # too wide -> crop sides
        nw = int(h * target)
        x0 = (w - nw) // 2
        img = img.crop((x0, 0, x0 + nw, h))
    else:                                    # too tall -> crop top/bottom evenly
        nh = int(w / target)
        y0 = (h - nh) // 2
        img = img.crop((0, y0, w, y0 + nh))
    return img.resize((W0, H0), Image.LANCZOS)


def export(meta: dict, img: Image.Image) -> Path:
    slug = slugify(f"{meta['artist'].split(' ')[-1]}_{meta['title']}")
    folder = OUT / slug
    folder.mkdir(parents=True, exist_ok=True)

    art = to_a3_portrait(print_grade(img.convert("RGB")))
    png = folder / f"{slug}_print.png"
    art.save(png, "PNG")

    page = (W0 / 300.0 * 72.0, H0 / 300.0 * 72.0)
    pdf = folder / f"{slug}_print.pdf"
    c = pdfcanvas.Canvas(str(pdf), pagesize=page)
    c.drawImage(ImageReader(art), 0, 0, width=page[0], height=page[1])
    c.showPage()
    c.save()

    (folder / "ATTRIBUTION.txt").write_text(
        f"Title:   {meta['title']}\n"
        f"Artist:  {meta['artist']}\n"
        f"Date:    {meta['date']}\n"
        f"Museum:  {meta['source']}\n"
        f"License: {meta['license']}\n"
        f"SourceID:{meta['id']}\n"
        f"Note:    Public-domain artwork. List as a vintage/fine-art reprint\n"
        f"         credited to the artist; do not claim original authorship.\n",
        encoding="utf-8")
    return png


def contact_sheet(paths: list[Path]) -> Path:
    thumbs = []
    for p in paths:
        im = Image.open(p)
        th = 820
        thumbs.append(im.resize((int(im.width * th / im.height), th), Image.LANCZOS))
    if not thumbs:
        raise SystemExit("no pieces exported")
    cols = 4
    tw = max(t.width for t in thumbs)
    pad = 36
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (tw + pad) + pad, rows * (820 + pad) + pad), (245, 243, 238))
    for i, t in enumerate(thumbs):
        r, c = divmod(i, cols)
        sheet.paste(t, (pad + c * (tw + pad) + (tw - t.width) // 2, pad + r * (820 + pad)))
    out = OUT / "_REVIEW_pd.png"
    sheet.save(out, "PNG")
    return out


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    seen: set = set()
    catalog, made = [], []

    for niche, query, want in NICHES:
        print(f"[{niche}] searching: {query}")
        picks = met_search(query, want, seen) + aic_search(query, max(0, want - 1), seen)
        for meta in picks:
            try:
                raw = get_bytes(meta["img_url"])
                img = Image.open(io.BytesIO(raw))
                img.load()
            except Exception as e:
                print(f"  skip (download failed): {meta['title'][:40]} - {e}")
                continue
            if img.width < MIN_SRC_W:
                print(f"  skip (too small {img.width}px): {meta['title'][:40]}")
                continue
            png = export(meta, img)
            made.append(png)
            catalog.append(f"{niche:22s} {meta['artist'][:28]:28s} "
                           f"{meta['title'][:44]:44s} {img.width}x{img.height}  {meta['source']}")
            print(f"  ok: {meta['artist'][:30]} - {meta['title'][:50]} ({img.width}px)")
            time.sleep(0.3)

    (OUT / "CATALOG.txt").write_text(
        "Public-domain fine-art prints (CC0/open access). A3 @ 300 DPI.\n"
        "Each folder has ATTRIBUTION.txt - credit artist + museum in listings.\n\n"
        + "\n".join(catalog) + "\n", encoding="utf-8")
    print(f"\n{len(made)} pieces exported")
    print(f"review sheet: {contact_sheet(made)}")
