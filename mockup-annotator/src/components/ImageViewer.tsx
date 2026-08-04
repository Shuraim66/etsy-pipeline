// ImageViewer - draws the current image to a native-resolution canvas and owns
// zoom + pan. It converts pointer positions to image-pixel coordinates and
// distinguishes a click (add point) from a drag (pan). Overlays are rendered as
// a render-prop child so the PolygonEditor stays in image-coordinate space.

import { useCallback, useEffect, useRef, useState } from "react";
import type { LoadedImage, Point } from "../types";

interface Props {
  image: LoadedImage;
  onCanvasReady: (canvas: HTMLCanvasElement) => void;
  onClickPoint: (p: Point) => void;
  children: (ctx: { zoom: number; toImage: (cx: number, cy: number) => Point }) => React.ReactNode;
}

const MIN_ZOOM = 0.05;
const MAX_ZOOM = 12;
const DRAG_THRESHOLD = 4; // px of movement before a press is treated as a pan

export function ImageViewer({ image, onCanvasReady, onClickPoint, children }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });

  const press = useRef<{ x: number; y: number; panx: number; pany: number; moved: boolean } | null>(null);

  // keep the callback in a ref so it is NOT an effect dependency (an inline
  // prop would change every render and re-run the fit effect -> setState loop)
  const onCanvasReadyRef = useRef(onCanvasReady);
  onCanvasReadyRef.current = onCanvasReady;

  // draw the image at native resolution and fit-to-view ONCE per image
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.width = image.width;
    canvas.height = image.height;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    ctx?.drawImage(image.element, 0, 0);
    onCanvasReadyRef.current(canvas);

    const box = containerRef.current?.getBoundingClientRect();
    if (box) {
      const z = Math.min(box.width / image.width, box.height / image.height) * 0.9;
      setZoom(z);
      setPan({ x: (box.width - image.width * z) / 2, y: (box.height - image.height * z) / 2 });
    }
  }, [image]);

  const toImage = useCallback(
    (clientX: number, clientY: number): Point => {
      const box = containerRef.current!.getBoundingClientRect();
      const sx = clientX - box.left;
      const sy = clientY - box.top;
      return [(sx - pan.x) / zoom, (sy - pan.y) / zoom];
    },
    [pan, zoom]
  );

  const onWheel = useCallback(
    (e: React.WheelEvent) => {
      e.preventDefault();
      const box = containerRef.current!.getBoundingClientRect();
      const cx = e.clientX - box.left;
      const cy = e.clientY - box.top;
      const factor = e.deltaY < 0 ? 1.1 : 1 / 1.1;
      const next = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, zoom * factor));
      // keep the image point under the cursor fixed
      const ix = (cx - pan.x) / zoom;
      const iy = (cy - pan.y) / zoom;
      setPan({ x: cx - ix * next, y: cy - iy * next });
      setZoom(next);
    },
    [pan, zoom]
  );

  const onPointerDown = (e: React.PointerEvent) => {
    (e.target as Element).setPointerCapture?.(e.pointerId);
    press.current = { x: e.clientX, y: e.clientY, panx: pan.x, pany: pan.y, moved: false };
  };

  const onPointerMove = (e: React.PointerEvent) => {
    const p = press.current;
    if (!p) return;
    const dx = e.clientX - p.x;
    const dy = e.clientY - p.y;
    if (!p.moved && Math.hypot(dx, dy) < DRAG_THRESHOLD) return;
    p.moved = true;
    setPan({ x: p.panx + dx, y: p.pany + dy });
  };

  const onPointerUp = (e: React.PointerEvent) => {
    const p = press.current;
    press.current = null;
    if (p && !p.moved) onClickPoint(toImage(e.clientX, e.clientY));
  };

  return (
    <div
      ref={containerRef}
      className="viewer"
      onWheel={onWheel}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
    >
      <div
        className="stage"
        style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`, transformOrigin: "0 0" }}
      >
        <canvas ref={canvasRef} className="image-canvas" />
        {children({ zoom, toImage })}
      </div>
    </div>
  );
}
