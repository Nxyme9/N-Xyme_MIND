"""
Tests for filesystem sandbox and security policy modules.

Run: python -m pytest tests/test_sandbox.py -v
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.security.sandbox import (
    AccessDeniedError,
    AccessLevel,
    FilesystemSandbox,
    PathTraversalError,
    SymlinkError,
    ValidationResult,
)
from src.security.policy import AgentPolicy, SecurityPolicy


# ── ValidationResult Tests ────────────────────────────────────────────


def test_validation_result_to_dict():
    result = ValidationResult(
        allowed=True,
        path="/tmp/test",
        resolved_path="/tmp/test",
        access_level=AccessLevel.READ,
        agent_type="explore",
    )
    d = result.to_dict()
    assert d["allowed"] is True
    assert d["path"] == "/tmp/test"
    assert d["access_level"] == "read"
    assert d["agent_type"] == "explore"


def test_validation_result_to_json():
    result = ValidationResult(
        allowed=False,
        path="/etc/passwd",
        reason="Path not in allowed paths",
        agent_type="hephaestus",
    )
    j = result.to_json()
    parsed = json.loads(j)
    assert parsed["allowed"] is False
    assert parsed["reason"] == "Path not in allowed paths"


# ── FilesystemSandbox — Path Traversal Prevention ────────────────────


def test_sandbox_blocks_path_traversal():
    sandbox = FilesystemSandbox(workspace_root="/workspace")
    sandbox.set_policy("explore", allowed_paths=["/workspace/src"])
    result = sandbox.validate_path("/workspace/src/../../../etc/passwd", "explore")
    assert not result.allowed
    assert "traversal" in result.reason.lower()


def test_sandbox_blocks_double_dot_traversal():
    sandbox = FilesystemSandbox(workspace_root="/workspace")
    sandbox.set_policy("explore", allowed_paths=["/workspace/src"])
    result = sandbox.validate_path("../../../etc/shadow", "explore")
    assert not result.allowed


def test_sandbox_allows_normal_path():
    sandbox = FilesystemSandbox(workspace_root="/workspace")
    sandbox.set_policy("explore", allowed_paths=["/workspace/src"])
    result = sandbox.validate_path("/workspace/src/main.py", "explore")
    assert result.allowed
    assert result.resolved_path == "/workspace/src/main.py"


# ── FilesystemSandbox — Path Validation ──────────────────────────────


def test_sandbox_blocks_path_outside_allowed():
    sandbox = FilesystemSandbox(workspace_root="/workspace")
    sandbox.set_policy("hephaestus", allowed_paths=["/workspace/src"])
    result = sandbox.validate_path("/workspace/docs/readme.md", "hephaestus")
    assert not result.allowed
    assert "not in allowed" in result.reason.lower()


def test_sandbox_allows_path_within_allowed():
    sandbox = FilesystemSandbox(workspace_root="/workspace")
    sandbox.set_policy(
        "hephaestus", allowed_paths=["/workspace/src", "/workspace/tests"]
    )
    result = sandbox.validate_path("/workspace/tests/test_main.py", "hephaestus")
    assert result.allowed


def test_sandbox_denied_overrides_allowed():
    sandbox = FilesystemSandbox(workspace_root="/workspace")
    sandbox.set_policy(
        "explore",
        allowed_paths=["/workspace"],
        denied_paths=["/workspace/secrets"],
    )
    result = sandbox.validate_path("/workspace/secrets/keys.txt", "explore")
    assert not result.allowed
    assert "denied" in result.reason.lower()


def test_sandbox_default_policy_uses_workspace_root():
    sandbox = FilesystemSandbox(workspace_root="/workspace")
    result = sandbox.validate_path("/workspace/file.txt", "unknown_agent")
    assert result.allowed


def test_sandbox_get_allowed_paths():
    sandbox = FilesystemSandbox(workspace_root="/workspace")
    sandbox.set_policy(
        "hephaestus", allowed_paths=["/workspace/src", "/workspace/tests"]
    )
    paths = sandbox.get_allowed_paths("hephaestus")
    assert "/workspace/src" in paths
    assert "/workspace/tests" in paths


def test_sandbox_get_allowed_paths_no_policy():
    sandbox = FilesystemSandbox(workspace_root="/workspace")
    paths = sandbox.get_allowed_paths("unknown")
    assert paths == ["/workspace"]


def test_sandbox_is_path_allowed():
    sandbox = FilesystemSandbox(workspace_root="/workspace")
    sandbox.set_policy("explore", allowed_paths=["/workspace/src"])
    assert sandbox.is_path_allowed("/workspace/src/main.py", "explore")
    assert not sandbox.is_path_allowed("/workspace/docs/readme.md", "explore")


# ── FilesystemSandbox — Access Level Checks ──────────────────────────


def test_sandbox_check_access_level_sufficient():
    sandbox = FilesystemSandbox(workspace_root="/workspace")
    sandbox.set_policy(
        "hephaestus",
        allowed_paths=["/workspace/src"],
        access_level=AccessLevel.READ_WRITE,
    )
    assert sandbox.check_access_level(
        "/workspace/src/main.py", "hephaestus", AccessLevel.READ
    )


def test_sandbox_check_access_level_insufficient():
    sandbox = FilesystemSandbox(workspace_root="/workspace")
    sandbox.set_policy(
        "oracle",
        allowed_paths=["/workspace"],
        access_level=AccessLevel.READ,
    )
    assert not sandbox.check_access_level(
        "/workspace/src/main.py", "oracle", AccessLevel.READ_WRITE
    )


def test_sandbox_get_access_level():
    sandbox = FilesystemSandbox(workspace_root="/workspace")
    sandbox.set_policy("hephaestus", access_level=AccessLevel.READ_WRITE)
    assert sandbox.get_access_level("hephaestus") == AccessLevel.READ_WRITE


def test_sandbox_get_access_level_default():
    sandbox = FilesystemSandbox(
        workspace_root="/workspace", default_access=AccessLevel.READ
    )
    assert sandbox.get_access_level("unknown") == AccessLevel.READ


# ── FilesystemSandbox — Symlink Resolution ───────────────────────────


def test_sandbox_resolve_path_absolute():
    sandbox = FilesystemSandbox(workspace_root="/workspace")
    # Non-existent path resolves to itself
    resolved = sandbox.resolve_path("/workspace/src/main.py")
    assert str(resolved) == "/workspace/src/main.py"


def test_sandbox_resolve_path_relative():
    sandbox = FilesystemSandbox(workspace_root="/workspace")
    resolved = sandbox.resolve_path("src/main.py")
    assert str(resolved) == "/workspace/src/main.py"


def test_sandbox_symlink_outside_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    link = workspace / "link"
    link.symlink_to(outside)

    sandbox = FilesystemSandbox(workspace_root=workspace)
    try:
        sandbox.resolve_path(str(link))
        assert False, "Should have raised SymlinkError"
    except SymlinkError as exc:
        assert "outside workspace" in str(exc).lower()


def test_sandbox_symlink_within_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "target.txt"
    target.write_text("hello")
    link = workspace / "link.txt"
    link.symlink_to(target)

    sandbox = FilesystemSandbox(workspace_root=workspace)
    resolved = sandbox.resolve_path(str(link))
    assert "workspace" in str(resolved)


# ── FilesystemSandbox — Observability Integration ────────────────────


def test_sandbox_get_stats():
    sandbox = FilesystemSandbox(workspace_root="/workspace")
    sandbox.set_policy("explore", allowed_paths=["/workspace/src"])
    sandbox.validate_path("/workspace/src/main.py", "explore")
    sandbox.validate_path("/workspace/docs/readme.md", "explore")
    stats = sandbox.get_stats()
    assert stats["total_validations"] >= 2
    assert stats["total_allowed"] >= 1
    assert stats["total_blocked"] >= 1
    assert stats["policies_count"] == 1


# ── SecurityPolicy — Default Policies ────────────────────────────────


def test_policy_has_default_policies():
    policy = SecurityPolicy(workspace_root="/workspace")
    assert policy.get_policy("sisyphus") is not None
    assert policy.get_policy("hephaestus") is not None
    assert policy.get_policy("oracle") is not None
    assert policy.get_policy("explore") is not None


def test_policy_default_sisyphus_full_access():
    policy = SecurityPolicy(workspace_root="/workspace")
    p = policy.get_policy("sisyphus")
    assert p is not None
    assert p.access_level == AccessLevel.FULL


def test_policy_default_explore_read_only():
    policy = SecurityPolicy(workspace_root="/workspace")
    p = policy.get_policy("explore")
    assert p is not None
    assert p.access_level == AccessLevel.READ


def test_policy_default_hephaestus_limited_paths():
    policy = SecurityPolicy(workspace_root="/workspace")
    p = policy.get_policy("hephaestus")
    assert p is not None
    assert any("src" in path for path in p.allowed_paths)


# ── SecurityPolicy — Custom Policies ─────────────────────────────────


def test_policy_set_custom_policy():
    policy = SecurityPolicy(workspace_root="/workspace")
    custom = AgentPolicy(
        agent_type="custom-agent",
        allowed_paths=["/workspace/custom"],
        access_level=AccessLevel.READ_WRITE,
    )
    policy.set_policy(custom)
    retrieved = policy.get_policy("custom-agent")
    assert retrieved is not None
    assert retrieved.access_level == AccessLevel.READ_WRITE


def test_policy_remove_custom_policy():
    policy = SecurityPolicy(workspace_root="/workspace")
    custom = AgentPolicy(
        agent_type="temp-agent",
        allowed_paths=["/workspace/temp"],
    )
    policy.set_policy(custom)
    assert policy.remove_policy("temp-agent")
    assert policy.get_policy("temp-agent") is None


def test_policy_cannot_remove_default_policy():
    policy = SecurityPolicy(workspace_root="/workspace")
    assert not policy.remove_policy("sisyphus")
    assert policy.get_policy("sisyphus") is not None


def test_policy_list_policies():
    policy = SecurityPolicy(workspace_root="/workspace")
    policies = policy.list_policies()
    assert len(policies) >= len(SecurityPolicy.DEFAULT_POLICIES)


# ── SecurityPolicy — Validation ──────────────────────────────────────


def test_policy_validate_valid_policy():
    policy = SecurityPolicy(workspace_root="/workspace")
    p = policy.get_policy("hephaestus")
    assert p is not None
    errors = policy.validate_policy(p)
    assert errors == []


def test_policy_validate_empty_agent_type():
    policy = SecurityPolicy(workspace_root="/workspace")
    bad = AgentPolicy(agent_type="", allowed_paths=["/workspace/src"])
    errors = policy.validate_policy(bad)
    assert any("agent_type" in e for e in errors)


def test_policy_validate_empty_allowed_paths():
    policy = SecurityPolicy(workspace_root="/workspace")
    bad = AgentPolicy(agent_type="test", allowed_paths=[])
    errors = policy.validate_policy(bad)
    assert any("allowed_paths" in e for e in errors)


# ── SecurityPolicy — Serialization ───────────────────────────────────


def test_policy_to_dict():
    policy = SecurityPolicy(workspace_root="/workspace")
    d = policy.to_dict()
    assert "sisyphus" in d
    assert "hephaestus" in d
    assert d["sisyphus"]["access_level"] == "full"


def test_policy_to_json():
    policy = SecurityPolicy(workspace_root="/workspace")
    j = policy.to_json()
    parsed = json.loads(j)
    assert "sisyphus" in parsed


def test_policy_from_dict():
    data = {
        "custom-agent": {
            "allowed_paths": ["/workspace/custom"],
            "access_level": "read_write",
            "follow_symlinks": False,
        }
    }
    policy = SecurityPolicy.from_dict(data, workspace_root="/workspace")
    p = policy.get_policy("custom-agent")
    assert p is not None
    assert p.access_level == AccessLevel.READ_WRITE


def test_policy_from_json():
    j = json.dumps(
        {
            "test-agent": {
                "allowed_paths": ["/workspace/test"],
                "access_level": "read",
                "follow_symlinks": True,
            }
        }
    )
    policy = SecurityPolicy.from_json(j, workspace_root="/workspace")
    p = policy.get_policy("test-agent")
    assert p is not None
    assert p.follow_symlinks is True


def test_policy_save_and_load(tmp_path):
    policy = SecurityPolicy(workspace_root="/workspace")
    save_path = tmp_path / "policy.json"
    policy.save(save_path)
    assert save_path.exists()

    loaded = SecurityPolicy.load(save_path, workspace_root="/workspace")
    assert loaded.get_policy("sisyphus") is not None
    assert loaded.get_policy("hephaestus") is not None


def test_policy_load_nonexistent(tmp_path):
    policy = SecurityPolicy.load(
        tmp_path / "nonexistent.json", workspace_root="/workspace"
    )
    assert policy.get_policy("sisyphus") is not None


# ── AgentPolicy ──────────────────────────────────────────────────────


def test_agent_policy_to_dict():
    p = AgentPolicy(
        agent_type="test",
        allowed_paths=["/workspace/src"],
        access_level=AccessLevel.READ,
        follow_symlinks=False,
        description="Test policy",
    )
    d = p.to_dict()
    assert d["agent_type"] == "test"
    assert d["access_level"] == "read"
    assert d["description"] == "Test policy"


def test_agent_policy_from_dict():
    data = {
        "agent_type": "test",
        "allowed_paths": ["/workspace/src"],
        "access_level": "read_write",
        "follow_symlinks": True,
        "description": "Test",
    }
    p = AgentPolicy.from_dict(data)
    assert p.agent_type == "test"
    assert p.access_level == AccessLevel.READ_WRITE
    assert p.follow_symlinks is True


# ── Integration: Sandbox + Policy ────────────────────────────────────


def test_sandbox_with_policy_integration():
    policy = SecurityPolicy(workspace_root="/workspace")
    sandbox = FilesystemSandbox(workspace_root="/workspace")

    for p in policy.list_policies():
        sandbox.set_policy(
            agent_type=p.agent_type,
            allowed_paths=p.allowed_paths,
            denied_paths=p.denied_paths,
            access_level=p.access_level,
            follow_symlinks=p.follow_symlinks,
        )

    hephaestus_result = sandbox.validate_path("/workspace/src/main.py", "hephaestus")
    assert hephaestus_result.allowed

    oracle_result = sandbox.validate_path("/workspace/src/main.py", "oracle")
    assert oracle_result.allowed
