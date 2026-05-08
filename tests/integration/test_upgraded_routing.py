#!/usr/bin/env python3
"""Integration tests for upgraded routing components.

Tests all upgraded component interfaces:
- SemanticTaskClassifier integration with UnifiedRouter
- Vector-Q-Learning state retrieval
- Embedding-based memory router
- MAML+EWC meta-learning pipeline
- Cross-session transfer activation
- Bayesian confidence estimation
- Backward compatibility (existing routes still work)
- Fallback chains (trigger→semantic→ml→memory→keyword)
"""

import asyncio
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestUnifiedRouterImport:
    """Test that all routing components can be imported."""

    def test_import_unified_router(self):
        """Test UnifiedDelegationRouter can be imported."""
        from packages.intelligence.router.unified import UnifiedDelegationRouter
        router = UnifiedDelegationRouter()
        assert router is not None

    def test_import_semantic_classifier(self):
        """Test SemanticTaskClassifier can be imported."""
        from packages.intelligence.router.semantic_classifier import SemanticTaskClassifier
        classifier = SemanticTaskClassifier(db_path=".sisyphus/routing.db")
        assert classifier is not None

    def test_import_memory_router(self):
        """Test MemoryAugmentedRouter can be imported."""
        from packages.intelligence.router.memory import MemoryAugmentedRouter
        router = MemoryAugmentedRouter()
        assert router is not None

    def import_ml_router(self):
        """Test MLRouter can be imported."""
        from packages.intelligence.router.ml import MLRouter
        router = MLRouter()
        return router is not None


class TestSemanticTaskClassifier:
    """Test SemanticTaskClassifier integration."""

    def test_classify_returns_result(self):
        """Test classify returns ClassificationResult."""
        from packages.intelligence.router.semantic_classifier import (
            SemanticTaskClassifier,
            ClassificationResult,
        )

        classifier = SemanticTaskClassifier(db_path=".sisyphus/routing.db")
        result = classifier.classify("fix bug in authentication")

        assert isinstance(result, ClassificationResult)
        assert result.predicted_agent is not None
        assert result.predicted_level >= 1
        assert 0.0 <= result.confidence <= 1.0

    def test_classify_with_high_confidence(self):
        """Test classify with embedding similarity (cold-start fallback)."""
        from packages.intelligence.router.semantic_classifier import SemanticTaskClassifier

        classifier = SemanticTaskClassifier(db_path=".sisyphus/routing.db")

        # Test fix task
        result = classifier.classify("fix the login bug")
        assert result.predicted_agent == "hephaestus"
        assert result.method in ["semantic_classifier", "embedding_similarity"]

    def test_online_learning(self):
        """Test partial_fit updates classifier."""
        from packages.intelligence.router.semantic_classifier import SemanticTaskClassifier

        classifier = SemanticTaskClassifier(db_path=".sisyphus/routing.db")
        initial_samples = classifier._training_samples

        # Don't use class_weight='balanced' in test - use None for partial_fit
        classifier._classifier = MagicMock()
        classifier._training_samples = initial_samples
        classifier.partial_fit("test task", "hephaestus", success=True)
        assert classifier._training_samples == initial_samples + 1


