#!/usr/bin/env python3
"""
Lumos Notebook Extractor — Parser 2
Reads .ipynb files using nbformat, extracts cells, uses AST on code cells,
computes per-cell defs/refs with data flow edges.
Handles Jupyter magics by pre-processing before AST parsing.
"""

import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path

try:
    import nbformat
except ImportError:
    print("Error: nbformat is required. Install with: pip install nbformat", file=sys.stderr)
    sys.exit(1)


# --- Magic pre-processing ---

LINE_MAGIC_RE = re.compile(r"^\s*%(?!%)(\w+)(.*)", re.MULTILINE)
CELL_MAGIC_RE = re.compile(r"^\s*%%(\w+)(.*\n?)", re.MULTILINE)
SHELL_CMD_RE = re.compile(r"^\s*!(.*)", re.MULTILINE)
INTROSPECT_RE = re.compile(r"^\s*(\w[\w.]*)\?\??.*$", re.MULTILINE)

MEANINGFUL_MAGICS = {
    "run": "cross_notebook",
    "load_ext": "extension",
    "autoreload": "autoreload",
    "sql": "sql_cell",
    "writefile": "generates_file",
    "time": "timing",
    "timeit": "timing",
    "matplotlib": "visualization",
    "pyspark": "spark",
}


def preprocess_cell_source(source: str) -> dict:
    """
    Strip magics and shell commands from cell source, returning clean Python
    plus metadata about what was stripped.
    """
    magics = []
    shell_commands = []
    clean_lines = []

    lines = source.split("\n")
    is_cell_magic = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Cell magic on first line
        if i == 0 and stripped.startswith("%%"):
            match = CELL_MAGIC_RE.match(stripped)
            if match:
                magic_name = match.group(1)
                magics.append({
                    "type": "cell_magic",
                    "name": magic_name,
                    "significance": MEANINGFUL_MAGICS.get(magic_name, "other"),
                    "line": i + 1,
                })
                # For %%sql, %%writefile etc, the rest is not Python
                if magic_name in ("sql", "html", "javascript", "bash", "sh"):
                    is_cell_magic = True
                continue

        if is_cell_magic:
            continue

        # Line magic
        if stripped.startswith("%") and not stripped.startswith("%%"):
            match = LINE_MAGIC_RE.match(stripped)
            if match:
                magic_name = match.group(1)
                magics.append({
                    "type": "line_magic",
                    "name": magic_name,
                    "significance": MEANINGFUL_MAGICS.get(magic_name, "other"),
                    "line": i + 1,
                })
                continue

        # Shell command
        if stripped.startswith("!"):
            match = SHELL_CMD_RE.match(stripped)
            if match:
                shell_commands.append({
                    "command": match.group(1).strip(),
                    "line": i + 1,
                })
                continue

        # IPython introspection (obj? or obj??)
        if stripped.endswith("?"):
            match = INTROSPECT_RE.match(stripped)
            if match:
                continue

        clean_lines.append(line)

    clean_source = "\n".join(clean_lines).strip()

    return {
        "clean_source": clean_source,
        "magics": magics,
        "shell_commands": shell_commands,
        "is_non_python": is_cell_magic,
    }


# --- AST analysis per cell ---

def extract_cell_defs(tree: ast.AST) -> list:
    """Extract names defined in a cell (assignments, function defs, class defs)."""
    defs = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defs.append({"name": node.name, "type": "function", "line": node.lineno})
        elif isinstance(node, ast.ClassDef):
            defs.append({"name": node.name, "type": "class", "line": node.lineno})
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    defs.append({"name": target.id, "type": "variable", "line": node.lineno})
                elif isinstance(target, ast.Tuple):
                    for elt in target.elts:
                        if isinstance(elt, ast.Name):
                            defs.append({"name": elt.id, "type": "variable", "line": node.lineno})
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            defs.append({"name": node.target.id, "type": "variable", "line": node.lineno})
    return defs


def extract_cell_refs(tree: ast.AST) -> list:
    """Extract names referenced (used) in a cell."""
    refs = set()
    # Names used in expressions, function calls, etc.
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            refs.add(node.id)
    return list(refs)


def extract_cell_imports(tree: ast.AST) -> list:
    """Extract imports from a cell."""
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({
                    "type": "import",
                    "module": alias.name,
                    "name": alias.asname or alias.name,
                    "line": node.lineno,
                })
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imports.append({
                    "type": "from_import",
                    "module": module,
                    "name": alias.name,
                    "alias": alias.asname,
                    "line": node.lineno,
                })
    return imports


