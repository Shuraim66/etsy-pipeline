#!/usr/bin/env python3
"""
sd_generate.py - CPU-only Stable Diffusion generator for painterly wall art.

Run with the pipeline venv:
  .venv-sd/bin/python sd_generate.py --prompt "..." [--steps 22] [--n 1]

Model: Lykon/dreamshaper-8 (SD 1.5 fine-tune, strong painterly output,
~2 GB fp16 safetensors loaded as float32 for CPU). First run downloads the
model to ~/.cache/huggingface. 512x768 portrait; upscale separately before
print (A3 needs ~4x upscale via Real-ESRGAN or Pillow LANCZOS as stopgap).

Expected on Ryzen 7700 (8C/16T, CPU-only): roughly 2-5 min per image.
"""
from __future__ import annotations

import argparse
import gc
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "staging_sd"

NEGATIVE = ("text, watermark, signature, frame, border, lowres, blurry, "
            "jpeg artifacts, deformed, ugly, oversaturated")

PRESETS = {
    "meadow": ("impressionist oil painting of a wildflower meadow at golden hour, "
               "red poppies and white daisies, loose expressive brushstrokes, "
               "thick impasto, warm hazy light, fine art print"),
    "botanical": ("delicate watercolor eucalyptus branches on cream paper, "
                  "soft green sage tones, minimalist botanical illustration, "
                  "gentle washes, fine art print"),
    "coast": ("abstract seascape oil painting, soft teal and cream waves, "
              "gold leaf accents, palette knife texture, calm minimalist coastal art"),
    "moody_floral": ("moody dark floral oil painting, dusty rose and mauve peonies "
                     "on deep charcoal background, dramatic chiaroscuro light, "
                     "baroque still life, fine art print"),
    "mountains": ("misty mountain landscape painting, layered ridges in sage and "
                  "slate blue, minimalist Japanese ink wash style, atmospheric"),
    # --- expansion niches ---
    "desert_boho": ("boho desert landscape oil painting at dusk, terracotta sand "
                    "dunes, saguaro cactus silhouette, burnt orange and blush pink "
                    "sky, large sun, warm earthy tones, modern southwestern art"),
    "tropical": ("lush tropical monstera and palm leaves painting, deep emerald "
                 "greens on cream background, soft gouache texture, botanical "
                 "jungle wall art, elegant and airy"),
    "gold_abstract": ("minimalist abstract painting, flowing organic shapes in "
                      "cream beige and charcoal with gold leaf veins, japandi "
                      "style, calm neutral luxury wall art, heavy canvas texture"),
    "autumn_birch": ("autumn birch forest oil painting, white birch trunks with "
                     "golden amber leaves, soft morning light through trees, "
                     "impressionist brushwork, cozy fall colors"),
    "ocean_wave": ("dramatic ocean wave oil painting close up, turquoise and deep "
                   "teal water with white sea foam, sunlight through the crest, "
                   "realistic seascape, dynamic motion"),
    "lavender": ("lavender field at sunset oil painting, rows of purple lavender "
                 "leading to a rustic farmhouse, provence countryside, warm "
                 "golden sky, impressionist style"),
    "winter_forest": ("quiet winter forest painting, snow covered pine trees in "
                      "soft blue dusk light, falling snowflakes, peaceful "
                      "minimalist scandinavian winter scene"),
    "sunflowers": ("expressive sunflower bouquet oil painting in a ceramic vase, "
                   "thick impasto strokes, golden yellows against soft sage "
                   "background, joyful modern farmhouse art"),
    "koi": ("two koi fish circling in dark teal water, japanese style painting, "
            "gold and white koi with flowing fins, water ripples, lily pads, "
            "zen tranquil japandi wall art"),
    "celestial": ("dreamy celestial painting, crescent moon and stars over calm "
                  "midnight ocean, deep navy and silver with gold accents, "
                  "ethereal night sky, magical minimalist art"),
    # --- heavy brushwork family ---
    "brush_floral": ("thick impasto oil painting of wild roses, heavy palette "
                     "knife strokes, paint ridges catching light, visible canvas "
                     "weave, expressive loose brushwork, soft pink and cream on "
                     "sage green, textured fine art"),
    "brush_landscape": ("palette knife landscape painting, rolling hills at "
                        "sunset, thick slabs of paint, bold impasto texture, "
                        "orange gold and deep green, expressive energetic "
                        "strokes, modern textured art"),
    "brush_abstract": ("abstract acrylic painting with huge sweeping brushstrokes, "
                       "layered dry brush texture, terracotta cream and charcoal, "
                       "raw canvas visible at edges, gestural modern art, bold "
                       "confident strokes"),
    "brush_stilllife": ("loose alla prima oil sketch of a fruit bowl and pitcher, "
                        "visible thick brushstrokes, unfinished edges, warm "
                        "candlelight, painterly old master study, rich texture"),
}


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:48] or "image"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", help="free-form prompt (or use --preset)")
    ap.add_argument("--preset", choices=sorted(PRESETS), help="named art prompt")
    ap.add_argument("--steps", type=int, default=22)
    ap.add_argument("--n", type=int, default=1, help="number of images")
    ap.add_argument("--seed", type=int, default=0, help="base seed (0 = random)")
    ap.add_argument("--w", type=int, default=512)
    ap.add_argument("--h", type=int, default=768)
    args = ap.parse_args()

    prompt = args.prompt or (PRESETS[args.preset] if args.preset else PRESETS["meadow"])

    import torch
    from diffusers import StableDiffusionPipeline

    print(f"loading model (first run downloads ~2 GB)...", flush=True)
    t0 = time.time()
    pipe = StableDiffusionPipeline.from_pretrained(
        "Lykon/dreamshaper-8",
        torch_dtype=torch.float32,
        safety_checker=None,
        requires_safety_checker=False,
    )
    pipe = pipe.to("cpu")
    pipe.enable_attention_slicing()          # keeps peak RAM lower
    print(f"model ready in {time.time()-t0:.0f}s", flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    base_seed = args.seed or int(time.time()) % 100_000

    for i in range(args.n):
        seed = base_seed + i
        g = torch.Generator("cpu").manual_seed(seed)
        t1 = time.time()
        print(f"[{i+1}/{args.n}] generating {args.w}x{args.h}, "
              f"{args.steps} steps, seed {seed} ...", flush=True)
        img = pipe(prompt, negative_prompt=NEGATIVE, width=args.w, height=args.h,
                   num_inference_steps=args.steps, guidance_scale=7.0,
                   generator=g).images[0]
        dt = time.time() - t1
        name = f"{slugify(args.preset or prompt)}_{seed}"
        path = OUT / f"{name}.png"
        img.save(path)
        print(f"  saved {path}  ({dt/60:.1f} min)", flush=True)
        gc.collect()


if __name__ == "__main__":
    main()
