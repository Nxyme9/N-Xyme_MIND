#!/usr/bin/env python3
"""
Block Registry Scanner for Enzyme Ecosystem
Scans Python files and builds a registry of blocks (functions/classes).
"""

import ast
import os
import sqlite3
from pathlib import Path
from typing import Any


# Configuration
SRC_DIR = r"D:\01_CODING\00_N-Xyme_CATALYST\src"
SCRIPTS_DIR = r"D:\01_CODING\00_N-Xyme_CATALYST\scripts"
DB_PATH = r"D:\01_CODING\00_N-Xyme_CATALYST\data\block_registry.db"

# Skip patterns
SKIP_DIRS = {"__pycache__", "node_modules", ".git", ".venv", "venv", "env"}
MIN_LINES = 10
MIN_WORKING_FUNCTIONS = 3


def init_db(conn: sqlite3.Connection) -> None:
    """Initialize database schema."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            path TEXT NOT NULL,
            source TEXT NOT NULL,
            language TEXT NOT NULL,
            signatures TEXT,
            imports TEXT,
            lines INTEGER,
            status TEXT DEFAULT 'unknown',
            description TEXT DEFAULT ''
        )
    """)
    conn.commit()


def is_stub_function(node: ast.FunctionDef) -> bool:
    """Check if a function is a stub (only pass, return {}, or docstring)."""
    # Check if it has a body
    if not node.body:
        return True

    # If only docstring or pass statements, it's a stub
    non_whitespace_lines = 0
    for stmt in node.body:
        # Skip docstring
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
            continue
        # Count meaningful statements
        if not isinstance(stmt, (ast.Pass, ast.Return)):
            non_whitespace_lines += 1
        elif isinstance(stmt, ast.Return):
            # Check if return {} or return None
            if stmt.value and not (
                isinstance(stmt.value, ast.Constant) and stmt.value.value is None
            ):
                non_whitespace_lines += 1

    return non_whitespace_lines == 0


def extract_imports(tree: ast.AST) -> list[str]:
    """Extract all import statements from AST."""
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                if module:
                    imports.append(f"{module}.{alias.name}")
                else:
                    imports.append(alias.name)
    return imports


def extract_signatures(node: ast.FunctionDef | ast.ClassDef) -> str:
    """Extract function/class signature."""
    if isinstance(node, ast.FunctionDef):
        args = node.args
        params = []

        # Regular args
        for arg in args.args:
            params.append(arg.arg)

        # *args
        if args.vararg:
            params.append(f"*{args.vararg.arg}")

        # **kwargs
        if args.kwarg:
            params.append(f"**{args.kwarg.arg}")

        # Defaults
        defaults = args.defaults
        args_list = args.args
        if defaults and args_list:
            # Map defaults to last N args
            offset = len(args_list) - len(defaults)
            for i, default in enumerate(defaults):
                if isinstance(default, ast.Constant):
                    default_val = repr(default.value)
                elif isinstance(default, ast.Name):
                    default_val = default.id
                else:
                    default_val = "..."
                params[offset + i] += f"={default_val}"

        return f"def {node.name}({', '.join(params)})"

    elif isinstance(node, ast.ClassDef):
        # Get base classes
        bases = [
            base if isinstance(base, str) else base.attr if hasattr(base, "attr") else str(base)
            for base in node.bases
        ]
        bases_str = f"({', '.join(bases)})" if bases else ""
        return f"class {node.name}{bases_str}"

    return ""


def get_docstring(node: ast.FunctionDef | ast.ClassDef) -> str:
    """Extract docstring from node."""
    if node.body and isinstance(node.body[0], ast.Expr):
        doc_node = node.body[0].value
        if isinstance(doc_node, ast.Constant) and isinstance(doc_node.value, str):
            return doc_node.value.strip()
    return ""


