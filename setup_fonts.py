#!/usr/bin/env python3
"""
setup_fonts.py - one-time font fetcher for the Barakah name-print pipeline.

Downloads the open-licensed (OFL) fonts the renderer needs into assets/fonts/:
  - Amiri        (Arabic)        : github.com/aliftype/amiri
  - EB Garamond  (Latin serif)   : github.com/google/fonts
  - Cinzel       (Latin display) : github.com/google/fonts

Each download is validated by its sfnt magic bytes so an HTML error page can
never be saved as a ".ttf" -- note the bare github /main/ path (without
/fonts/) serves HTML for Amiri, which this guard rejects.

This script downloads font binaries only. It never reads, writes, generates,
or transliterates any Arabic text content.
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

ASSET_DIR = Path(__file__).resolve().parent / "assets" / "fonts"

# (url, saved filename, human label)
FONTS = [
    ("https://raw.githubusercontent.com/aliftype/amiri/main/fonts/Amiri-Regular.ttf",
     "Amiri-Regular.ttf", "Amiri Regular (Arabic)"),
    ("https://raw.githubusercontent.com/aliftype/amiri/main/fonts/Amiri-Bold.ttf",
     "Amiri-Bold.ttf", "Amiri Bold (Arabic)"),
    # google/fonts ships these as variable fonts; the [wght] brackets are
    # url-encoded (%5B / %5D) so HTTP clients accept the path.
    ("https://raw.githubusercontent.com/google/fonts/main/ofl/ebgaramond/EBGaramond%5Bwght%5D.ttf",
     "EBGaramond[wght].ttf", "EB Garamond (Latin serif, variable)"),
    ("https://raw.githubusercontent.com/google/fonts/main/ofl/ebgaramond/EBGaramond-Italic%5Bwght%5D.ttf",
     "EBGaramond-Italic[wght].ttf", "EB Garamond Italic (Latin serif, variable)"),
    ("https://raw.githubusercontent.com/google/fonts/main/ofl/cinzel/Cinzel%5Bwght%5D.ttf",
     "Cinzel[wght].ttf", "Cinzel (Latin display, variable)"),
    # additional Arabic calligraphy scripts (operator-selectable)
    ("https://raw.githubusercontent.com/google/fonts/main/ofl/reemkufi/ReemKufi%5Bwght%5D.ttf",
     "ReemKufi[wght].ttf", "Reem Kufi (Arabic, Kufic, variable)"),
    ("https://raw.githubusercontent.com/google/fonts/main/ofl/arefruqaa/ArefRuqaa-Regular.ttf",
     "ArefRuqaa-Regular.ttf", "Aref Ruqaa Regular (Arabic, Ruqaa)"),
    ("https://raw.githubusercontent.com/google/fonts/main/ofl/arefruqaa/ArefRuqaa-Bold.ttf",
     "ArefRuqaa-Bold.ttf", "Aref Ruqaa Bold (Arabic, Ruqaa)"),
]

# Valid sfnt version tags for TrueType / OpenType / web font wrappers.
FONT_MAGIC = (b"\x00\x01\x00\x00", b"true", b"ttcf", b"OTTO", b"wOFF", b"wOF2")


def looks_like_font(data: bytes) -> bool:
    return len(data) > 4096 and data[:4] in FONT_MAGIC


def fetch(url: str, dest: Path, label: str) -> bool:
    req = urllib.request.Request(url, headers={"User-Agent": "barakah-pipeline/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
    except Exception as exc:  # noqa: BLE001 - report any network/HTTP failure
        print(f"  [FAIL] {label}: download error ({exc})")
        return False
    if not looks_like_font(data):
        print(f"  [FAIL] {label}: response is not a font "
              f"({len(data)} bytes, head={data[:16]!r}). "
              f"Likely an HTML page -- verify the URL path.")
        return False
    dest.write_bytes(data)
    print(f"  [ OK ] {label}: {len(data) // 1024} KB -> {dest.name}")
    return True


def main() -> int:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Fetching fonts into {ASSET_DIR}")
    ok = sum(fetch(url, ASSET_DIR / name, label) for url, name, label in FONTS)
    print(f"\n{ok}/{len(FONTS)} fonts ready.")
    if ok != len(FONTS):
        print("Some fonts failed; the renderer needs all of them. See errors above.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
