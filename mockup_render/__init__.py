"""
mockup_render - data-driven perspective mockup renderer.

Every mockup is a self-contained directory:

    <mockup>/
        background.webp   (required)
        frame.png         (optional - moulding drawn in front of the artwork)
        shadow.png        (optional - multiplied over the composite)
        glare.png         (optional - screened over the composite)
        config.json       (required - geometry + effects, see MockupConfig)

The renderer holds NO coordinates. All geometry comes from config.json, and the
artwork is placed with a perspective transform solved from the four inner-quad
points (never x/y/width/height).

Public API:

    from mockup_render import render_mockup
    render_mockup(artwork_path, mockup_directory, output_path)

The four single-responsibility classes are also exported for extension:
MockupConfig, PerspectiveTransformer, LayerComposer, MockupRenderer.
"""
from .config import MockupConfig
from .transform import PerspectiveTransformer
from .compose import LayerComposer
from .renderer import MockupRenderer, render_mockup

__all__ = [
    "MockupConfig",
    "PerspectiveTransformer",
    "LayerComposer",
    "MockupRenderer",
    "render_mockup",
]