def analyze_file(filepath: Path) -> dict[str, Any] | None:
    """Analyze a single Python file and return block info."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None

    lines = content.count("\n") + 1
    if lines < MIN_LINES:
        return None

    try:
        tree = ast.parse(content, filename=str(filepath))
    except SyntaxError:
        return None

    imports = extract_imports(tree)

    # Extract top-level functions and classes
    functions = []
    classes = []

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            functions.append(node)
        elif isinstance(node, ast.ClassDef):
            classes.append(node)

    # Count non-stub functions
    working_funcs = sum(1 for f in functions if not is_stub_function(f))

    # Determine status
    if working_funcs >= MIN_WORKING_FUNCTIONS:
        status = "working"
    elif functions or classes:
        status = "stub"
    else:
        status = "unknown"

    # Build signatures and descriptions
    all_nodes = functions + classes
    signatures = []
    descriptions = []

    for node in all_nodes:
        sig = extract_signatures(node)
        if sig:
            signatures.append(sig)
        desc = get_docstring(node)
        if desc:
            # Truncate long docstrings
            desc = desc[:200] + "..." if len(desc) > 200 else desc
            descriptions.append(desc)

    # Determine source directory
    source = "src" if "src" in str(filepath) else "scripts"

    return {
        "name": filepath.stem,
        "path": str(filepath),
        "source": source,
        "language": "python",
        "signatures": "\n".join(signatures) if signatures else None,
        "imports": "\n".join(imports) if imports else None,
        "lines": lines,
        "status": status,
        "description": " | ".join(descriptions[:3]) if descriptions else "",
    }


def scan_directory(conn: sqlite3.Connection, directory: Path) -> tuple[int, int, int]:
    """Scan a directory for Python files."""
    total = 0
    working = 0
    stubs = 0

    for root, dirs, files in os.walk(directory):
        # Remove skip directories in-place
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for filename in files:
            if filename.endswith(".py"):
                filepath = Path(root) / filename
                total += 1

                block_info = analyze_file(filepath)
                if block_info:
                    # Insert into database
                    conn.execute(
                        """
                        INSERT INTO blocks (name, path, source, language, signatures, imports, lines, status, description)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            block_info["name"],
                            block_info["path"],
                            block_info["source"],
                            block_info["language"],
                            block_info["signatures"],
                            block_info["imports"],
                            block_info["lines"],
                            block_info["status"],
                            block_info["description"],
                        ),
                    )

                    if block_info["status"] == "working":
                        working += 1
                    elif block_info["status"] == "stub":
                        stubs += 1

    return total, working, stubs


def main():
    """Main entry point."""
    print("=" * 60)
    print("Block Registry Scanner for Enzyme Ecosystem")
    print("=" * 60)

    # Ensure data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    # Connect to database
    conn = sqlite3.Connection(DB_PATH)

    # Initialize schema
    init_db(conn)

    # Clear existing data (optional - remove if you want to append)
    conn.execute("DELETE FROM blocks")
    conn.commit()

    print(f"\nScanning: {SRC_DIR}")
    src_total, src_working, src_stubs = scan_directory(conn, Path(SRC_DIR))
    print(f"  Found: {src_total} files | Working: {src_working} | Stubs: {src_stubs}")

    print(f"\nScanning: {SCRIPTS_DIR}")
    scripts_total, scripts_working, scripts_stubs = scan_directory(conn, Path(SCRIPTS_DIR))
    print(f"  Found: {scripts_total} files | Working: {scripts_working} | Stubs: {scripts_stubs}")

    # Commit all changes
    conn.commit()

    # Final summary
    total_blocks = src_total + scripts_total
    total_working = src_working + scripts_working
    total_stubs = src_stubs + scripts_stubs

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total blocks scanned: {total_blocks}")
    print(f"  Working (real code):  {total_working}")
    print(f"  Stubs (pass/return): {total_stubs}")
    print(f"  Database: {DB_PATH}")
    print("=" * 60)

    conn.close()


if __name__ == "__main__":
    main()
