"""Smoke tests — verify config files are valid JSON."""

import json
import os
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_opencode_json_valid():
    with open(os.path.join(ROOT, "opencode.json")) as f:
        config = json.load(f)
    assert "mcp" in config


def test_oh_my_opencode_json_valid():
    pytest.skip("oh-my-opencode.json not present in this repo", allow_module_level=True)
    with open(os.path.join(ROOT, "oh-my-opencode.json")) as f:
        config = json.load(f)
    assert "$schema" in config


def test_agents_md_exists():
    path = os.path.join(ROOT, "AGENTS.md")
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()
    assert len(content) > 100


def test_env_example_exists():
    path = os.path.join(ROOT, ".env.example")
    assert os.path.exists(path)
