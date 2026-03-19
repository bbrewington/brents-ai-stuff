---
name: recipe-engineer
description: Convert unstructured recipe data into Cooking for Engineers-style Tabular Recipe Notation (TRN) grids. Use this skill whenever a user pastes, uploads, or links to a recipe and wants it converted to an engineering-style matrix/grid format, or when they mention "Cooking for Engineers", "recipe table", "recipe grid", "TRN", "tabular recipe", or want to see which cooking steps can be parallelized. Also triggers when a user asks to "engineer" or "optimize" a recipe's workflow, or when they want a visual overview of a recipe's structure. Handles pasted text from articles, uploaded files (HTML, PDF, text), and URLs. Produces both an interactive React TRN matrix artifact AND Claude's built-in recipe widget.
---

# Recipe Engineer

Convert unstructured recipes into Cooking for Engineers-style Tabular Recipe Notation (TRN) - a matrix visualization showing how ingredients flow through preparation steps, merge together, and become the final dish.

## Architecture

This skill uses the `recipe_grid` Python library (v2, from github.com/mossblaser/recipe_grid) as the core engine. The pipeline is:

```
Raw recipe (pasted text / URL / file)
  -> Claude translates into recipe_grid markdown DSL
  -> recipe_grid parses and builds Table objects (Python)
  -> scripts/recipe_to_json.py serializes to JSON
  -> React artifact renders the TRN grid with correct spans + borders
  -> recipe_display_v0 widget provides a cooking-focused companion view
```

The recipe_grid library handles all the hard layout work: right-padding shorter branches, computing cell spans, assigning border types (none/normal/sub-recipe). We do NOT reimplement grid layout logic ourselves.

## Setup

Before first use, install the library:

```bash
pip install recipe_grid
```

> If your project uses `uv`, follow the setup in your project's CLAUDE.md instead.

## DSL Gotchas

- **Step names with commas must be quoted**: `"sear until golden, 5 min"(...)` - unquoted commas are parsed as argument separators
- **No trailing period on units**: write `1 Tbsp olive oil` not `1 Tbsp. olive oil` - the period leaks into the ingredient `name` field

## Step 1: Extract recipe content from the input

### Pasted text
The user pastes raw recipe text from an article or blog. Extract the title, ingredient list, and instructions.

### Uploaded files
The user will provide a file path (e.g. `'/Users/you/Downloads/recipe.pdf'`). Read it directly using the file path. For HTML files, look for schema.org Recipe JSON-LD first. For PDFs, extract text. For markdown/text, read directly.

### URLs
Use `web_fetch` to retrieve the page. Look for JSON-LD `@type: Recipe` structured data first, then parse visible content.

## Step 2: Translate into recipe_grid markdown DSL

This is Claude's primary job. Take the extracted recipe content and convert it into the recipe_grid DSL format. The DSL is embedded in markdown as indented blocks.

### DSL syntax reference

The full syntax is documented at https://mossblaser.github.io/recipe_grid/tutorial.html. Key patterns:

**Basic structure**: Steps wrap their inputs in parentheses.
```
step_name(input1, input2, input3)
```

**Nesting**: Steps can contain other steps, forming the tree.
```
bake(
    layer(
        simmer(sauce_ingredients),
        boiled_noodles
    )
)
```

**Ingredients with quantities**: Written naturally.
```
6 tsp of cocoa powder
200g of chocolate
1/2 cup of butter
1 onion
```

**Listing ingredients up front**: You can list ingredients first, then reference them by name in the recipe block. This is the preferred approach for complex recipes.
```
    400g of chopped tomatoes
    1 tsp of mixed herbs
    1 onion, finely chopped, fried

    top(
        boil down(chopped tomatoes, mixed herbs, onion),
        grated(200g mozzarella),
        1 pizza base,
    )
```

Note: When listing ingredients up front, prep steps after commas (e.g., "finely chopped, fried") become operations in the grid automatically.

**Named sub-recipes** (with `=` or `:=`):
```
pizza sauce = boil down(
    400g chopped tomatoes,
    1 tsp mixed herbs,
    fried(finely chopped(1 onion)),
)

top(
    grated(200g mozzarella),
    pizza sauce,
    1 pizza base,
)
```

Use `:=` instead of `=` to make the sub-recipe visually highlighted with a header row in the grid.

**Splitting ingredients**: When part of a sub-recipe is used in multiple places:
```
tomato sauce = boil down(400g chopped tomatoes, spices)

bake(
    pour over(
        fill(
            simmer(chicken, 2/3 of the tomato sauce),
            tortilla wraps,
        ),
        remaining tomato sauce,
        grated cheese,
    )
)
```

**Quoted names**: If a step or ingredient name contains special characters, quote it:
```
"fry (don't let it burn)"(1 can of spam)
```

**Scalable numbers in steps**: Wrap numbers that should scale with servings in curly braces:
```
divide into {4} patties(mash together(450g minced beef, 1 onion))
```

### Title and servings

The markdown document title can include serving info:
```
Meat Lasagna for 8
==================
```

### Translation guidelines

When converting a raw recipe to the DSL:

