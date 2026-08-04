# Islamic Ornamentation - Implementation Status

This document describes which ornamental elements are available in the Barakah pipeline and how they're used across templates.

## Core Ornament Library (Pillow-based)

### Central Geometric Ornaments
- **medallion(size, color, line)** - Primary circular Islamic geometric rosette (shamsa), featuring beaded rim, radiating petals, and overlaid star polygons
  - Used in: `medallion_style.json`, `hero.json`, `mihrab.json`
  - Styles: Central focal point with cultural authenticity

### Architectural Ornaments
- **arch_frame(width, height, color, line, crown_ratio)** - Double-line pointed-arch frame (mihrab-style), open at bottom for titles
  - Used in: `mihrab.json`, `emblazon_style.json`, `signature_style.json`
  - Features: Architectural precision with decorative crown

### Corner Ornaments
- **corner_bracket(size, color, line)** - L-shaped double-line corner flourish (top-left), rotated/flipable for other corners
  - Used in: `corner_bracket.json`, `emblazon_style.json`
  - Style: Traditional Islamic corner calligraphy support

- **corner_floral(size, color, line)** - Small inward-growing floral sprig from corner
  - Used in: `botanical.json`, `emblazon_style.json`
  - Style: Organic corner flourishes

- **deco_corner(size, color, line)** - Angular stepped Art-Deco corner flourish
  - Used in: `decor_archivi.json`, `medallion_style.json`
  - Style: Modern architectural corners

### Floral and Crest Elements
- **floral_crest(width, height, color, line)** - Horizontal symmetric floral spray, center diamond with mirrored vines ending in buds
  - Used in: `botanical.json`, `emblazon_style.json`
  - Style: Delicate botanical accent element

### Divider Elements
- **divider(width, color, height, style)** - Horizontal dividers with multiple styles:
  - "diamond" - Diamond motif (recommended)
  - "rule" - Simple line
  - "bar" - Bold solid block
  - "double" - Two parallel lines
  - "chevron" - Chevron pattern
  - "leaf" - Leaf-style divider
  - Used across all templates for visual separation

### Frame Elements
- **draw_border(canvas, color, inset, gap, width, style)** - Dynamic frame drawing:
  - "single" - Single line frame
  - "double" - Double line frame
  - "rules_tb" - Top+bottom rules only
  - "stepped" - Decorative double frame with bevelled corners
  - Used in: Most templates for border treatment

### Modern and Minimal Options
- **geometric(size, color, line)** - Bold monochrome 8-point star emblem (modern + angular)
  - Used in: `geometric.json`, as accent element

## Template Usage Patterns

### Medallion Style
- Central element: `ornament: "medallion"` → calls `medallion(320, color, line=0.0012)`
- Corner treatment: `corner: {style: "deco"}` → uses `deco_corner`
- Layout: Zones with central positioning, medallion at focal point

### Emblazon Style  
- Architectural element: `arch_big` configuration → `arch_frame` implementation
- Corner treatment: `corner: {style: "bracket"}` → `corner_bracket`
- Additional decoration: Crests array for geometric and decorative corners

### Signature Style
- Architectural element: `arch_big` configuration with smaller dimensions
- Corner treatment: `corner: {style: "none"}` (clean minimalist)
- Divider: Chevron-style for transition elements

## Cultural Authenticity Features

1. **Procural Generation** - All ornaments are generated from geometry, not copied art
2. **License-Clean** - Original designs with no external dependencies
3. **Recolorable** - Full color palette integration across all ornament types
4. **High-Resolution** - Supersampled rendering with smooth downscaling via LANCZOS
5. **Traditional Motifs** - Islamic geometric patterns, arabesque, star polygons

## Integration Notes

- All ornaments render to transparent RGBA layers at supersampled resolution
- Line weights scale proportionally with canvas size
- Colors are integrated with the selected palette from `palettes.json`
- Ornament generation is consistent across all templates in the pipeline

## Extensions for New Styles

The ornament library can be extended for additional Islamic design styles:
- **Star patterns** - Enhanced star polygon variations
- **Arabesque vines** - More intricate flowing plant motifs
- **Architectural elements** - More complex geometric architectural forms
- **Surface decoration** - Tile, carpet, and manuscript-style patterns

All new templates should follow the established pattern of using the existing ornament library for consistency and maintainability.