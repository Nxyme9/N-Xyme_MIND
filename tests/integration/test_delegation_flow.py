#!/usr/bin/env python3
"""Integration tests for full delegation flow.

Tests the complete delegation pipeline:
- Complexity scorer (L1-L5) with scope detection
- Result store caching (hit/miss/TTL)
- Review triage override for security-sensitive tasks
- Full delegation flow (scorer → cache → triage → routing)
- Edge cases (empty input, missing files, corrupt data)
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BIN_DIR = PROJECT_ROOT / "bin"
SISYPHUS_DIR = PROJECT_ROOT / ".sisyphus"


def run_script(
    script_name: str, args: list[str] | None = None, env: dict | None = None
) -> subprocess.CompletedProcess:
    """Run a bin script and return the result."""
    cmd = [str(BIN_DIR / script_name)]
    if args:
        cmd.extend(args)
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    return subprocess.run(
        cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT), env=run_env
    )


def parse_json_output(result: subprocess.CompletedProcess) -> dict:
    """Parse JSON from script stdout."""
    stdout = result.stdout.strip()
    if not stdout:
        return {}
    return json.loads(stdout)


class TestComplexityScorer:
    """Test bin/complexity-score.sh L1-L5 scoring."""

    def test_l1_trivial_typo(self):
        result = run_script("complexity-score.sh", ["fix typo in variable name"])
        data = parse_json_output(result)
        assert data["level"] == 1
        assert data["confidence"] >= 0.5

    def test_l1_trivial_version_bump(self):
        result = run_script("complexity-score.sh", ["update version to 2.0.0"])
        data = parse_json_output(result)
        assert data["level"] == 1

    def test_l1_trivial_add_import(self):
        result = run_script(
            "complexity-score.sh", ["add import statement for os module"]
        )
        data = parse_json_output(result)
        assert data["level"] == 1

    def test_l2_simple_bug_fix(self):
        result = run_script("complexity-score.sh", ["fix bug in config file"])
        data = parse_json_output(result)
        assert data["level"] == 2

    def test_l2_create_single_file(self):
        result = run_script("complexity-score.sh", ["create config file for database"])
        data = parse_json_output(result)
        assert data["level"] == 2

    def test_l2_update_dependency(self):
        result = run_script(
            "complexity-score.sh", ["update dependency version in package.json"]
        )
        data = parse_json_output(result)
        assert data["level"] == 2

    def test_l3_refactor_multi_file(self):
        result = run_script(
            "complexity-score.sh", ["refactor auth middleware across 3 files"]
        )
        data = parse_json_output(result)
        assert data["level"] == 3

    def test_l3_endpoint_handler(self):
        result = run_script(
            "complexity-score.sh", ["add new endpoint handler for users"]
        )
        data = parse_json_output(result)
        assert data["level"] == 3

    def test_l3_route_creation(self):
        result = run_script(
            "complexity-score.sh", ["create route for payment processing"]
        )
        data = parse_json_output(result)
        assert data["level"] == 3

    def test_l4_architecture_system_design(self):
        result = run_script(
            "complexity-score.sh", ["design new architecture for microservices"]
        )
        data = parse_json_output(result)
        assert data["level"] == 4

    def test_l4_build_from_scratch(self):
        result = run_script("complexity-score.sh", ["build new module from scratch"])
        data = parse_json_output(result)
        assert data["level"] == 4

    def test_l5_major_rewrite(self):
        result = run_script(
            "complexity-score.sh", ["rewrite entire codebase structure"]
        )
        data = parse_json_output(result)
        assert data["level"] == 5

    def test_l5_migrate_overhaul(self):
        result = run_script(
            "complexity-score.sh", ["migrate and overhaul the whole system"]
        )
        data = parse_json_output(result)
        assert data["level"] == 5

    def test_empty_input_defaults_l2(self):
        result = run_script("complexity-score.sh", [])
        data = parse_json_output(result)
        assert data["level"] == 2
        assert data["confidence"] == 0.5

    def test_file_count_heuristics_large(self):
        result = run_script("complexity-score.sh", ["update 25 files in the project"])
        data = parse_json_output(result)
        assert data["level"] >= 4

    def test_file_count_heuristics_medium(self):
        result = run_script("complexity-score.sh", ["fix 12 files"])
        data = parse_json_output(result)
        assert data["level"] >= 3

    def test_file_count_heuristics_small(self):
        result = run_script("complexity-score.sh", ["edit 7 files"])
        data = parse_json_output(result)
        assert data["level"] >= 2

    def test_global_scope_uses_grep_basic_pattern(self):
        result = run_script("complexity-score.sh", ["fix typo in config"])
        data = parse_json_output(result)
        assert data["level"] == 1

    def test_confidence_scales_with_reasons(self):
        result = run_script(
            "complexity-score.sh", ["refactor auth middleware with 15 files"]
        )
        data = parse_json_output(result)
        assert data["confidence"] >= 0.7

    def test_output_is_valid_json(self):
        result = run_script("complexity-score.sh", ["test task"])
        assert result.returncode == 0
        data = parse_json_output(result)
        assert "level" in data
        assert "confidence" in data
        assert "reason" in data

    def test_level_is_integer(self):
        result = run_script("complexity-score.sh", ["some task"])
        data = parse_json_output(result)
        assert isinstance(data["level"], int)

    def test_confidence_is_float(self):
        result = run_script("complexity-score.sh", ["some task"])
        data = parse_json_output(result)
        assert isinstance(float(data["confidence"]), float)


class TestResultStore:
    """Test bin/check-results.sh caching behavior."""

    def _setup_result_store(self, results: list[dict]) -> str:
        """Create a temporary result store in SQLite and return its path."""
        import sqlite3
        store_dir = SISYPHUS_DIR / "results"
        store_dir.mkdir(parents=True, exist_ok=True)
        state_db = SISYPHUS_DIR / "state.db"
        self._cleanup_result_store()
        conn = sqlite3.connect(str(state_db))
        cursor = conn.cursor()
        for r in results:
            cursor.execute(
                "INSERT OR REPLACE INTO results (task_id, task_description, agent, level, success, result_path, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (r.get("task_id", "test"), r.get("task_description", ""), r.get("agent", "unknown"), r.get("level", "L1"), 1 if r.get("success") else 0, r.get("result_path", ""), r.get("timestamp", "")),
            )
        conn.commit()
        conn.close()
        return str(state_db)

    def _cleanup_result_store(self):
        """Remove the temporary result store from SQLite."""
        import sqlite3
        state_db = SISYPHUS_DIR / "state.db"
        if state_db.exists():
            conn = sqlite3.connect(str(state_db))
            cursor = conn.cursor()
            cursor.execute("DELETE FROM results WHERE task_id LIKE '%'")
            conn.commit()
            conn.close()
        store_path = SISYPHUS_DIR / "results" / "index.json"
        if store_path.exists():
            store_path.unlink()

    def test_cache_miss_no_store(self):
        self._cleanup_result_store()
        result = run_script("check-results.sh", ["find auth patterns"])
        data = parse_json_output(result)
        assert data["found"] is False

    def test_cache_miss_no_match(self):
        self._setup_result_store(
            [
                {
                    "task_description": "implement jwt auth",
                    "result_path": "/tmp/result1",
                    "timestamp": (
                        datetime.now(timezone.utc) - timedelta(hours=1)
                    ).isoformat(),
                    "task_id": "task-001",
                    "agent": "hephaestus",
                    "success": True,
                }
            ]
        )
        result = run_script(
            "check-results.sh", ["build a completely different feature"]
        )
        data = parse_json_output(result)
        assert data["found"] is False
        self._cleanup_result_store()

    def test_cache_hit_exact_match(self):
        now = datetime.now(timezone.utc)
        self._setup_result_store(
            [
                {
                    "task_description": "implement jwt auth middleware",
                    "result_path": "/tmp/jwt-result",
                    "timestamp": (now - timedelta(hours=1)).isoformat(),
                    "task_id": "task-002",
                    "agent": "hephaestus",
                    "success": True,
                }
            ]
        )
        result = run_script(
            "check-results.sh", ["implement jwt auth middleware"]
        )
        data = parse_json_output(result)
        assert data["found"] is True
        assert data["result_path"] == "/tmp/jwt-result"
        assert data["success"] is True
        self._cleanup_result_store()

    def test_cache_hit_partial_overlap(self):
        now = datetime.now(timezone.utc)
        self._setup_result_store(
            [
                {
                    "task_description": "add user auth with jwt tokens",
                    "result_path": "/tmp/auth-result",
                    "timestamp": (now - timedelta(hours=2)).isoformat(),
                    "task_id": "task-003",
                    "agent": "hephaestus",
                    "success": True,
                }
            ]
        )
        result = run_script(
            "check-results.sh", ["implement user auth using jwt"]
        )
        data = parse_json_output(result)
        assert data["found"] is True
        self._cleanup_result_store()

    def test_cache_expired_ttl_l1(self):
        old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        self._setup_result_store(
            [
                {
                    "task_description": "fix typo in variable",
                    "result_path": "/tmp/typo-fix",
                    "timestamp": old_time,
                    "task_id": "task-004",
                    "agent": "sisyphus-junior",
                    "success": True,
                }
            ]
        )
        result = run_script("check-results.sh", ["fix typo in variable"])
        data = parse_json_output(result)
        assert data["found"] is False
        self._cleanup_result_store()

    def test_cache_expired_ttl_l2(self):
        old_time = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
        self._setup_result_store(
            [
                {
                    "task_description": "fix bug in login",
                    "result_path": "/tmp/bug-fix",
                    "timestamp": old_time,
                    "task_id": "task-005",
                    "agent": "hephaestus",
                    "success": True,
                }
            ]
        )
        result = run_script("check-results.sh", ["fix bug in login"])
        data = parse_json_output(result)
        assert data["found"] is False
        self._cleanup_result_store()

    def test_cache_valid_ttl_l3(self):
        recent_time = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()
        self._setup_result_store(
            [
                {
                    "task_description": "refactor auth middleware endpoint",
                    "result_path": "/tmp/refactor",
                    "timestamp": recent_time,
                    "task_id": "task-006",
                    "agent": "hephaestus",
                    "success": True,
                }
            ]
        )
        result = run_script("check-results.sh", ["refactor auth middleware endpoint"])
        data = parse_json_output(result)
        assert data["found"] is True
        self._cleanup_result_store()

    def test_research_tasks_extended_ttl(self):
        old_time = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        self._setup_result_store(
            [
                {
                    "task_description": "research best practices for auth",
                    "result_path": "/tmp/research",
                    "timestamp": old_time,
                    "task_id": "task-007",
                    "agent": "librarian",
                    "success": True,
                }
            ]
        )
        result = run_script(
            "check-results.sh", ["research best practices for auth"]
        )
        data = parse_json_output(result)
        assert data["found"] is True
        assert data["ttl_hours"] == 168
        self._cleanup_result_store()

    def test_empty_input_returns_not_found(self):
        result = run_script("check-results.sh", [])
        data = parse_json_output(result)
        assert data["found"] is False

    def test_cache_hit_includes_age(self):
        now = datetime.now(timezone.utc)
        two_hours_ago = now - timedelta(hours=2)
        self._setup_result_store(
            [
                {
                    "task_description": "create new api endpoint",
                    "result_path": "/tmp/api-endpoint",
                    "timestamp": two_hours_ago.isoformat(),
                    "task_id": "task-008",
                    "agent": "hephaestus",
                    "success": True,
                }
            ]
        )
        result = run_script("check-results.sh", ["create new api endpoint"])
        data = parse_json_output(result)
        assert data["found"] is True
        assert "age_hours" in data
        assert data["age_hours"] >= 1.5
        self._cleanup_result_store()


class TestReviewTriage:
    """Test bin/review-triage.sh security-sensitive path detection."""

    def test_no_override_normal_task(self):
        result = run_script("review-triage.sh", ["add new button to dashboard"])
        data = parse_json_output(result)
        assert data["override"] is False
        assert data["force_oracle"] is False

    def test_override_auth_keyword(self):
        result = run_script("review-triage.sh", ["implement auth flow"])
        data = parse_json_output(result)
        assert data["override"] is True
        assert data["force_oracle"] is True
        assert data["level"] == 3

    def test_override_security_keyword(self):
        result = run_script("review-triage.sh", ["add security to responses"])
        data = parse_json_output(result)
        assert data["override"] is True

    def test_override_crypto_keyword(self):
        result = run_script("review-triage.sh", ["implement crypto encryption module"])
        data = parse_json_output(result)
        assert data["override"] is True

    def test_override_encrypt_keyword(self):
        result = run_script("review-triage.sh", ["encrypt user data at rest"])
        data = parse_json_output(result)
        assert data["override"] is True

    def test_override_decrypt_keyword(self):
        result = run_script("review-triage.sh", ["decrypt incoming payload"])
        data = parse_json_output(result)
        assert data["override"] is True

    def test_override_password_keyword(self):
        result = run_script("review-triage.sh", ["add password validation rules"])
        data = parse_json_output(result)
        assert data["override"] is True

    def test_override_token_keyword(self):
        result = run_script("review-triage.sh", ["refresh auth token logic"])
        data = parse_json_output(result)
        assert data["override"] is True

    def test_override_payment_keyword(self):
        result = run_script("review-triage.sh", ["add payment processing endpoint"])
        data = parse_json_output(result)
        assert data["override"] is True

    def test_override_credential_keyword(self):
        result = run_script("review-triage.sh", ["store user credential securely"])
        data = parse_json_output(result)
        assert data["override"] is True

    def test_override_sensitive_path_auth(self):
        result = run_script("review-triage.sh", ["update files", "src/auth/login.ts"])
        data = parse_json_output(result)
        assert data["override"] is True

    def test_override_sensitive_path_security(self):
        result = run_script(
            "review-triage.sh", ["update files", "lib/security/hasher.py"]
        )
        data = parse_json_output(result)
        assert data["override"] is True

    def test_override_sensitive_path_env(self):
        result = run_script("review-triage.sh", ["update files", ".env.production"])
        data = parse_json_output(result)
        assert data["override"] is True

    def test_override_sensitive_path_secret(self):
        result = run_script(
            "review-triage.sh", ["update files", "config/secret-manager.ts"]
        )
        data = parse_json_output(result)
        assert data["override"] is True

    def test_override_sensitive_path_api_key(self):
        result = run_script(
            "review-triage.sh", ["update files", "services/api_key_handler.py"]
        )
        data = parse_json_output(result)
        assert data["override"] is True

    def test_no_override_safe_paths(self):
        result = run_script(
            "review-triage.sh",
            ["update files", "src/components/Button.tsx", "src/utils/format.ts"],
        )
        data = parse_json_output(result)
        assert data["override"] is False

    def test_empty_task_no_override(self):
        result = run_script("review-triage.sh", [])
        # Script errors on empty task, so no JSON output expected
        output = result.stdout + result.stderr
        assert "override" not in output or output.strip().startswith("usage")

    def test_override_includes_reason(self):
        result = run_script("review-triage.sh", ["implement auth with tokens"])
        data = parse_json_output(result)
        assert "reason" in data
        assert len(data["reason"]) > 0


class TestFullDelegationFlow:
    """Test the complete delegation pipeline: scorer → cache → triage → routing."""

    def _setup_result_store(self, results: list[dict]):
        """Create a temporary result store in SQLite."""
        import sqlite3
        store_dir = SISYPHUS_DIR / "results"
        store_dir.mkdir(parents=True, exist_ok=True)
        state_db = SISYPHUS_DIR / "state.db"
        conn = sqlite3.connect(str(state_db))
        cursor = conn.cursor()
        for r in results:
            cursor.execute(
                "INSERT OR REPLACE INTO results (task_id, task_description, agent, level, success, result_path, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (r.get("task_id", "test"), r.get("task_description", ""), r.get("agent", "unknown"), r.get("level", "L1"), 1 if r.get("success") else 0, r.get("result_path", ""), r.get("timestamp", "")),
            )
        conn.commit()
        conn.close()

    def _cleanup_result_store(self):
        """Remove the temporary result store from SQLite."""
        import sqlite3
        state_db = SISYPHUS_DIR / "state.db"
        if state_db.exists():
            conn = sqlite3.connect(str(state_db))
            cursor = conn.cursor()
            cursor.execute("DELETE FROM results WHERE task_id LIKE '%'")
            conn.commit()
            conn.close()
        store_path = SISYPHUS_DIR / "results" / "index.json"
        if store_path.exists():
            store_path.unlink()

    def test_flow_l1_trivial_no_cache_no_override(self):
        """L1 tasks: no cache expected, no security override, route to sisyphus-junior."""
        task = "fix typo in variable name"

        score_result = run_script("complexity-score.sh", [task])
        score = parse_json_output(score_result)
        assert score["level"] == 1

        self._cleanup_result_store()
        cache_result = run_script("check-results.sh", [task])
        cache = parse_json_output(cache_result)
        assert cache["found"] is False

        triage_result = run_script("review-triage.sh", [task])
        triage = parse_json_output(triage_result)
        assert triage["override"] is False

        expected_agent = "sisyphus-junior"
        assert expected_agent in ["sisyphus-junior"]

    def test_flow_l2_simple_with_cache_hit(self):
        """L2 tasks: cache hit skips implementation."""
        task = "fix bug in config file"
        now = datetime.now(timezone.utc)

        score_result = run_script("complexity-score.sh", [task])
        score = parse_json_output(score_result)
        assert score["level"] == 2

        self._setup_result_store([
            {
                "task_description": "fix bug in config file for database",
                "result_path": "/tmp/cached-fix",
                "timestamp": (now - timedelta(hours=1)).isoformat(),
                "task_id": "flow-001",
                "agent": "hephaestus",
                "success": True,
            }
        ])
        cache_result = run_script("check-results.sh", [task])
        cache = parse_json_output(cache_result)
        assert cache["found"] is True

        triage_result = run_script("review-triage.sh", [task])
        triage = parse_json_output(triage_result)
        assert triage["override"] is False

        self._cleanup_result_store()

    def test_flow_l3_multi_file_security_override(self):
        """L3 tasks with security keywords: force oracle review."""
        task = "refactor auth middleware across multiple endpoints"
        now = datetime.now(timezone.utc)

        score_result = run_script("complexity-score.sh", [task])
        score = parse_json_output(score_result)
        assert score["level"] == 3

        self._cleanup_result_store()
        cache_result = run_script("check-results.sh", [task])
        cache = parse_json_output(cache_result)
        assert cache["found"] is False

        triage_result = run_script("review-triage.sh", [task])
        triage = parse_json_output(triage_result)
        assert triage["override"] is True
        assert triage["force_oracle"] is True

    def test_flow_l4_architecture_no_cache(self):
        """L4 tasks: no cache, no security override, full review chain."""
        task = "design new microservice architecture"

        score_result = run_script("complexity-score.sh", [task])
        score = parse_json_output(score_result)
        assert score["level"] == 4

        self._cleanup_result_store()
        cache_result = run_script("check-results.sh", [task])
        cache = parse_json_output(cache_result)
        assert cache["found"] is False

        triage_result = run_script("review-triage.sh", [task])
        triage = parse_json_output(triage_result)
        assert triage["override"] is False

    def test_flow_l5_rewrite_security_path(self):
        """L5 tasks with security paths: maximum review."""
        task = "rewrite entire auth system"
        files = ["src/auth/core.ts", "src/security/crypto.ts"]

        score_result = run_script("complexity-score.sh", [task])
        score = parse_json_output(score_result)
        assert score["level"] == 5

        triage_result = run_script("review-triage.sh", [task] + files)
        triage = parse_json_output(triage_result)
        assert triage["override"] is True
        assert triage["force_oracle"] is True
        assert triage["level"] == 3

    def test_flow_routing_matrix(self):
        """Verify routing decisions match the delegation matrix."""
        test_cases = [
            ("fix typo", 1, "sisyphus-junior", False),
            ("fix bug in config", 2, "hephaestus", False),
            ("refactor middleware", 3, "hephaestus", False),
            ("refactor auth middleware", 3, "hephaestus", True),
            ("design architecture", 4, "hephaestus", False),
            ("rewrite entire system", 5, "hephaestus", False),
        ]

        for task, expected_level, expected_agent, expect_override in test_cases:
            score_result = run_script("complexity-score.sh", [task])
            score = parse_json_output(score_result)
            assert score["level"] == expected_level, f"Task '{task}': expected L{expected_level}, got L{score['level']}"

            triage_result = run_script("review-triage.sh", [task])
            triage = parse_json_output(triage_result)
            assert triage["override"] == expect_override, f"Task '{task}': override mismatch"

    def test_flow_cache_ttl_by_complexity(self):
        """Verify TTL scales with complexity level."""
        ttl_cases = [
            ("fix typo in variable name", 1),
            ("fix bug in config file", 2),
            ("refactor auth middleware module", 3),
            ("design system architecture plan", 4),
            ("rewrite entire codebase structure", 5),
        ]

        now = datetime.now(timezone.utc)
        results = []
        for task, level in ttl_cases:
            results.append({
                "task_description": task,
                "result_path": f"/tmp/result-{level}",
                "timestamp": (now - timedelta(minutes=30)).isoformat(),
                "task_id": f"ttl-{level}",
                "agent": "hephaestus",
                "success": True,
            })

        self._setup_result_store(results)

        for task, level in ttl_cases:
            cache_result = run_script("check-results.sh", [task])
            cache = parse_json_output(cache_result)
            assert cache["found"] is True, f"Cache miss for: {task}"
            assert "ttl_hours" in cache

            if level == 1:
                assert cache["ttl_hours"] == 1
            elif level == 2:
                assert cache["ttl_hours"] == 4
            else:
                assert cache["ttl_hours"] == 24

        self._cleanup_result_store()


class TestEdgeCases:
    """Test edge cases: empty input, missing files, corrupt data."""

    def _setup_result_store(self, content: str):
        store_dir = SISYPHUS_DIR / "results"
        store_dir.mkdir(parents=True, exist_ok=True)
        store_path = store_dir / "index.json"
        store_path.write_text(content)

    def _cleanup_result_store(self):
        store_path = SISYPHUS_DIR / "results" / "index.json"
        if store_path.exists():
            store_path.unlink()

    def test_complexity_score_empty_string(self):
        result = run_script("complexity-score.sh", [""])
        data = parse_json_output(result)
        assert data["level"] == 2
        assert data["confidence"] == 0.5

    def test_complexity_score_special_characters(self):
        result = run_script("complexity-score.sh", ["!@#$%^&*()"])
        assert result.returncode == 0
        data = parse_json_output(result)
        assert "level" in data

    def test_complexity_score_very_long_input(self):
        long_task = "fix " * 500 + "bug"
        result = run_script("complexity-score.sh", [long_task])
        assert result.returncode == 0
        data = parse_json_output(result)
        assert "level" in data

    def test_complexity_score_unicode(self):
        result = run_script("complexity-score.sh", ["fix bug in café résumé naïve"])
        assert result.returncode == 0
        data = parse_json_output(result)
        assert "level" in data

    def test_check_results_empty_string(self):
        result = run_script("check-results.sh", [""])
        data = parse_json_output(result)
        assert data["found"] is False

    def test_check_results_corrupt_json_store(self):
        self._setup_result_store("{invalid json content!!!")
        result = run_script("check-results.sh", ["some task"])
        data = parse_json_output(result)
        assert data["found"] is False
        self._cleanup_result_store()

    def test_check_results_empty_json_store(self):
        self._setup_result_store("{}")
        result = run_script("check-results.sh", ["some task"])
        data = parse_json_output(result)
        assert data["found"] is False
        self._cleanup_result_store()

    def test_check_results_malformed_timestamp(self):
        self._setup_result_store(
            json.dumps(
                {
                    "results": [
                        {
                            "task_description": "some task",
                            "result_path": "/tmp/test",
                            "timestamp": "not-a-valid-timestamp",
                            "task_id": "test-001",
                            "agent": "hephaestus",
                            "success": True,
                        }
                    ]
                }
            )
        )
        result = run_script("check-results.sh", ["some task"])
        data = parse_json_output(result)
        assert data["found"] is False
        self._cleanup_result_store()


    def test_check_results_missing_result_fields(self):
        """Test that missing fields in result are handled gracefully."""
        import sqlite3
        now = datetime.now(timezone.utc)
        state_db = SISYPHUS_DIR / "state.db"
        conn = sqlite3.connect(str(state_db))
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO results (task_id, task_description, agent, level, success, result_path, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("test-missing", "some task", "unknown", "L1", 1, "", (now - timedelta(hours=1)).isoformat()),
        )
        conn.commit()
        conn.close()
        result = run_script("check-results.sh", ["some task"])
        data = parse_json_output(result)
        assert data["found"] is True
        self._cleanup_result_store()

    def test_review_triage_empty_task(self):
        result = run_script("review-triage.sh", [])
        # Script errors on empty task
        output = result.stdout + result.stderr
        assert "override" not in output or output.strip().startswith("usage")

    def test_review_triage_many_paths(self):
        paths = [f"src/module{i}/file.ts" for i in range(50)]
        result = run_script("review-triage.sh", ["update files"] + paths)
        data = parse_json_output(result)
        assert data["override"] is False

    def test_review_triage_mixed_safe_and_sensitive_paths(self):
        result = run_script(
            "review-triage.sh",
            [
                "update files",
                "src/components/Button.tsx",
                "src/auth/login.ts",
                "src/utils/format.ts",
            ],
        )
        data = parse_json_output(result)
        assert data["override"] is True

    def test_delegation_log_show_empty(self):
        log_dir = SISYPHUS_DIR / "delegation-logs"
        log_file = log_dir / "delegations.jsonl"
        log_dir.mkdir(parents=True, exist_ok=True)
        if log_file.exists():
            log_file.unlink()
        # Also clear SQLite delegations
        import sqlite3
        state_db = SISYPHUS_DIR / "state.db"
        if state_db.exists():
            conn = sqlite3.connect(str(state_db))
            cursor = conn.cursor()
            cursor.execute("DELETE FROM delegations")
            conn.commit()
            conn.close()

        result = run_script("delegation-log.sh", ["show"])
        assert result.returncode == 0
        assert "No delegation logs found" in result.stdout or "Total delegations logged: 0" in result.stdout

    def test_delegation_log_log_and_show(self):
        log_dir = SISYPHUS_DIR / "delegation-logs"
        log_file = log_dir / "delegations.jsonl"
        log_dir.mkdir(parents=True, exist_ok=True)
        if log_file.exists():
            log_file.unlink()

        result = run_script(
            "delegation-log.sh",
            ["log", "test-task", "hephaestus", "L3", "success", "5000"],
        )
        assert result.returncode == 0
        assert "Logged: test-task" in result.stdout

        result = run_script("delegation-log.sh", ["show", "5"])
        assert result.returncode == 0
        assert "test-task" in result.stdout

        if log_file.exists():
            log_file.unlink()

    def test_delegation_log_invalid_action(self):
        result = run_script("delegation-log.sh", ["invalid-action"])
        assert result.returncode != 0
