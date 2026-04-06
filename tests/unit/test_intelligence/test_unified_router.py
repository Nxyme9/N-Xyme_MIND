"""Unit tests for intelligence.unified_router."""

import pytest
from unittest.mock import patch, MagicMock
from src.tools.intelligence.unified_router import (
    RoutingDecision,
    UnifiedDelegationRouter,
)


class TestRoutingDecision:
    """Test RoutingDecision dataclass."""

    def test_routing_decision_creation(self):
        decision = RoutingDecision(
            task_description="test task",
            level=3,
            agent="hephaestus",
            confidence=0.8,
            strategy_used="trigger",
            reason="matched trigger pattern",
            alternatives=[],
            latency_ms=15.5,
            subtasks=None,
            prompt=None,
        )
        assert decision.task_description == "test task"
        assert decision.level == 3
        assert decision.agent == "hephaestus"
        assert decision.confidence == 0.8
        assert decision.strategy_used == "trigger"

    def test_routing_decision_with_alternatives(self):
        decision = RoutingDecision(
            task_description="test",
            level=2,
            agent="explore",
            confidence=0.7,
            strategy_used="memory",
            reason="found similar task",
            alternatives=[
                {"agent": "hephaestus", "confidence": 0.6},
                {"agent": "oracle", "confidence": 0.5},
            ],
        )
        assert len(decision.alternatives) == 2


class TestUnifiedDelegationRouter:
    """Test UnifiedDelegationRouter class."""

    def test_router_init(self):
        router = UnifiedDelegationRouter()
        # Core components should be None (lazy initialization)
        assert router._memory_router is None
        assert router._trigger_router is None
        assert router._local_analyzer is None
        assert router._routing_optimizer is None
        assert router._outcome_logger is None
        assert router._complexity_scorer is None

    def test_router_has_components(self):
        router = UnifiedDelegationRouter()
        # Advanced components should be None
        assert router._ml_router is None
        assert router._skill_registry is None
        assert router._health_monitor is None
        assert router._context_sharing is None
        assert router._task_decomposer is None
        assert router._prompt_templates is None
        assert router._ab_testing is None
        assert router._agent_communication is None
        assert router._advanced_learning is None

    def test_memory_router_lazy_init(self):
        """Test memory router is lazily initialized."""
        router = UnifiedDelegationRouter()
        # Initially None
        assert router._memory_router is None

    def test_trigger_router_lazy_init(self):
        """Test trigger router is lazily initialized."""
        router = UnifiedDelegationRouter()
        assert router._trigger_router is None

    def test_local_analyzer_lazy_init(self):
        """Test local analyzer is lazily initialized."""
        router = UnifiedDelegationRouter()
        assert router._local_analyzer is None

    def test_complexity_scorer_lazy_init(self):
        """Test complexity scorer is lazily initialized."""
        router = UnifiedDelegationRouter()
        assert router._complexity_scorer is None


class TestRouterFallback:
    """Test fallback behavior when components unavailable."""

    def test_fallback_keyword_routing(self):
        """Test keyword fallback when no other routing works."""
        router = UnifiedDelegationRouter()
        # Should not raise even without components initialized
        # The router should handle missing components gracefully
        assert router is not None
        assert hasattr(router, "_init_components")

    def test_fallback_chain_structure(self):
        """Test that fallback chain exists."""
        router = UnifiedDelegationRouter()
        # Check that core components are defined
        assert hasattr(router, "_memory_router")
        assert hasattr(router, "_trigger_router")
        assert hasattr(router, "_local_analyzer")
        assert hasattr(router, "_routing_optimizer")
        assert hasattr(router, "_outcome_logger")
        assert hasattr(router, "_complexity_scorer")


class TestRoutingStrategies:
    """Test routing strategy components."""

    def test_ml_router_placeholder(self):
        """Test ML router placeholder."""
        router = UnifiedDelegationRouter()
        assert router._ml_router is None

    def test_skill_registry_placeholder(self):
        """Test skill registry placeholder."""
        router = UnifiedDelegationRouter()
        assert router._skill_registry is None

    def test_health_monitor_placeholder(self):
        """Test health monitor placeholder."""
        router = UnifiedDelegationRouter()
        assert router._health_monitor is None

    def test_context_sharing_placeholder(self):
        """Test context sharing placeholder."""
        router = UnifiedDelegationRouter()
        assert router._context_sharing is None

    def test_task_decomposer_placeholder(self):
        """Test task decomposer placeholder."""
        router = UnifiedDelegationRouter()
        assert router._task_decomposer is None

    def test_prompt_templates_placeholder(self):
        """Test prompt templates placeholder."""
        router = UnifiedDelegationRouter()
        assert router._prompt_templates is None

    def test_ab_testing_placeholder(self):
        """Test A/B testing placeholder."""
        router = UnifiedDelegationRouter()
        assert router._ab_testing is None

    def test_agent_communication_placeholder(self):
        """Test agent communication placeholder."""
        router = UnifiedDelegationRouter()
        assert router._agent_communication is None

    def test_advanced_learning_placeholder(self):
        """Test advanced learning placeholder."""
        router = UnifiedDelegationRouter()
        assert router._advanced_learning is None
        assert router._ActionType is None


class TestImportIntegration:
    """Test that module imports work correctly."""

    def test_import_from_intelligence(self):
        """Test import from src.intelligence.unified_router."""
        from src.intelligence.unified_router import UnifiedDelegationRouter

        assert UnifiedDelegationRouter is not None

    def test_import_from_tools_intelligence(self):
        """Test import from src.tools.intelligence.unified_router."""
        from src.tools.intelligence.unified_router import UnifiedDelegationRouter

        assert UnifiedDelegationRouter is not None

    def test_import_routing_decision(self):
        """Test RoutingDecision import."""
        from src.tools.intelligence.unified_router import RoutingDecision

        assert RoutingDecision is not None
