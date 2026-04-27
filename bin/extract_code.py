#!/usr/bin/env python3
"""
Lumos Code Extractor — Parser 1
Walks .py files using Python AST, extracts module → class → function hierarchy
and internal imports. Produces code nodes and edges.
"""

import argparse
import ast
import json
import os
import sys
from pathlib import Path


def extract_imports(tree: ast.AST) -> list:
    """Extract all import statements from an AST."""
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


def extract_functions(tree: ast.AST, filepath: str) -> list:
    """Extract top-level and class-level function definitions."""
    functions = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_info = {
                "name": node.name,
                "type": "function",
                "file": filepath,
                "line_start": node.lineno,
                "line_end": getattr(node, 'end_lineno', None) or node.lineno,
                "args": [arg.arg for arg in node.args.args if arg.arg != "self"],
                "decorators": [_decorator_name(d) for d in node.decorator_list],
                "is_async": isinstance(node, ast.AsyncFunctionDef),
                "docstring": ast.get_docstring(node) or "",
            }
            functions.append(func_info)
    return functions


def extract_classes(tree: ast.AST, filepath: str) -> list:
    """Extract class definitions with their methods."""
    classes = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            methods = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append({
                        "name": item.name,
                        "line_start": item.lineno,
                        "line_end": getattr(item, 'end_lineno', None) or item.lineno,
                        "args": [a.arg for a in item.args.args if a.arg != "self"],
                        "decorators": [_decorator_name(d) for d in item.decorator_list],
                        "is_async": isinstance(item, ast.AsyncFunctionDef),
                        "docstring": ast.get_docstring(item) or "",
                    })

            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(_attribute_name(base))

            class_info = {
                "name": node.name,
                "type": "class",
                "file": filepath,
                "line_start": node.lineno,
                "line_end": getattr(node, 'end_lineno', None) or node.lineno,
                "bases": bases,
                "methods": methods,
                "decorators": [_decorator_name(d) for d in node.decorator_list],
                "docstring": ast.get_docstring(node) or "",
            }
            classes.append(class_info)
    return classes


def extract_top_level_assignments(tree: ast.AST) -> list:
    """Extract top-level variable assignments (constants, configs)."""
    assignments = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments.append({
                        "name": target.id,
                        "line": node.lineno,
                    })
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            assignments.append({
                "name": node.target.id,
                "line": node.lineno,
            })
    return assignments


def extract_call_references(tree: ast.AST) -> list:
    """Extract all function/method call references."""
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.append({"name": node.func.id, "line": node.lineno})
            elif isinstance(node.func, ast.Attribute):
                calls.append({
                    "name": _attribute_name(node.func),
                    "line": node.lineno,
                })
    return calls


# --- Py4J Bridge Detection ---
# Recognizes patterns like:
#   spark._jvm.com.example.MyClass()
#   sc._jvm.org.apache.spark.MyHelper.doWork()
#   self._jvm.com.company.Pipeline.run(df._jdf)
#   gateway.jvm.scala.collection.mutable.ListBuffer()

PY4J_GATEWAY_NAMES = {"_jvm", "jvm"}
# Skip well-known framework JVM packages — they're not user Scala code
PY4J_FRAMEWORK_PREFIXES = (
    "org.apache.spark.",
    "org.apache.hadoop.",
    "org.apache.kafka.",
    "scala.",
    "java.",
    "javax.",
    "org.apache.",
)


def _attribute_chain(node):
    """Walk an Attribute chain and return the list of attribute names + the leftmost base name."""
    parts = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    base = None
    if isinstance(current, ast.Name):
        base = current.id
    return list(reversed(parts)), base