def extract_cell_calls(tree: ast.AST) -> list:
    """Extract function/method calls from a cell."""
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.append({"name": node.func.id, "line": node.lineno})
            elif isinstance(node.func, ast.Attribute):
                parts = []
                current = node.func
                while isinstance(current, ast.Attribute):
                    parts.append(current.attr)
                    current = current.value
                if isinstance(current, ast.Name):
                    parts.append(current.id)
                calls.append({
                    "name": ".".join(reversed(parts)),
                    "line": node.lineno,
                })
    return calls


# --- Execution anomaly detection ---

def detect_anomalies(cells: list) -> list:
    """Detect execution order anomalies."""
    anomalies = []
    exec_counts = []

    for cell in cells:
        if cell.get("cell_type") == "code":
            ec = cell.get("execution_count")
            exec_counts.append(ec)

    non_null = [c for c in exec_counts if c is not None]

    if None in exec_counts:
        anomalies.append("unexecuted_cells")

    if non_null and non_null != sorted(non_null):
        anomalies.append("out_of_order_execution")

    if len(non_null) != len(set(non_null)):
        anomalies.append("duplicate_execution_counts")

    # Check for large gaps in execution counts
    if len(non_null) >= 2:
        sorted_counts = sorted(non_null)
        for i in range(1, len(sorted_counts)):
            if sorted_counts[i] - sorted_counts[i - 1] > 5:
                anomalies.append("execution_count_gaps")
                break

    return anomalies


def detect_cell_errors(cell_outputs: list) -> dict:
    """Check if cell outputs contain errors."""
    for output in cell_outputs:
        if output.get("output_type") == "error":
            return {
                "has_error": True,
                "error_name": output.get("ename", ""),
                "error_value": output.get("evalue", ""),
            }
    return {"has_error": False}


# --- Main notebook extraction ---

def analyze_notebook(filepath: str, project_root: str) -> dict:
    """Analyze a single Jupyter notebook."""
    rel_path = os.path.relpath(filepath, project_root)

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            nb = nbformat.read(f, as_version=4)
    except Exception as e:
        return {"file": rel_path, "error": str(e), "nodes": [], "edges": []}

    nodes = []
    edges = []
    all_imports = []
    all_calls = []

    # Notebook-level node
    nb_id = f"notebook:{rel_path}"
    kernel_info = nb.metadata.get("kernelspec", {})
    nodes.append({
        "id": nb_id,
        "type": "notebook",
        "name": Path(rel_path).stem,
        "file": rel_path,
        "summary": "",
        "kernel": kernel_info.get("display_name", "unknown"),
        "cell_count": len(nb.cells),
        "tags": [],
    })

    # Detect execution anomalies at notebook level
    raw_cells = [{"cell_type": c.cell_type, "execution_count": getattr(c, "execution_count", None)}
                 for c in nb.cells]
    notebook_anomalies = detect_anomalies(raw_cells)

    # Track variable scope for data flow
    defined_vars = {}  # var_name -> cell_id that last defined it
    prev_cell_id = None

    for idx, cell in enumerate(nb.cells):
        cell_id = f"cell:{rel_path}:{idx + 1}"

        if cell.cell_type == "markdown":
            # Extract heading from markdown
            source = cell.source.strip()
            heading = ""
            for line in source.split("\n"):
                if line.startswith("#"):
                    heading = line.lstrip("#").strip()
                    break

            nodes.append({
                "id": cell_id,
                "type": "cell",
                "name": heading or f"Cell {idx + 1} (markdown)",
                "file": rel_path,
                "cell_index": idx + 1,
                "cell_type": "markdown",
                "source_preview": source[:200],
                "summary": "",
                "tags": [],
            })

        elif cell.cell_type == "code":
            source = cell.source
            execution_count = cell.execution_count

            # Pre-process magics
            preprocessed = preprocess_cell_source(source)
            clean_source = preprocessed["clean_source"]

            # Detect errors in outputs
            error_info = detect_cell_errors(cell.get("outputs", []))

            # Determine cell status
            if error_info["has_error"]:
                status = "error"
            elif execution_count is None:
                status = "unexecuted"
            elif "out_of_order_execution" in notebook_anomalies:
                status = "executed_out_of_order"
            else:
                status = "executed"

            # AST analysis on clean source
            cell_defs = []
            cell_refs = []
            cell_imports = []
            cell_calls = []
            parse_error = None

            if clean_source and not preprocessed["is_non_python"]:
                try:
                    tree = ast.parse(clean_source)
                    cell_defs = extract_cell_defs(tree)
                    cell_refs = extract_cell_refs(tree)
                    cell_imports = extract_cell_imports(tree)
                    cell_calls = extract_cell_calls(tree)
                except SyntaxError as e:
                    parse_error = str(e)

            all_imports.extend([{**imp, "cell_id": cell_id, "cell_index": idx + 1} for imp in cell_imports])
            all_calls.extend([{**call, "cell_id": cell_id, "cell_index": idx + 1} for call in cell_calls])

            nodes.append({
                "id": cell_id,
                "type": "cell",
                "name": f"Cell {idx + 1}",
                "file": rel_path,
                "cell_index": idx + 1,
                "cell_type": "code",
                "execution_count": execution_count,
                "status": status,
                "source_preview": source[:300],
                "defs": [d["name"] for d in cell_defs],
                "refs": [r for r in cell_refs],
                "imports": cell_imports,
                "calls": [c["name"] for c in cell_calls],
                "magics": preprocessed["magics"],
                "shell_commands": preprocessed["shell_commands"],
                "error": error_info if error_info["has_error"] else None,
                "parse_error": parse_error,
                "summary": "",
                "tags": [],
            })

            # Data flow edges: this cell refs a variable defined in an earlier cell
            for ref in cell_refs:
                if ref in defined_vars:
                    source_cell_id = defined_vars[ref]
                    if source_cell_id != cell_id:
                        edges.append({
                            "source": source_cell_id,
                            "target": cell_id,
                            "type": "cell_data_flow",
                            "direction": "forward",
                            "weight": 0.6,
                            "detail": {"variable": ref},
                        })

            # Update defined vars
            for d in cell_defs:
                defined_vars[d["name"]] = cell_id

            # Error propagation: if this cell depends on an error cell
            for ref in cell_refs:
                if ref in defined_vars:
                    source_node = next(
                        (n for n in nodes if n["id"] == defined_vars[ref] and n.get("status") == "error"),
                        None,
                    )
                    if source_node:
                        # Mark this cell as depending on error
                        for n in nodes:
                            if n["id"] == cell_id:
                                n["status"] = "depends_on_error"

            # Magic-based edges
            for magic in preprocessed["magics"]:
                if magic["name"] == "run" and magic.get("significance") == "cross_notebook":
                    edges.append({
                        "source": cell_id,
                        "target": f"magic_run:{magic.get('name', '')}",
                        "type": "magic_execution",
                        "direction": "forward",
                        "weight": 0.7,
                    })

        # Contains edge: notebook → cell
        edges.append({
            "source": nb_id,
            "target": cell_id,
            "type": "contains",
            "direction": "forward",
            "weight": 1.0,
        })

        # Cell flow edge: sequential cell order
        if prev_cell_id:
            edges.append({
                "source": prev_cell_id,
                "target": cell_id,
                "type": "cell_flow",
                "direction": "forward",
                "weight": 0.5,
            })
        prev_cell_id = cell_id

    return {
        "file": rel_path,
        "nodes": nodes,
        "edges": edges,
        "imports": all_imports,
        "calls": all_calls,
        "anomalies": notebook_anomalies,
    }


