# Barakah — Islamic Name-Print Generation Pipeline

Turns a row of verified data (a name + meaning + dua + style) into print-ready,
personalized Islamic name-print files: a high-res PNG, a print-ready A3 PDF, a
framed wall mockup, and an optional watermarked proof. Built to compete on
**volume × multiple styles**.

## Core rule (do not violate)

**The pipeline PLACES Arabic; it never invents, transliterates, or "corrects"
it.** Every Arabic string (`name_arabic`, `dua_arabic`) must be operator-verified
Unicode supplied in the input row. A wrong letter is fatal for this product, so
unverified rows are never rendered. All Arabic handling lives in one auditable
module: [`arabic_text.py`](arabic_text.py).

## What it produces (per row × style)

```
output/{name}_{style}/
  {name}_{style}_print.png    # 3508×4961 (A3 @ 300 DPI), long edge ≥ 3000
  {name}_{style}_print.pdf    # A3 portrait page (raster-in-PDF, print-perfect)
  {name}_{style}_mockup.png   # 2000×2000 framed-wall scene
  {name}_{style}_proof.png    # optional (--proof): low-res, watermarked
```

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python setup_fonts.py        # downloads Amiri + EB Garamond + Cinzel (OFL)
```

**Arabic correctness depends on `libraqm`** (HarfBuzz). Pillow uses it
automatically when present, giving correct letter shaping *and* harakat (vowel
marks). If it is missing, the pipeline falls back to `arabic-reshaper` +
`python-bidi` and prints a loud warning that harakat may be wrong. On Debian/
Ubuntu: `sudo apt install libraqm0`.

## Usage

```bash
# render each row in its own `style` column, + mockups
.venv/bin/python generate.py --input input/names.csv

# force specific styles, write proofs + the multi-size download pack
.venv/bin/python generate.py --styles hero,mihrab --proof --sizes

# volume: an order CSV can list just name_latin,style — verified Arabic + meaning
# are filled from data/names_db.json (see Names database below)

