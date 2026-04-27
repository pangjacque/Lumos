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

**IMPORTANT: Use the TodoWrite tool to show progress through each phase.** Create the full task list at the start, then update each task as you work through it. This gives the user a clear progress indicator.

At the start, create this todo list:

```
◻ Phase 1 — SCAN (discover project files)
◻ Phase 2 — CODE (extract codebase structure)
◻ Phase 3 — NOTEBOOKS (extract cell structure)
◻ Phase 4 — DOCS (extract documentation)
◻ Phase 5 — RESOLVE (cross-boundary imports)
◻ Phase 6 — MERGE (build knowledge graph)
◻ Phase 7 — REPORT (generate HTML reports)
```

Mark each task as `in_progress` when starting it and `completed` when done.

### Phase 1 — SCAN

Unless `--rebuild` is specified:
Read `.lumos/metadata.json` if it exists. Compare the stored `last_commit` against the current `git rev-parse HEAD`. If they match and no files have changed, ask the user:
- **Full rebuild**: re-scan everything
- **Skip**: the graph is up to date

If metadata doesn't exist or commits differ, proceed with full scan.

Dispatch the **project-scanner** agent to discover all files and categorize them.

### Phase 2 — CODE

Skip if `--notebook-only` or `--doc-only`.

Dispatch language-specific extractor agents in parallel based on what languages were detected in Phase 1 (`scan-result.json` → `languages` field). Currently supported:

- **code-analyzer** — Python (`.py`) — uses Python `ast`. Always dispatch if any Python files exist.
- **scala-analyzer** — Scala (`.scala`) — uses tree-sitter. Dispatch only if any `.scala` files exist.

If multiple languages are present, run the analyzers concurrently. Skip languages that have zero files in the scan.

### Phase 3 — NOTEBOOKS

Skip if `--code-only` or `--doc-only`.

Dispatch the **notebook-analyzer** agent to extract cell structure from Jupyter notebooks.

### Phase 4 — DOCS

Skip if `--code-only` or `--notebook-only`.

Dispatch the **doc-analyzer** agent to extract documentation structure from markdown files.

### Phase 5 — RESOLVE

Skip if `--code-only` or `--doc-only` (cross-boundary requires both code and notebooks).

Dispatch the **import-resolver** agent to create cross-boundary edges linking notebook cells to codebase entities and doc references to code/notebooks.

### Phase 6 — MERGE

Dispatch the **graph-reviewer** agent to merge all outputs into `knowledge-graph.json` and validate integrity.

### Phase 7 — REPORT

Unless `--no-report` is specified, generate the HTML reports.

### Final Summary

After all phases complete, read `.lumos/knowledge-graph.json` and present a summary like this:

```
Lumos Knowledge Graph

Project: <project name> — <one-line description from README or inferred>

Files analyzed: X
  code: N · notebooks: N · docs: N · config: N

Nodes: X
  file: N · class: N · function: N · notebook: N · cell: N · document: N · doc_section: N

Edges: X
  contains: N · imports: N · cell_flow: N · cell_data_flow: N
  cross_boundary_import: N · cross_boundary_call: N
  doc_references_code: N · doc_references_notebook: N

Notebooks: N total, M cells
  Cross-boundary connections: N (notebook cells → codebase)
  Data flow edges: N (variable dependencies between cells)
  Execution anomalies: list any notebooks with out-of-order or error cells

Documentation: N files
  Types: model_doc (N), data_dictionary (N), general (N)
  Code references found: N
  Notebook references found: N

Outputs at .lumos/:
  knowledge-graph.json (X KB)
  report-cards.html (hierarchy + notebook view)
  report-force.html (force graph view)
  metadata.json

Use /lumos:chat to ask questions about the project.
Use /lumos:diff to check impact of changes.
```

Read the actual stats from the knowledge graph JSON to fill in the numbers. Do NOT guess or make up numbers.
