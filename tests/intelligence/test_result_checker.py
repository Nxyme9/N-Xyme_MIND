"""Tests for result_checker.py."""

import json
import pytest
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from src.intelligence.result_checker import (
    check_results,
    ResultChecker,
    _match_task,
    _get_ttl,
)


class TestMatchTask:
    def test_exact_match(self):
        assert _match_task("fix auth bug", "fix auth bug") is True

    def test_substring_match(self):
        assert _match_task("fix auth bug in middleware", "fix auth bug") is True

    def test_word_overlap(self):
        assert (
            _match_task("fix authentication middleware bug", "fix auth bug middleware")
            is True
        )

    def test_no_match(self):
        assert _match_task("add new feature", "remove old code") is False

    def test_case_insensitive(self):
        assert _match_task("FIX AUTH BUG", "fix auth bug") is True


class TestGetTTL:
    def test_l1_ttl(self):
        assert _get_ttl("fix typo") == 1

    def test_l2_ttl(self):
        assert _get_ttl("fix bug in code") == 4

    def test_l3_ttl(self):
        assert _get_ttl("refactor middleware") == 24

    def test_research_ttl(self):
        assert _get_ttl("search for documentation") == 168

    def test_explore_ttl(self):
        assert _get_ttl("explore the codebase") == 168


class TestCheckResults:
    def test_empty_input(self):
        result = check_results("")
        assert result["found"] is False
        assert "empty input" in result["reason"]

    def test_no_store_found(self, tmp_path):
        result = check_results("some task", root_dir=tmp_path)
        assert result["found"] is False

    def test_json_store_match(self, tmp_path):
        sisyphus = tmp_path / ".sisyphus" / "results"
        sisyphus.mkdir(parents=True)

        now = datetime.now(timezone.utc).isoformat()
        store = {
            "results": [
                {
                    "task_id": "test-1",
                    "task_description": "fix auth middleware bug",
                    "agent": "hephaestus",
                    "level": "L2",
                    "success": True,
                    "result_path": "/some/path",
                    "timestamp": now,
                }
            ]
        }
        with open(sisyphus / "index.json", "w") as f:
            json.dump(store, f)

        result = check_results("fix auth middleware bug", root_dir=tmp_path)
        assert result["found"] is True
        assert result["agent"] == "hephaestus"

    def test_json_store_expired(self, tmp_path):
        sisyphus = tmp_path / ".sisyphus" / "results"
        sisyphus.mkdir(parents=True)

        old_time = (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat()
        store = {
            "results": [
                {
                    "task_id": "test-1",
                    "task_description": "fix typo",
                    "agent": "sisyphus-junior",
                    "level": "L1",
                    "success": True,
                    "result_path": "/some/path",
                    "timestamp": old_time,
                }
            ]
        }
        with open(sisyphus / "index.json", "w") as f:
            json.dump(store, f)

        result = check_results("fix typo", root_dir=tmp_path)
        assert result["found"] is False

    def test_json_store_no_match(self, tmp_path):
        sisyphus = tmp_path / ".sisyphus" / "results"
        sisyphus.mkdir(parents=True)

        now = datetime.now(timezone.utc).isoformat()
        store = {
            "results": [
                {
                    "task_id": "test-1",
                    "task_description": "completely different task",
                    "agent": "hephaestus",
                    "level": "L2",
                    "success": True,
                    "result_path": "/some/path",
                    "timestamp": now,
                }
            ]
        }
        with open(sisyphus / "index.json", "w") as f:
            json.dump(store, f)

        result = check_results("fix auth middleware", root_dir=tmp_path)
        assert result["found"] is False


class TestResultCheckerClass:
    def test_check(self, tmp_path):
        checker = ResultChecker(root_dir=tmp_path)
        result = checker.check("")
        assert result["found"] is False
