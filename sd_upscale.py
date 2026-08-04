#!/usr/bin/env python3
"""
sd_upscale.py - upscale SD candidates to A3 print files (CPU).

Usage:
  .venv-sd/bin/python sd_upscale.py output/staging_sd/meadow_42.png [more.png ...]

Pipeline per image:
  1. Real-ESRGAN 4x (realesrgan-x4plus, auto-downloads weights ~64 MB)
     512x768 -> 2048x3072 with detail synthesis (CPU: a few minutes)
  2. LANCZOS to exact A3 @ 300 DPI portrait (3508x4961), center-crop ratio
  3. Writes <stem>_print.png + <stem>_print.pdf into output/staging_sd/<stem>/
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdfcanvas

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "staging_sd"
W0, H0 = 3508, 4961

WEIGHTS_URL = ("https://github.com/xinntao/Real-ESRGAN/releases/download/"
               "v0.1.0/RealESRGAN_x4plus.pth")


def build_upsampler() -> RealESRGANer:
    model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23,
                    num_grow_ch=32, scale=4)
    return RealESRGANer(scale=4, model_path=WEIGHTS_URL, model=model,
                        tile=256, tile_pad=10, pre_pad=0, half=False,
                        device=torch.device("cpu"))


def to_a3(img: Image.Image) -> Image.Image:
    target = W0 / H0
    w, h = img.size
    if w / h > target:
        nw = int(h * target)
        img = img.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(w / target)
        img = img.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    return img.resize((W0, H0), Image.LANCZOS)


def main(paths: list[str]):
    up = build_upsampler()
    for p in paths:
        src = Path(p)
        if not src.exists():
            print(f"skip (missing): {src}")
            continue
        t0 = time.time()
        print(f"upscaling {src.name} ...", flush=True)
        img = Image.open(src).convert("RGB")
        arr = np.array(img)[:, :, ::-1]              # RGB -> BGR for realesrgan
        out, _ = up.enhance(arr, outscale=4)
        big = Image.fromarray(out[:, :, ::-1])       # BGR -> RGB
        art = to_a3(big)

        folder = OUT / src.stem
        folder.mkdir(parents=True, exist_ok=True)
        png = folder / f"{src.stem}_print.png"
        art.save(png, "PNG")
        page = (W0 / 300.0 * 72.0, H0 / 300.0 * 72.0)
        pdf = folder / f"{src.stem}_print.pdf"
        c = pdfcanvas.Canvas(str(pdf), pagesize=page)
        c.drawImage(ImageReader(art), 0, 0, width=page[0], height=page[1])
        c.showPage()
        c.save()
        print(f"  done {png}  ({(time.time()-t0)/60:.1f} min)", flush=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: sd_upscale.py <image.png> [...]")
    main(sys.argv[1:])
