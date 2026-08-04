"""MockupConfig - load, validate and expose a mockup's config.json.

Single responsibility: turn the on-disk config.json (plus the fixed asset
filenames) into a validated, typed object the rest of the pipeline can trust.
It knows nothing about warping or compositing.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

Quad = list[list[float]]        # exactly four [x, y] points, clockwise from TL

# The only hardcoded filenames allowed anywhere in the pipeline.
CONFIG_NAME = "config.json"
BACKGROUND_NAME = "background.webp"
FRAME_NAME = "frame.png"
SHADOW_NAME = "shadow.png"
GLARE_NAME = "glare.png"

_INTERP = {"nearest", "bilinear", "bicubic", "lanczos", "area"}
_BLEND = {"normal", "multiply", "screen"}


@dataclass(frozen=True)
class EffectLayer:
    """A shadow or glare layer's compositing parameters."""
    enabled: bool
    opacity: float
    blend_mode: str
    path: Optional[Path]        # resolved asset path, or None if the file is absent

    @property
    def active(self) -> bool:
        """Effect should be applied only if enabled AND its asset exists."""
        return self.enabled and self.path is not None


@dataclass(frozen=True)
class RenderOptions:
    allow_crop: bool
    default_padding: int
    interpolation: str


class MockupConfig:
    """Validated view over one mockup directory."""

    def __init__(self, directory: str | Path):
        self.directory = Path(directory)
        cfg_path = self.directory / CONFIG_NAME
        if not cfg_path.is_file():
            raise FileNotFoundError(f"missing {CONFIG_NAME} in {self.directory}")
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
        self._raw = raw
        self._validate(raw)

        # canvas
        self.width = int(raw["canvas"]["width"])
        self.height = int(raw["canvas"]["height"])

        # descriptive frame metadata (no behavioural booleans derived from it)
        self.frame = dict(raw.get("frame", {}))

        # geometry - the two quads are the source of truth
        self.outer_quad: Quad = [[float(x), float(y)] for x, y in raw["outer_quad"]]
        self.inner_quad: Quad = [[float(x), float(y)] for x, y in raw["inner_quad"]]

        # effects
        eff = raw.get("effects", {})
        self.shadow = self._effect(eff.get("shadow"), SHADOW_NAME, default_blend="multiply")
        self.glare = self._effect(eff.get("glare"), GLARE_NAME, default_blend="screen")

        # render options
        r = raw.get("render", {})
        interp = str(r.get("interpolation", "lanczos")).lower()
        if interp not in _INTERP:
            raise ValueError(f"interpolation must be one of {_INTERP}, got {interp!r}")
        self.render = RenderOptions(
            allow_crop=bool(r.get("allow_crop", False)),
            default_padding=int(r.get("default_padding", 0)),
            interpolation=interp,
        )

    # ---- resolved asset paths (optional layers return None when absent) ----
    @property
    def background_path(self) -> Path:
        p = self.directory / BACKGROUND_NAME
        if not p.is_file():
            raise FileNotFoundError(f"missing {BACKGROUND_NAME} in {self.directory}")
        return p

    @property
    def frame_path(self) -> Optional[Path]:
        p = self.directory / FRAME_NAME
        return p if p.is_file() else None

    @property
    def canvas_size(self) -> tuple[int, int]:
        return (self.width, self.height)

    @property
    def is_perspective(self) -> bool:
        """Derived, never stored: true when outer_quad is not an axis-aligned
        rectangle. Redundant booleans are intentionally not read from config."""
        return not self._is_rectangle(self.outer_quad)

    # ------------------------------------------------------------------ utils
    def _effect(self, spec: Optional[dict], filename: str, default_blend: str) -> EffectLayer:
        spec = spec or {}
        blend = str(spec.get("blend_mode", default_blend)).lower()
        if blend not in _BLEND:
            raise ValueError(f"blend_mode must be one of {_BLEND}, got {blend!r}")
        opacity = float(spec.get("opacity", 1.0))
        if not 0.0 <= opacity <= 1.0:
            raise ValueError(f"opacity must be in [0,1], got {opacity}")
        p = self.directory / filename
        return EffectLayer(
            enabled=bool(spec.get("enabled", False)),
            opacity=opacity,
            blend_mode=blend,
            path=p if p.is_file() else None,
        )

    @staticmethod
    def _is_rectangle(quad: Quad, tol: float = 1.0) -> bool:
        (x0, y0), (x1, y1), (x2, y2), (x3, y3) = quad
        # axis-aligned rectangle: top/bottom share y, left/right share x
        return (
            abs(y0 - y1) <= tol and abs(y2 - y3) <= tol
            and abs(x0 - x3) <= tol and abs(x1 - x2) <= tol
        )

    @staticmethod
    def _validate(raw: dict) -> None:
        if raw.get("version") != 1:
            raise ValueError(f"unsupported config version: {raw.get('version')!r}")
        for key in ("canvas", "outer_quad", "inner_quad"):
            if key not in raw:
                raise ValueError(f"config missing required key: {key!r}")
        for q in ("outer_quad", "inner_quad"):
            pts = raw[q]
            if not (isinstance(pts, list) and len(pts) == 4 and all(len(p) == 2 for p in pts)):
                raise ValueError(f"{q} must be exactly four [x, y] points")
        c = raw["canvas"]
        if not (isinstance(c, dict) and "width" in c and "height" in c):
            raise ValueError("canvas must have width and height")
