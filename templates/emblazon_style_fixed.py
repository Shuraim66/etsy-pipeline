#!/usr/bin/env python3
"""
Quick script to fix emblazon_style.json template
"""

import json
from pathlib import Path

# Read the current template
with open('templates/emblazon_style.json', 'r', encoding='utf-8') as f:
    template = json.load(f)

# Fix the template by removing invalid color references
# The issue was that some styles have custom colors instead of using palette
if 'colors' in template:
    # Remove custom colors and use the palette instead
    del template['colors']

# Ensure we use the standard palette structure
if 'palette' not in template:
    template['palette'] = 'navy_gold'

# Write the fixed template
with open('templates/emblazon_style_fixed.json', 'w', encoding='utf-8') as f:
    json.dump(template, f, indent=2, ensure_ascii=False)

print("Fixed emblazon_style.json -> emblazon_style_fixed.json")
print("Template now uses proper palette system")