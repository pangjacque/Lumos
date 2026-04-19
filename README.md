# Lumos

**Illuminate your data science project.** Lumos is a Claude Code plugin that builds a knowledge graph from your **codebase**, **Jupyter notebooks**, and **documentation** — with cross-boundary import resolution that connects them all.

Most tools understand code OR notebooks. Lumos understands both — and the connections between them.

## The Problem

Data scientists work in a split world:

```
my-project/
├── src/
│   ├── metrics.py          # def gini_coefficient()
│   ├── features.py         # class FeatureStore
│   └── model.py            # class LogisticModel
├── notebooks/
│   ├── eda.ipynb            # from src.features import FeatureStore
│   └── model_training.ipynb # from src.model import LogisticModel
└── docs/
    ├── model_document.md    # "Gini coefficient: 0.45 (see src/metrics.py)"
    └── data_dictionary.md   # Feature definitions → code references
```

- **Code-only tools** see `src/` but have no idea about the notebooks
- **Notebook-only tools** see `notebooks/` but don't know what `gini_coefficient()` actually does
- **No tool** connects documentation to the code and notebooks it describes

The cross-boundary import is where all the meaning lives.

## What Lumos Does

Lumos runs 4 parsers and produces a unified knowledge graph:

| Parser | Input | Method | Output |
|--------|-------|--------|--------|
| **Code Scanner** | `.py` files | Python `ast` | module, class, function nodes |
| **Notebook Scanner** | `.ipynb` files | `nbformat` + `ast` | cell nodes + data flow edges |
| **Doc Scanner** | `.md` files | Markdown parser + regex | document, section, metric nodes |
| **Import Resolver** | Import statements | `importlib.util.find_spec()` + `ast` | cross-boundary edges |

The result: a graph where you can trace from a model document's "Gini = 0.45" → to `src/metrics.py:gini_coefficient()` → to `notebooks/model_training.ipynb cell 6` that calls it.

## Quick Start

### Prerequisites

- [Claude Code](https://claude.com/claude-code) installed
- Python 3.7+
- `pip install nbformat`

### Install

```bash
# Clone the plugin
git clone https://github.com/your-org/lumos.git

# Run Claude Code with the plugin
claude --plugin-dir ./lumos
```

### Usage

```bash
# Full project scan — code + notebooks + docs + cross-references
/lumos:scan

# Analyze only code / notebooks / docs
/lumos:codebase
/lumos:notebook
/lumos:doc

# Ask questions about the project
/lumos:chat "which notebooks use gini_coefficient?"
/lumos:chat "if I change LogisticModel, what breaks?"
/lumos:chat "which metrics in the model doc are implemented in code?"

# Impact analysis before committing
/lumos:diff
```

### Open the Report

After scanning, open the interactive HTML report:

```bash
open .lumos/report-force.html
```

## How It Works

```
/lumos:scan
    │
    ├── 1. Project Scanner    → discovers files, categorizes them
    │
    ├── 2. Code Scanner       → AST extracts functions, classes, imports
    ├── 2. Notebook Scanner   → nbformat extracts cells, data flow, magics
    ├── 2. Doc Scanner        → classifies docs, extracts references
    │      (these 3 run in parallel)
    │
    ├── 3. Import Resolver    → links notebook imports to codebase entities
    │                         → links doc references to code/notebooks
    │
    ├── 4. Graph Merger       → deduplicates, validates, produces knowledge-graph.json
    │
    └── 5. Report Generator   → produces interactive HTML report
```

## Knowledge Graph

### Node Types

| Type | Color | Description |
|------|-------|-------------|
| `file` | Blue | Python source file |
| `function` | Light Blue | Function definition |
| `class` | Lighter Blue | Class definition |
| `notebook` | Green | Jupyter notebook |
| `cell` | Light Green | Notebook cell (code or markdown) |
| `document` | Yellow | Documentation file |
| `doc_section` | Light Yellow | Section within a document |
| `metric_def` | Purple | Documented metric value |

### Edge Types

| Type | Description |
|------|-------------|
| `contains` | Parent contains child (file→function, notebook→cell) |
| `imports` | Code file imports from another |
| `cell_flow` | Sequential cell order in notebook |
| `cell_data_flow` | Variable flows from one cell to another |
| `cross_boundary_import` | Notebook cell imports from codebase |
| `cross_boundary_call` | Notebook cell calls a codebase function |
| `doc_references_code` | Doc section mentions a code file/function |
| `doc_references_notebook` | Doc section mentions a notebook |
| `metric_implemented_by` | Documented metric linked to implementing function |

## Notebook-Specific Features

### Magic Handling

Jupyter magics (`%%time`, `%matplotlib inline`, `!pip install`) are stripped before AST parsing but preserved as metadata:

- `%%time`, `%%timeit` → recorded as timing magic
- `%load_ext autoreload` → signals hot-reload from codebase
- `%%sql` → cell is SQL, not Python
- `%%writefile` → cell generates a file
- `%run notebook.ipynb` → cross-notebook dependency
- `!pip install X` → recorded as shell command

### Execution Anomaly Detection

Lumos detects when notebook execution order doesn't match document order:

- **Out-of-order execution** — execution counts aren't sequential
- **Unexecuted cells** — cells that were never run
- **Error cells** — cells with error outputs
- **Error propagation** — cells that depend on variables from error cells

### Cell Data Flow

Tracks which variables flow between cells:
```
Cell 1: defs={df}         
Cell 2: refs={df} defs={X, y}    ← data flow edge from cell 1
Cell 3: refs={X, y} defs={model} ← data flow edge from cell 2
```

## Documentation-Specific Features

### Document Type Classification

Lumos classifies docs by content, not just filename:

| Type | Signals |
|------|---------|
| **model_doc** | "methodology", "performance metrics", "Gini", "PSI" |
| **data_dictionary** | "feature name", "data source", "variable description" |
| **governance** | "approved by", "review date", "change log" |
| **design_doc** | "decision", "alternatives", "trade-offs" |

### Cross-Reference Detection

Lumos finds references to code and notebooks in documentation:
- Backtick-quoted paths: `` `src/metrics.py` ``
- Backtick-quoted functions: `` `gini_coefficient()` ``
- Inline references: "see `notebooks/eda.ipynb`"
- Metric values: "Gini: 0.45" linked to implementing function

## Output Files

```
.lumos/
├── knowledge-graph.json     ← complete graph (all nodes + edges)
├── report-force.html              ← interactive visualization (open in browser)
├── metadata.json            ← commit hash + file hashes (for incremental updates)
└── intermediate/            ← working files (can be .gitignored)
    ├── scan-result.json
    ├── code-extract.json
    ├── notebook-extract.json
    ├── doc-extract.json
    └── import-resolution.json
```

## Platform Support

| Platform | Status |
|----------|--------|
| Claude Code | Supported |
| VS Code + GitHub Copilot | Supported (auto-discovery via `.copilot-plugin/`) |
| Cursor | Supported (auto-discovery via `.cursor-plugin/`) |

## Languages Supported (v0.1)

- **Python** — full AST analysis
- **Scala** — planned (via tree-sitter)
- **Jupyter Notebooks** — full cell analysis with magic handling
- **Markdown** — full section and reference extraction

## Contributing

Contributions welcome! Key areas:

- **Scala support** via tree-sitter
- **PDF/Word doc parsing** for model documents
- **Dashboard** with React Flow (v0.2 goal)
- **Incremental scanning** (only re-analyze changed files)
- **More magic handlers** for domain-specific magics

## License

MIT
