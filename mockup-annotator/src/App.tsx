// App - orchestrates the annotation workflow and keyboard shortcuts. It holds
// the images, the persisted annotations file, and the working quads for the
// current image, and wires the ImageViewer, PolygonEditor, SnappingEngine and
// persistence together. Each of those stays single-responsibility.

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ImageViewer } from "./components/ImageViewer";
import { PolygonEditor } from "./components/PolygonEditor";
import { Toolbar } from "./components/Toolbar";
import { SnappingEngine } from "./engine/snapping";
import * as store from "./persistence/annotations";
import { useImageFolder } from "./hooks/useImageFolder";
import type { AnnotationsFile, Point, QuadKind, WorkingAnnotation } from "./types";

function emptyWorking(w: number, h: number): WorkingAnnotation {
  return { canvas: [w, h], outer: [], inner: [] };
}

export default function App() {
  const { images, loadFiles } = useImageFolder();
  const [index, setIndex] = useState(0);
  const [file, setFile] = useState<AnnotationsFile>(store.emptyFile());
  const [working, setWorking] = useState<WorkingAnnotation | null>(null);
  const [active, setActive] = useState<QuadKind>("outer");

  const nativeCanvas = useRef<HTMLCanvasElement | null>(null);
  const snapper = useMemo(() => new SnappingEngine(), []);
  const image = images[index] ?? null;

  // (re)load working state whenever the current image changes
  useEffect(() => {
    if (!image) {
      setWorking(null);
      return;
    }
    const existing = file.mockups[image.name];
    setWorking(
      existing
        ? { canvas: existing.canvas, outer: [...existing.outer_quad], inner: [...existing.inner_quad] }
        : emptyWorking(image.width, image.height)
    );
    setActive("outer");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [image?.name]);

  const addPoint = useCallback(
    (raw: Point) => {
      if (!working) return;
      const canvas = nativeCanvas.current;
      const snapped = canvas ? snapper.snap(canvas, raw) : raw;
      setWorking((w) => {
        if (!w) return w;
        const arr = active === "outer" ? w.outer : w.inner;
        if (arr.length >= 4) return w; // quad complete
        const nextArr = [...arr, snapped];
        const updated = active === "outer" ? { ...w, outer: nextArr } : { ...w, inner: nextArr };
        // auto-advance to inner once the outer quad is complete
        if (active === "outer" && nextArr.length === 4 && w.inner.length < 4) setActive("inner");
        return updated;
      });
    },
    [working, active, snapper]
  );

  const movePoint = useCallback((kind: QuadKind, i: number, p: Point) => {
    setWorking((w) => {
      if (!w) return w;
      const arr = [...(kind === "outer" ? w.outer : w.inner)];
      arr[i] = p;
      return kind === "outer" ? { ...w, outer: arr } : { ...w, inner: arr };
    });
  }, []);

  const undo = useCallback(() => {
    setWorking((w) => {
      if (!w) return w;
      const arr = active === "outer" ? w.outer : w.inner;
      if (arr.length === 0) return w;
      const nextArr = arr.slice(0, -1);
      return active === "outer" ? { ...w, outer: nextArr } : { ...w, inner: nextArr };
    });
  }, [active]);

  const commit = useCallback(() => {
    if (!image || !working || !store.isComplete(working)) return;
    setFile((f) => store.commit(f, image.name, working));
  }, [image, working]);

  const next = useCallback(() => setIndex((i) => Math.min(images.length - 1, i + 1)), [images.length]);
  const prev = useCallback(() => setIndex((i) => Math.max(0, i - 1)), []);
  const saveFile = useCallback(() => { void store.download(file); }, [file]);

  // resume from a saved annotations.json: load all entries, then refresh the
  // current image's working quads from it so they show up immediately (other
  // images load their quads as you navigate to them)
  const loadAnnotations = useCallback(
    async (f: File) => {
      try {
        const parsed = store.parse(await f.text());
        setFile(parsed);
        if (image) {
          const e = parsed.mockups[image.name];
          setWorking(
            e
              ? { canvas: e.canvas, outer: [...e.outer_quad], inner: [...e.inner_quad] }
              : emptyWorking(image.width, image.height)
          );
          setActive("outer");
        }
      } catch (err) {
        alert("Could not read annotations.json: " + (err as Error).message);
      }
    },
    [image]
  );

  // keyboard shortcuts
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        saveFile();
        return;
      }
      switch (e.key) {
        case "1": setActive("outer"); break;
        case "2": setActive("inner"); break;
        case "Backspace": e.preventDefault(); undo(); break;
        case "Enter": commit(); break;
        case " ": e.preventDefault(); commit(); next(); break;
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [saveFile, undo, commit, next]);

  return (
    <div className="app">
      <Toolbar
        imageName={image?.name ?? null}
        index={index}
        total={images.length}
        active={active}
        outerCount={working?.outer.length ?? 0}
        innerCount={working?.inner.length ?? 0}
        opencvReady={true}
        onLoadFolder={(fl) => { loadFiles(fl); setIndex(0); }}
        onLoadAnnotations={loadAnnotations}
        onSetActive={setActive}
        onPrev={prev}
        onNext={next}
        onCommit={commit}
        onSaveFile={saveFile}
      />

      {image && working ? (
        <ImageViewer
          image={image}
          onCanvasReady={(c) => (nativeCanvas.current = c)}
          onClickPoint={addPoint}
        >
          {({ zoom, toImage }) => (
            <PolygonEditor
              outer={working.outer}
              inner={working.inner}
              active={active}
              zoom={zoom}
              width={image.width}
              height={image.height}
              toImage={toImage}
              onMovePoint={movePoint}
            />
          )}
        </ImageViewer>
      ) : (
        <div className="empty">
          <p>Load a folder of mockup images to begin.</p>
          <p className="hint">
            1 outer · 2 inner · click 4 corners each · Backspace undo · Enter commit ·
            Space next · Ctrl+S save
          </p>
        </div>
      )}
    </div>
  );
}
