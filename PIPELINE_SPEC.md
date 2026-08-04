# Islamic Name Print — Design Generation Pipeline (Spec for Claude Code)

## Goal
A Python pipeline that turns a row of data (a verified name + meaning + dua + style)
into print-ready, personalized Islamic name-print files matching a template design.
Human stays in the loop ONLY to verify Arabic correctness. Everything else automated.

## Why this exists
Selling personalized Islamic name prints on Etsy. Competing on VOLUME + multiple
STYLES that manual (Canva) sellers can't match. The pipeline is the moat.

## Core principle (do not violate)
The pipeline PLACES Arabic text; it must NEVER invent/transliterate Arabic itself.
Arabic name strings are supplied pre-verified by a human (the operator reads Arabic).
AI/auto-transliteration of names is forbidden — a wrong letter is fatal for this product.

---

## INPUT
A CSV (or JSON) row with these fields:
- name_latin        e.g. "Ibrahim"
- name_arabic       e.g. "إبراهيم"   (pre-verified unicode, supplied by operator)
- date              e.g. "15 / 05 / 2020"  (optional, may be blank)
- meaning           paragraph text (operator-supplied or from a curated names DB)
- dua_arabic        verified dua unicode (can default to one standard protection dua)
- dua_translation   English translation
- style             one of: emerald_gold | watercolor | black_geo
- ornament          one of: medallion | arch | floral  (optional, default per style)

## OUTPUT (per row)
A folder named after the name+style containing:
- {name}_{style}_print.pdf      (vector-quality, print-ready)
- {name}_{style}_print.png      (high-res, >= 3000px long edge, for preview/upload)
- {name}_{style}_mockup.png     (design composited into a framed-wall scene, 2000x2000)
Optionally a proof.png (low-res, watermarked) for sending to buyers before final.

---

## RENDERING REQUIREMENTS
- Arabic shaping: use `arabic-reshaper` + `python-bidi`, render with the **Amiri** font
  (Amiri-Regular.ttf; download from github.com/aliftype/amiri main/fonts/). This
  correctly shapes connected RTL Arabic. (Proven to work.)
- English: an elegant serif (e.g. EB Garamond / Cinzel from Google Fonts OFL).
- Page: A-series ratio (1:1.414), portrait. Build canvas at 300 DPI for A3
  (3508 x 4961 px) so it scales down to A4/A5 cleanly. Export PDF (vector text where
  possible) + PNG.
- Layout (top→bottom): top ornament → large Arabic name → Latin name → date →
  divider → meaning paragraph → divider → dua (Arabic) → dua translation → border.
- Colors per style:
  - emerald_gold:  bg #103826 (gradient to #0B2A1C), text/gold #F8B83A, cream #E8E0CE
  - watercolor:    soft cream bg, dusty rose/sage accents, charcoal text
  - black_geo:     white bg, bold black elements, thin geometric border
- All design (ornaments, borders) must be either code-drawn or from
  commercial-use/owned assets — NO copyrighted calligraphy art.

## TECH
- Python 3, libraries: Pillow, arabic-reshaper, python-bidi, reportlab (or svglib) for PDF,
  pandas (CSV). Keep deps minimal.
- Structure:
  /templates  -> style definitions (colors, fonts, layout coords) as config (JSON/py)
  /assets     -> fonts, ornament SVGs/PNGs (transparent, recolorable)
  /input      -> names.csv
  /output     -> generated folders
  generate.py -> main: reads CSV, loops rows, renders, writes output
  render.py   -> the rendering engine (one function: render(row, style) -> files)
  mockup.py   -> composites a finished design into a frame scene
- CLI: `python generate.py --input input/names.csv --styles emerald_gold,watercolor`
- Batch-safe: skip rows already generated; log failures; never crash whole batch on one bad row.

## HUMAN-IN-THE-LOOP (must build in)
- Before rendering, print each row's name_latin + name_arabic to console and require
  the operator to confirm (or a `verified=true` column in the CSV). Do not render
  unverified Arabic.

## BUILD ORDER (do this incrementally, test each step)
1. render.py for ONE style (emerald_gold), ONE row, hardcoded -> matches the reference design.
2. Externalize style into a config; add watercolor + black_geo.
3. CSV input + batch loop + output folders.
4. mockup.py compositing.
5. Ornament variants (medallion/arch/floral).
6. PDF export (vector). 
7. Proof generator (watermarked low-res).

## DEFINITION OF DONE
Run `python generate.py` on a 5-row CSV (5 names) and get 5 folders, each with a
correct, print-ready PDF+PNG+mockup in the chosen style(s), with correct Arabic,
in under a minute, with zero manual design work after Arabic verification.