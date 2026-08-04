"""CLI: python -m mockup_render <artwork> <mockup_dir> <output> [<mockup_dir> ...]

Renders one artwork into one or more mockup directories. With multiple mockup
dirs, <output> is treated as a directory and each result is named after its
mockup.
"""
from __future__ import annotations

import sys
from pathlib import Path

from . import render_mockup


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 3:
        print(__doc__.strip())
        return 2
    artwork, *rest = argv
    output = rest.pop()
    mockups = rest if rest else [output] and rest
    mockups = rest
    if not mockups:
        print("need at least one mockup directory")
        return 2

    if len(mockups) == 1:
        res = render_mockup(artwork, mockups[0], output)
        print(res["png"], res["jpg"])
    else:
        outdir = Path(output)
        outdir.mkdir(parents=True, exist_ok=True)
        for m in mockups:
            name = Path(m).name
            res = render_mockup(artwork, m, outdir / f"{name}.png")
            print(res["png"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