# other flags: --output DIR  --force  --no-mockup  --sizes (ratio pack)  --pins (Pinterest)
```

### Input CSV columns

| column            | notes |
|-------------------|-------|
| `name_latin`      | e.g. `Ibrahim` |
| `name_arabic`     | **verified Unicode**, operator-supplied (e.g. `إبراهيم`); may be blank if the name is in the verified names DB |
| `date`            | optional; blank → block omits and layout reflows |
| `meaning`         | paragraph text — **from the CSV only**, never auto-generated |
| `dua_arabic`      | **verified Unicode**; blank → dua line omits and reflows |
| `dua_translation` | English translation of the dua |
| `style`           | any template in `templates/` — lead line: `hero` \| `mihrab` \| `split_panel` (see Styles) |
| `ornament`        | informational; the top ornament is chosen per style (see below). |
| `verified`        | `true` renders unattended; otherwise the operator is asked to confirm the Arabic at the console (non-interactive stdin → row is skipped) |

If `dua_arabic` is blank, the **default dua** in `config.json` is used (operator-verified); a row may override it with its own verified `dua_arabic`.

**Names database.** `data/names_db.json` maps `name_latin → verified name_arabic + meaning`. An order CSV can then list just `name_latin,style`; the pipeline fills the verified Arabic + meaning (a row's own values always win). Add a name once, reuse forever — entries are operator-verified, and blank/unverified ones never render.

**Sizes.** `--sizes` (or `python sizes.py <style>`) exports each design at the standard print ratios — ISO-A, 2:3, 3:4, 4:5, 5:7 — the fraction layout reflows to each, plus a `SIZES.txt` of which physical sizes each ratio covers. A ready digital-download pack.

**Pinterest pins.** `--pins` (or `python pins.py <style>`) writes a `pins/` subfolder per design with four **1000×1500 (2:3)** pins — framed-room mockup, name close-up, headline text-overlay (in the design's own fonts/palette), and a style-comparison — plus `pins.csv` of keyword-rich `pin_title`, `pin_description`, `suggested_board`, and a blank `listing_url` to fill.

## Etsy listings (drafts → your existing shop)

Push rendered designs into **your existing Etsy shop** as **draft** digital-download
listings (you review + publish — it never publishes for you).

**Safety:** drafts only; `etsy_publish.py` is **dry-run by default** (preview, no API
calls) and needs `--live` to create drafts. Credentials (`etsy_secrets.json`,
`etsy_token.json`) are gitignored.

One-time setup:
1. Register an app at etsy.com/developers → copy `etsy_secrets.example.json` to
   `etsy_secrets.json`; fill `client_id` / `client_secret` / `shop_id` + listing
   defaults (set a real `taxonomy_id` and `price`).
2. `python etsy_api.py ping`     — validate the API key
3. `python etsy_auth.py`         — one-time OAuth (PKCE) → `etsy_token.json`
4. `python etsy_api.py whoami`   — confirm it's your existing shop

Create drafts:
```bash
python etsy_publish.py output/catalog                       # dry-run preview (all)
python etsy_publish.py output/catalog/ibrahim_hero --live   # create one draft
```
Each draft attaches the **size-pack PDFs** as digital files and the **mockup + pins**
as photos; title/description/tags come from `etsy_meta.py`. New API apps start in
Etsy's personal-access tier, which already allows managing your own shop's listings.

## Pinterest pins (post to boards)

Post the generated pins (from `--pins`) to Pinterest, routed to themed boards.

**Safety:** dry-run by default; `--live` to post. Posts to a board with the
`privacy` from secrets (default **SECRET** — Pinterest has no "draft", so a secret
board is the safe equivalent). New apps are in **Trial** access, where pins are
**sandbox-only / private to you** anyway (use the sandbox `api_base` while in Trial;
switch to production + a public board after Standard access). Credentials gitignored.

Setup + use:
1. Register an app at developers.pinterest.com → fill `pinterest_secrets.json`.
2. `python pinterest_auth.py`        — one-time OAuth → `pinterest_token.json`
3. `python pinterest_api.py whoami`  — confirm the account (or `boards` to list)
4. ```bash
   python pinterest_publish.py output/catalog          # dry-run preview
   python pinterest_publish.py output/catalog --live   # post pins
   ```

Each pin uses its `pin_title` / `pin_description` / `suggested_board` from
`pins.csv` and the `listing_url` as its link — so after publishing the Etsy
listing, paste its URL into the `pins.csv` `listing_url` column and the pins drive
traffic straight to it.

## Styles

Each style is a self-contained config in [`templates/`](templates/) — background,
palette, fonts, and layout **coordinates as fractions of the canvas**, so style
and canvas size stay independent. `emerald_gold` is tuned to the reference in
[`reference/`](reference/).

Layout is fully config-driven, so templates differ by **composition**, not just
palette. A template lays content out either as a single centred **flow** or as
positioned **zones** (multiple stacks), and composes from:
- **background**: gradient, colour `panels` (banners), a faded name `watermark`, `vignette`
- **ornament**: `medallion` | `floral` | `geometric` | `deco_fan` | `arch` | `none`
- **frame**: border `none`/`single`/`double`/`rules_tb`/`stepped`, corners `bracket`/`deco`/`floral`/`none`
- **dividers**: `rule` | `bar` | `double` | `diamond` | `dot` | `deco` | `chevron` | `leaf` | `none`
- **script**: `naskh` | `kufic` | `ruqaa` — swaps the Arabic calligraphy font (Amiri / Reem Kufi / Aref Ruqaa)

**Lead production line (emerald + gold):**
- `hero` — oversized Arabic name as the artwork
- `mihrab` — name inside a large architectural arch
- `split_panel` — top colour banner, content on light below

Other looks in the library: `emerald_gold` (reference-matched), `ornate_classic`,
`minimalist`, `geo_modern`, `botanical`, `art_deco`, `editorial`, `encircled`,
`backdrop`. A **shrink-to-fit** safety net keeps a long meaning from overflowing.

**Palettes & recolour SKUs.** `palettes.json` defines role-based palettes
(`emerald_gold`, `black_gold`, `navy_gold`, `ivory_gold`). A layout sets
`"palette": "..."`, and a variant SKU is a 3-line file that inherits a layout and
swaps the palette — e.g. `{ "name": "hero_black", "extends": "hero", "palette":
"black_gold" }`. Layout and palette are independent axes, so the lead line ships
as a **3×4 grid = 12 SKUs** (hero / mihrab / split_panel × the four palettes).
Run `python contact_sheet.py` to regenerate the comparison grid.

## Project layout

```
generate.py        CLI: read CSV → DB fill → verify gate → render + mockup/proof/sizes
render.py          rendering engine: render(row, style, canvas, tag) → PNG + PDF
arabic_text.py     the ONLY Arabic module (raqm-preferred shaping; reshaper fallback)
ornaments.py       procedural medallion / arch / floral / wreath / borders (code-drawn)
mockup.py          procedural framed-wall compositor
proof.py           watermarked low-res proof
sizes.py           multi-ratio print-pack exporter
pins.py            Pinterest pin generator (4 pins + pins.csv per design)
etsy_auth.py       one-time Etsy OAuth (PKCE) -> etsy_token.json
etsy_api.py        Etsy Open API v3 client (ping / whoami / create draft + uploads)
etsy_meta.py       listing title / description / tags
etsy_publish.py    create DRAFT Etsy listings from folders (dry-run default)
pinterest_auth.py  one-time Pinterest OAuth -> pinterest_token.json
pinterest_api.py   Pinterest API v5 client (whoami / boards / create pin)
pinterest_publish.py  post pins from pins.csv (dry-run default)
setup_fonts.py     one-time OFL font fetcher
templates/         layout configs (JSON; `extends` for variants)
palettes.json      role-based colour palettes
config.json        pipeline defaults (default dua, bismillah)
data/names_db.json operator-verified name → arabic + meaning
assets/fonts/      downloaded fonts (gitignored)
assets/scenes/     room photos for photoreal mockups (framed print composited onto the wall)
input/             sample CSVs
output/            generated folders (gitignored)
```

## Build status

Zone-based layout engine (flow/zones, panels, watermark, vignette, wreath, big
arch) · verification gate · framed mockups · print-ready PDFs · watermarked proofs ·
config default dua/bismillah with correct harakat. **~25-design catalog** across
layouts (hero, mihrab, split_panel, duo, aquarelle, birth, verse, vertical, 3-piece
set) × **role palettes** (emerald/black/navy/ivory/oatmeal/terracotta/sage) ×
**calligraphy scripts** (naskh/kufic/ruqaa). **Multi-size** export at 5 print
ratios. **Names DB** so order CSVs need only name + style. **Pinterest pins** —
4 vertical pins + a keyword-rich pins.csv per design.

Operator actions: keep adding verified entries to `data/names_db.json`; paste the
verified **Bismillah** Arabic into `config.json` to complete `set_bismillah`.
