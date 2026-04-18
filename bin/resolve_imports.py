#!/usr/bin/env python3
"""
Lumos Import Resolver — Parser 3
For every import statement found in notebook cells, checks whether it resolves
to a file in the project's codebase. If yes, creates cross-boundary edges.
Also resolves doc references to actual code/notebook nodes.
"""

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path


def build_module_to_file_map(code_extract: dict) -> dict:
    """Build a map from module paths to file nodes."""
    module_map = {}
    for node in code_extract.get("nodes", []):
        if node["type"] == "file":
            # Convert file path to module path: src/metrics.py -> src.metrics
            file_path = node["file"]
            module_path = file_path.replace("/", ".").replace(".py", "").replace(".__init__", "")
            module_map[module_path] = node["id"]

            # Also map just the filename without extension
            stem = Path(file_path).stem
            if stem != "__init__":
                module_map[stem] = node["id"]
    return module_map


def build_entity_map(code_extract: dict) -> dict:
    """Build a map from entity names to node IDs."""
    entity_map = {}
    for node in code_extract.get("nodes", []):
        if node["type"] in ("function", "class"):
            name = node["name"]
            entity_map[name] = node["id"]
            # Also map by module.name
            file_path = node.get("file", "")
            module = file_path.replace("/", ".").replace(".py", "").replace(".__init__", "")
            short_name = name.split(".")[-1]
            entity_map[f"{module}.{short_name}"] = node["id"]
    return entity_map


def build_file_path_map(code_extract: dict, notebook_extract: dict) -> dict:
    """Build a map from file paths to node IDs (for doc reference resolution)."""
    path_map = {}
    for node in code_extract.get("nodes", []):
        if node["type"] == "file":
            path_map[node["file"]] = node["id"]
    for node in notebook_extract.get("nodes", []):
        if node["type"] == "notebook":
            path_map[node["file"]] = node["id"]
    return path_map


def try_importlib_resolve(module_path: str, project_root: str) -> bool:
    """Try to resolve a module using importlib to check if it's local."""
    try:
        # Add project root to sys.path temporarily
        original_path = sys.path[:]
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        spec = importlib.util.find_spec(module_path)
        sys.path[:] = original_path

        if spec and spec.origin:
            # Check if the resolved file is inside the project
            resolved_path = os.path.abspath(spec.origin)
            return resolved_path.startswith(os.path.abspath(project_root))
        return False
    except (ModuleNotFoundError, ValueError, AttributeError):
        return False


def resolve_notebook_imports(
    project_root: str,
    notebook_extract: dict,
    code_extract: dict,
) -> list:
    """
    Resolve notebook imports to codebase entities.
    Returns list of cross-boundary edges.
    """
    module_map = build_module_to_file_map(code_extract)
    entity_map = build_entity_map(code_extract)
    cross_edges = []

    for imp in notebook_extract.get("imports", []):
        cell_id = imp["cell_id"]
        module = imp.get("module", "")
        name = imp.get("name", "")
        imp_type = imp.get("type", "")

        resolved_target = None
        edge_type = "cross_boundary_import"

        if imp_type == "from_import":
            # Try full path: module.name
            full_path = f"{module}.{name}" if module else name
            if full_path in entity_map:
                resolved_target = entity_map[full_path]
            elif name in entity_map:
                resolved_target = entity_map[name]
            elif module in module_map:
                resolved_target = module_map[module]
            elif try_importlib_resolve(module, project_root):
                # It's local but we don't have a node for it
                resolved_target = f"module:{module}"
        elif imp_type == "import":
            if module in module_map:
                resolved_target = module_map[module]
            elif try_importlib_resolve(module, project_root):
                resolved_target = f"module:{module}"

        if resolved_target:
            cross_edges.append({
                "source": cell_id,
                "target": resolved_target,
                "type": edge_type,
                "direction": "forward",
                "weight": 1.0,
                "detail": {
                    "import_type": imp_type,
                    "module": module,
                    "name": name,
                },
            })

    return cross_edges


def resolve_notebook_calls(
    notebook_extract: dict,
    code_extract: dict,
) -> list:
    """
    Resolve function calls in notebooks to codebase entities.
    Only resolves calls where the function was imported from the local codebase.
    """
    entity_map = build_entity_map(code_extract)
    cross_edges = []

    # First, build a set of locally-imported names per cell
    local_imports_per_cell = {}
    for imp in notebook_extract.get("imports", []):
        cell_id = imp["cell_id"]
        name = imp.get("name", "")
        alias = imp.get("alias")
        effective_name = alias or name

        module = imp.get("module", "")
        full_path = f"{module}.{name}" if module else name

        # Check if this import resolves to a local entity
        if full_path in entity_map or name in entity_map:
            if cell_id not in local_imports_per_cell:
                local_imports_per_cell[cell_id] = {}
            local_imports_per_cell[cell_id][effective_name] = entity_map.get(full_path) or entity_map.get(name)

    # Now resolve calls
    for call in notebook_extract.get("calls", []):
        cell_id = call["cell_id"]
        call_name = call["name"]

        local_imports = local_imports_per_cell.get(cell_id, {})

        # Direct function call: gini_coefficient()
        if call_name in local_imports:
            cross_edges.append({
                "source": cell_id,
                "target": local_imports[call_name],
                "type": "cross_boundary_call",
                "direction": "forward",
                "weight": 0.9,
                "detail": {"call": call_name},
            })
        # Method call: model.fit() — check if 'model' type traces to imported class
        elif "." in call_name:
            parts = call_name.split(".")
            obj_name = parts[0]
            method_name = parts[-1]
            # Check if the object was imported from local code
            if obj_name in local_imports:
                target = local_imports[obj_name]
                # Try to find the specific method
                method_target = f"{target}.{method_name}" if target else None
                if method_target and method_target in entity_map:
                    target = entity_map[method_target]
                cross_edges.append({
                    "source": cell_id,
                    "target": target,
                    "type": "cross_boundary_method_call",
                    "direction": "forward",
                    "weight": 0.8,
                    "detail": {"call": call_name, "object": obj_name, "method": method_name},
                })

    return cross_edges


