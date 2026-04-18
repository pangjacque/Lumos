---
description: Ask questions about your project using the knowledge graph. Requires a prior /lumos:scan. Use for questions like "which notebooks use function X?", "what does this module do?", "if I change X, what breaks?".
---

# Lumos Chat

Answer questions about the project using the knowledge graph.

## Prerequisites

`.lumos/knowledge-graph.json` must exist. If it doesn't, tell the user to run `/lumos:scan` first.

## Instructions

1. Read `.lumos/knowledge-graph.json`.

2. Parse the user's question from `$ARGUMENTS`.

3. Search the graph to answer the question. Common question patterns:

### "Which notebooks use function X?"
- Find the function node by name
- Find all `cross_boundary_import` and `cross_boundary_call` edges targeting that function
- List the source notebook cells

### "What does module/function/class X do?"
- Find the node by name
- Return its summary, tags, complexity
- List its connections (incoming and outgoing edges)

### "If I change function X, what breaks?"
- Find the function node
- Traverse all incoming edges recursively (1-2 hops)
- List all notebook cells, doc sections, and other code that depends on it

### "Show me the data flow in notebook X"
- Find all cell nodes for that notebook
- List them in order with their defs/refs
- Highlight data flow edges between cells

### "Which metrics are documented but not implemented?"
- Find all `metric_def` nodes
- Check if each has a `metric_implemented_by` edge
- List any without implementation

### "Which documentation references code that doesn't exist?"
- Find all `doc_references_code` edges
- Check if target nodes exist
- List broken references

4. Present the answer clearly with node names, file paths, and edge types.

## Constraints

- Only answer based on information in the knowledge graph
- If the graph doesn't contain enough information, say so and suggest running `/lumos:scan` again
- Do not read source files unless necessary to supplement the graph answer
