// Toolbar - folder loading, mode toggle, navigation and save controls. Pure
// presentation; all actions are delegated to callbacks.

import type { QuadKind } from "../types";

interface Props {
  imageName: string | null;
  index: number;
  total: number;
  active: QuadKind;
  outerCount: number;
  innerCount: number;
  opencvReady: boolean;
  onLoadFolder: (files: FileList) => void;
  onLoadAnnotations: (file: File) => void;
  onSetActive: (k: QuadKind) => void;
  onPrev: () => void;
  onNext: () => void;
  onCommit: () => void;
  onSaveFile: () => void;
}

export function Toolbar(p: Props) {
  return (
    <div className="toolbar">
      <label className="btn">
        Load folder
        <input
          type="file"
          // @ts-expect-error non-standard but widely supported directory picker
          webkitdirectory=""
          directory=""
          multiple
          hidden
          onChange={(e) => e.target.files && p.onLoadFolder(e.target.files)}
        />
      </label>

      <label className="btn" title="Resume from a saved annotations.json to adjust frames">
        Load annotations
        <input
          type="file"
          accept="application/json,.json"
          hidden
          onChange={(e) => e.target.files?.[0] && p.onLoadAnnotations(e.target.files[0])}
        />
      </label>

      <div className="group">
        <button
          className={`btn ${p.active === "outer" ? "on outer" : ""}`}
          onClick={() => p.onSetActive("outer")}
          title="Annotate outer (1)"
        >
          Outer {p.outerCount}/4
        </button>
        <button
          className={`btn ${p.active === "inner" ? "on inner" : ""}`}
          onClick={() => p.onSetActive("inner")}
          title="Annotate inner (2)"
        >
          Inner {p.innerCount}/4
        </button>
      </div>

      <div className="group">
        <button className="btn" onClick={p.onPrev} disabled={p.index <= 0}>
          ‹
        </button>
        <span className="counter">
          {p.total ? p.index + 1 : 0} / {p.total}
        </span>
        <button className="btn" onClick={p.onNext} disabled={p.index >= p.total - 1}>
          ›
        </button>
      </div>

      <span className="name">{p.imageName ?? "no folder loaded"}</span>

      <div className="spacer" />

      <span className={`chip ${p.opencvReady ? "ok" : "warn"}`}>
        {p.opencvReady ? "snapping on" : "snapping off"}
      </span>
      <button className="btn" onClick={p.onCommit} title="Commit this image (Enter)">
        Commit
      </button>
      <button className="btn primary" onClick={p.onSaveFile} title="Download annotations.json (Ctrl+S)">
        Save file
      </button>
    </div>
  );
}
