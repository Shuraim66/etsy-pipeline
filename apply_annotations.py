#!/usr/bin/env python3
"""
apply_annotations.py - push traced quads from the annotator into mockup configs.

Reads an annotations.json (produced by mockup-annotator) and, for each
"<image_name>", updates the matching mockups/<name>/config.json in place with the
operator-traced `canvas`, `outer_quad` and `inner_quad`. Everything else in the
config (frame metadata, effects, render options) is preserved.

    python3 apply_annotations.py [annotations.json]

Default annotations path: assets/mockups/frames/annotations.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MOCKUPS = ROOT / "mockups"


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    ann_path = Path(argv[0]) if argv else ROOT / "assets/mockups/frames/annotations.json"
    data = json.loads(ann_path.read_text())
    if data.get("version") != 1:
        raise SystemExit(f"unexpected annotations version: {data.get('version')!r}")

    updated, missing = 0, []
    for image_name, a in data.get("mockups", {}).items():
        name = Path(image_name).stem                      # "m1_black_hung.jpg" -> "m1_black_hung"
        cfg_path = MOCKUPS / name / "config.json"
        if not cfg_path.is_file():
            missing.append(name)
            continue
        cfg = json.loads(cfg_path.read_text())
        cfg["canvas"] = {"width": int(a["canvas"][0]), "height": int(a["canvas"][1])}
        cfg["outer_quad"] = [[round(float(x), 1), round(float(y), 1)] for x, y in a["outer_quad"]]
        cfg["inner_quad"] = [[round(float(x), 1), round(float(y), 1)] for x, y in a["inner_quad"]]
        cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        updated += 1
        print("updated", name)

    print(f"\n{updated} configs updated from {ann_path}")
    if missing:
        print("no mockup dir for:", ", ".join(missing))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
