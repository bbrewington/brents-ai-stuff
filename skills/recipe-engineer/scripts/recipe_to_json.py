"""
recipe_to_json.py

Uses the recipe_grid library to parse a recipe in its markdown DSL format,
convert to a table, and output JSON suitable for the React TRN artifact.

Usage:
    python recipe_to_json.py input.md > output.json
    python recipe_to_json.py input.md --html > output.html
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


def cell_type_name(val) -> str:
    if isinstance(val, Ingredient):
        return "ingredient"
    elif isinstance(val, Step):
        return "step"
    elif isinstance(val, SubRecipe):
        return "sub_recipe"
    elif isinstance(val, Reference):
        return "reference"
    return "unknown"


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
                cell_data["type"] = "sub_recipe"
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


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python recipe_to_json.py input.md", file=sys.stderr)
        sys.exit(1)
    
    with open(sys.argv[1]) as f:
        md_text = f.read()
    
    data = parse_recipe_md(md_text)
    print(json.dumps(data, indent=2))
