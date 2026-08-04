# Render Engine and Ornament Integration Guide

This document explains how the three new ornamental styles integrate with the render engine and ornament library.

## Integration Architecture

The render pipeline uses `render.py` as the core engine, which:
- Reads template JSON configurations
- Calls ornament functions from `ornaments.py`
- Renders text elements using `arabic_text.py`
- Composes final images with mockups and proofs
- Exports PDF prints and other variants

## Ornament Library Integration

### Available Ornament Functions

The `ornaments.py` library provides the following procedural Islamic ornamental elements:

#### Central Geometric Ornaments
- **medallion(size, color, line)** - Primary circular Islamic rosette with beaded rim, radiating petals, and star polygons
  - Size: Integer pixel value (recommended: 300-400)
  - Color: RGB tuple or named color
  - Line: Float line weight (recommended: 0.004-0.006)

#### Architectural Ornaments  
- **arch_frame(width, height, color, line, crown_ratio)** - Pointed-arch frame for titles
  - Width/Height: Container dimensions
  - Color: RGB tuple or named color
  - Line: Float line weight (recommended: 0.004-0.006)

#### Corner Ornaments
- **corner_bracket(size, color, line)** - L-shaped corner flourish (top-left)
- **corner_floral(size, color, line)** - Small inward-growing floral sprig
- **deco_corner(size, color, line)** - Angular stepped Art-Deco corner

#### Floral and Crest Elements
- **floral_crest(width, height, color, line)** - Horizontal floral spray with center diamond

#### Divider Elements
- **divider(width, color, height, style)** - Various divider styles:
  - "diamond" - Diamond motif (recommended)
  - "chevron" - Chevron pattern
  - "leaf" - Leaf-style divider
  - "bar" - Bold solid block

### Template to Ornament Mapping

#### Medallion Style
- Central ornament: Calls `medallion(320, color, line=0.0010)`
- Corner treatment: Uses `deco_corner` for angular corners
- Integration: Central placement within zones[0] region
- Color integration: Uses palette's "accent" color for medallion

#### Emblazon Style
- Architectural element: Calls `arch_frame(width, height, color, line, crown_ratio)`
- Corner treatment: Uses `corner_bracket` for heraldic corners  
- Integration: arch_big region maps to arch_frame with specific dimensions
- Additional elements: Creates decorative frames and architectural borders

#### Signature Style
- Architectural element: Smaller arch_frame for elegant presentation
- Corner treatment: Minimal `corner: {style: "none"}` for clean look
- Integration: Balanced composition with arch_big region
- Dividers: Uses chevron-style for modern-traditional blend

## Render Engine Integration

### Template Structure Requirements

Each template must define:

1. **Canvas Dimensions**:
   ```json
   "canvas": { "w": 3508, "h": 4961 }  // 2000px x 3000px at 300 DPI
   ```

2. **Palette Selection**:
   ```json
   "palette": "emerald_gold"  // From palettes.json
   ```

3. **Ornament Configuration**:
   ```json
   "ornament": "medallion",  // Calls appropriate function
   "border": { "style": "double", "color": "accent" }
   "corner": { "style": "deco", "size": 0.16 }
   ```

4. **Layout Zones**:
   ```json
   "zones": [
     { "region": [x1, y1, x2, y2], "valign": "center", "blocks": [...] }
   ]
   ```

5. **Font Specifications**:
   ```json
   "fonts": {
     "arabic_name": { "file": "Amiri-Bold.ttf" },
     "latin_name": { "file": "Cinzel[wght].ttf", "weight": 500 }
   }
   ```

### Color System Integration

Templates use the 9-palette system from `palettes.json`:

- **emerald_gold** - Primary palette with gold accents on deep green
- **navy_gold** - Gold accents on navy blue backgrounds  
- **black_gold** - Gold accents on deep black
- **ivory_gold** - Gold accents on ivory cream
- **terracotta** - Earthy gold on warm terracotta
- **sage** - Soft gold on sage green
- **burgundy_gold** - Rich gold on burgundy
- **dusty_blue** - Warm gold on dusty blue
- **blush** - Soft rose with warm accents

