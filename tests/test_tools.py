"""Tests for src/tools/ modules — import verification + basic smoke tests."""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


class TestToolImports:
    """Verify all tool modules import correctly."""

    def test_create_memory_import(self):
        from src.tools import create_memory
        assert create_memory is not None

    def test_delete_memory_import(self):
        from src.tools import delete_memory
        assert delete_memory is not None

    def test_update_memory_import(self):
        from src.tools import update_memory
        assert update_memory is not None

    def test_search_memories_import(self):
        from src.tools import search_memories
        assert search_memories is not None

    def test_semantic_search_import(self):
        from src.tools import semantic_search
        assert semantic_search is not None

    def test_tempr_search_import(self):
        from src.tools import tempr_search
        assert tempr_search is not None

    def test_get_memory_stats_import(self):
        from src.tools import get_memory_stats
        assert get_memory_stats is not None

    def test_recall_session_import(self):
        from src.tools import recall_session
        assert recall_session is not None

    def test_find_context_import(self):
        from src.tools import find_context
        assert find_context is not None

    def test_get_learning_stats_import(self):
        from src.tools import get_learning_stats
        assert get_learning_stats is not None

    def test_get_skill_status_import(self):
        from src.tools import get_skill_status
        assert get_skill_status is not None

    def test_record_skill_outcome_import(self):
        from src.tools import record_skill_outcome
        assert record_skill_outcome is not None

    def test_get_learning_patterns_import(self):
        from src.tools import get_learning_patterns
        assert get_learning_patterns is not None

    def test_evolve_prompt_import(self):
        from src.tools import evolve_prompt
        assert evolve_prompt is not None


class TestToolRegistry:
    """Verify tools are registered."""

    def test_tools_registered(self):
        from src.orchestration.tool_registry import registry
        tools = registry.get_tool_list()
        tool_names = [t.get("name", t) if isinstance(t, dict) else t.name for t in tools]
        expected = [
            "create_memory", "delete_memory", "update_memory",
            "search_memories", "semantic_search", "tempr_search",
            "get_memory_stats", "recall_session", "find_context",
            "get_learning_stats", "get_skill_status",
            "record_skill_outcome", "get_learning_patterns", "evolve_prompt",
        ]
        for name in expected:
            assert name in tool_names, f"Tool {name} not registered"
