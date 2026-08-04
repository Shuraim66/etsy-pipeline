# Mockup pipeline

Data-driven, perspective-correct mockup rendering. Two pieces:

1. **`mockup_render/`** — the Python renderer (Pillow + OpenCV).
2. **`mockup-annotator/`** — a React/Vite/TS tool to draw the frame quads.

Together: annotate a frame's corners → get `config.json` → render any artwork
into it with a perspective transform. No coordinates live in code.

---

## 1. Renderer (`mockup_render/`)

Every mockup is a **self-contained directory**:

```
mockups/<name>/
    background.webp   # required
    frame.png         # optional — moulding drawn in front of the artwork
    shadow.png        # optional — multiplied over the composite
    glare.png         # optional — screened over the composite
    config.json       # required — geometry + effects
```

Missing optional layers are skipped automatically. The five filenames above are
the *only* hardcoded strings in the pipeline.

### Public API

```python
from mockup_render import render_mockup
render_mockup(artwork_path, mockup_directory, output_path)   # writes .png and .jpg
```

CLI:

```bash
python -m mockup_render artwork.png mockups/m1_black_hung out/result.png
python -m mockup_render artwork.png mockups/m1 mockups/m2 out/   # many -> a dir
```

### Pipeline (fixed order)

```
background → warp artwork to inner_quad → clip → multiply shadow
          → screen glare → frame overlay → save
```

Artwork is always placed with a **perspective transform solved from the four
inner-quad points** — never x/y/width/height. Whether a mockup is perspective
is *derived* (`outer_quad` is not an axis-aligned rectangle), never stored.

### Classes (one responsibility each)

| Class | Responsibility |
|-------|----------------|
| `MockupConfig` | load + validate `config.json`, resolve asset paths, derive `is_perspective` |
| `PerspectiveTransformer` | fit artwork to a quad's aspect (preserving ratio) and warp it (OpenCV homography) |
| `LayerComposer` | alpha-over + `multiply`/`screen` blends, clip-to-mask |
| `MockupRenderer` | sequence the stages and do file I/O |

New stages (paper grain, texture, canvas weave, …) are added as extra
`LayerComposer.over(...)` calls in `MockupRenderer.render` — the maths never
change. New geometry features (smart crop, auto inner_quad, thickness
estimation) go in `PerspectiveTransformer`.

### `config.json` schema (version 1)

```json
{
  "version": 1,
  "canvas": { "width": 2000, "height": 2500 },
  "frame": { "style": "hung", "color": "black", "has_mat": false, "glass": true },
  "outer_quad": [[360,457],[1640,449],[1637,2241],[362,2241]],
  "inner_quad": [[369,466],[1631,458],[1628,2232],[371,2232]],
  "effects": {
    "shadow": { "enabled": true, "opacity": 0.45, "blend_mode": "multiply" },
    "glare":  { "enabled": true, "opacity": 0.18, "blend_mode": "screen" }
  },
  "render": { "allow_crop": false, "default_padding": 8, "interpolation": "lanczos" }
}
```

- `frame.*` is descriptive metadata only — no behaviour is derived from it.
- `render.default_padding` grows the opening outward a few px so the print tucks
  under the frame lip (no grey gap).
- `render.allow_crop` false = contain (whole artwork), true = cover (fill quad).

The current 16 shop frames are already migrated (`migrate_mockups.py`) — they
are single photographs, so they ship with just `background.webp` + `config.json`.

---

## 2. Annotator (`mockup-annotator/`)

React + Vite + TypeScript + OpenCV.js. Draw the two quads on each frame photo
and export `annotations.json` (same geometry the renderer's config uses).

```bash
cd mockup-annotator
npm install
npm run dev        # http://localhost:5178
```

### Workflow

1. **Load folder** of frame images.
2. Press **1** (outer) and click the four outer corners, then **2** (inner) and
   click the four inner corners. Each click **snaps** to the nearest frame
   corner (Canny + probabilistic Hough → line intersection closest to the click;
   falls back to the raw click if OpenCV is unavailable or no corner is found).
3. **Drag** any placed point to fine-tune.
4. **Enter** commits the image; **Space** commits + advances; **Ctrl+S**
   downloads `annotations.json`.

Outer is drawn blue, inner green.

### Shortcuts

| Key | Action |
|-----|--------|
| `1` | annotate outer |
| `2` | annotate inner |
| `Backspace` | undo last point |
| `Enter` | commit current image |
| `Space` | commit + next image |
| `Ctrl/Cmd+S` | download `annotations.json` |

Wheel = zoom to cursor, drag background = pan.

### Modules

- `components/ImageViewer` — native-res canvas, zoom/pan, screen↔image coords.
- `components/PolygonEditor` — draws + drags the quads (SVG, image space).
- `engine/snapping` (`SnappingEngine`) — Canny + Hough corner snapping.
- `persistence/annotations` — the `annotations.json` schema + save/load.

### Output schema

```json
{
  "version": 1,
  "mockups": {
    "<image_name>": {
      "canvas": [width, height],
      "outer_quad": [[x,y],[x,y],[x,y],[x,y]],
      "inner_quad": [[x,y],[x,y],[x,y],[x,y]]
    }
  }
}
```

Each entry maps directly onto a renderer `config.json` (`canvas`, `outer_quad`,
`inner_quad`); add `frame`, `effects`, `render` to finish a mockup.
