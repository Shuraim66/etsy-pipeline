#!/usr/bin/env python3
"""
build_shop_45.py - render every single-print listing's photo set on the new
data-driven mockup pipeline (mockup_render + mockups/).

Per listing: a lead from a strong/warm frame + 5 varied scenes + a sizes card,
all uniform 4:5 (2000x2500). Frame choice rotates by a hash of the slug so
neighbouring shop results never share a lead. Writes <slug>_v1..v7.jpg into the
listing's own folder. Local only - pushing is a separate, approved step.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image

import sizes_card
from mockup_render import render_mockup

ROOT = Path(__file__).resolve().parent
MOCKUPS = ROOT / "mockups"
FRAMES = sorted(d.name for d in MOCKUPS.iterdir() if d.is_dir())
# strong, art-dominant frames suitable for the lead/thumbnail
LEAD_POOL = ["px_8534228", "m1_black_hung", "px_12486417", "px_12486418",
             "m2_gold_lean", "m3_brass_flatlay", "px_8490197"]
LEAD_POOL = [f for f in LEAD_POOL if f in FRAMES]
N_SCENES = 6


def _hash(s: str) -> int:
    return int(hashlib.md5(s.encode()).hexdigest(), 16)


# frames that must never be the lead/thumbnail (kept as secondaries though):
# m1_black_hung's black moulding disappears behind dark prints, so the thumbnail
# reads as a frameless poster.
NO_LEAD = {"m1_black_hung"}
_ALLOWED_LEADS = [f for f in LEAD_POOL if f not in NO_LEAD]


def lead_for(slug: str) -> str:
    lead = LEAD_POOL[_hash(slug) % len(LEAD_POOL)]
    if lead in NO_LEAD:
        # reassign to a VARIED allowed lead (a second hash spreads the affected
        # listings across frames instead of all landing on the same one)
        lead = _ALLOWED_LEADS[_hash(slug + "lead") % len(_ALLOWED_LEADS)]
    return lead


def frames_for(slug: str) -> list[str]:
    lead = lead_for(slug)
    off = _hash(slug + "x") % len(FRAMES)
    rot = FRAMES[off:] + FRAMES[:off]
    order = [lead] + [f for f in rot if f != lead]
    return order[:N_SCENES]


def sizes_card_45(out: Path) -> Path:
    sq = sizes_card.build(out.with_name(out.stem + "_sq.jpg"))
    ci = Image.open(sq).convert("RGB")
    canv = Image.new("RGB", (2000, 2500), (244, 241, 235))
    canv.paste(ci.resize((2000, 2000)), (0, 250))
    canv.save(out, quality=94)
    return out


def build_one(print_png: Path, folder: Path, slug: str) -> list[Path]:
    out = []
    for i, fr in enumerate(frames_for(slug), 1):
        r = render_mockup(print_png, MOCKUPS / fr, folder / f"{slug}_v{i}.jpg")
        out.append(r["jpg"])
    out.append(sizes_card_45(folder / f"{slug}_v{N_SCENES + 1}.jpg"))
    return out


def main():
    rollout = json.loads((ROOT / "assets/mockups/pexels/OPENINGS.json").exists() and
                         Path("/tmp/claude-1000/-home-alpha-products-barakah-pipeline/"
                              "816bc583-a082-4ed0-829d-65c9a115ca14/scratchpad/rollout.json").read_text())
    done = 0
    for lid, folder_name, print_path in rollout:
        pp = Path(print_path)
        folder = pp.parent
        slug = pp.name[:-len("_print.png")]
        try:
            build_one(pp, folder, slug)
            done += 1
            print(f"[{done}/{len(rollout)}] {lid} {slug}", flush=True)
        except Exception as e:
            print(f"FAIL {lid} {slug}: {e}", flush=True)
    print(f"\nbuilt {done}/{len(rollout)} listing sets")


if __name__ == "__main__":
    main()
