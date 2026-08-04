// Shared domain types. The persisted schema matches the renderer's config.json
// geometry exactly (four [x, y] points per quad, clockwise from top-left).

export type Point = [number, number];
export type Quad = [Point, Point, Point, Point];

export type QuadKind = "outer" | "inner";

export interface MockupAnnotation {
  canvas: [number, number]; // [width, height] in image pixels
  outer_quad: Quad;
  inner_quad: Quad;
}

export interface AnnotationsFile {
  version: 1;
  mockups: Record<string, MockupAnnotation>;
}

// In-progress annotation for the current image: quads may be partial (< 4 pts).
export interface WorkingAnnotation {
  canvas: [number, number];
  outer: Point[];
  inner: Point[];
}

export interface LoadedImage {
  name: string;
  url: string;
  width: number;
  height: number;
  element: HTMLImageElement;
}
