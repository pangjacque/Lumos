#!/usr/bin/env python3
"""
Lumos Documentation Extractor — Parser 4
Parses markdown documentation, classifies document types (model doc, data dictionary,
design doc, governance, general), extracts sections and code/notebook references.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


# --- Document type detection ---

MODEL_DOC_SIGNALS = [
    "model purpose", "model objective", "methodology", "performance metrics",
    "model performance", "gini", "auc", "roc", "backtesting", "validation",
    "population stability", "psi", "ks statistic", "kolmogorov",
    "feature importance", "model risk", "champion", "challenger",
    "model inventory", "model governance",
]

DATA_DICT_SIGNALS = [
    "data dictionary", "feature name", "feature definition", "data source",
    "variable name", "variable description", "field name", "column name",
    "data type", "source table", "source system",
]

GOVERNANCE_SIGNALS = [
    "approval", "approved by", "review date", "next review", "change log",
    "sign-off", "attestation", "model owner", "model validator",
    "effective date", "supersedes",
]

DESIGN_DOC_SIGNALS = [
    "decision", "alternatives", "trade-off", "architecture", "design",
    "proposal", "rfc", "adr",
]


def classify_document(content: str, filename: str) -> str:
    """Classify document type based on content signals."""
    lower_content = content.lower()
    lower_name = filename.lower()

    # Score each type
    scores = {
        "model_doc": 0,
        "data_dictionary": 0,
        "governance": 0,
        "design_doc": 0,
        "general": 0,
    }

    for signal in MODEL_DOC_SIGNALS:
        if signal in lower_content:
            scores["model_doc"] += 1

    for signal in DATA_DICT_SIGNALS:
        if signal in lower_content:
            scores["data_dictionary"] += 1

    for signal in GOVERNANCE_SIGNALS:
        if signal in lower_content:
            scores["governance"] += 1

    for signal in DESIGN_DOC_SIGNALS:
        if signal in lower_content:
            scores["design_doc"] += 1

    # Filename hints
    if "model" in lower_name and ("doc" in lower_name or "spec" in lower_name):
        scores["model_doc"] += 3
    if "data_dict" in lower_name or "dictionary" in lower_name:
        scores["data_dictionary"] += 3
    if "governance" in lower_name or "approval" in lower_name or "change_log" in lower_name:
        scores["governance"] += 3
    if "design" in lower_name or "adr" in lower_name or "rfc" in lower_name:
        scores["design_doc"] += 3

    # Pick highest score, default to general
    best_type = max(scores, key=scores.get)
    if scores[best_type] < 2:
        return "general"
    return best_type


# --- Section extraction ---

def extract_sections(content: str) -> list:
    """Extract markdown sections with their heading hierarchy."""
    sections = []
    current_section = None
    current_body_lines = []

    for line in content.split("\n"):
        heading_match = re.match(r"^(#{1,6})\s+(.+)", line)
        if heading_match:
            # Save previous section
            if current_section:
                current_section["body"] = "\n".join(current_body_lines).strip()
                sections.append(current_section)

            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()
            current_section = {
                "title": title,
                "level": level,
                "body": "",
            }
            current_body_lines = []
        elif current_section:
            current_body_lines.append(line)

    # Save last section
    if current_section:
        current_section["body"] = "\n".join(current_body_lines).strip()
        sections.append(current_section)

    return sections


# --- Reference extraction ---

# Patterns for code references in documentation
CODE_REF_PATTERNS = [
    # Backtick-quoted paths: `src/metrics.py`
    re.compile(r"`([a-zA-Z_][\w/\-.]*(\.py|\.scala|\.ipynb))`"),
    # Backtick-quoted functions: `gini_coefficient()`
    re.compile(r"`([a-zA-Z_]\w*(?:\.\w+)*)\(\)`"),
    # Backtick-quoted classes/modules: `LogisticModel`
    re.compile(r"`([A-Z]\w+)`"),
    # File path references without backticks: see src/metrics.py
    re.compile(r"(?:see|in|from|at)\s+([a-zA-Z_][\w/\-.]*(\.py|\.scala|\.ipynb))"),
    # Notebook references: notebook_name.ipynb
    re.compile(r"(\w[\w/\-]*\.ipynb)"),
]

# Patterns for metric values
METRIC_PATTERNS = [
    # "Gini: 0.45" or "Gini = 0.45" or "Gini coefficient: 0.45"
    re.compile(r"(gini|auc|roc|psi|ks|accuracy|precision|recall|f1|rmse|mae|mse|r2|r-squared)[\s\w]*[=:]\s*([\d.]+)", re.IGNORECASE),
]


def extract_references(content: str) -> dict:
    """Extract code, notebook, and metric references from documentation."""
    code_refs = []
    notebook_refs = []
    metric_refs = []

    for pattern in CODE_REF_PATTERNS:
        for match in pattern.finditer(content):
            ref = match.group(1)
            if ref.endswith(".ipynb"):
                notebook_refs.append(ref)
            elif ref.endswith(".py") or ref.endswith(".scala"):
                code_refs.append(ref)
            elif ref[0].isupper() or ref.endswith("()"):
                code_refs.append(ref.rstrip("()"))

    for pattern in METRIC_PATTERNS:
        for match in pattern.finditer(content):
            metric_refs.append({
                "name": match.group(1).lower(),
                "value": match.group(2),
            })

    return {
        "code_refs": list(set(code_refs)),
        "notebook_refs": list(set(notebook_refs)),
        "metric_refs": metric_refs,
    }


def extract_section_references(section: dict) -> dict:
    """Extract references from a single section."""
    full_text = f"{section['title']}\n{section['body']}"
    return extract_references(full_text)


# --- Main doc extraction ---

def analyze_document(filepath: str, project_root: str) -> dict:
    """Analyze a single documentation file."""
    rel_path = os.path.relpath(filepath, project_root)

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, IOError, UnicodeDecodeError) as e:
        return {"file": rel_path, "error": str(e), "nodes": [], "edges": []}

    doc_type = classify_document(content, Path(rel_path).name)
    sections = extract_sections(content)
    doc_refs = extract_references(content)

    nodes = []
    edges = []

    # Document node
    doc_id = f"document:{rel_path}"
    nodes.append({
        "id": doc_id,
        "type": "document",
        "name": Path(rel_path).stem,
        "file": rel_path,
        "doc_type": doc_type,
        "summary": "",
        "lines": len(content.splitlines()),
        "section_count": len(sections),
        "references": doc_refs,
        "tags": [doc_type],
    })

    # Section nodes
    for idx, section in enumerate(sections):
        section_id = f"doc_section:{rel_path}:{idx + 1}"
        section_refs = extract_section_references(section)

        nodes.append({
            "id": section_id,
            "type": "doc_section",
            "name": section["title"],
            "file": rel_path,
            "section_index": idx + 1,
            "level": section["level"],
            "body_preview": section["body"][:300],
            "references": section_refs,
            "summary": "",
            "tags": [],
        })

        # Contains edge: document → section
        edges.append({
            "source": doc_id,
            "target": section_id,
            "type": "contains",
            "direction": "forward",
            "weight": 1.0,
        })

        # Reference edges: section → code files
        for code_ref in section_refs["code_refs"]:
            edges.append({
                "source": section_id,
                "target": f"ref:{code_ref}",
                "type": "doc_references_code",
                "direction": "forward",
                "weight": 0.8,
                "detail": {"reference": code_ref},
            })

        # Reference edges: section → notebooks
        for nb_ref in section_refs["notebook_refs"]:
            edges.append({
                "source": section_id,
                "target": f"ref:{nb_ref}",
                "type": "doc_references_notebook",
                "direction": "forward",
                "weight": 0.8,
                "detail": {"reference": nb_ref},
            })

        # Metric definition nodes
        for metric in section_refs["metric_refs"]:
            metric_id = f"metric:{rel_path}:{metric['name']}"
            # Only add if not already present
            if not any(n["id"] == metric_id for n in nodes):
                nodes.append({
                    "id": metric_id,
                    "type": "metric_def",
                    "name": f"{metric['name']} = {metric['value']}",
                    "file": rel_path,
                    "metric_name": metric["name"],
                    "metric_value": metric["value"],
                    "summary": "",
                    "tags": ["metric"],
                })
            edges.append({
                "source": section_id,
                "target": metric_id,
                "type": "defines_metric",
                "direction": "forward",
                "weight": 0.9,
            })

    return {
        "file": rel_path,
        "doc_type": doc_type,
        "nodes": nodes,
        "edges": edges,
        "references": doc_refs,
    }


def extract_docs(project_root: str, scan_result: dict) -> dict:
    """Extract all documentation files in the project."""
    project_root = os.path.abspath(project_root)
    doc_files = [
        f for f in scan_result.get("files", [])
        if f["category"] == "doc"
    ]

    all_nodes = []
    all_edges = []
    doc_results = []

    for file_info in doc_files:
        filepath = os.path.join(project_root, file_info["path"])
        result = analyze_document(filepath, project_root)
        doc_results.append(result)
        all_nodes.extend(result["nodes"])
        all_edges.extend(result["edges"])

    return {
        "nodes": all_nodes,
        "edges": all_edges,
        "doc_results": doc_results,
    }


def main():
    parser = argparse.ArgumentParser(description="Lumos Documentation Extractor")
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

    result = extract_docs(project_root, scan_result)

    output_path = args.output or os.path.join(
        project_root, ".lumos", "intermediate", "doc-extract.json"
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)

    print(json.dumps({
        "status": "success",
        "nodes": len(result["nodes"]),
        "edges": len(result["edges"]),
        "output": output_path,
    }))


if __name__ == "__main__":
    main()
