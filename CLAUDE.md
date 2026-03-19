# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

This repository contains a Claude skill that converts unstructured recipes into **Tabular Recipe Notation (TRN)** - an engineering-style matrix grid (inspired by "Cooking for Engineers") that visualizes ingredient flow, parallel cooking steps, and ingredient merges.

## Setup

Use `uv` for all Python tooling (running scripts, managing dependencies, virtual environments).

First-time setup (creates venv and records dependency in `pyproject.toml`):

```bash
uv init --bare
uv add recipe_grid
```

## Running the Script

```bash
# Convert recipe markdown DSL to JSON
uv run skills/recipe-engineer/scripts/recipe_to_json.py input.md > output.json
```

## Key Files

- `skills/recipe-engineer/SKILL.md` - primary operational guide (DSL syntax, pipeline, gotchas)
- `skills/recipe-engineer/scripts/recipe_to_json.py` - core conversion engine
- `skills/recipe-engineer/references/react-template.md` - React component reference
