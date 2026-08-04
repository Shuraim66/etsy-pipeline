// JSON persistence - build, serialize, download and parse annotations.json.
// Single responsibility: the on-disk schema. No React, no canvas.

import type {
  AnnotationsFile,
  MockupAnnotation,
  Quad,
  WorkingAnnotation,
} from "../types";

export function emptyFile(): AnnotationsFile {
  return { version: 1, mockups: {} };
}

export function isComplete(w: WorkingAnnotation): boolean {
  return w.outer.length === 4 && w.inner.length === 4;
}

/** Commit a completed working annotation into the file under `name`. */
export function commit(
  file: AnnotationsFile,
  name: string,
  w: WorkingAnnotation
): AnnotationsFile {
  if (!isComplete(w)) throw new Error("both quads need exactly 4 points");
  const entry: MockupAnnotation = {
    canvas: w.canvas,
    outer_quad: w.outer.slice(0, 4) as Quad,
    inner_quad: w.inner.slice(0, 4) as Quad,
  };
  return { ...file, mockups: { ...file.mockups, [name]: entry } };
}

export function serialize(file: AnnotationsFile): string {
  return JSON.stringify(file, null, 2);
}

export async function download(file: AnnotationsFile, filename = "annotations.json"): Promise<void> {
  const text = serialize(file);

  // Preferred: let the user choose where to save (e.g. straight into the repo).
  const picker = (window as any).showSaveFilePicker;
  if (typeof picker === "function") {
    try {
      const handle = await picker({
        suggestedName: filename,
        types: [{ description: "JSON", accept: { "application/json": [".json"] } }],
      });
      const writable = await handle.createWritable();
      await writable.write(text);
      await writable.close();
      return;
    } catch (e: any) {
      if (e?.name === "AbortError") return; // user cancelled
      // otherwise fall through to the classic download
    }
  }

  // Fallback: browser's default Downloads folder.
  const blob = new Blob([text], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function parse(text: string): AnnotationsFile {
  const raw = JSON.parse(text);
  if (raw?.version !== 1 || typeof raw.mockups !== "object") {
    throw new Error("not a valid annotations.json (version 1)");
  }
  return raw as AnnotationsFile;
}
