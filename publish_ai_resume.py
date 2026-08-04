#!/usr/bin/env python3
"""Resume AI-line publishing: waits for DNS, verifies which drafts already
exist on Etsy (by title), deletes any partial (files/images incomplete), and
publishes the rest. Safe to re-run until it reports 21/21."""
import socket
import time
from pathlib import Path

import requests

import etsy_api
import etsy_publish_art as pub

ROOT = Path(__file__).resolve().parent


def wait_dns(host="openapi.etsy.com", max_wait=1800):
    t0 = time.time()
    while time.time() - t0 < max_wait:
        try:
            socket.getaddrinfo(host, 443)
            return True
        except OSError:
            time.sleep(20)
    return False


if not wait_dns():
    raise SystemExit("DNS never recovered")
print("DNS ok", flush=True)

secrets_all = etsy_api.load_secrets()
defaults = dict(secrets_all.get("listing", {}))
defaults.pop("personalization_instructions", None)
client = etsy_api.EtsyClient()
section_id = int(secrets_all["listing"]["art_section_id"])

# existing drafts in the art section
res = client.get(f"/shops/{client.shop_id}/listings", state="draft", limit=100)
drafts = [l for l in res.get("results", []) if l.get("shop_section_id") == section_id]
by_title = {}
for l in drafts:
    by_title[l["title"]] = l["listing_id"]
print(f"{len(drafts)} existing drafts in section", flush=True)

root = ROOT / "output" / "staging_sd"
done = skipped = 0
for folder in sorted(p for p in root.iterdir() if p.is_dir()):
    slug = folder.name
    if not (folder / f"{slug}_print.png").exists():
        continue
    meta = pub.build_meta(folder, "ai")
    if meta is None:
        continue
    lid = by_title.get(meta["title"])
    if lid:
        # verify completeness: needs 5 files
        try:
            fres = client.get(f"/shops/{client.shop_id}/listings/{lid}/files")
            nfiles = fres.get("count", len(fres.get("results", [])))
        except Exception:
            nfiles = -1
        if nfiles >= 5:
            skipped += 1
            print(f"skip (complete): {slug}", flush=True)
            continue
        print(f"deleting partial {lid} ({slug}, files={nfiles})", flush=True)
        requests.delete(f"https://openapi.etsy.com/v3/application/listings/{lid}",
                        headers=client._headers(), timeout=60)
    pub.process_one(folder, "ai", defaults, True, client, section_id)
    done += 1

print(f"\npublished {done}, skipped {skipped} already-complete", flush=True)
