"""
recipe_render.py

Uses the recipe_grid library to parse a recipe in its markdown DSL format,
convert to a table, and output JSON or a standalone HTML page.

Usage:
    python recipe_render.py input.md > output.json
    python recipe_render.py input.md --html > output.html
"""

import json
import sys
from fractions import Fraction
from typing import Union

from recipe_grid.markdown import compile_markdown
from recipe_grid.renderer.recipe_to_table import recipe_tree_to_table
from recipe_grid.renderer.table import Cell, ExtendedCell, BorderType
from recipe_grid.recipe import Ingredient, Step, SubRecipe, Reference


def fraction_to_str(val: Union[int, float, Fraction]) -> str:
    if isinstance(val, Fraction):
        if val.denominator == 1:
            return str(val.numerator)
        whole = val.numerator // val.denominator
        remainder = val - whole
        if whole > 0:
            return f"{whole} {remainder.numerator}/{remainder.denominator}"
        return f"{val.numerator}/{val.denominator}"
    if isinstance(val, float) and val == int(val):
        return str(int(val))
    return str(val)


def border_name(bt: BorderType) -> str:
    return bt.name.replace("_", "-")  # none, normal, sub-recipe


def table_to_json(table, tree_index=0):
    """Convert a recipe_grid Table into a JSON-serializable dict."""
    rows = table.rows
    cols = table.columns
    
    cells = []
    for r in range(rows):
        for c in range(cols):
            entry = table[r, c]
            if isinstance(entry, ExtendedCell):
                continue  # skip - covered by a spanning cell
            
            cell = entry  # it's a Cell
            val = cell.value
            
            cell_data = {
                "row": r,
                "col": c,
                "rowSpan": cell.rows,
                "colSpan": cell.columns,
                "borders": {
                    "left": border_name(cell.border_left),
                    "right": border_name(cell.border_right),
                    "top": border_name(cell.border_top),
                    "bottom": border_name(cell.border_bottom),
                },
            }
            
            if isinstance(val, Ingredient):
                cell_data["type"] = "ingredient"
                cell_data["name"] = str(val.description)
                if val.quantity:
                    cell_data["amount"] = fraction_to_str(val.quantity.value)
                    cell_data["unit"] = val.quantity.unit or ""
                else:
                    cell_data["amount"] = ""
                    cell_data["unit"] = ""
            elif isinstance(val, Step):
                cell_data["type"] = "step"
                cell_data["text"] = str(val.description)
            elif isinstance(val, SubRecipe):
                cell_data["type"] = "sub-recipe"
                cell_data["outputNames"] = [str(n) for n in val.output_names]
                cell_data["showNames"] = val.show_output_names
            elif isinstance(val, Reference):
                cell_data["type"] = "reference"
                cell_data["name"] = str(val.sub_recipe.output_names[val.output_index])
            else:
                cell_data["type"] = "unknown"
            
            cells.append(cell_data)
    
    return {
        "treeIndex": tree_index,
        "rows": rows,
        "cols": cols,
        "cells": cells,
    }


def parse_recipe_md(md_text: str) -> dict:
    """Parse recipe markdown and return full JSON structure."""
    result = compile_markdown(md_text)

    tables = []
    for block_idx, recipe_block in enumerate(result.recipes):
        for recipe in recipe_block:
            for tree_idx, tree in enumerate(recipe.recipe_trees):
                table = recipe_tree_to_table(tree)
                tables.append(table_to_json(table, tree_idx))

    return {
        "title": result.title or "",
        "servings": result.servings,
        "tables": tables,
    }


_BORDER_CSS = {
    "none": "none",
    "normal": "1px solid #94a3b8",
    "sub-recipe": "2px solid #1e293b",
}