def detect_py4j_bridges(tree: ast.AST, source: str) -> list:
    """
    Detect Py4J bridge patterns where Python code invokes Scala/Java JVM classes.

    Returns a list of bridge dicts:
      [
        {
          "kind": "instantiate" | "method_call" | "static_access",
          "jvm_path": "com.example.MyClass",
          "method": "doWork" or None,
          "gateway": "_jvm" or "jvm",
          "line": 42,
          "is_framework": False  # True if it's Spark/Hadoop/Java internals
        }, ...
      ]
    """
    bridges = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue

        # Build the full attribute chain
        parts, base = _attribute_chain(node.func)
        if not parts:
            continue

        # Find _jvm or .jvm in the chain
        gateway_idx = None
        for i, p in enumerate(parts):
            if p in PY4J_GATEWAY_NAMES:
                gateway_idx = i
                break
        # Also check if base name itself is .jvm via something like spark._jvm
        # parts already contains _jvm in that case

        if gateway_idx is None:
            continue

        # After the gateway, we have a JVM class path
        jvm_parts = parts[gateway_idx + 1:]
        if not jvm_parts:
            continue

        # The last part might be a method (for static calls) or class name
        # Heuristic: if the last segment is lowercase, it's likely a method;
        # if PascalCase (or has parens treated as constructor), it's a class.
        # For Call nodes, we treat the whole chain as the called thing.
        # Common patterns:
        #   spark._jvm.com.example.MyClass()           -> instantiate MyClass
        #   spark._jvm.com.example.MyClass.doWork()    -> static call doWork
        #   self._jvm.com.example.MyClass.helper(...)  -> static call helper

        is_framework = any(".".join(jvm_parts).startswith(p.rstrip(".")) for p in PY4J_FRAMEWORK_PREFIXES)

        # If the last segment starts with uppercase, treat as constructor
        if jvm_parts[-1] and jvm_parts[-1][0].isupper():
            kind = "instantiate"
            jvm_path = ".".join(jvm_parts)
            method = None
        else:
            # static method call: last segment is the method, rest is the class path
            kind = "method_call"
            method = jvm_parts[-1]
            jvm_path = ".".join(jvm_parts[:-1])

        bridges.append({
            "kind": kind,
            "jvm_path": jvm_path,
            "method": method,
            "gateway": parts[gateway_idx],
            "line": node.lineno,
            "is_framework": is_framework,
        })

    return bridges


def _decorator_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return _attribute_name(node)
    elif isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return ""


def _attribute_name(node: ast.Attribute) -> str:
    parts = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts))


def analyze_file(filepath: str, project_root: str) -> dict:
    """Analyze a single Python file and extract all code entities."""
    rel_path = os.path.relpath(filepath, project_root)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
    except (OSError, IOError, UnicodeDecodeError) as e:
        return {"file": rel_path, "error": str(e), "nodes": [], "edges": []}

    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError as e:
        return {"file": rel_path, "error": f"SyntaxError: {e}", "nodes": [], "edges": []}

    module_docstring = ast.get_docstring(tree) or ""
    imports = extract_imports(tree)
    functions = extract_functions(tree, rel_path)
    classes = extract_classes(tree, rel_path)
    assignments = extract_top_level_assignments(tree)
    py4j_bridges = detect_py4j_bridges(tree, source)
    calls = extract_call_references(tree)
    line_count = len(source.splitlines())

    # Build nodes
    nodes = []
    edges = []

    # Module/file node
    module_name = rel_path.replace("/", ".").replace(".py", "").replace(".__init__", "")
    file_node_id = f"file:{rel_path}"
    nodes.append({
        "id": file_node_id,
        "type": "file",
        "name": Path(rel_path).name,
        "file": rel_path,
        "summary": module_docstring[:200] if module_docstring else "",
        "language": "python",
        "lines": line_count,
        "complexity": "simple" if line_count < 50 else ("moderate" if line_count < 200 else "complex"),
        "tags": [],
    })

    # Function nodes
    for func in functions:
        func_id = f"function:{rel_path}:{func['name']}"
        nodes.append({
            "id": func_id,
            "type": "function",
            "name": func["name"],
            "file": rel_path,
            "line_start": func["line_start"],
            "line_end": func["line_end"],
            "args": func["args"],
            "decorators": func["decorators"],
            "is_async": func["is_async"],
            "summary": func["docstring"][:200] if func["docstring"] else "",
            "complexity": "simple" if (func["line_end"] - func["line_start"]) < 20 else "moderate",
            "tags": [],
        })
        edges.append({
            "source": file_node_id,
            "target": func_id,
            "type": "contains",
            "direction": "forward",
            "weight": 1.0,
        })

    # Class nodes
    for cls in classes:
        cls_id = f"class:{rel_path}:{cls['name']}"
        nodes.append({
            "id": cls_id,
            "type": "class",
            "name": cls["name"],
            "file": rel_path,
            "line_start": cls["line_start"],
            "line_end": cls["line_end"],
            "bases": cls["bases"],
            "methods": [m["name"] for m in cls["methods"]],
            "summary": cls["docstring"][:200] if cls["docstring"] else "",
            "complexity": "moderate" if len(cls["methods"]) < 10 else "complex",
            "tags": [],
        })
        edges.append({
            "source": file_node_id,
            "target": cls_id,
            "type": "contains",
            "direction": "forward",
            "weight": 1.0,
        })

        # Method nodes
        for method in cls["methods"]:
            method_id = f"function:{rel_path}:{cls['name']}.{method['name']}"
            nodes.append({
                "id": method_id,
                "type": "function",
                "name": f"{cls['name']}.{method['name']}",
                "file": rel_path,
                "line_start": method["line_start"],
                "line_end": method["line_end"],
                "args": method["args"],
                "decorators": method["decorators"],
                "is_async": method["is_async"],
                "summary": method["docstring"][:200] if method["docstring"] else "",
                "complexity": "simple",
                "tags": [],
            })
            edges.append({
                "source": cls_id,
                "target": method_id,
                "type": "contains",
                "direction": "forward",
                "weight": 1.0,
            })

        # Inheritance edges
        for base in cls["bases"]:
            edges.append({
                "source": cls_id,
                "target": f"class:__external__:{base}",
                "type": "inherits",
                "direction": "forward",
                "weight": 0.8,
            })

    # Import edges
    for imp in imports:
        edges.append({
            "source": file_node_id,
            "target": f"module:{imp['module']}",
            "type": "imports",
            "direction": "forward",
            "weight": 0.7,
            "detail": imp,
        })

    # Annotate the file node with detected Py4J bridges so downstream
    # resolution can create cross-language edges.
    if py4j_bridges:
        for n in nodes:
            if n["id"] == file_node_id:
                n["py4j_bridges"] = py4j_bridges
                break

    return {
        "file": rel_path,
        "module_name": module_name,
        "nodes": nodes,
        "edges": edges,
        "imports": imports,
        "calls": calls,
        "assignments": [a["name"] for a in assignments],
        "py4j_bridges": py4j_bridges,
    }


