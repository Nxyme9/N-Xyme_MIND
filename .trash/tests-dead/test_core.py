#!/usr/bin/env python3
"""Integration tests for N-Xyme_MIND"""

import os
import sys
import subprocess
import importlib.util
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("NX_MIND_PROJECT_DIR", Path(__file__).resolve().parent.parent.parent))


def test_trigger_engine_imports():
    """Test that trigger_engine.py can be imported."""
    try:
        spec = importlib.util.spec_from_file_location(
            "trigger_engine", PROJECT_ROOT / "src" / "orchestration" / "trigger_engine.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        print("✓ trigger_engine imports OK")
        assert True
    except Exception as e:
        print(f"✗ trigger_engine import failed: {e}")
        assert False


def test_trigger_actions_exist():
    """Test that trigger actions are defined."""
    spec = importlib.util.spec_from_file_location(
        "trigger_engine", PROJECT_ROOT / "src" / "orchestration" / "trigger_engine.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    actions = [
        "clean_stale_sessions",
        "clear_db_lock",
        "force_garbage_collection",
        "throttle_ollama",
    ]
    for action in actions:
        if hasattr(module, action):
            print(f"✓ {action} exists")
        else:
            print(f"✗ {action} missing")
            assert False
    assert True


def test_vpn_rotator_cli():
    """Test that VPN rotator CLI works."""
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "vpn" / "rotator.py"), "--list"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    print(f"VPN rotator output: {result.stdout[:200]}")
    assert result.returncode == 0


def test_json_configs_valid():
    """Test that JSON configs are valid."""
    configs = [
        PROJECT_ROOT / "opencode.json",
        PROJECT_ROOT / "triggers.json",
        PROJECT_ROOT / "oh-my-opencode.json",
    ]
    import json

    for config in configs:
        if config.exists():
            with open(config) as f:
                json.load(f)
            print(f"✓ {config.name} valid")
        else:
            print(f"⚠ {config.name} not found")
    assert True
