#!/usr/bin/env python3
"""
generate.py - batch driver for the Barakah name-print pipeline.

Reads a CSV of rows and produces, per (row x style), an output folder with a
print PNG + PDF (+ optional mockup and watermarked proof).

HUMAN-IN-THE-LOOP (Arabic verification gate):
  * A truthy `verified` column (true/yes/1) renders the row unattended.
  * Otherwise the operator is shown name_latin + name_arabic and must confirm at
    the console. On a NON-interactive stdin the row is SKIPPED (never render
    unverified Arabic) - the pipeline will not invent or guess Arabic.

Batch-safe:
  * Folders that already exist are skipped (unless --force).
  * Any row/style that errors is logged and skipped; one bad row never crashes
    the whole batch.

CLI:
  python generate.py --input input/names.csv --styles emerald_gold,watercolor
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import traceback
from pathlib import Path

import mockup
import mockup_photo
import pins
import proof
import render
import sizes

ROOT = Path(__file__).resolve().parent
TEMPLATE_DIR = ROOT / "templates"
NAMES_DB = ROOT / "data" / "names_db.json"
TRUTHY = {"true", "yes", "y", "1", "verified", "ok"}


def load_names_db() -> dict:
    return json.loads(NAMES_DB.read_text(encoding="utf-8")) if NAMES_DB.exists() else {}


def fill_from_db(row: dict, db: dict) -> bool:
    """Fill a blank name_arabic (and meaning) from a VERIFIED DB entry, keyed by
    name_latin. Returns True if filled (counts as operator-verified)."""
    if str(row.get("name_arabic", "") or "").strip():
        return False
    entry = db.get(render.slugify(row.get("name_latin", "")))
    if not (entry and entry.get("verified") and str(entry.get("name_arabic", "") or "").strip()):
        return False
    row["name_arabic"] = entry["name_arabic"]
    if not str(row.get("meaning", "") or "").strip() and entry.get("meaning"):
        row["meaning"] = entry["meaning"]
    return True


def available_styles() -> set[str]:
    return {p.stem for p in TEMPLATE_DIR.glob("*.json")}


def is_verified(row: dict) -> bool:
    return str(row.get("verified", "")).strip().lower() in TRUTHY


def confirm_arabic(row: dict) -> bool:
    """Show Latin + Arabic and require operator confirmation. Skip if non-TTY."""
    print(f"    VERIFY ARABIC:  {row.get('name_latin', '?')}    |    {row.get('name_arabic') or '(no arabic supplied)'}")
    if not sys.stdin.isatty():
        print("      -> stdin not interactive and row not marked verified: SKIPPING "
              "(will not render unverified Arabic).")
        return False
    return input("      Confirm the Arabic is correct and render? [y/N]: ").strip().lower() in ("y", "yes")


def styles_for(row: dict, cli_styles: list[str]) -> list[str]:
    if cli_styles:
        return cli_styles
    s = str(row.get("style", "")).strip()
    return [s] if s else ["emerald_gold"]


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate Islamic name prints from a verified CSV.")
    ap.add_argument("--input", default=str(ROOT / "input" / "names.csv"))
    ap.add_argument("--styles", default="",
                    help="comma list forced for ALL rows (else each row's `style` column)")
    ap.add_argument("--output", default=str(ROOT / "output"))
    ap.add_argument("--force", action="store_true", help="re-render even if the output folder exists")
    ap.add_argument("--no-mockup", action="store_true", help="skip the framed wall mockup")
    ap.add_argument("--proof", action="store_true", help="also write a watermarked proof.png")
    ap.add_argument("--sizes", action="store_true", help="also export the multi-ratio print pack")
    ap.add_argument("--pins", action="store_true", help="also generate Pinterest pins + pins.csv")
    args = ap.parse_args()

    valid = available_styles()
    cli_styles = [s.strip() for s in args.styles.split(",") if s.strip()]
    for s in cli_styles:
        if s not in valid:
            ap.error(f"unknown style '{s}'. available: {', '.join(sorted(valid))}")

    in_path, out_dir = Path(args.input), Path(args.output)
    if not in_path.exists():
        ap.error(f"input CSV not found: {in_path}")

    with in_path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    db = load_names_db()

    print(f"Loaded {len(rows)} row(s) from {in_path}")
    print(f"Styles available: {', '.join(sorted(valid))}\n")

    rendered = skipped = failed = 0
    for i, row in enumerate(rows, 1):
        name = row.get("name_latin") or f"(row {i})"
        from_db = fill_from_db(row, db)

        # ---- verification gate ----
        if is_verified(row) or from_db:
            print(f"[{i}] {name}: verified" + (" (from names DB)" if from_db else ""))
        else:
            print(f"[{i}] {name}: not pre-verified")
            if not confirm_arabic(row):
                print(f"     skipped (unverified)\n")
                skipped += 1
                continue

        for style in styles_for(row, cli_styles):
            if style not in valid:
                print(f"     ! unknown style '{style}'; skipping")
                failed += 1
                continue
            slug = f"{render.slugify(name)}_{style}"
            folder = out_dir / slug
            if folder.exists() and any(folder.iterdir()) and not args.force:
                print(f"     = {slug}: exists, skip (use --force to overwrite)")
                skipped += 1
                continue
            try:
                paths = render.render(row, style, out_dir)
                extras = ""
                if not args.no_mockup:
                    if mockup_photo.OPENINGS and any((mockup_photo.MOCKS).glob("*.jpg")):
                        mockup_photo.generate_for(paths["png"], paths["folder"], slug)
                        extras += " + mockups(photo)"
                    else:
                        mockup.composite(paths["png"], paths["folder"] / f"{slug}_mockup.png")
                        extras += " + mockup"
                if args.proof:
                    proof.make_proof(paths["png"], paths["folder"] / f"{slug}_proof.png")
                    extras += " + proof"
                if args.sizes:
                    sizes.export(row, style, out_dir)
                    extras += " + sizes"
                if args.pins:
                    pins.build(row, style, paths["folder"], out_dir)
                    extras += " + pins"
                print(f"     + {slug}: print.png + print.pdf{extras}")
                rendered += 1
            except Exception as exc:  # noqa: BLE001 - never crash the batch
                print(f"     ! {slug}: FAILED -> {exc}")
                traceback.print_exc(file=sys.stderr)
                failed += 1
        print()

    print(f"Done. rendered={rendered}  skipped={skipped}  failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
