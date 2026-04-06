#!/usr/bin/env python3
"""Unit tests for skill_registry module."""

import pytest
import sys
import tempfile
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from src.tools.learning.skill_registry import (
    SkillRegistry,
    SkillInfo,
    DEFAULT_WEIGHTS,
    DEFAULT_SUCCESS_RATE,
    DEFAULT_AVG_LATENCY_MS,
)


class TestSkillInfo:
    """Tests for SkillInfo dataclass."""

    def test_creation(self):
        """Test creating a skill info."""
        skill = SkillInfo(
            skill_id="test_skill",
            name="Test Skill",
            description="A test skill",
            triggers=["test", "example"],
            trigger_type="semantic",
        )

        assert skill.skill_id == "test_skill"
        assert skill.name == "Test Skill"
        assert skill.triggers == ["test", "example"]
        assert skill.trigger_type == "semantic"

    def test_default_values(self):
        """Test default values."""
        skill = SkillInfo(
            skill_id="test",
            name="Test",
            description="Test skill",
            triggers=[],
            trigger_type="semantic",
        )

        assert skill.success_rate == DEFAULT_SUCCESS_RATE
        assert skill.avg_latency_ms == DEFAULT_AVG_LATENCY_MS
        assert skill.invocation_count == 0


class TestSkillRegistry:
    """Tests for SkillRegistry class."""

    @pytest.fixture
    def registry(self):
        """Create registry with temp database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_skill_registry.db")
            yield SkillRegistry(db_name=db_path)

    def test_register_new_skill(self, registry):
        """Test registering a new skill."""
        skill = registry.register_skill(
            skill_id="code_review",
            name="Code Review",
            triggers=["review", "code", "analyze"],
            trigger_type="semantic",
            description="Automated code review",
        )

        assert skill.skill_id == "code_review"
        assert skill.name == "Code Review"
        assert len(skill.triggers) == 3

    def test_register_duplicate_skill(self, registry):
        """Test registering duplicate skill returns existing."""
        skill1 = registry.register_skill(
            skill_id="test_skill",
            name="Test",
            triggers=["test"],
            trigger_type="semantic",
        )

        skill2 = registry.register_skill(
            skill_id="test_skill",
            name="Test Duplicate",
            triggers=["different"],
            trigger_type="keyword",
        )

        assert skill1.skill_id == skill2.skill_id

    def test_get_skill(self, registry):
        """Test retrieving skill details."""
        registry.register_skill(
            skill_id="test_skill",
            name="Test Skill",
            triggers=["test"],
            trigger_type="semantic",
            description="A test",
        )

        skill_dict = registry.get_skill("test_skill")

        assert skill_dict is not None
        assert skill_dict["skill_id"] == "test_skill"
        assert skill_dict["name"] == "Test Skill"

    def test_get_nonexistent_skill(self, registry):
        """Test retrieving nonexistent skill returns None."""
        skill = registry.get_skill("nonexistent")
        assert skill is None

    def test_list_skills(self, registry):
        """Test listing all skills."""
        registry.register_skill("skill1", "Skill 1", ["test1"], "semantic")
        registry.register_skill("skill2", "Skill 2", ["test2"], "keyword")

        skills = registry.list_skills()

        assert len(skills) == 2

    def test_route_query_empty_registry(self, registry):
        """Test routing with empty registry."""
        routes = registry.route_query("test query")
        assert routes == []

    def test_route_query_single_match(self, registry):
        """Test routing single query to matching skill."""
        registry.register_skill(
            skill_id="memory_search",
            name="Memory Search",
            triggers=["search", "find", "memory"],
            trigger_type="semantic",
        )

        routes = registry.route_query("search for memories")

        assert len(routes) > 0
        assert routes[0]["skill_id"] == "memory_search"

    def test_route_query_trigger_match(self, registry):
        """Test routing with trigger keyword match."""
        registry.register_skill(
            skill_id="create_memory",
            name="Create Memory",
            triggers=["create", "add", "store"],
            trigger_type="keyword",
        )

        routes = registry.route_query("create a new memory")

        assert len(routes) > 0
        assert "create" in routes[0].get("matched_triggers", [])

    def test_route_query_scores(self, registry):
        """Test that routing returns scores."""
        registry.register_skill(
            skill_id="test_skill",
            name="Test",
            triggers=["test"],
            trigger_type="semantic",
        )

        routes = registry.route_query("test query")

        assert "score" in routes[0]
        assert "sem_score" in routes[0]
        assert "trigger_score" in routes[0]
        assert "perf_score" in routes[0]

    def test_update_performance(self, registry):
        """Test updating performance metrics."""
        registry.register_skill(
            skill_id="test_skill",
            name="Test",
            triggers=["test"],
            trigger_type="semantic",
        )

        registry.update_performance("test_skill", success=True, latency_ms=50.0)

        skill_dict = registry.get_skill("test_skill")
        assert skill_dict["invocation_count"] == 1
        assert skill_dict["success_rate"] == 1.0

    def test_update_performance_multiple(self, registry):
        """Test updating performance with multiple invocations."""
        registry.register_skill(
            skill_id="test_skill",
            name="Test",
            triggers=["test"],
            trigger_type="semantic",
        )

        registry.update_performance("test_skill", success=True, latency_ms=100.0)
        registry.update_performance("test_skill", success=True, latency_ms=200.0)
        registry.update_performance("test_skill", success=False, latency_ms=150.0)

        skill_dict = registry.get_skill("test_skill")
        assert skill_dict["invocation_count"] == 3
        assert skill_dict["success_rate"] == pytest.approx(2 / 3, rel=0.01)

    def test_update_performance_nonexistent(self, registry):
        """Test updating performance for nonexistent skill."""
        registry.update_performance("nonexistent", success=True, latency_ms=50.0)

    def test_route_query_sorted_by_score(self, registry):
        """Test that routes are sorted by score descending."""
        registry.register_skill("skill1", "Skill 1", ["test"], trigger_type="semantic")
        registry.register_skill(
            "skill2", "Skill 2", ["test", "more"], trigger_type="semantic"
        )

        registry.update_performance("skill1", success=True, latency_ms=50.0)

        routes = registry.route_query("test more")

        assert routes[0]["score"] >= routes[1]["score"]


class TestDefaultWeights:
    """Tests for default weights."""

    def test_weights_exist(self):
        """Test that default weights exist."""
        assert "w_sem" in DEFAULT_WEIGHTS
        assert "w_trig" in DEFAULT_WEIGHTS
        assert "w_perf" in DEFAULT_WEIGHTS

    def test_weights_sum_to_one(self):
        """Test that weights sum to 1.0."""
        total = (
            DEFAULT_WEIGHTS["w_sem"]
            + DEFAULT_WEIGHTS["w_trig"]
            + DEFAULT_WEIGHTS["w_perf"]
        )
        assert total == pytest.approx(1.0, rel=0.001)