_HTML_STYLE = """
body { font-family: system-ui, sans-serif; padding: 24px 32px; }
h1 { font-family: Georgia, Charter, Palatino, serif; font-size: 26px; margin-bottom: 4px; color: #0f172a; }
.meta { color: #64748b; font-size: 13px; margin-bottom: 20px; }
.trn-wrap { overflow-x: auto; margin-bottom: 24px; }
table { border-collapse: collapse; }
td { padding: 6px 10px; font-size: 13px; vertical-align: middle; }
td.ingredient { background: #fafafa; text-align: left; white-space: nowrap; }
td.step { background: #fff; text-align: center; }
td.sub-recipe { background: #f1f5f9; text-align: center; font-weight: bold; }
td.reference { background: #f0f9ff; text-align: center; font-style: italic; color: #0284c7; }
.amount { font-family: monospace; color: #64748b; margin-right: 4px; }
.hint { font-size: 11px; color: #94a3b8; margin-top: 8px; }
@media print {
  td { border-color: #000 !important; }
  td.ingredient { background: #fff !important; }
  td.sub-recipe { background: #eee !important; }
}
"""


def _td_style(borders: dict) -> str:
    parts = []
    for side in ("left", "right", "top", "bottom"):
        css = _BORDER_CSS[borders[side]]
        if css != "none":
            parts.append(f"border-{side}: {css}")
    return "; ".join(parts)


def _escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def table_to_html(table_data: dict) -> str:
    """Render a single TRN table dict (from table_to_json) as an HTML <table>."""
    rows = table_data["rows"]

    # Group cells by row, build covered-position set
    by_row: dict[int, list] = {}
    covered: set = set()
    for cell in table_data["cells"]:
        by_row.setdefault(cell["row"], []).append(cell)
        for r in range(cell["row"], cell["row"] + cell["rowSpan"]):
            for c in range(cell["col"], cell["col"] + cell["colSpan"]):
                if r != cell["row"] or c != cell["col"]:
                    covered.add((r, c))

    lines = ["<table>"]
    for r in range(rows):
        row_cells = sorted(by_row.get(r, []), key=lambda c: c["col"])
        if not row_cells:
            continue
        lines.append("  <tr>")
        for cell in row_cells:
            typ = cell["type"]
            style = _td_style(cell["borders"])
            attrs = f'class="{typ}" style="{style}"'
            if cell["rowSpan"] > 1:
                attrs += f' rowspan="{cell["rowSpan"]}"'
            if cell["colSpan"] > 1:
                attrs += f' colspan="{cell["colSpan"]}"'

            if typ == "ingredient":
                amount = _escape(cell["amount"])
                unit = _escape(cell["unit"])
                name = _escape(cell["name"])
                amount_str = f'<span class="amount">{amount}{" " + unit if unit else ""}</span>' if amount else ""
                inner = f"{amount_str}{name}"
            elif typ == "step":
                inner = _escape(cell["text"])
            elif typ == "sub-recipe":
                inner = _escape(", ".join(cell.get("outputNames", [])))
            elif typ == "reference":
                inner = f'<em>{_escape(cell["name"])}</em>'
            else:
                inner = ""

            lines.append(f'    <td {attrs}>{inner}</td>')
        lines.append("  </tr>")
    lines.append("</table>")
    return "\n".join(lines)


def recipe_to_html(data: dict) -> str:
    """Render full recipe data dict as a standalone HTML page."""
    title = _escape(data["title"])
    servings = data.get("servings")
    meta = f"Serves {servings}" if servings else ""

    tables_html = "\n".join(
        f'<div class="trn-wrap">{table_to_html(t)}</div>'
        for t in data["tables"]
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{_HTML_STYLE}</style>
</head>
<body>
<h1>{title}</h1>
{f'<p class="meta">{meta}</p>' if meta else ""}
{tables_html}
<p class="hint">Read left → right. Ingredients enter from the left and merge into the final dish on the right.</p>
</body>
</html>"""


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python recipe_to_json.py input.md [--html]", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        md_text = f.read()

    data = parse_recipe_md(md_text)

    if "--html" in sys.argv:
        print(recipe_to_html(data))
    else:
        print(json.dumps(data, indent=2))