def extract_codebase(project_root: str, scan_result: dict) -> dict:
    """Extract code entities from all Python files in the project."""
    project_root = os.path.abspath(project_root)
    code_files = [
        f for f in scan_result.get("files", [])
        if f["category"] == "code" and f["language"] == "python"
    ]

    all_nodes = []
    all_edges = []
    file_results = []
    code_registry = {}

    for file_info in code_files:
        filepath = os.path.join(project_root, file_info["path"])
        result = analyze_file(filepath, project_root)
        file_results.append(result)

        all_nodes.extend(result["nodes"])
        all_edges.extend(result["edges"])

        # Build code registry for import resolution
        for node in result["nodes"]:
            if node["type"] in ("function", "class"):
                # Register by module.name pattern
                module_name = result["module_name"]
                entity_name = node["name"].split(".")[-1]  # Handle Class.method
                full_path = f"{module_name}.{entity_name}"
                code_registry[full_path] = {
                    "node_id": node["id"],
                    "type": node["type"],
                    "file": node["file"],
                    "name": node["name"],
                }
                # Also register short name for direct imports
                code_registry[entity_name] = {
                    "node_id": node["id"],
                    "type": node["type"],
                    "file": node["file"],
                    "name": node["name"],
                }

    # Resolve internal import edges (replace module:xxx targets with actual node IDs)
    resolved_edges = []
    for edge in all_edges:
        if edge["type"] == "imports":
            target = edge["target"]
            module_name = target.replace("module:", "")
            # Check if this import points to a local file
            matching_nodes = [
                n for n in all_nodes
                if n["type"] == "file" and n["file"].replace("/", ".").replace(".py", "").replace(".__init__", "") == module_name
            ]
            if matching_nodes:
                edge["target"] = matching_nodes[0]["id"]
                resolved_edges.append(edge)
            else:
                edge["is_external"] = True
                resolved_edges.append(edge)
        else:
            resolved_edges.append(edge)

    # Aggregate Py4J bridge findings across all files
    all_py4j_bridges = []
    for r in file_results:
        for b in r.get("py4j_bridges", []):
            all_py4j_bridges.append({
                **b,
                "source_file": r["file"],
            })

    return {
        "nodes": all_nodes,
        "edges": resolved_edges,
        "code_registry": code_registry,
        "file_results": file_results,
        "py4j_bridges": all_py4j_bridges,
    }


def main():
    parser = argparse.ArgumentParser(description="Lumos Code Extractor")
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

    result = extract_codebase(project_root, scan_result)

    output_path = args.output or os.path.join(
        project_root, ".lumos", "intermediate", "code-extract.json"
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)

    print(json.dumps({
        "status": "success",
        "nodes": len(result["nodes"]),
        "edges": len(result["edges"]),
        "registry_entries": len(result["code_registry"]),
        "output": output_path,
    }))


if __name__ == "__main__":
    main()