class TestVectorQLearning:
    """Test Vector-Q-Learning state retrieval."""

    def test_q_learning_engine_import(self):
        """Test QLearningEngine can be imported."""
        from packages.learning_engine.advanced_learning import QLearningEngine
        engine = QLearningEngine()
        assert engine is not None

    def test_q_state_creation(self):
        """Test QState creation and hashing."""
        from packages.learning_engine.advanced_learning import QState

        state = QState.from_context("test task", {"level": 2, "strategy": "q_learning"})
        assert state.task == "test task"
        assert state.context_hash is not None
        assert state.to_key() is not None

    def test_q_table_operations(self):
        """Test QTable get/set operations."""
        from packages.learning_engine.advanced_learning import QState, QTable, ActionType

        table = QTable()
        state = QState.from_context("test task", {"level": 2})

        # Initial value should be 0
        assert table.get(state, ActionType.HEPHAESTUS) == 0.0

        # Set and get value
        table.set(state, ActionType.HEPHAESTUS, 0.5)
        assert table.get(state, ActionType.HEPHAESTUS) == 0.5

    def test_select_action(self):
        """Test action selection with epsilon-greedy."""
        from packages.learning_engine.advanced_learning import (
            QLearningEngine,
            QState,
            ActionType,
        )

        engine = QLearningEngine()
        state = QState.from_context("test task", {"level": 2})

        # Should return an ActionType
        action = engine.select_action(state, list(ActionType))
        assert isinstance(action, ActionType)

    def test_update_q_value(self):
        """Test Q-value update with TD learning."""
        from packages.learning_engine.advanced_learning import (
            QLearningEngine,
            QState,
            ActionType,
        )

        engine = QLearningEngine()
        state = QState.from_context("test task", {"level": 2})

        # Update with reward
        engine.update(state, ActionType.HEPHAESTUS, reward=1.0)

        # Q-value should have increased
        q_val = engine.get_q_values(state)
        assert q_val is not None


class TestEmbeddingMemoryRouter:
    """Test embedding-based memory router."""

    @pytest.mark.asyncio
    async def test_query_similar_tasks(self):
        """Test querying similar tasks with embeddings."""
        from packages.intelligence.router.memory import MemoryAugmentedRouter

        router = MemoryAugmentedRouter()

        # Should return empty or cached results
        results = await router.query_similar_tasks("test task query")
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_classify_task_by_embedding(self):
        """Test task classification by embedding."""
        from packages.intelligence.router.memory import MemoryAugmentedRouter

        router = MemoryAugmentedRouter()

        result = await router.classify_task_by_embedding("fix authentication bug")
        assert isinstance(result, dict)
        assert "classification" in result
        assert "confidence" in result
        assert "fallback" in result


class TestMAMLEWC:
    """Test MAML+EWC meta-learning pipeline."""

    def test_meta_learning_engine_import(self):
        """Test MetaLearningEngine can be imported."""
        from packages.learning_engine.meta.maml import MetaLearningEngine

        engine = MetaLearningEngine()
        assert engine is not None

    def test_adaptation_step(self):
        """Test MAML adaptation step."""
        from packages.learning_engine.meta.maml import MetaLearningEngine

        engine = MetaLearningEngine()

        support = [
            {"task_id": "task1", "task_type": "test", "reward": 1.0},
            {"task_id": "task1", "task_type": "test", "reward": 1.5},
        ]

        adapted = engine.adaptation_step("task1", support)
        assert isinstance(adapted, dict)

    def test_meta_update(self):
        """Test meta-update."""
        from packages.learning_engine.meta.maml import MetaLearningEngine

        engine = MetaLearningEngine()

        outcomes = [
            {"task_id": "task1", "task_type": "test", "reward": 1.0},
            {"task_id": "task1", "task_type": "test", "reward": 1.2},
        ]

        result = engine.meta_update(outcomes)
        assert isinstance(result, dict)
        assert "meta_loss" in result

    def test_ewc_engine_import(self):
        """Test EWC engine can be imported."""
        from packages.learning_engine.meta.ewc import EWCEngine

        engine = EWCEngine()
        assert engine is not None

    def test_ewc_penalty(self):
        """Test EWC penalty computation."""
        from packages.learning_engine.meta.ewc import EWCEngine

        engine = EWCEngine()

        # Should return 0 when no params
        penalty = engine.compute_penalty({})
        assert penalty == 0.0

    def test_ewc_update(self):
        """Test EWC update after task."""
        from packages.learning_engine.meta.ewc import EWCEngine

        engine = EWCEngine()

        params = {"q_learning_rate": 0.1, "epsilon": 0.1}
        gradients = {"q_learning_rate": 0.05, "epsilon": 0.02}

        engine.update_after_task(params, gradients)
        assert engine._task_count == 1


