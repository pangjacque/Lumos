---
description: Understand everything — analyzes your codebase, Jupyter notebooks, and documentation to build a unified knowledge graph with cross-boundary import resolution. Use when you want to understand the complete project structure and connections.
---

# Lumos — Understand Everything

Perform a complete project analysis that builds a knowledge graph connecting code, notebooks, and documentation.

## Arguments

Parse `$ARGUMENTS` for optional flags:

| Flag | Effect |
|------|--------|
| `--code-only` | Only scan code files (skip notebooks and docs) |
| `--notebook-only` | Only scan notebooks (skip code and docs) |
| `--doc-only` | Only scan documentation (skip code and notebooks) |
| `--no-report` | Skip HTML report generation |
| `--rebuild` | Force full rebuild, ignore incremental cache |
| (no flags) | Scan everything: code + notebooks + docs + cross-references + report |

Examples:
```
/lumos:everything                    ← scan all
/lumos:everything --code-only        ← just the codebase
/lumos:everything --rebuild          ← force full re-scan
/lumos:everything --notebook-only    ← just notebooks
```

## Prerequisites

- Python 3.8+ installed
- `nbformat` package installed (`pip install nbformat`)

## Workflow

Execute these steps in order. The plugin's Python scripts are located in the `bin/` directory of this plugin.

### Step 1 — Check for incremental update

Unless `--rebuild` is specified:
Read `.lumos/metadata.json` if it exists. Compare the stored `last_commit` against the current `git rev-parse HEAD`. If they match and no files have changed, ask the user:
- **Full rebuild**: re-scan everything
- **Skip**: the graph is up to date

If metadata doesn't exist or commits differ, proceed with full scan.

### Step 2 — Project scan

Dispatch the **project-scanner** agent to discover all files and categorize them.

### Step 3 — Extraction

Based on flags, run the appropriate agents. If no flags, run all three concurrently:
1. **code-analyzer** — extract code structure from Python files (skip if `--notebook-only` or `--doc-only`)
2. **notebook-analyzer** — extract cell structure from Jupyter notebooks (skip if `--code-only` or `--doc-only`)
3. **doc-analyzer** — extract documentation structure from markdown files (skip if `--code-only` or `--notebook-only`)

### Step 4 — Import resolution

Skip if `--code-only` or `--doc-only` (cross-boundary requires both code and notebooks).

Dispatch the **import-resolver** agent to create cross-boundary edges linking notebook cells to codebase entities and doc references to code/notebooks.

### Step 5 — Graph merge and validation

Dispatch the **graph-reviewer** agent to merge all outputs into `knowledge-graph.json` and validate integrity.

### Step 6 — Report

Unless `--no-report` is specified, generate the HTML reports.

Tell the user:
1. Summary: X nodes, Y edges, Z cross-boundary connections
2. Open the interactive report: `.lumos/report-cards.html`
3. Use `/lumos:chat` to ask questions about the project
4. Use `/lumos:diff` to check impact of changes
