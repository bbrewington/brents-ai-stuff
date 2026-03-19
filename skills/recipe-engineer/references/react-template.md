# React Template Reference

This document provides the React component template for rendering TRN grids from recipe_grid JSON output. Read this before generating the artifact.

## JSON data format

The Python pipeline produces JSON with this structure:

```json
{
  "title": "Recipe Title",
  "servings": 4,
  "tables": [
    {
      "treeIndex": 0,
      "rows": 6,
      "cols": 4,
      "cells": [
        {
          "row": 0,
          "col": 0,
          "rowSpan": 1,
          "colSpan": 1,
          "borders": {
            "left": "sub-recipe",
            "right": "normal",
            "top": "sub-recipe",
            "bottom": "normal"
          },
          "type": "ingredient",
          "name": "cocoa powder",
          "amount": "6",
          "unit": "tsp"
        },
        {
          "row": 0,
          "col": 1,
          "rowSpan": 4,
          "colSpan": 1,
          "borders": { "left": "normal", "right": "normal", "top": "sub-recipe", "bottom": "normal" },
          "type": "step",
          "text": "heat until bubbling"
        }
      ]
    }
  ]
}
```

### Cell types

- **ingredient**: Has `name`, `amount`, `unit`. Rendered left-aligned with monospace amount.
- **step**: Has `text`. Rendered centered. This is the most common cell type for operations.
- **sub_recipe**: Has `outputNames` (array) and `showNames` (bool). Rendered as a header row for named sub-recipes.
- **reference**: Has `name`. Rendered as an italicized link-style reference to a sub-recipe defined elsewhere.

### Border types

Each cell has four border values:
- `"none"` - no border (cell appears outside the table visually)
- `"normal"` - thin solid line (internal grid lines)
- `"sub-recipe"` - thick solid line (outer border of recipe blocks)

These are computed by recipe_grid's `set_border_around_table` and must be rendered exactly.

### Spans

- `rowSpan` and `colSpan` come directly from the library's grid layout engine
- When a step merges multiple ingredient tracks, it gets a large `rowSpan`
- When a branch is shorter than others, its rightmost cells get extra `colSpan` via `right_pad_table`
- Cells "covered" by a span (ExtendedCells in the library) are omitted from the JSON - skip those grid positions during render

## Component structure

```jsx
import { useState, useMemo } from "react";

const RECIPE = { /* embedded JSON */ };

const BORDER = {
  none: "none",
  normal: "1px solid #94a3b8",
  "sub-recipe": "2px solid #1e293b",
};

function borderStyle(borders) {
  return {
    borderLeft: BORDER[borders.left],
    borderRight: BORDER[borders.right],
    borderTop: BORDER[borders.top],
    borderBottom: BORDER[borders.bottom],
  };
}

function RecipeTable({ table }) {
  // Build a set of covered positions (from rowSpan/colSpan)
  // Group cells by row, sort by column
  // Render <table> with <tr>s, skipping covered positions
  // Apply borderStyle to each <td>
  // Use rowSpan/colSpan attributes on <td> elements
}

export default function RecipeGrid() {
  return (
    <div>
      <h1>{RECIPE.title}</h1>
      {RECIPE.tables.map((table, i) => (
        <RecipeTable key={i} table={table} />
      ))}
    </div>
  );
}
```

## Styling rules

### Table
- `borderCollapse: "collapse"` is essential
- `width: "auto"` - let content determine width
- No outer border on the `<table>` element itself (borders are on individual cells)

### Ingredient cells
- Light background (#fafafa)
- Left-aligned
- Amount in monospace font, muted color
- Name in normal weight, dark color
- `whiteSpace: "nowrap"` to prevent wrapping

### Step cells
- White background
- Center-aligned
- Normal color, no bold (the grid structure provides emphasis)

### Sub-recipe header cells
- Slightly different background
- Bold text
- Center-aligned

### Reference cells
- Light blue tint (#f0f9ff)
- Italic
- Links to the referenced sub-recipe table

### Hover
- Highlight hovered cell with a light blue (#e0f2fe)
- Optional: trace dependency chain on hover

### Typography
- Use a serif font for the recipe title (Charter, Georgia, Palatino)
- Use system sans-serif for UI elements (badges, hints)
- Use monospace for ingredient amounts

## Multiple tables

Complex recipes with split sub-recipes produce multiple tables in the JSON. Render each as a separate `<table>` element with a small gap between them. The library handles splitting automatically when a sub-recipe is referenced from multiple places.

## Print styles

Add `@media print` to:
- Remove hover effects
- Ensure borders print cleanly (use solid black)
- Force white backgrounds
- Add the recipe title as header