def extract_notebooks(project_root: str, scan_result: dict) -> dict:
    """Extract all notebooks in the project."""
    project_root = os.path.abspath(project_root)
    notebook_files = [
        f for f in scan_result.get("files", [])
        if f["category"] == "notebook"
    ]

    all_nodes = []
    all_edges = []
    all_imports = []
    all_calls = []
    notebook_results = []

    for file_info in notebook_files:
        filepath = os.path.join(project_root, file_info["path"])
        result = analyze_notebook(filepath, project_root)
        notebook_results.append(result)
        all_nodes.extend(result["nodes"])
        all_edges.extend(result["edges"])
        all_imports.extend(result.get("imports", []))
        all_calls.extend(result.get("calls", []))

    return {
        "nodes": all_nodes,
        "edges": all_edges,
        "imports": all_imports,
        "calls": all_calls,
        "notebook_results": notebook_results,
    }


def main():
    parser = argparse.ArgumentParser(description="Lumos Notebook Extractor")
    parser.add_argument("project_root", nargs="?", default=".",
                        help="Project root directory")
    parser.add_argument("--scan-result", default=None,
                        help="Path to scan-result.json")
    parser.add_argument("--output", "-o", default=None,
                        help="Output file")
    args = parser.parse_args()

    project_root = os.path.abspath(args.project_root)

    scan_path = args.scan_result or os.path.join(
        project_root, ".lumos", "intermediate", "scan-result.json"
    )
    with open(scan_path, "r") as f:
        scan_result = json.load(f)

    result = extract_notebooks(project_root, scan_result)

    output_path = args.output or os.path.join(
        project_root, ".lumos", "intermediate", "notebook-extract.json"
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)

    print(json.dumps({
        "status": "success",
        "nodes": len(result["nodes"]),
        "edges": len(result["edges"]),
        "imports": len(result["imports"]),
        "output": output_path,
    }))


if __name__ == "__main__":
    main()
