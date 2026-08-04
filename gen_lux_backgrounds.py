#!/usr/bin/env python3
"""
gen_lux_backgrounds.py - premium verse-art backgrounds tuned to what the
market's top sellers use (gold-foil marble, navy/gold, layered watercolor,
luxe finishes). SD 1.5 local, text-free, HARD anti-figure negatives.

Every output MUST pass a full-size human/agent review for figures, faces, or
anything inappropriate BEFORE any verse is composited (standing rule after
the plum_silk incident).
"""
from __future__ import annotations

import time
from pathlib import Path

import torch
from diffusers import StableDiffusionPipeline

OUT = Path(__file__).resolve().parent / "output" / "staging_sd"

NEG = ("person, people, woman, man, girl, human, figure, body, face, skin, "
       "portrait, lingerie, model, pose, hair, hands, "
       "text, letters, words, writing, calligraphy, characters, watermark, "
       "signature, frame, mirror, furniture, room, objects, flowers in vase, "
       "3d render, lowres, blurry")

JOBS = [
    # (name, seed, prompt) — tuned to bestseller looks
    ("bg2_marble_emerald", 201,
     "elegant dark emerald green marble stone texture with fine delicate gold "
     "foil veins and subtle white mineral streaks, polished luxury surface, "
     "top-down flat texture photograph, seamless, full frame"),
    ("bg2_marble_black", 202,
     "black marble stone texture with dramatic thin gold foil veins and faint "
     "smoke grey clouds, luxurious polished surface, flat texture photograph, "
     "full frame"),
    ("bg2_navy_gold", 203,
     "deep midnight navy blue painted texture with drifting gold leaf dust and "
     "fine gold foil flecks concentrated near the bottom corner, elegant "
     "luxury abstract, flat texture, full frame"),
    ("bg2_burgundy_gold", 204,
     "rich dark burgundy maroon painted texture with scattered antique gold "
     "leaf flakes and soft tonal depth, opulent luxury abstract background, "
     "flat texture, full frame"),
    ("bg2_ivory_gold_wc", 205,
     "soft ivory cream watercolor wash with pale grey undertones and delicate "
     "gold foil splatter accents, airy elegant abstract background, paper "
     "grain, flat texture, full frame"),
    ("bg2_teal_ink", 206,
     "deep teal and dark green ink wash texture with soft black gradients and "
     "a whisper of gold shimmer, moody elegant abstract background, flat "
     "texture, full frame"),
]

if __name__ == "__main__":
    pipe = StableDiffusionPipeline.from_pretrained(
        "Lykon/dreamshaper-8", torch_dtype=torch.float32,
        safety_checker=None, requires_safety_checker=False).to("cpu")
    pipe.enable_attention_slicing()
    for name, seed, prompt in JOBS:
        g = torch.Generator("cpu").manual_seed(seed)
        t0 = time.time()
        img = pipe(prompt, negative_prompt=NEG, width=512, height=768,
                   num_inference_steps=22, guidance_scale=7.5, generator=g).images[0]
        img.save(OUT / f"{name}.png")
        print(f"saved {name} ({(time.time()-t0)/60:.1f} min)", flush=True)