Each palette defines:
- `accent`: Gold color for primary elements
- `body`: Main text color
- `muted`: Secondary text color
- `bgFrom/To`: Background gradients
- `banner/bannerText`: Split panel styling
- `pageFrom/To`: Light panel backgrounds
- `vignette`: Edge darkening for dark canvases

## Testing and Validation

### Pipeline Integration

The templates integrate with:

1. **render.py** - Core rendering engine
   - Processes template JSON
   - Calls ornament functions
   - Renders text elements
   - Composes final output

2. **arabic_text.py** - Arabic text handling
   - Proper harakat rendering with libraqm
   - Fallback for systems without HarfBuzz
   - Cultural correctness validation

3. **generate.py** - Batch processing driver
   - Reads CSV input
   - Applies human verification gates
   - Generates mockups and proofs
   - Handles size variants and Pinterest pins

### Validation Checklist

For each new template, validate:

- ✅ JSON syntax and structure
- ✅ Required fields present (canvas, palette, fonts, zones)
- ✅ Ornament functions exist in ornaments.py
- ✅ Color references match palette keys
- ✅ Font files exist in assets/fonts/
- ✅ Integration tested with render.py
- ✅ Mockup generation works
- ✅ PDF export functions correctly
- ✅ All pipeline components integrate properly

## Style Matrix

The new styles expand the existing portfolio:

| Style Type | Existing Examples | New Examples | Aesthetic |
|------------|-------------------|--------------|-----------|
| Hero/Portrait | hero, mihrab, split_panel | signature_style | Central focus on name |
| Geometric | geometric, zellige patterns | medallion_style | Pure ornamental geometry |
| Architectural | arch, mihrab | emblazon_style | Architectural framing |
| Botanical | botanical, floral | signature_style | Organic blending |

## Usage Examples

### Generating with Styles

```bash
# Generate all three new styles
python3 generate.py \
  --input data/names.csv \
  --styles medallion_style,emblazon_style,signature_style \
  --proof --sizes --pins

# Style variations using different palettes
python3 generate.py \
  --styles hero_black,hero_navy,hero_ivory \
  --input data/names.csv
```

### Template Extension

Each style can be extended with palette variants:
- `medallion_emerald.json` - Uses emerald_gold palette
- `medallion_black.json` - Uses black_gold palette
- `medallion_navy.json` - Uses navy_gold palette

## Limitations and Considerations

1. **Arabic Correctness** - All Arabic must be pre-verified Unicode
2. **File Dependencies** - Fonts and ornaments must be present
3. **Performance** - Complex ornaments may affect rendering speed
4. **Cultural Accuracy** - Ornament patterns should respect Islamic geometric principles

## Future Extensions

The ornament library and template system support:

1. **New Ornament Types**:
   - Star polygons with varying complexity
   - Arabesque vine patterns
   - Calligraphic ornamental borders
   - Surface tiling motifs

2. **Advanced Styles**:
   - Fusion styles combining multiple ornament types
   - Dynamic ornament generation based on input data
   - Responsive layouts for different text lengths

3. **Integration Enhancements**:
   - Real-time ornament preview
   - Automated style recommendations
   - Cultural correctness validation tools

## Conclusion

The three new ornamental styles successfully integrate with the existing Barakah pipeline, providing:

- **Cultural Authenticity** - Traditional Islamic geometric and architectural elements
- **Visual Distinction** - Three unique aesthetic approaches
- **Pipeline Compatibility** - Seamless integration with render, arabic_text, and generate systems
- **Scalable Design** - Foundation for future style variations and ornament extensions

These styles expand the portfolio while maintaining the high standards of correctness, aesthetics, and technical excellence that define the Barakah name-print generation pipeline.