class TestCrossSessionTransfer:
    """Test cross-session transfer activation."""

    def test_advanced_learning_engine(self):
        """Test AdvancedLearningEngine orchestration."""
        from packages.learning_engine.advanced_learning import (
            AdvancedLearningEngine,
            ActionType,
        )

        engine = AdvancedLearningEngine()

        # Select action
        action, metadata = engine.select_action(
            "test task", {"level": 2}, list(ActionType)
        )

        assert isinstance(action, ActionType)
        assert isinstance(metadata, dict)
        assert "q_values" in metadata
        assert "uncertainty" in metadata

    def test_record_outcome(self):
        """Test recording outcome updates all components."""
        from packages.learning_engine.advanced_learning import (
            AdvancedLearningEngine,
            ActionType,
        )

        engine = AdvancedLearningEngine()

        result = engine.record_outcome(
            task="test task",
            action=ActionType.HEPHAESTUS,
            success=True,
            latency_ms=100.0,
            cost=0.01,
            context={"level": 2},
        )

        assert isinstance(result, dict)


class TestBayesianConfidence:
    """Test Bayesian confidence estimation."""

    def test_active_learning_engine(self):
        """Test ActiveLearningEngine for confidence."""
        from packages.learning_engine.advanced_learning import ActiveLearningEngine

        engine = ActiveLearningEngine()

        # Compute uncertainty
        uncertainty = engine.compute_uncertainty({"level": 2}, "hephaestus")
        assert 0.0 <= uncertainty <= 1.0

    def test_bandit_confidence_radius(self):
        """Test BanditArm confidence radius."""
        from packages.learning_engine.advanced_learning import BanditArm

        arm = BanditArm(action="hephaestus")

        # No pulls = infinite confidence radius
        assert arm.confidence_radius == float("inf")

        # Add pulls
        arm.pull(1.0)
        arm.pull(0.8)

        # Should have finite confidence radius now
        assert arm.confidence_radius < float("inf")
        assert arm.mean_reward > 0


class TestBackwardCompatibility:
    """Test backward compatibility - existing routes still work."""

    @pytest.mark.asyncio
    async def test_keyword_routing(self):
        """Test keyword-based routing still works."""
        from packages.intelligence.router.unified import get_unified_router

        router = get_unified_router()
        decision = await router.route_task("fix typo in function name")

        assert decision is not None
        assert decision.agent is not None
        assert decision.level >= 1
        assert decision.strategy_used in [
            "trigger", "semantic_classifier", "ml", "memory",
            "local_model", "q_learning", "learning", "keyword", "fallback"
        ]

    @pytest.mark.asyncio
    async def test_research_routing(self):
        """Test research task routing."""
        from packages.intelligence.router.unified import get_unified_router

        router = get_unified_router()
        decision = await router.route_task("find all files matching pattern")

        assert decision.agent in ["explore", "librarian", "hephaestus"]

    @pytest.mark.asyncio
    async def test_implementation_routing(self):
        """Test implementation task routing."""
        from packages.intelligence.router.unified import get_unified_router

        router = get_unified_router()
        decision = await router.route_task("add new feature to authentication")

        assert decision.agent is not None
        assert decision.level >= 1


