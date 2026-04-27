<h1 align="center">Lumos</h1>

<p align="center">
  <strong>Illuminate the dark matter within the modeling void. </strong>
  <br />
  <em>A Claude Code plugin that builds a unified knowledge graph from your codebase, Jupyter notebooks, and documentation — with cross-boundary import resolution that connects them all.</em>
</p>

<p align="center">
  <a href="#-quick-start"><img src="https://img.shields.io/badge/Quick_Start-blue" alt="Quick Start" /></a>
  <a href="https://github.com/pangjacque/Lumos/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow" alt="License: MIT" /></a>
  <a href="https://docs.anthropic.com/en/docs/claude-code"><img src="https://img.shields.io/badge/Claude_Code-8A2BE2" alt="Claude Code" /></a>
  <a href="#vs-code--github-copilot"><img src="https://img.shields.io/badge/Copilot-24292e" alt="Copilot" /></a>
  <a href="#-under-the-hood"><img src="https://img.shields.io/badge/Multi_Agent-success" alt="Multi-Agent Pipeline" /></a>
  <a href="https://github.com/microsoft/markitdown"><img src="https://img.shields.io/badge/Word_+_PDF-markitdown-1f6feb" alt="Markitdown" /></a>
</p>

---

> **Codebase is the skeleton. Notebooks are the soul. Lumos is the nervous system — the lineage between them.**

Data scientists work in a split world:

- **Codebase** is engineering execution.
- **Notebooks** are experimentation.
- **Docs** are intent.

Most tools operate within a single modality:

- IDEs understand code.
- Notebook tools understand cells.
- Documentation tools understand text.

**None understand the system as a whole.**

**Lumos** dissolves the wall — a Claude Code plugin that constructs a cross-modal knowledge graph over your entire modeling stack:

- Codebase (Python modules — flat layout, `src/` layout, monorepo, anything `git ls-files` can see)
- Jupyter notebooks (`.ipynb`)
- Documentation (Markdown, PDF, Word, Excel)

It resolves **cross-boundary dependencies** — from exploratory notebooks to production code, from model documentation to implementation — and exposes them as a **queryable, inspectable graph**.


---

## 🎯 Why Lumos?

We love data. Here's why Lumos beats your IDE's "Find All References":

| Capability                     | Standard IDE | Lumos        |
|--------------------------------|--------------|--------------|
| Code lineage ↔ Notebook tracing      | ❌ Blind     | ✅ Native    |
| Cross-language dependency  | ❌ Opaque   | ✅ First-class edges  |
| Doc ↔ Implementation traceability          | ❌ Manual    | ✅ Automated |
| Notebook execution order       | ❌ Ignored   | ✅ Validated |

> **You don’t break models because of bad code.
You break them because you don’t know what depends on what.**

Lumos turns that uncertainty into a deterministic graph query problem.

---

## ✨ Superpowers

### Collapse the Research-Production Duality

Notebook imports a class from codebase? Lumos resolves it to the actual class node and emits a `cross_boundary_import` edge. Doc references `gini_coefficient()` in backticks? Lumos finds the function and emits a `doc_references_code` edge. The graph captures the wiring most tools miss.

### Sanitize the Exploratory Chaos

Strips Jupyter magics (`%%time`, `%matplotlib`, `!pip`) before AST parsing while preserving them as metadata. Detects out-of-order execution, error cells, and error propagation. Tracks variable data flow between cells.

### Pierce the JVM Bridge (Python ↔ Scala bridge detection)

Spark/Databricks projects mix Python orchestration with Scala compute. Lumos automatically detects `spark._jvm.com.example.MyClass()` patterns and links them to the actual Scala class — exposing the JVM bridge as first-class graph edges.

### Documentation classification

Classifies markdown by content (model_doc, data_dictionary, governance, design_doc), extracts metric definitions ("Gini: 0.45"), and links them to implementing code.

### Interactive force-directed graph

Open the HTML report and explore — pan, zoom, click any node to see its details. Filter by notebook to isolate a single pipeline. Toggle dark/light themes.

---

## 🚀 Quick Start

### 1. Install the plugin

```bash
/plugin marketplace add pangjacque/Lumos
/plugin install lumos
```

Requires Python 3.7+ and the dependencies in [bin/requirements.txt](bin/requirements.txt):
```bash
pip install -r bin/requirements.txt
```

### 2. Scan your project

```bash
/lumos:everything
```

Runs the full pipeline (code + notebooks + docs + cross-references) and writes results to `.lumos/`.

### 3. Open the dashboard

```bash
open .lumos/report-force.html
```

### 4. Ask questions and analyze impact

```bash
# Ask anything about the project
/lumos:chat which notebooks use gini_coefficient?
/lumos:chat if I change LogisticModel, what breaks?
/lumos:chat which metrics in the model doc are implemented in code?

# Impact analysis before committing
/lumos:diff
```

---

## 🌐 Multi-Platform Installation

### Claude Code (Native)

```bash
/plugin marketplace add pangjacque/Lumos
/plugin install lumos
```

