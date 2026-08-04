"""LayerComposer - blend RGBA layers.

Single responsibility: pixel compositing. It implements alpha-over plus the
'multiply' and 'screen' blend modes, and a clip-to-mask helper. It has no
knowledge of mockups, files, or geometry - it only takes arrays in and returns
arrays out, so new blend modes or layers can be added without touching the
renderer.
"""
from __future__ import annotations

import numpy as np

Array = np.ndarray


class LayerComposer:
    # ------------------------------------------------------------------ public
    def over(self, base: Array, overlay: Array | None, opacity: float = 1.0,
             blend_mode: str = "normal") -> Array:
        """Composite overlay onto base (both HxWx4 uint8). No-op if overlay is
        None so callers can pass optional layers unconditionally."""
        if overlay is None:
            return base
        base_f = base.astype(np.float32) / 255.0
        over_f = overlay.astype(np.float32) / 255.0

        blended_rgb = self._blend_rgb(base_f[..., :3], over_f[..., :3], blend_mode)
        # effective source alpha = overlay alpha * layer opacity
        a = over_f[..., 3:4] * float(opacity)

        out_rgb = blended_rgb * a + base_f[..., :3] * (1.0 - a)
        out_a = a + base_f[..., 3:4] * (1.0 - a)
        out = np.concatenate([out_rgb, out_a], axis=-1)
        return (np.clip(out, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)

    @staticmethod
    def clip(image: Array, mask: Array) -> Array:
        """Zero the alpha of image wherever mask (HxW uint8) is 0."""
        out = image.copy()
        keep = (mask.astype(np.float32) / 255.0)
        out[..., 3] = (out[..., 3].astype(np.float32) * keep + 0.5).astype(np.uint8)
        return out

    # ------------------------------------------------------------------ blends
    def _blend_rgb(self, base: Array, over: Array, mode: str) -> Array:
        if mode == "multiply":
            return base * over
        if mode == "screen":
            return 1.0 - (1.0 - base) * (1.0 - over)
        return over            # 'normal' - straight source colour, alpha does the mixing
