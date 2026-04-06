#!/usr/bin/env python3
"""Standalone verification tests for N-Xyme_MIND."""

import os
import sys
import subprocess
import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()


def test_no_hardcoded_home_paths():
    """No file should contain hardcoded /home/nxyme paths used for actual I/O.

    Note: Migration scripts, modelrouter/, scripts/, and test files are excluded
    as they may reference external data locations or be one-off utilities.
    """
    violations = []
    skip_dirs = {
        "venv",
        ".venv",
        "modelrouter",
        "scripts",
        "tests",
        "packages",
        "athena",
        "migrations",
    }

    for py_file in PROJECT_ROOT.rglob("*.py"):
        parts = py_file.parts
        if any(d in skip_dirs for d in parts):
            continue

        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#") or "os.environ" in line or "getenv" in line:
                continue
            if "/home/nxyme" in line:
                violations.append(f"{py_file.relative_to(PROJECT_ROOT)}:{i}")

    assert len(violations) == 0, f"Found hardcoded paths in: {violations}"


def test_no_hardcoded_mnt_library_paths():
    """No core src/ file should contain hardcoded /mnt/Library paths used for I/O.

    Note: Migration scripts are excluded as they reference old data locations.
    """
    violations = []
    target = "/mnt/Library"
    skip_dirs = {"venv", ".venv", "scripts", "tests", "migrations", "packages"}

    for py_file in PROJECT_ROOT.rglob("*.py"):
        parts = py_file.parts
        if any(d in skip_dirs for d in parts):
            continue

        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#") or "os.environ" in line or "getenv" in line:
                continue
            if target in line:
                violations.append(f"{py_file.relative_to(PROJECT_ROOT)}:{i}")

    assert len(violations) == 0, f"Found /mnt/Library paths in: {violations}"


def test_pyproject_toml_exists_and_valid():
    """pyproject.toml should exist and be valid."""
    pyproject = PROJECT_ROOT / "pyproject.toml"
    assert pyproject.exists(), "pyproject.toml missing"

    content = pyproject.read_text()
    assert "[project]" in content, "Missing [project] section"
    assert "dependencies" in content, "Missing dependencies"


def test_opencode_json_valid():
    """opencode.json should be valid JSON."""
    config = PROJECT_ROOT / "opencode.json"
    assert config.exists(), "opencode.json missing"

    with open(config) as f:
        data = json.load(f)

    assert "mcp" in data, "Missing 'mcp' section"


def test_mcp_servers_importable():
    """All MCP servers should be importable from main venv."""
    venv_python = PROJECT_ROOT / "venv" / "bin" / "python"

    if not venv_python.exists():
        venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"

    if not venv_python.exists():
        pytest.skip("venv not found - run bootstrap.sh first")

    mcps = [
        "athena_context_mcp",
        "trigger_guardian_mcp",
        "nx_mind_mcp",
    ]

    for mcp in mcps:
        result = subprocess.run(
            [str(venv_python), "-c", f"import {mcp}"],
            capture_output=True,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0, (
            f"Failed to import {mcp}: {result.stderr.decode()}"
        )


def test_n_xyme_mind_sh_syntax():
    """n-xyme-mind.sh should have valid bash syntax."""
    script = PROJECT_ROOT / "n-xyme-mind.sh"
    assert script.exists(), "n-xyme-mind.sh missing"

    result = subprocess.run(["bash", "-n", str(script)], capture_output=True)
    assert result.returncode == 0, f"Syntax error: {result.stderr.decode()}"


def test_bootstrap_sh_syntax():
    """bootstrap.sh should have valid bash syntax."""
    script = PROJECT_ROOT / "bootstrap.sh"
    assert script.exists(), "bootstrap.sh missing"

    result = subprocess.run(["bash", "-n", str(script)], capture_output=True)
    assert result.returncode == 0, f"Syntax error: {result.stderr.decode()}"


def test_single_venv_exists():
    """Main venv directory should exist."""
    main_venv = PROJECT_ROOT / "venv"
    assert main_venv.exists(), "Main venv missing - run bootstrap.sh"


def test_pyproject_toml_has_required_deps():
    """pyproject.toml should have fastmcp and pyyaml."""
    pyproject = PROJECT_ROOT / "pyproject.toml"
    content = pyproject.read_text()

    assert "fastmcp" in content, "Missing fastmcp dependency"
    assert "pyyaml" in content, "Missing pyyaml dependency"


def test_memory_registry_no_external_paths():
    """src/memory/registry.py should use env vars, not hardcoded paths."""
    registry = PROJECT_ROOT / "src" / "memory" / "registry.py"

    if not registry.exists():
        pytest.skip("registry.py not found")

    content = registry.read_text()

    assert "os.environ" in content or "os.getenv" in content, (
        "registry.py should use environment variables"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