**Offline / restricted environments:** clone or [download the ZIP](https://github.com/pangjacque/Lumos/archive/refs/heads/main.zip), unzip locally, then run:

```bash
claude --plugin-dir /path/to/Lumos
```

### VS Code + GitHub Copilot

**Online:** Open the Command Palette (`Cmd+Shift+P`) → run `Chat: Install Plugin From Source` → paste:

```
https://github.com/pangjacque/Lumos
```

**Offline:** [Download the ZIP](https://github.com/pangjacque/Lumos/archive/refs/heads/main.zip) from GitHub, unzip to a known location (e.g. `~/lumos`), then add the **unzipped folder path** to your VS Code `settings.json`:

```json
{
  "chat.pluginLocations": [
    "/Users/yourname/lumos"
  ]
}
```

> Point at the **directory containing `.claude-plugin/plugin.json`** — not at the `.zip` file. GitHub ZIPs sometimes unzip to a doubly-nested folder (`Lumos-main/Lumos-main/`) — point at the inner one.

Reload VS Code (`Cmd+Shift+P` → `Developer: Reload Window`). Skills appear when you type `/` in Copilot Chat. Both methods register Lumos via the [`.claude-plugin/plugin.json`](https://code.visualstudio.com/docs/copilot/customization/agent-plugins) manifest, an officially supported location. Requires VS Code 1.110+ (Agent Plugins, Preview).

### Platform Compatibility

| Platform | Status | Install Method |
|----------|--------|----------------|
| Claude Code | ✅ Native | Plugin marketplace, or `--plugin-dir` for offline |
| VS Code + GitHub Copilot | ✅ Supported | `Chat: Install Plugin From Source`, or `chat.pluginLocations` for offline |
| Cursor | 🚧 Planned (v0.2) | Cursor marketplace submission pending |

---

## 🔧 Under the Hood

### Multi-Agent Pipeline

The `/lumos:everything` command orchestrates a multi-agent pipeline. Extractors run in parallel, then results are merged into a single knowledge graph.

| Agent | Role |
|-------|------|
| `project-scanner` | Discover files, detect languages, categorize as code / notebook / doc / config / data |
| `code-analyzer` | Python AST extraction — modules, classes, functions, imports |
| `scala-analyzer` | Scala tree-sitter extraction — classes, objects, traits, methods (for Spark/Databricks projects) |
| `notebook-analyzer` | nbformat extraction — cells, magic handling, execution anomaly detection, cell data flow |
| `doc-analyzer` | Markdown extraction — sections, doc-type classification, code/notebook references, metric definitions |
| `import-resolver` | Cross-boundary resolution — links notebook imports to codebase entities, doc references to code, Py4J bridges to Scala classes |
| `graph-reviewer` | Validates graph completeness, deduplicates nodes, removes dangling edges |

### Pipeline Flow

```
/lumos:everything
    │
    ├── 1. project-scanner    → discover files, categorize
    │
    ├── 2. code-analyzer      ┐
    ├── 2. scala-analyzer     │  (parallel)
    ├── 2. notebook-analyzer  │
    ├── 2. doc-analyzer       ┘
    │
    ├── 3. import-resolver    → link notebook → code, doc → code, Python → Scala (Py4J)
    │
    ├── 4. graph-reviewer     → merge into knowledge-graph.json
    │
    └── 5. report generator   → produce interactive HTML
```

The 4 extractors in Phase 2 run in parallel — typically 30–60 seconds for a project with thousands of files.

---

## 📊 Knowledge Graph

### Node Types

| Type | Description |
|------|-------------|
| `file` | Python or Scala source file |
| `function` | Function or method definition |
| `class` | Class, object, or trait definition |
| `notebook` | Jupyter notebook |
| `cell` | Notebook cell (code or markdown) |
| `document` | Documentation file (.md / .rst) |
| `doc_section` | Section within a document |
| `metric_def` | Documented metric value |

### Edge Types

| Type | Description |
|------|-------------|
| `contains` | Parent contains child (file → function, notebook → cell) |
| `imports` | Code file imports from another |
| `cell_flow` | Sequential cell order in notebook |
| `cell_data_flow` | Variable flows from one cell to another |
| `cross_boundary_import` | Notebook cell imports from codebase |
| `cross_boundary_call` | Notebook cell calls a codebase function |
| `py4j_bridge` | Python instantiates a Scala class via `spark._jvm` |
| `py4j_method_call` | Python calls a Scala method via `spark._jvm` |
| `doc_references_code` | Doc section mentions a code file/function |
| `doc_references_notebook` | Doc section mentions a notebook |
| `metric_implemented_by` | Documented metric linked to implementing function |

---

## 📓 Notebook-Specific Features

### Magic Handling

Jupyter magics are stripped before AST parsing but preserved as metadata:

- `%%time`, `%%timeit` → recorded as timing magic
- `%load_ext autoreload` → signals hot-reload from codebase
- `%%sql` → cell is SQL, not Python
- `%%writefile` → cell generates a file
- `%run notebook.ipynb` → cross-notebook dependency
- `!pip install X` → recorded as shell command

### Execution Anomaly Detection

- **Out-of-order execution** — execution counts aren't sequential
- **Unexecuted cells** — cells that were never run
- **Error cells** — cells with error outputs
- **Error propagation** — cells depending on variables from error cells

### Cell Data Flow

Tracks which variables flow between cells:
```
Cell 1: defs={df}
Cell 2: refs={df} defs={X, y}        ← data flow edge from cell 1
Cell 3: refs={X, y} defs={model}     ← data flow edge from cell 2
```

---

## ⚡ Cross-Runtime Bridges

Cross-language calls — Python invoking the JVM, native binaries, or other runtimes — are where data-science code commonly goes opaque. Lumos surfaces them as graph edges so impact analysis can trace through.

### Supported today

**Py4J (Python → JVM)** — for Spark/Databricks projects that mix Python orchestration with Scala compute. Lumos detects `spark._jvm.com.example.MyClass()` and `spark._jvm.com.example.MyClass.method(...)` patterns and links them to the matching Scala class:

```python
class FeatureEngineerWrapper:
    def __init__(self, spark):
        self._scala_obj = spark._jvm.com.example.FeatureEngineer()  # → py4j_bridge

    def compute(self, df):
        return spark._jvm.com.example.FeatureEngineer.giniCoefficient(df._jdf)  # → py4j_method_call
```

Framework calls (`org.apache.spark.*`, `org.apache.hadoop.*`, `java.*`) are recognized and skipped to avoid noise. For cases where auto-detection misses a bridge, drop a `python_scala.yaml` at your project root — see [docs/python_scala.yaml.example](docs/python_scala.yaml.example).

### Roadmap (v0.2+)

- **pybind11 / Cython** — Python → compiled C++ (XGBoost, PyTorch internals)
- **ctypes / CFFI** — Python → shared libraries
- **PyO3** — Python → Rust

---

## 📚 Documentation Features

### Document Type Classification

Lumos reads each doc and tags it with a `doc_type` based on the keywords below. Both content signals and filename hints contribute to the score.

| Type | Detected by content signals |
|------|-----------------------------|
| `model_doc` | "methodology", "performance metrics", "Gini", "PSI" |
| `data_dictionary` | "feature name", "data source", "variable description" |
| `governance` | "approved by", "review date", "change log" |
| `design_doc` | "decision", "alternatives", "trade-offs" |

### Supported formats

- **Markdown** (`.md`), **reStructuredText** (`.rst`), **plain text** (`.txt`) — read directly
- **Word** (`.docx`, `.doc`), **PDF** (`.pdf`), **PowerPoint** (`.pptx`, `.ppt`), **Excel** (`.xlsx`) — converted via [Microsoft markitdown](https://github.com/microsoft/markitdown)

Rich-doc support requires `markitdown[all]` (Python 3.10+). The original format is preserved on each document node as `source_format`. Caveat: PDF→markdown is lossy — tables often render as plain text, scanned PDFs need OCR (markitdown handles it but slower).

### Cross-Reference Detection

- Backtick-quoted paths: `` `mymodel/metrics.py` ``
- Backtick-quoted functions: `` `gini_coefficient()` ``
- Inline references: `` "see `notebooks/eda.ipynb`" ``
- Metric values: `"Gini: 0.45"` linked to implementing function

---

## 📁 Output Files

```
.lumos/
├── knowledge-graph.json     ← complete graph (all nodes + edges)
├── report-force.html        ← interactive visualization
├── metadata.json            ← commit hash + file hashes (for incremental updates)
└── intermediate/            ← per-extractor outputs (gitignorable)
    ├── scan-result.json
    ├── code-extract.json
    ├── scala-extract.json
    ├── notebook-extract.json
    ├── doc-extract.json
    └── import-resolution.json
```

---

## 🌍 Languages Supported

- **Python** — full AST analysis
- **Scala** — tree-sitter analysis (classes, objects, traits, methods). Useful for Spark/Databricks projects.
- **Jupyter Notebooks** — full cell analysis with magic handling
- **Markdown** — full section and reference extraction

---

## 🤝 Contributing

Contributions welcome! Key areas:

- **R support** via tree-sitter (statistical/biomedical ML)
- **PDF/Word doc parsing** (`.docx`, `.pdf`) — currently only `.md` and `.rst` are read; enterprise model docs are usually Word/PDF
- **Filename-aware doc classification** — combine content signals with filename hints (e.g. `model_12345_documentation_v3.docx` is obviously a `model_doc`)
- **Cross-runtime bridges beyond Py4J** — pybind11, Cython, ctypes, PyO3 (see [Cross-Runtime Bridges roadmap](#-cross-runtime-bridges))
- **Notebook-direct Py4J detection** — currently only `.py` files are scanned for `spark._jvm` patterns
- **Incremental scanning** — only re-analyze changed files
- **More magic handlers** for domain-specific Jupyter magics

To get started:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Run `bash scripts/setup-examples.sh` to fetch a real-world test project (Microsoft FLAML)
4. Make changes and open a PR

---

<p align="center">
  MIT License © <a href="https://github.com/pangjacque">Lumos Contributors</a>
</p>
