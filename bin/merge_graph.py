#!/usr/bin/env python3
"""
Lumos Graph Merger
Merges all extraction outputs into a single knowledge-graph.json.
Deduplicates nodes, resolves dangling edges, builds metadata.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone


def merge_graphs(project_root: str) -> dict:
    """Merge all intermediate outputs into one knowledge graph."""
    intermediate_dir = os.path.join(project_root, ".lumos", "intermediate")

    # Load all intermediate files
    scan_result = {}
    code_extract = {"nodes": [], "edges": []}
    notebook_extract = {"nodes": [], "edges": []}
    doc_extract = {"nodes": [], "edges": []}
    import_resolution = {"cross_boundary_edges": []}

    scan_path = os.path.join(intermediate_dir, "scan-result.json")
    if os.path.exists(scan_path):
        with open(scan_path, "r") as f:
            scan_result = json.load(f)

    code_path = os.path.join(intermediate_dir, "code-extract.json")
    if os.path.exists(code_path):
        with open(code_path, "r") as f:
            code_extract = json.load(f)

    notebook_path = os.path.join(intermediate_dir, "notebook-extract.json")
    if os.path.exists(notebook_path):
        with open(notebook_path, "r") as f:
            notebook_extract = json.load(f)

    doc_path = os.path.join(intermediate_dir, "doc-extract.json")
    if os.path.exists(doc_path):
        with open(doc_path, "r") as f:
            doc_extract = json.load(f)

    resolution_path = os.path.join(intermediate_dir, "import-resolution.json")
    if os.path.exists(resolution_path):
        with open(resolution_path, "r") as f:
            import_resolution = json.load(f)

    # Merge nodes with deduplication
    all_nodes = []
    seen_node_ids = set()

    for source in [code_extract, notebook_extract, doc_extract]:
        for node in source.get("nodes", []):
            if node["id"] not in seen_node_ids:
                seen_node_ids.add(node["id"])
                all_nodes.append(node)

    # Merge edges with deduplication
    all_edges = []
    seen_edge_keys = set()

    for source in [code_extract, notebook_extract, doc_extract]:
        for edge in source.get("edges", []):
            key = (edge["source"], edge["target"], edge["type"])
            if key not in seen_edge_keys:
                seen_edge_keys.add(key)
                all_edges.append(edge)

    # Add cross-boundary edges
    for edge in import_resolution.get("cross_boundary_edges", []):
        key = (edge["source"], edge["target"], edge["type"])
        if key not in seen_edge_keys:
            seen_edge_keys.add(key)
            all_edges.append(edge)

    # Remove dangling edges (edges pointing to non-existent nodes)
    valid_edges = []
    dangling_count = 0
    for edge in all_edges:
        source_exists = edge["source"] in seen_node_ids
        target_exists = edge["target"] in seen_node_ids
        # Allow external/unresolved references
        target_is_ref = edge["target"].startswith(("ref:", "module:", "class:__external__", "magic_run:"))

        if source_exists and (target_exists or target_is_ref):
            valid_edges.append(edge)
        else:
            dangling_count += 1

    # Compute stats
    node_types = {}
    for node in all_nodes:
        t = node["type"]
        node_types[t] = node_types.get(t, 0) + 1

    edge_types = {}
    for edge in valid_edges:
        t = edge["type"]
        edge_types[t] = edge_types.get(t, 0) + 1

    # Build file hashes for incremental updates
    file_hashes = {}
    for f in scan_result.get("files", []):
        file_hashes[f["path"]] = f.get("hash", "")

    # Assemble knowledge graph
    knowledge_graph = {
        "version": "0.1.0",
        "project": {
            "root": scan_result.get("project_root", project_root),
            "commit": scan_result.get("commit", ""),
            "total_files": scan_result.get("total_files", 0),
            "categories": scan_result.get("categories", {}),
            "languages": scan_result.get("languages", {}),
        },
        "nodes": all_nodes,
        "edges": valid_edges,
        "stats": {
            "total_nodes": len(all_nodes),
            "total_edges": len(valid_edges),
            "dangling_edges_removed": dangling_count,
            "node_types": node_types,
            "edge_types": edge_types,
        },
    }

    # Write metadata for incremental updates
    metadata = {
        "last_commit": scan_result.get("commit", ""),
        "last_scan_timestamp": datetime.now(timezone.utc).isoformat(),
        "file_count": scan_result.get("total_files", 0),
        "file_hashes": file_hashes,
    }

    return knowledge_graph, metadata


def main():
    parser = argparse.ArgumentParser(description="Lumos Graph Merger")
    parser.add_argument("project_root", nargs="?", default=".",
                        help="Project root directory")
    args = parser.parse_args()

    project_root = os.path.abspath(args.project_root)
    lumos_dir = os.path.join(project_root, ".lumos")
    os.makedirs(lumos_dir, exist_ok=True)

    knowledge_graph, metadata = merge_graphs(project_root)

    # Write knowledge graph
    graph_path = os.path.join(lumos_dir, "knowledge-graph.json")
    with open(graph_path, "w", encoding="utf-8") as f:
        json.dump(knowledge_graph, f, indent=2, default=str)

    # Write metadata
    metadata_path = os.path.join(lumos_dir, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, default=str)

    print(json.dumps({
        "status": "success",
        "stats": knowledge_graph["stats"],
        "graph_path": graph_path,
        "metadata_path": metadata_path,
    }))


if __name__ == "__main__":
    main()
