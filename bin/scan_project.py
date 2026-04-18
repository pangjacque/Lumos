#!/usr/bin/env python3
"""
Lumos Project Scanner — Phase 1
Discovers all project files, detects languages, categorizes files.
Outputs structured JSON to .lumos/intermediate/scan-result.json
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

PYTHON_EXTENSIONS = {".py", ".pyi"}
SCALA_EXTENSIONS = {".scala", ".sc"}
NOTEBOOK_EXTENSIONS = {".ipynb"}
DOC_EXTENSIONS = {".md", ".rst", ".txt"}
CONFIG_EXTENSIONS = {".yaml", ".yml", ".toml", ".cfg", ".ini", ".json"}
DATA_EXTENSIONS = {".csv", ".parquet", ".tsv"}

IGNORE_DIRS = {
    "node_modules", ".git", "__pycache__", ".tox", ".mypy_cache",
    ".pytest_cache", "dist", "build", ".eggs", "*.egg-info",
    ".venv", "venv", "env", ".env", ".lumos",
}

IGNORE_FILES = {
    ".DS_Store", "Thumbs.db", "*.pyc", "*.pyo", "*.so", "*.dylib",
}


def file_hash(filepath: str) -> str:
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    except (OSError, IOError):
        return ""
    return h.hexdigest()


def categorize_file(path: str) -> str:
    ext = Path(path).suffix.lower()
    name = Path(path).name.lower()

    if ext in NOTEBOOK_EXTENSIONS:
        return "notebook"
    if ext in PYTHON_EXTENSIONS or ext in SCALA_EXTENSIONS:
        return "code"
    if ext in DOC_EXTENSIONS or name == "readme" or name.startswith("readme"):
        return "doc"
    if ext in CONFIG_EXTENSIONS or name in (
        "makefile", "dockerfile", ".dockerignore", ".gitignore",
        "pyproject.toml", "setup.py", "setup.cfg",
    ):
        return "config"
    if ext in DATA_EXTENSIONS:
        return "data"
    return "other"


def detect_language(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext in PYTHON_EXTENSIONS:
        return "python"
    if ext in SCALA_EXTENSIONS:
        return "scala"
    if ext in NOTEBOOK_EXTENSIONS:
        return "jupyter"
    if ext in DOC_EXTENSIONS:
        return "markdown"
    if ext in {".yaml", ".yml"}:
        return "yaml"
    if ext == ".toml":
        return "toml"
    if ext == ".json":
        return "json"
    return "unknown"


def count_lines(filepath: str) -> int:
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except (OSError, IOError):
        return 0


def should_ignore(path: str, root: str) -> bool:
    rel = os.path.relpath(path, root)
    parts = Path(rel).parts
    for part in parts:
        if part in IGNORE_DIRS:
            return True
        for pattern in IGNORE_DIRS:
            if "*" in pattern and part.endswith(pattern.replace("*", "")):
                return True
    name = Path(path).name
    if name in IGNORE_FILES:
        return True
    for pattern in IGNORE_FILES:
        if "*" in pattern and name.endswith(pattern.replace("*", "")):
            return True
    return False


def discover_files(project_root: str) -> list:
    """Discover files using git ls-files or directory walk."""
    files = []

    # Try git ls-files first
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            capture_output=True, text=True, cwd=project_root, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                filepath = os.path.join(project_root, line)
                if os.path.isfile(filepath) and not should_ignore(filepath, project_root):
                    files.append(line)
            return files
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    # Fallback: walk directory
    for dirpath, dirnames, filenames in os.walk(project_root):
        # Filter out ignored directories in-place
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if not should_ignore(filepath, project_root):
                rel_path = os.path.relpath(filepath, project_root)
                files.append(rel_path)

    return files


def get_git_commit(project_root: str) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=project_root, timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return ""


def scan_project(project_root: str) -> dict:
    project_root = os.path.abspath(project_root)
    raw_files = discover_files(project_root)

    files = []
    languages = {}
    categories = {"code": 0, "notebook": 0, "doc": 0, "config": 0, "data": 0, "other": 0}

    for rel_path in sorted(raw_files):
        abs_path = os.path.join(project_root, rel_path)
        cat = categorize_file(rel_path)
        lang = detect_language(rel_path)
        lines = count_lines(abs_path)
        fhash = file_hash(abs_path)

        file_info = {
            "path": rel_path,
            "category": cat,
            "language": lang,
            "lines": lines,
            "hash": fhash,
        }
        files.append(file_info)
        categories[cat] = categories.get(cat, 0) + 1
        languages[lang] = languages.get(lang, 0) + 1

    return {
        "project_root": project_root,
        "commit": get_git_commit(project_root),
        "total_files": len(files),
        "categories": categories,
        "languages": languages,
        "files": files,
    }


def main():
    parser = argparse.ArgumentParser(description="Lumos Project Scanner")
    parser.add_argument("project_root", nargs="?", default=".",
                        help="Project root directory")
    parser.add_argument("--output", "-o", default=None,
                        help="Output file (default: .lumos/intermediate/scan-result.json)")
    args = parser.parse_args()

    project_root = os.path.abspath(args.project_root)
    result = scan_project(project_root)

    output_path = args.output
    if output_path is None:
        output_dir = os.path.join(project_root, ".lumos", "intermediate")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "scan-result.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(json.dumps({
        "status": "success",
        "total_files": result["total_files"],
        "categories": result["categories"],
        "output": output_path,
    }))


if __name__ == "__main__":
    main()
