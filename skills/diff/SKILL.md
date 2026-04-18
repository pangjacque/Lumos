---
description: Impact analysis — shows what notebooks, docs, and code are affected by recent changes. Requires a prior /lumos:scan. Use before committing to understand blast radius.
---

# Lumos Diff — Impact Analysis

Analyze the impact of code changes on notebooks, documentation, and the rest of the codebase.

## Prerequisites

`.lumos/knowledge-graph.json` must exist. If it doesn't, tell the user to run `/lumos:scan` first.

## Instructions

1. Read `.lumos/knowledge-graph.json`.

2. Get changed files:

```bash
git diff --name-only          # Uncommitted changes
git diff main...HEAD --name-only   # Branch changes
```

If `$ARGUMENTS` contains a branch name or PR number, use that instead.

3. For each changed file:
   - Find its node in the knowledge graph
   - Find all edges connected to that node (incoming and outgoing)
   - Traverse 1-2 hops to find affected components

4. Categorize the impact:

### Direct impact
- Functions/classes modified in the changed file
- Notebook cells that import from the changed file (`cross_boundary_import`)
- Doc sections that reference the changed file (`doc_references_code`)

### Indirect impact
- Other code files that import from the changed file
- Notebook cells that call functions from the changed file (`cross_boundary_call`)
- Metrics documented that are implemented by changed functions (`metric_implemented_by`)

5. Report:
   - Changed files and what they contain
   - Directly affected: X notebook cells, Y doc sections, Z code files
   - Indirectly affected: list with edge types
   - Risk assessment: high (cross-boundary changes), medium (internal code), low (docs only)
   - Recommendations: "Update model_document.md §4 if Gini calculation changed"
