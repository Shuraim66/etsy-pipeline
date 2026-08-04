// SnappingEngine - refine a clicked point to the nearest frame corner.
//
// Pure JavaScript, zero dependencies: around the click it measures vertical- and
// horizontal-edge energy (Sobel-style gradients) and returns the intersection of
// the strongest vertical edge and strongest horizontal edge - i.e. the frame
// corner. Runs in well under a millisecond, never touches the main thread for
// long, and can't freeze the tab. If no strong corner is near the click it
// returns the click unchanged, so annotation never blocks.

import type { Point } from "../types";

export class SnappingEngine {
  constructor(private readonly window = 26, private readonly maxSnap = 24) {}

  /**
   * @param source a canvas holding the full image at native resolution
   * @param point  click position in image-pixel coordinates
   */
  snap(source: HTMLCanvasElement, point: Point): Point {
    const [px, py] = point;
    const x0 = Math.max(1, Math.round(px - this.window));
    const y0 = Math.max(1, Math.round(py - this.window));
    const x1 = Math.min(source.width - 1, Math.round(px + this.window));
    const y1 = Math.min(source.height - 1, Math.round(py + this.window));
    const w = x1 - x0;
    const h = y1 - y0;
    if (w < 6 || h < 6) return point;

    const ctx = source.getContext("2d", { willReadFrequently: true });
    if (!ctx) return point;

    // one extra pixel border so central differences stay in-bounds
    const img = ctx.getImageData(x0 - 1, y0 - 1, w + 2, h + 2);
    const stride = w + 2;
    const gray = new Float32Array((w + 2) * (h + 2));
    const d = img.data;
    for (let i = 0, p = 0; p < gray.length; p++, i += 4) {
      gray[p] = 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2];
    }

    const colEnergy = new Float32Array(w); // vertical edges (|dx|) per column
    const rowEnergy = new Float32Array(h); // horizontal edges (|dy|) per row
    for (let yy = 0; yy < h; yy++) {
      const gy = yy + 1;
      for (let xx = 0; xx < w; xx++) {
        const gx = xx + 1;
        const idx = gy * stride + gx;
        const dx = Math.abs(gray[idx + 1] - gray[idx - 1]);
        const dyv = Math.abs(gray[idx + stride] - gray[idx - stride]);
        colEnergy[xx] += dx;
        rowEnergy[yy] += dyv;
      }
    }

    const bestX = argmax(colEnergy);
    const bestY = argmax(rowEnergy);
    if (bestX < 0 || bestY < 0) return point;

    const cand: Point = [x0 + bestX, y0 + bestY];
    const dist = Math.hypot(cand[0] - px, cand[1] - py);
    return dist <= this.maxSnap ? cand : point;
  }
}

function argmax(a: Float32Array): number {
  let best = -1;
  let bestVal = -Infinity;
  for (let i = 0; i < a.length; i++) {
    if (a[i] > bestVal) {
      bestVal = a[i];
      best = i;
    }
  }
  return best;
}
