"""PerspectiveTransformer - warp artwork onto the canvas via a homography.

Single responsibility: geometry. Given artwork pixels and a destination quad,
it (1) fits the artwork to the quad's aspect while preserving the artwork's own
aspect ratio, and (2) warps it with an OpenCV perspective transform solved from
the four points. It never reads config files or composites layers.
"""
from __future__ import annotations

import cv2
import numpy as np

Quad = list[list[float]]

_CV_INTERP = {
    "nearest": cv2.INTER_NEAREST,
    "bilinear": cv2.INTER_LINEAR,
    "bicubic": cv2.INTER_CUBIC,
    "lanczos": cv2.INTER_LANCZOS4,
    "area": cv2.INTER_AREA,
}


class PerspectiveTransformer:
    def __init__(self, interpolation: str = "lanczos"):
        self.flag = _CV_INTERP.get(interpolation, cv2.INTER_LANCZOS4)

    # ------------------------------------------------------------------ public
    def warp(self, artwork_rgba: np.ndarray, dst_quad: Quad,
             canvas_size: tuple[int, int], allow_crop: bool) -> np.ndarray:
        """Return an RGBA canvas with the artwork warped into dst_quad.

        allow_crop=False  -> the whole artwork is preserved (contain); if its
                             aspect differs from the quad it is centred inside a
                             proportionally inset quad (letterbox, no crop).
        allow_crop=True   -> the artwork is centre-cropped to the quad's aspect
                             so it fills the quad completely (cover).
        """
        art = self._ensure_rgba(artwork_rgba)
        h, w = art.shape[:2]
        quad_aspect = self._quad_aspect(dst_quad)

        if allow_crop:
            art = self._cover_crop(art, quad_aspect)
            target = dst_quad
        else:
            target = self._contain_quad(dst_quad, w / h, quad_aspect)

        h, w = art.shape[:2]
        src = np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=np.float32)
        dst = np.array(target, dtype=np.float32)
        matrix = cv2.getPerspectiveTransform(src, dst)
        cw, ch = canvas_size
        warped = cv2.warpPerspective(
            art, matrix, (cw, ch), flags=self.flag,
            borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0),
        )
        return warped

    @staticmethod
    def quad_mask(quad: Quad, canvas_size: tuple[int, int]) -> np.ndarray:
        """Single-channel uint8 mask (255 inside the quad) for clipping."""
        cw, ch = canvas_size
        mask = np.zeros((ch, cw), dtype=np.uint8)
        cv2.fillConvexPoly(mask, np.int32(np.round(quad)), 255)
        return mask

    # ------------------------------------------------------------------ geometry
    @staticmethod
    def _quad_aspect(quad: Quad) -> float:
        (x0, y0), (x1, y1), (x2, y2), (x3, y3) = quad
        top = np.hypot(x1 - x0, y1 - y0)
        bottom = np.hypot(x2 - x3, y2 - y3)
        left = np.hypot(x3 - x0, y3 - y0)
        right = np.hypot(x2 - x1, y2 - y1)
        return ((top + bottom) / 2.0) / max(1e-6, (left + right) / 2.0)

    @staticmethod
    def _contain_quad(quad: Quad, art_aspect: float, quad_aspect: float) -> Quad:
        """Inset the quad so an art-aspect rectangle fits inside it centred."""
        q = np.array(quad, dtype=np.float64)          # TL, TR, BR, BL
        tl, tr, br, bl = q
        if art_aspect > quad_aspect:                  # art wider -> inset top/bottom
            f = (1.0 - quad_aspect / art_aspect) / 2.0
            new = [tl + (bl - tl) * f, tr + (br - tr) * f,
                   br + (tr - br) * f, bl + (tl - bl) * f]
        else:                                         # art taller -> inset sides
            f = (1.0 - art_aspect / quad_aspect) / 2.0
            new = [tl + (tr - tl) * f, tr + (tl - tr) * f,
                   br + (bl - br) * f, bl + (br - bl) * f]
        return [[float(p[0]), float(p[1])] for p in new]

    @staticmethod
    def _cover_crop(art: np.ndarray, target_aspect: float) -> np.ndarray:
        h, w = art.shape[:2]
        if w / h > target_aspect:                     # too wide -> trim sides
            nw = int(round(h * target_aspect))
            x0 = (w - nw) // 2
            return art[:, x0:x0 + nw]
        nh = int(round(w / target_aspect))            # too tall -> trim top/bottom
        y0 = (h - nh) // 2
        return art[y0:y0 + nh, :]

    @staticmethod
    def _ensure_rgba(img: np.ndarray) -> np.ndarray:
        if img.ndim == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGBA)
        elif img.shape[2] == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2RGBA)
        return img
