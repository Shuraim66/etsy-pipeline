// Loads a folder of images (via <input webkitdirectory>) into decoded
// HTMLImageElements, sorted by name. Object URLs are revoked on replacement.

import { useCallback, useRef, useState } from "react";
import type { LoadedImage } from "../types";

const IMAGE_RE = /\.(png|jpe?g|webp|bmp)$/i;

export function useImageFolder() {
  const [images, setImages] = useState<LoadedImage[]>([]);
  const [loading, setLoading] = useState(false);
  const urls = useRef<string[]>([]);

  const loadFiles = useCallback(async (fileList: FileList | File[]) => {
    setLoading(true);
    urls.current.forEach((u) => URL.revokeObjectURL(u));
    urls.current = [];

    const files = Array.from(fileList)
      .filter((f) => IMAGE_RE.test(f.name))
      .sort((a, b) => a.name.localeCompare(b.name));

    const loaded: LoadedImage[] = [];
    for (const f of files) {
      const url = URL.createObjectURL(f);
      urls.current.push(url);
      const el = await decode(url);
      loaded.push({
        name: f.name,
        url,
        width: el.naturalWidth,
        height: el.naturalHeight,
        element: el,
      });
    }
    setImages(loaded);
    setLoading(false);
  }, []);

  return { images, loading, loadFiles };
}

function decode(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = url;
  });
}
