# Islamic Name-Print Templates

This directory contains JSON configuration files for generating Islamic name-print designs.

## Available Styles

### Built-in Styles
- **hero** - Oversized Arabic name as artwork (reference style)
- **mihrab** - Name inside architectural arch
- **split_panel** - Top banner, content on light below
- **botanical** - Organic floral top spray with corner sprigs
- **aquarelle** - Watercolour aura with pastel halos
- **geometric** - Modern monochrome 8-point star emblem

### New Ornamental Styles

#### 1. medallion_style
- **Description**: Ornate geometric rosette with cultural authenticity
- **Ornament**: Central medallion/rosette
- **Palette**: emerald_gold
- **Features**: Circular Islamic geometric medallion, intricate arabesque patterns
- **Output**: Premium archival-style name presentation

#### 2. emblazon_style  
- **Description**: Architectural heraldic emblazonment with Islamic mihrab
- **Ornament**: Pointed-arch frame with heraldic elements
- **Palette**: navy_gold
- **Features**: Islamic mihrab arch, decorative linework, shield-like elements
- **Output**: Authoritative heraldic-style presentation

#### 3. signature_style
- **Description**: Mahal style with rich devotional sacred geometry
- **Ornament**: Architectural arches with floral/crested elements
- **Palette**: black_gold
- **Features**: Devotional sacred geometry, intricate patterns, spiritual focus
- **Output**: Elegant signature-style presentation

## Integration

All templates integrate with:
- `render.py` - Rendering engine
- `ornaments.py` - Procedural ornament generation  
- `arabic_text.py` - Arabic text handling
- Pipeline's verification and rendering system

Each template defines:
- Canvas dimensions
- Color palette selection
- Layout zones and positioning
- Font specifications
- Border and corner styles
- Divider styles
- Ornamentation

## Usage

Templates are used by the `generate.py` script:

```bash
python3 generate.py --input data/names.csv --styles medallion_style,emblazon_style,signature_style
```

## Style Variations

The three new styles provide additional aesthetic options alongside the existing five:
- **hero/mihrab/split_panel** - Contemporary design language
- **botanical/aquarelle** - Organic, artistic expressions
- **medallion_style/emblazon_style/signature_style** - Ornate, traditional aesthetics

This expands the portfolio while maintaining design coherence.