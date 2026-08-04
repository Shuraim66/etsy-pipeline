#!/usr/bin/env python3
"""
revert_push.py - put back the photo set that was on each listing before the
refresh_photos.py run.

What survived: the rebuild only ever wrote <slug>_lead.jpg, <slug>_scene_<room>.jpg,
<slug>_detail.jpg and <slug>_sizes.jpg. The ORIGINAL <slug>_mock1..3.jpg and
<slug>_scene1..4.jpg files were never touched, so the old photos still exist on
disk byte-for-byte. Only the old lead was overwritten, and that is regenerated
here from the pre-fix frame quads (kept in OLD_QUADS below) with the original
single-plate routing.

Which photo led each listing is recovered from the snapshot taken before the
push: it recorded rank-1's pixel dimensions per listing, and those dimensions
identify the plate uniquely.

Usage:
  python3 revert_push.py            # dry run
  python3 revert_push.py --live
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from PIL import Image

import etsy_api
import make_leads
import mockup_photo
from refresh_photos import delete_image, images_of

ROOT = Path(__file__).resolve().parent
S = Path("/tmp/claude-1000/-home-alpha-products-barakah-pipeline/"
         "816bc583-a082-4ed0-829d-65c9a115ca14/scratchpad")

# the frame quads exactly as they were before verify_plates.py rewrote them
OLD_QUADS = {
    "8148588":  [[191, 131], [859, 137], [858, 1077], [197, 1080]],
    "8490186":  [[301, 85], [556, 84], [554, 442], [302, 442]],
    "8490172":  [[394, 378], [739, 371], [739, 865], [399, 866]],
    "12486080": [[338, 505], [619, 504], [623, 890], [339, 890]],
    "12486417": [[224, 362], [676, 364], [672, 976], [222, 968]],
    "12486418": [[230, 372], [660, 372], [667, 943], [228, 948]],
    "20553171": [[238, 333], [511, 332], [511, 709], [237, 706]],
    "8490259":  [[311, 228], [542, 228], [542, 558], [311, 558]],
    "8490187":  [[789, 193], [1161, 193], [1161, 700], [789, 700]],
    "8490229":  [[1064, 410], [1425, 410], [1425, 928], [1064, 928]],
}

OLD_LEAD_LIGHT = "12486418"
OLD_LEAD_DARK = "8490186"


def use_old_quads():
    """Point every module that reads the quads at the pre-fix values."""
    make_leads.OPENINGS = {k: v for k, v in OLD_QUADS.items()}
    make_leads.LEAD_LIGHT = [OLD_LEAD_LIGHT]
    make_leads.LEAD_DARK = [OLD_LEAD_DARK]
    for pid, quad in OLD_QUADS.items():
        mockup_photo.OPENINGS[f"px_{pid}"] = [tuple(p) for p in quad]


def original_files(folder: Path, slug: str) -> list[Path]:
    """The photo files that existed before the refresh, in their old order."""
    order = [folder / f"{slug}_lead.jpg"]
    order += [folder / f"{slug}_scene{i}.jpg" for i in (1, 2, 3, 4)]
    order += [folder / f"{slug}_mock{i}.jpg" for i in (1, 2, 3)]
    order += [folder / f"{slug}_print.png"]
    return [p for p in order if p.exists()]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args(argv)

    use_old_quads()
    mapping = json.loads((S / "final_map.json").read_text())
    snapshot = {str(r[1]): r for r in json.loads((S / "shop.json").read_text())}
    pushed = [l.split()[0] for l in (S / "pushed.txt").read_text().split("\n") if l.strip()]
    print(f"{len(pushed)} listings to restore"
          f"{'' if args.live else '  (DRY RUN)'}\n")

    client = etsy_api.EtsyClient() if args.live else None
    for lid in pushed:
        v = mapping[lid]
        folder = ROOT / v["path"]
        slug = v["folder"]
        # rebuild the pre-fix lead in place
        make_leads.lead_for(folder / f"{slug}_print.png", folder, slug)
        files = original_files(folder, slug)

        # restore the photo that used to be rank 1, identified by its dimensions
        want = snapshot.get(lid)
        if want:
            wanted = (want[5], want[6])
            for i, p in enumerate(files):
                if Image.open(p).size == wanted and i:
                    files.insert(0, files.pop(i))
                    break
        files = files[: (want[4] if want else 9)]

        if not args.live:
            print(f"{lid} {slug}: {len(files)} photos -> "
                  f"{', '.join(p.name.replace(slug + '_', '') for p in files)}")
            continue

        before = {im["listing_image_id"] for im in images_of(client, lid)}
        for rank, p in enumerate(files, start=1):
            client.upload_listing_image(lid, p, rank=rank)
        for iid in before:
            delete_image(client, lid, iid)
        imgs = sorted(images_of(client, lid), key=lambda i: i.get("rank", 99))
        f = imgs[0] if imgs else {}
        print(f"restored {lid} {slug}: {len(imgs)} imgs, "
              f"rank1 {f.get('full_width')}x{f.get('full_height')} "
              f"(was {want[5]}x{want[6]})" if want else "", flush=True)
        time.sleep(0.2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