def resolve_doc_references(
    doc_extract: dict,
    code_extract: dict,
    notebook_extract: dict,
) -> list:
    """Resolve documentation references to actual code/notebook nodes."""
    path_map = build_file_path_map(code_extract, notebook_extract)
    entity_map = build_entity_map(code_extract)
    cross_edges = []

    for edge in doc_extract.get("edges", []):
        if edge["type"] in ("doc_references_code", "doc_references_notebook"):
            ref_target = edge["target"]
            ref_value = edge.get("detail", {}).get("reference", "")

            resolved = None

            # Try as file path
            if ref_value in path_map:
                resolved = path_map[ref_value]
            # Try with common prefixes
            for prefix in ["", "src/", "lib/", "notebooks/"]:
                candidate = prefix + ref_value
                if candidate in path_map:
                    resolved = path_map[candidate]
                    break
            # Try as entity name (function/class)
            if not resolved and ref_value in entity_map:
                resolved = entity_map[ref_value]

            if resolved:
                cross_edges.append({
                    "source": edge["source"],
                    "target": resolved,
                    "type": edge["type"],
                    "direction": "forward",
                    "weight": edge.get("weight", 0.8),
                    "detail": edge.get("detail", {}),
                })

    # Resolve metric → function edges
    for node in doc_extract.get("nodes", []):
        if node["type"] == "metric_def":
            metric_name = node.get("metric_name", "")
            # Try to find a function that implements this metric
            for entity_name, entity_id in entity_map.items():
                short_name = entity_name.split(".")[-1].lower()
                if metric_name in short_name or short_name in metric_name:
                    cross_edges.append({
                        "source": node["id"],
                        "target": entity_id,
                        "type": "metric_implemented_by",
                        "direction": "forward",
                        "weight": 0.7,
                        "detail": {"metric": metric_name, "function": entity_name},
                    })

    return cross_edges


def resolve_all(project_root: str, code_extract: dict, notebook_extract: dict, doc_extract: dict) -> dict:
    """Run all import resolution passes."""
    all_edges = []

    # Pass 1: Notebook imports → codebase
    import_edges = resolve_notebook_imports(project_root, notebook_extract, code_extract)
    all_edges.extend(import_edges)

    # Pass 2: Notebook calls → codebase functions
    call_edges = resolve_notebook_calls(notebook_extract, code_extract)
    all_edges.extend(call_edges)

    # Pass 3: Doc references → code/notebooks
    doc_edges = resolve_doc_references(doc_extract, code_extract, notebook_extract)
    all_edges.extend(doc_edges)

    # Deduplicate edges
    seen = set()
    unique_edges = []
    for edge in all_edges:
        key = (edge["source"], edge["target"], edge["type"])
        if key not in seen:
            seen.add(key)
            unique_edges.append(edge)

    return {
        "cross_boundary_edges": unique_edges,
        "stats": {
            "import_edges": len(import_edges),
            "call_edges": len(call_edges),
            "doc_edges": len(doc_edges),
            "total_unique": len(unique_edges),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Lumos Import Resolver")
    parser.add_argument("project_root", nargs="?", default=".",
                        help="Project root directory")
    parser.add_argument("--output", "-o", default=None,
                        help="Output file")
    args = parser.parse_args()

    project_root = os.path.abspath(args.project_root)
    intermediate_dir = os.path.join(project_root, ".lumos", "intermediate")

    with open(os.path.join(intermediate_dir, "code-extract.json"), "r") as f:
        code_extract = json.load(f)
    with open(os.path.join(intermediate_dir, "notebook-extract.json"), "r") as f:
        notebook_extract = json.load(f)

    doc_extract = {"nodes": [], "edges": []}
    doc_path = os.path.join(intermediate_dir, "doc-extract.json")
    if os.path.exists(doc_path):
        with open(doc_path, "r") as f:
            doc_extract = json.load(f)

    result = resolve_all(project_root, code_extract, notebook_extract, doc_extract)

    output_path = args.output or os.path.join(intermediate_dir, "import-resolution.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)

    print(json.dumps({
        "status": "success",
        "stats": result["stats"],
        "output": output_path,
    }))


if __name__ == "__main__":
    main()
