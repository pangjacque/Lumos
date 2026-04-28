#!/usr/bin/env python3
"""
Lumos Scala Extractor — Parser 1 (Scala)
Walks .scala files using tree-sitter, extracts package, object, class, trait,
function, and import structure. Produces code nodes and edges compatible with
the Python code extractor output.
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import tree_sitter_scala as tsscala
    from tree_sitter import Language, Parser, Node
    SCALA_LANGUAGE = Language(tsscala.language())
    parser = Parser(SCALA_LANGUAGE)
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    Node = object  # placeholder for type hints below
except ValueError as e:
    # Version mismatch between tree-sitter and tree-sitter-scala
    print(f"Warning: tree-sitter version mismatch ({e}). "
          "Pin compatible versions in requirements.txt.", file=sys.stderr)
    TREE_SITTER_AVAILABLE = False
    Node = object


def node_text(node: Node, source_bytes: bytes) -> str:
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def find_children(node: Node, type_name: str) -> list:
    return [c for c in node.children if c.type == type_name]


def find_descendant_field(node: Node, field_name: str):
    """Get a child by field name (tree-sitter named field)."""
    return node.child_by_field_name(field_name)


def extract_package(tree_root: Node, source_bytes: bytes) -> str:
    """Extract package declaration from a Scala file."""
    for node in tree_root.children:
        if node.type == "package_clause":
            name_node = node.child_by_field_name("name")
            if name_node:
                return node_text(name_node, source_bytes)
    return ""


def extract_imports(tree_root: Node, source_bytes: bytes) -> list:
    """Extract all import statements."""
    imports = []
    for node in walk_nodes(tree_root):
        if node.type == "import_declaration":
            text = node_text(node, source_bytes)
            text = text.replace("import", "").strip().rstrip(";").strip()
            imports.append({
                "type": "import",
                "module": text,
                "name": text.split(".")[-1] if "." in text else text,
                "line": node.start_point[0] + 1,
            })
    return imports


def walk_nodes(node: Node):
    """Recursively walk all nodes."""
    yield node
    for child in node.children:
        yield from walk_nodes(child)


def get_name(node: Node, source_bytes: bytes) -> str:
    """Try to extract the name field from a definition node."""
    name_node = node.child_by_field_name("name")
    if name_node:
        return node_text(name_node, source_bytes)
    # Fallback: look for an identifier child
    for child in node.children:
        if child.type == "identifier" or child.type == "operator_identifier":
            return node_text(child, source_bytes)
    return ""


def get_parameters(node: Node, source_bytes: bytes) -> list:
    """Extract parameter names from a function/method definition."""
    params = []
    param_list = node.child_by_field_name("parameters")
    if not param_list:
        # Try parameter_clauses for curried defs
        for child in node.children:
            if child.type == "parameters" or child.type == "parameter_clauses":
                param_list = child
                break
    if not param_list:
        return params
    for child in walk_nodes(param_list):
        if child.type == "parameter":
            name_node = child.child_by_field_name("name")
            if name_node:
                params.append(node_text(name_node, source_bytes))
    return params


def get_extends(node: Node, source_bytes: bytes) -> list:
    """Extract base classes/traits from a class/object/trait definition."""
    bases = []
    extends_node = node.child_by_field_name("extend") or node.child_by_field_name("extends")
    if extends_node:
        for child in walk_nodes(extends_node):
            if child.type in ("type_identifier", "stable_type_identifier", "generic_type"):
                text = node_text(child, source_bytes)
                if text and text not in bases:
                    bases.append(text)
                    break  # Just take the first type
    # Fallback: look for extends keyword followed by type
    for i, child in enumerate(node.children):
        if child.type == "extends_clause":
            for sub in walk_nodes(child):
                if sub.type in ("type_identifier", "stable_type_identifier"):
                    text = node_text(sub, source_bytes)
                    if text and text not in bases:
                        bases.append(text)
    return bases


def extract_definitions(tree_root: Node, source_bytes: bytes, filepath: str, package: str) -> dict:
    """Extract classes, objects, traits, and functions from the file."""
    classes = []
    functions = []
    objects = []
    traits = []

    # Top-level definitions
    for node in walk_nodes(tree_root):
        ntype = node.type

        if ntype == "class_definition":
            name = get_name(node, source_bytes)
            if not name:
                continue
            # Methods inside the class
            methods = []
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    if child.type == "function_definition":
                        m_name = get_name(child, source_bytes)
                        if m_name:
                            methods.append({
                                "name": m_name,
                                "line_start": child.start_point[0] + 1,
                                "line_end": child.end_point[0] + 1,
                                "args": get_parameters(child, source_bytes),
                            })
            classes.append({
                "name": name,
                "type": "class",
                "file": filepath,
                "line_start": node.start_point[0] + 1,
                "line_end": node.end_point[0] + 1,
                "bases": get_extends(node, source_bytes),
                "methods": methods,
            })

        elif ntype == "object_definition":
            name = get_name(node, source_bytes)
            if not name:
                continue
            methods = []
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    if child.type == "function_definition":
                        m_name = get_name(child, source_bytes)
                        if m_name:
                            methods.append({
                                "name": m_name,
                                "line_start": child.start_point[0] + 1,
                                "line_end": child.end_point[0] + 1,
                                "args": get_parameters(child, source_bytes),
                            })
            objects.append({
                "name": name,
                "type": "object",
                "file": filepath,
                "line_start": node.start_point[0] + 1,
                "line_end": node.end_point[0] + 1,
                "bases": get_extends(node, source_bytes),
                "methods": methods,
            })

        elif ntype == "trait_definition":
            name = get_name(node, source_bytes)
            if not name:
                continue
            methods = []
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    if child.type == "function_definition":
                        m_name = get_name(child, source_bytes)
                        if m_name:
                            methods.append({
                                "name": m_name,
                                "line_start": child.start_point[0] + 1,
                                "line_end": child.end_point[0] + 1,
                                "args": get_parameters(child, source_bytes),
                            })
            traits.append({
                "name": name,
                "type": "trait",
                "file": filepath,
                "line_start": node.start_point[0] + 1,
                "line_end": node.end_point[0] + 1,
                "bases": get_extends(node, source_bytes),
                "methods": methods,
            })

    # Top-level functions (not inside class/object/trait)
    for child in tree_root.children:
        if child.type == "function_definition":
            name = get_name(child, source_bytes)
            if name:
                functions.append({
                    "name": name,
                    "type": "function",
                    "file": filepath,
                    "line_start": child.start_point[0] + 1,
                    "line_end": child.end_point[0] + 1,
                    "args": get_parameters(child, source_bytes),
                })

    return {
        "classes": classes,
        "objects": objects,
        "traits": traits,
        "functions": functions,
    }


def analyze_file(filepath: str, project_root: str) -> dict:
    """Analyze a single Scala file and extract all code entities."""
    rel_path = os.path.relpath(filepath, project_root).replace(os.sep, "/")
    try:
        with open(filepath, "rb") as f:
            source_bytes = f.read()
    except (OSError, IOError) as e:
        return {"file": rel_path, "error": str(e), "nodes": [], "edges": []}

    try:
        tree = parser.parse(source_bytes)
    except Exception as e:
        return {"file": rel_path, "error": f"ParseError: {e}", "nodes": [], "edges": []}

    package = extract_package(tree.root_node, source_bytes)
    imports = extract_imports(tree.root_node, source_bytes)
    defs = extract_definitions(tree.root_node, source_bytes, rel_path, package)
    line_count = source_bytes.count(b"\n") + 1

    nodes = []
    edges = []
    file_node_id = f"file:{rel_path}"
    module_name = package or rel_path.replace("/", ".").replace(".scala", "")

    nodes.append({
        "id": file_node_id,
        "type": "file",
        "name": Path(rel_path).name,
        "file": rel_path,
        "summary": "",
        "language": "scala",
        "package": package,
        "lines": line_count,
        "complexity": "simple" if line_count < 50 else ("moderate" if line_count < 200 else "complex"),
        "tags": [],
    })

    # Class/object/trait nodes (all rendered as "class" type for graph compatibility)
    for entity_list, entity_kind in [
        (defs["classes"], "class"),
        (defs["objects"], "class"),  # Treat object as class for graph
        (defs["traits"], "class"),   # Treat trait as class for graph
    ]:
        for ent in entity_list:
            ent_id = f"class:{rel_path}:{ent['name']}"
            nodes.append({
                "id": ent_id,
                "type": entity_kind,
                "name": ent["name"],
                "file": rel_path,
                "language": "scala",
                "package": package,
                "line_start": ent["line_start"],
                "line_end": ent["line_end"],
                "bases": ent.get("bases", []),
                "methods": [m["name"] for m in ent.get("methods", [])],
                "scala_kind": ent["type"],  # original kind: class/object/trait
                "summary": "",
                "complexity": "moderate" if len(ent.get("methods", [])) < 10 else "complex",
                "tags": [],
            })
            edges.append({
                "source": file_node_id,
                "target": ent_id,
                "type": "contains",
                "direction": "forward",
                "weight": 1.0,
            })

            # Method nodes
            for m in ent.get("methods", []):
                m_id = f"function:{rel_path}:{ent['name']}.{m['name']}"
                nodes.append({
                    "id": m_id,
                    "type": "function",
                    "name": f"{ent['name']}.{m['name']}",
                    "file": rel_path,
                    "line_start": m["line_start"],
                    "line_end": m["line_end"],
                    "args": m.get("args", []),
                    "summary": "",
                    "complexity": "simple",
                    "tags": [],
                })
                edges.append({
                    "source": ent_id,
                    "target": m_id,
                    "type": "contains",
                    "direction": "forward",
                    "weight": 1.0,
                })

            # Inheritance edges
            for base in ent.get("bases", []):
                edges.append({
                    "source": ent_id,
                    "target": f"class:__external__:{base}",
                    "type": "inherits",
                    "direction": "forward",
                    "weight": 0.8,
                })

    # Top-level functions
    for func in defs["functions"]:
        func_id = f"function:{rel_path}:{func['name']}"
        nodes.append({
            "id": func_id,
            "type": "function",
            "name": func["name"],
            "file": rel_path,
            "line_start": func["line_start"],
            "line_end": func["line_end"],
            "args": func.get("args", []),
            "summary": "",
            "complexity": "simple",
            "tags": [],
        })
        edges.append({
            "source": file_node_id,
            "target": func_id,
            "type": "contains",
            "direction": "forward",
            "weight": 1.0,
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

    return {
        "file": rel_path,
        "package": package,
        "module_name": module_name,
        "nodes": nodes,
        "edges": edges,
        "imports": imports,
    }


def extract_scala_codebase(project_root: str, scan_result: dict) -> dict:
    """Extract code entities from all Scala files in the project."""
    project_root = os.path.abspath(project_root)
    scala_files = [
        f for f in scan_result.get("files", [])
        if f["category"] == "code" and f["language"] == "scala"
    ]

    if not scala_files:
        return {"nodes": [], "edges": [], "code_registry": {}, "file_results": [], "skipped": "no_scala_files"}

    if not TREE_SITTER_AVAILABLE:
        return {
            "nodes": [], "edges": [], "code_registry": {}, "file_results": [],
            "skipped": "tree_sitter_unavailable",
            "message": "tree-sitter or tree-sitter-scala not installed. Install with: pip install -r bin/requirements.txt",
        }

    all_nodes = []
    all_edges = []
    file_results = []
    code_registry = {}

    for file_info in scala_files:
        filepath = os.path.join(project_root, file_info["path"])
        result = analyze_file(filepath, project_root)
        file_results.append(result)
        all_nodes.extend(result["nodes"])
        all_edges.extend(result["edges"])

        for node in result["nodes"]:
            if node["type"] in ("function", "class"):
                module_name = result["module_name"]
                entity_name = node["name"].split(".")[-1]
                full_path = f"{module_name}.{entity_name}"
                code_registry[full_path] = {
                    "node_id": node["id"],
                    "type": node["type"],
                    "file": node["file"],
                    "name": node["name"],
                }
                code_registry[entity_name] = {
                    "node_id": node["id"],
                    "type": node["type"],
                    "file": node["file"],
                    "name": node["name"],
                }

    return {
        "nodes": all_nodes,
        "edges": all_edges,
        "code_registry": code_registry,
        "file_results": file_results,
    }


def main():
    ap = argparse.ArgumentParser(description="Lumos Scala Extractor")
    ap.add_argument("project_root", nargs="?", default=".", help="Project root directory")
    ap.add_argument("--scan-result", default=None, help="Path to scan-result.json")
    ap.add_argument("--output", "-o", default=None, help="Output file")
    args = ap.parse_args()

    project_root = os.path.abspath(args.project_root)
    scan_path = args.scan_result or os.path.join(
        project_root, ".lumos", "intermediate", "scan-result.json"
    )
    with open(scan_path, "r") as f:
        scan_result = json.load(f)

    result = extract_scala_codebase(project_root, scan_result)

    output_path = args.output or os.path.join(
        project_root, ".lumos", "intermediate", "scala-extract.json"
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)

    print(json.dumps({
        "status": "success",
        "nodes": len(result["nodes"]),
        "edges": len(result["edges"]),
        "registry_entries": len(result["code_registry"]),
        "files_analyzed": len(result["file_results"]),
        "output": output_path,
    }))


if __name__ == "__main__":
    main()
