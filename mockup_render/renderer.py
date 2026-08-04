"""MockupRenderer - orchestrates the render pipeline.

Single responsibility: sequencing. It wires MockupConfig, PerspectiveTransformer
and LayerComposer together in the fixed order

    background -> warp artwork to inner_quad -> clip -> multiply shadow
              -> screen glare -> frame overlay -> save

and does the file I/O. All geometry and blending live in the other classes, so
adding a stage (paper grain, texture overlay, ...) is a new composite call here,
not a change to the maths.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from .compose import LayerComposer
from .config import MockupConfig
from .transform import PerspectiveTransformer


class MockupRenderer:
    def __init__(self, config: MockupConfig):
        self.config = config
        self.transformer = PerspectiveTransformer(config.render.interpolation)
        self.composer = LayerComposer()

    # ------------------------------------------------------------------ public
    def render(self, artwork_path: str | Path, output_path: str | Path) -> dict[str, Path]:
        cfg = self.config
        canvas = cfg.canvas_size

        # 1. background (required, forced to canvas size)
        result = self._load_rgba(cfg.background_path, canvas)

        # 2. warp artwork to the inner quad (expanded by padding so it tucks
        #    under the frame lip instead of leaving a gap)
        art = self._load_rgba(artwork_path)
        dst = self._expand_quad(cfg.inner_quad, cfg.render.default_padding)
        warped = self.transformer.warp(art, dst, canvas, cfg.render.allow_crop)

        # 3. clip artwork to the (expanded) opening, then place on background
        warped = self.composer.clip(warped, self.transformer.quad_mask(dst, canvas))
        result = self.composer.over(result, warped, blend_mode="normal")

        # 4. multiply shadow  5. screen glare  (optional, skipped if absent)
        if cfg.shadow.active:
            result = self.composer.over(result, self._load_rgba(cfg.shadow.path, canvas),
                                        cfg.shadow.opacity, cfg.shadow.blend_mode)
        if cfg.glare.active:
            result = self.composer.over(result, self._load_rgba(cfg.glare.path, canvas),
                                        cfg.glare.opacity, cfg.glare.blend_mode)

        # 6. frame overlay (moulding in front of the artwork), if present
        if cfg.frame_path is not None:
            result = self.composer.over(result, self._load_rgba(cfg.frame_path, canvas),
                                        1.0, "normal")

        # 7. save PNG + JPEG
        return self._save(result, output_path)

    # ------------------------------------------------------------------ io
    @staticmethod
    def _load_rgba(path, size: tuple[int, int] | None = None) -> np.ndarray:
        img = Image.open(path).convert("RGBA")
        if size is not None and img.size != size:
            img = img.resize(size, Image.LANCZOS)
        return np.asarray(img)

    @staticmethod
    def _save(rgba: np.ndarray, output_path) -> dict[str, Path]:
        out = Path(output_path)
        stem = out.with_suffix("")
        png_path = stem.with_suffix(".png")
        jpg_path = stem.with_suffix(".jpg")
        img = Image.fromarray(rgba, "RGBA")
        img.save(png_path)
        # JPEG has no alpha - flatten onto white
        flat = Image.new("RGB", img.size, (255, 255, 255))
        flat.paste(img, mask=img.split()[3])
        flat.save(jpg_path, quality=94, subsampling=0)
        return {"png": png_path, "jpg": jpg_path}

    # ------------------------------------------------------------------ geometry
    @staticmethod
    def _expand_quad(quad, px: float):
        """Grow the quad outward from its centroid so its edges move out by
        ~px pixels (used to tuck the print under the frame lip)."""
        if not px:
            return quad
        q = np.array(quad, dtype=np.float64)
        c = q.mean(axis=0)
        radii = np.hypot(*(q - c).T)
        scale = 1.0 + float(px) / max(1.0, radii.mean())
        return [[float(x), float(y)] for x, y in (c + (q - c) * scale)]


def render_mockup(artwork_path: str | Path, mockup_directory: str | Path,
                  output_path: str | Path) -> dict[str, Path]:
    """Single public entry point: render `artwork_path` into the mockup at
    `mockup_directory` (which contains its assets + config.json) and write the
    result to `output_path` (as both .png and .jpg). Returns the written paths.
    """
    config = MockupConfig(mockup_directory)
    return MockupRenderer(config).render(artwork_path, output_path)
