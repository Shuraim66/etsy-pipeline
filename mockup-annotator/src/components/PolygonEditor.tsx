// PolygonEditor - draws the outer (blue) and inner (green) quads in image space
// and lets any placed point be dragged. Handle size / stroke scale by 1/zoom so
// they stay a constant on-screen size. Dragging uses window-level pointer
// listeners (not SVG bubbling / pointer capture) so it works reliably at any
// zoom and under the stage's CSS transform. It only knows about points.

import { useRef } from "react";
import type { Point, QuadKind } from "../types";

interface Props {
  outer: Point[];
  inner: Point[];
  active: QuadKind;
  zoom: number;
  width: number;
  height: number;
  toImage: (clientX: number, clientY: number) => Point;
  onMovePoint: (kind: QuadKind, index: number, p: Point) => void;
}

const COLOR: Record<QuadKind, string> = { outer: "#2f7bff", inner: "#26c26b" };
const LABEL: Record<QuadKind, string> = { outer: "OUTER", inner: "INNER" };

export function PolygonEditor({
  outer,
  inner,
  active,
  zoom,
  width,
  height,
  toImage,
  onMovePoint,
}: Props) {
  // refs keep the window listeners reading the latest transform / handler
  const toImageRef = useRef(toImage);
  toImageRef.current = toImage;
  const moveRef = useRef(onMovePoint);
  moveRef.current = onMovePoint;

  const r = 6 / zoom;
  const sw = 1.5 / zoom;

  const startDrag = (kind: QuadKind, index: number) => (e: React.PointerEvent) => {
    e.stopPropagation(); // don't let the viewer treat this as a pan / add-point
    e.preventDefault();
    const onMove = (ev: PointerEvent) => {
      moveRef.current(kind, index, toImageRef.current(ev.clientX, ev.clientY));
    };
    const onUp = () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  };

  return (
    <svg
      className="overlay"
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
    >
      {(["outer", "inner"] as QuadKind[]).map((kind) => {
        const pts = kind === "outer" ? outer : inner;
        const color = COLOR[kind];
        const path = pts.map((p) => p.join(",")).join(" ");
        return (
          <g key={kind} opacity={kind === active ? 1 : 0.55}>
            {pts.length >= 2 &&
              (pts.length === 4 ? (
                <polygon points={path} fill="none" stroke={color} strokeWidth={sw} />
              ) : (
                <polyline points={path} fill="none" stroke={color} strokeWidth={sw} />
              ))}
            {pts.map((p, i) => (
              <g key={i}>
                {/* larger invisible hit area so tiny handles stay grabbable */}
                <circle
                  cx={p[0]}
                  cy={p[1]}
                  r={r * 2.2}
                  fill="transparent"
                  style={{ cursor: "grab" }}
                  onPointerDown={startDrag(kind, i)}
                />
                <circle
                  cx={p[0]}
                  cy={p[1]}
                  r={r}
                  fill={color}
                  stroke="#fff"
                  strokeWidth={sw}
                  pointerEvents="none"
                />
                <text x={p[0] + r * 1.8} y={p[1] - r} fontSize={11 / zoom} fill={color} pointerEvents="none">
                  {i + 1}
                </text>
              </g>
            ))}
            {pts.length > 0 && (
              <text
                x={pts[0][0]}
                y={pts[0][1] - r * 2.6}
                fontSize={13 / zoom}
                fill={color}
                fontWeight="bold"
                pointerEvents="none"
              >
                {LABEL[kind]}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}