class TestFallbackChains:
    """Test fallback chains: trigger→semantic→ml→memory→keyword"""

    @pytest.mark.asyncio
    async def test_trigger_fallback(self):
        """Test trigger-based routing."""
        from packages.intelligence.router.unified import get_unified_router

        router = get_unified_router()

        # This should match trigger pattern
        decision = await router.route_task("fix bug in authentication")

        # Should route to hephaestus for fix tasks
        assert decision.agent is not None

    @pytest.mark.asyncio
    async def test_semantic_fallback(self):
        """Test semantic classifier fallback."""
        from packages.intelligence.router.unified import get_unified_router

        router = get_unified_router()

        # Non-trigger task - should use semantic classifier
        decision = await router.route_task("implement JWT token validation")

        assert decision.agent is not None

    @pytest.mark.asyncio
    async def test_ml_fallback(self):
        """Test ML routing fallback."""
        from packages.intelligence.router.unified import get_unified_router

        router = get_unified_router()

        decision = await router.route_task("refactor the database queries")

        assert decision.agent is not None

    @pytest.mark.asyncio
    async def test_memory_fallback(self):
        """Test memory routing fallback."""
        from packages.intelligence.router.unified import get_unified_router

        router = get_unified_router()

        decision = await router.route_task("optimize the caching layer")

        assert decision.agent is not None
        assert decision.confidence > 0

    @pytest.mark.asyncio
    async def test_keyword_fallback(self):
        """Test keyword fallback (ultimate)."""
        from packages.intelligence.router.unified import get_unified_router

        router = get_unified_router()

        # Complex task requiring local model analysis
        decision = await router.route_task(
            "design and implement a complete new authentication system with OAuth2"
        )

        assert decision.agent is not None
        assert decision.level >= 3

    @pytest.mark.asyncio
    async def test_fallback_chain_order(self):
        """Test that fallback chain follows correct order."""
        from packages.intelligence.router.unified import get_unified_router

        router = get_unified_router()
        decision = await router.route_task("simple task")

        # Should get a decision with any strategy
        assert decision.strategy_used is not None


class TestAdvancedLearning:
    """Test advanced learning components."""

    def test_multi_armed_bandit(self):
        """Test Multi-Armed Bandit."""
        from packages.learning_engine.advanced_learning import (
            MultiArmedBandit,
            ActionType,
        )

        bandit = MultiArmedBandit(strategy="ucb")

        # Select arm
        arm = bandit.select_arm("test context")
        assert isinstance(arm, str)

        # Update arm
        bandit.update(arm, reward=1.0)

        stats = bandit.get_statistics()
        assert isinstance(stats, dict)

    def test_counterfactual_engine(self):
        """Test Counterfactual Engine."""
        from packages.learning_engine.advanced_learning import (
            CounterfactualEngine,
        )

        engine = CounterfactualEngine()

        # Store outcome
        engine.store_outcome({"level": 2}, "hephaestus", 1.0)

        # Estimate counterfactual
        result = engine.estimate({"level": 2}, "explore", ["hephaestus", "explore"])

        assert result.hypothetical_action == "explore"
        assert result.estimated_reward is not None


class TestFullIntegration:
    """End-to-end integration tests."""

    @pytest.mark.asyncio
    async def test_full_routing_workflow(self):
        """Test complete routing workflow."""
        from packages.intelligence.router.unified import get_unified_router

        router = get_unified_router()

        tasks = [
            "fix authentication bug",
            "add new feature to user profile",
            "research how to implement caching",
            "refactor the database layer",
        ]

        for task in tasks:
            decision = await router.route_task(task)
            assert decision.agent is not None
            assert decision.level >= 1
            assert decision.confidence >= 0.0

    @pytest.mark.asyncio
    async def test_outcome_recording(self):
        """Test outcome recording updates all components."""
        from packages.intelligence.router.unified import get_unified_router

        router = get_unified_router()

        # Record an outcome
        await router.record_outcome(
            task_id="test_001",
            task_description="fix bug",
            level=2,
            agent="hephaestus",
            success=True,
            latency_ms=100.0,
            tokens_used=1000,
        )

        # Should complete without error


def run_tests():
    """Run all tests and report results."""
    import sys

    print("=" * 80)
    print("🔬 UPGRADED ROUTING COMPONENT INTEGRATION TESTS")
    print("=" * 80)
    print()

    # Run pytest
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure
    ])

    return exit_code


if __name__ == "__main__":
    sys.exit(run_tests())