1. **Identify the tree structure**: Read the instructions and figure out the dependency graph. What can happen in parallel? Where do things merge?

2. **Prep steps matter**: "1 onion, diced" should become either:
   - An ingredient listed up front with prep: `1 onion, diced`
   - Or inline: `diced(1 onion)`

3. **Group parallel tracks**: If the recipe says "while the pasta boils, make the sauce" - those are independent branches that merge at the end.

4. **Sequential additions are nested**: "Add tomatoes, then herbs, then simmer" becomes:
   ```
   simmer(add herbs(add tomatoes(base)))
   ```
   Or more readably with ingredient listing.

5. **Use sub-recipes for complex recipes**: If there are clearly named components (crust, filling, sauce), use named sub-recipes with `=` or `:=`.

6. **Preserve the cook's language**: Use the recipe's own words for step descriptions where possible. "Fold gently" is better than "combine".

7. **Model oven preheating (and similar appliance prep) as a parallel row**: Treat the oven as a pseudo-ingredient with a preheat step that merges at the baking/roasting step. This ensures it appears in the grid at the correct column - aligned with when the recipe says to start preheating, not buried or omitted.

   - Use `oven` as the ingredient name (no quantity needed - recipe_grid renders it with a blank amount)
   - Wrap it in a descriptive step: `"preheat to 375°F"(oven)`
   - Make that step an input to the baking/roasting step alongside the other inputs

   The column position follows naturally from tree depth: if preheat is a direct input to `bake(...)`, it appears in the column immediately before bake - which is correct when the recipe says "preheat while you prepare the other components". If the recipe says to preheat earlier (e.g., "preheat first, before any prep"), nest it deeper to push it left:
   ```
   bake(
       ...(other prep steps),
       "preheat to 375°F"(oven)   ← appears at same column as other bake inputs (parallel)
   )
   ```

   Example - recipe says "preheat oven while searing the chicken, then bake":
   ```
   bake at 375°F for 30 min(
       "return to skillet and add sauce"(
           "sear until golden, 5 min per side"(seasoned chicken),
           cream sauce,
       ),
       "preheat to 375°F"(oven),
   )
   ```
   This puts the preheat row in the same column as the sauce-making, parallel to searing - exactly where the recipe says to do it.

## Step 3: Run the recipe_grid pipeline

Once you have the DSL markdown, run the Python pipeline:

```python
import json
import sys
sys.path.insert(0, '<skill_dir>/scripts')  # skill_dir = directory containing this SKILL.md
from recipe_to_json import parse_recipe_md

md_text = """
Recipe Title
============

Description text here.

    # ingredient list and recipe DSL here
"""

data = parse_recipe_md(md_text)
# data has: { title, servings, tables: [{ rows, cols, cells: [...] }] }
```

The `recipe_to_json.py` script (in `scripts/`) handles:
- Parsing the markdown via `recipe_grid.markdown.compile_markdown`
- Converting each recipe tree to a table via `recipe_grid.renderer.recipe_to_table.recipe_tree_to_table`
- Serializing the table cells with their types, spans, and border info to JSON

### Error handling

If the DSL has syntax errors, `compile_markdown` will raise exceptions. Common issues:
- Unmatched parentheses
- Referencing an ingredient name that doesn't match the listed name exactly
- Forward references to sub-recipes (not allowed - define before use)

If parsing fails, show the error to the user and offer to fix the DSL.

## Step 4: Generate the React artifact

Create a `.jsx` file that embeds the JSON data and renders the TRN grid. Read `references/react-template.md` for the full component template.

Key rendering rules (all handled by the template):
- Use `border-collapse: collapse` on the table
- Map border types from the JSON: `none` -> no border, `normal` -> thin solid, `sub-recipe` -> thick solid
- Respect `rowSpan` and `colSpan` exactly as provided by recipe_grid (this is what creates the visual merge structure)
- Ingredient cells: left-aligned, show amount + unit + name
- Step cells: center-aligned
- Skip ExtendedCell positions (cells covered by spans)

## Step 5: Generate the recipe widget

Also produce a `recipe_display_v0` widget call for the cooking-focused view. Extract from the parsed data:

- **ingredients**: Each ingredient from the JSON, with an id like `"0001"`, `"0002"`, etc.
- **steps**: Walk the recipe tree depth-first. Each Step becomes a step in the widget. Reference ingredients using `{id}` syntax.
- **timer_seconds**: Parse duration hints from step descriptions (e.g., "simmer 20 min" -> 1200, "bake 45 min at 375F" -> 2700).
- **base_servings**: From the recipe's servings field if available.

**Important**: Only use `{id}` references for ingredients that have a meaningful numeric amount. "To taste" ingredients (salt, pepper, etc.) with amount `0` or empty will not render properly in the widget - the raw `{0012}` token will show through instead of the ingredient name. For these, write the ingredient name directly in the step text (e.g., "season with salt and pepper to taste") instead of using a `{id}` reference.

## Presentation

Always produce both outputs in this order:
1. **React artifact** (the TRN grid) - present via `present_files`
2. **Recipe widget** - call `recipe_display_v0` tool

The artifact is the "engineering" view showing the process structure. The widget is the "cooking" view with timers and servings adjustment.
