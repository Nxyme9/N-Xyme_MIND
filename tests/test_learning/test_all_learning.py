"""Comprehensive unit tests for all learning modules."""

import pytest
import sys
import os
import tempfile
import sqlite3
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestSkillLifecycle:
    """Tests for skill_lifecycle.py"""

    def test_register_skill(self):
        from src.tools.learning.skill_lifecycle import SkillLifecycleManager

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            mgr = SkillLifecycleManager(f.name)
            skill = mgr.register("test_skill", "A test skill")
            assert skill.name == "test_skill"
            assert skill.state.value == "proposed"
            os.unlink(f.name)

    def test_transition_states(self):
        from src.tools.learning.skill_lifecycle import SkillLifecycleManager, SkillState

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            mgr = SkillLifecycleManager(f.name)
            mgr.register("test_skill", "A test skill")
            mgr.transition("test_skill", SkillState.EXPERIMENTAL)
            skill = mgr.get("test_skill")
            assert skill.state == SkillState.EXPERIMENTAL
            os.unlink(f.name)

    def test_record_outcome(self):
        from src.tools.learning.skill_lifecycle import SkillLifecycleManager

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            mgr = SkillLifecycleManager(f.name)
            mgr.register("test_skill", "A test skill")
            metrics = mgr.record_outcome("test_skill", success=True, latency_ms=100.0)
            assert metrics.success_rate == 1.0
            assert metrics.invocation_count == 1
            os.unlink(f.name)

    def test_list_skills(self):
        from src.tools.learning.skill_lifecycle import SkillLifecycleManager

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            mgr = SkillLifecycleManager(f.name)
            mgr.register("skill1", "Skill 1")
            mgr.register("skill2", "Skill 2")
            skills = mgr.list_skills()
            assert len(skills) == 2
            os.unlink(f.name)

    def test_delete_skill(self):
        from src.tools.learning.skill_lifecycle import SkillLifecycleManager

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            mgr = SkillLifecycleManager(f.name)
            mgr.register("test_skill", "A test skill")
            mgr.delete("test_skill")
            skill = mgr.get("test_skill")
            assert skill is None
            os.unlink(f.name)


class TestSelfLearning:
    """Tests for self_learning.py"""

    def test_record_outcome(self):
        from src.tools.learning.self_learning import SelfLearner

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            learner = SelfLearner(db_path=f.name)
            learner.record_outcome("task1", "action1", True, 100.0)
            outcomes = learner.get_outcomes()
            assert len(outcomes) == 1
            assert outcomes[0].success == True
            os.unlink(f.name)

    def test_get_patterns(self):
        from src.tools.learning.self_learning import SelfLearner

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            learner = SelfLearner(db_path=f.name)
            # Record multiple outcomes for same task
            for i in range(5):
                learner.record_outcome("task1", "action1", i < 4, 100.0)
            pattern = learner.get_pattern("task1", "action1")
            assert pattern is not None
            os.unlink(f.name)

    def test_get_best_action(self):
        from src.tools.learning.self_learning import SelfLearner

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            learner = SelfLearner(db_path=f.name)
            learner.record_outcome("task1", "action_a", True, 100.0)
            learner.record_outcome("task1", "action_a", True, 100.0)
            learner.record_outcome("task1", "action_b", False, 200.0)
            best = learner.get_best_action("task1")
            assert best == "action_a"
            os.unlink(f.name)

    def test_task_status(self):
        from src.tools.learning.self_learning import SelfLearner

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            learner = SelfLearner(db_path=f.name)
            learner.record_outcome("task1", "action1", True, 100.0)
            learner.record_outcome("task1", "action1", False, 150.0)
            status = learner.task_status("task1")
            assert status.get("total_outcomes", 0) == 2
            assert status["success_rate"] == 0.5
            os.unlink(f.name)

    def test_clear_outcomes(self):
        from src.tools.learning.self_learning import SelfLearner

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            learner = SelfLearner(db_path=f.name)
            learner.record_outcome("task1", "action1", True, 100.0)
            learner.clear_outcomes()
            outcomes = learner.get_outcomes()
            assert len(outcomes) == 0
            os.unlink(f.name)


class TestPromptEvolution:
    """Tests for prompt_evolution.py"""

    def test_register_prompt(self):
        from src.tools.learning.prompt_evolution import PromptWizard

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            pw = PromptWizard(db_path=f.name)
            record = pw.register("test_prompt", "Test prompt content")
            assert record.prompt_id == "test_prompt"
            assert len(record.versions) == 1
            os.unlink(f.name)

    def test_evolve_prompt(self):
        from src.tools.learning.prompt_evolution import PromptWizard

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            pw = PromptWizard(db_path=f.name)
            pw.register("test_prompt", "Test prompt content")
            record = pw.evolve("test_prompt", max_iterations=1)
            assert len(record.versions) >= 1
            os.unlink(f.name)

    def test_get_current_prompt(self):
        from src.tools.learning.prompt_evolution import PromptWizard

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            pw = PromptWizard(db_path=f.name)
            pw.register("test_prompt", "Test prompt content")
            current = pw.get_current("test_prompt")
            assert current is not None
            assert current.content == "Test prompt content"
            os.unlink(f.name)

    def test_list_prompts(self):
        from src.tools.learning.prompt_evolution import PromptWizard

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            pw = PromptWizard(db_path=f.name)
            pw.register("prompt1", "Content 1")
            pw.register("prompt2", "Content 2")
            prompts = pw.list_prompts()
            assert len(prompts) == 2
            os.unlink(f.name)

    def test_delete_prompt(self):
        from src.tools.learning.prompt_evolution import PromptWizard

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            pw = PromptWizard(db_path=f.name)
            pw.register("test_prompt", "Test prompt content")
            pw.delete("test_prompt")
            record = pw.get("test_prompt")
            assert record is None
            os.unlink(f.name)


class TestEventBus:
    """Tests for event_bus.py"""

    def test_publish_and_query(self):
        from src.tools.learning.event_bus import LearningEventBus, LearningEvent

        bus = LearningEventBus()
        bus.publish(LearningEvent("test", "task1", "action1", True, {}))
        events = bus.get_events("task1")
        assert len(events) >= 1

    def test_flush(self):
        from src.tools.learning.event_bus import LearningEventBus, LearningEvent

        bus = LearningEventBus()
        bus.publish(LearningEvent("test", "task1", "action1", True, {}))
        bus.flush()
        # After flush, events should be persisted
        events = bus.get_events("task1")
        assert len(events) >= 1

    def test_subscribe(self):
        from src.tools.learning.event_bus import LearningEventBus, LearningEvent

        bus = LearningEventBus()
        received = []
        bus.subscribe("test", lambda e: received.append(e))
        bus.publish(LearningEvent("test", "task1", "action1", True, {}))
        assert len(received) == 1


class TestSignals:
    """Tests for signals.py"""

    def test_detect_interaction_signals(self):
        from src.tools.learning.signals import SignalDetector

        detector = SignalDetector()
        signals = detector.detect_interaction_signals(
            "test query", [{"id": "r1"}], "response"
        )
        assert isinstance(signals, list)

    def test_compute_signal_score(self):
        from src.tools.learning.signals import (
            SignalDetector,
            Signal,
            SignalCategory,
            SignalType,
        )

        detector = SignalDetector()
        signals = [
            Signal(SignalCategory.INTERACTION, SignalType.SATISFACTION, 0.8, {}, 0)
        ]
        score = detector.compute_signal_score(signals)
        assert 0.0 <= score <= 1.0

    def test_detect_execution_signals(self):
        from src.tools.learning.signals import SignalDetector

        detector = SignalDetector()
        signals = detector.detect_execution_signals([], ["error1", "error2"])
        assert isinstance(signals, list)

    def test_detect_environment_signals(self):
        from src.tools.learning.signals import SignalDetector

        detector = SignalDetector()
        signals = detector.detect_environment_signals([], {"cpu": 90})
        assert isinstance(signals, list)


class TestSkillRegistry:
    """Tests for skill_registry.py"""

    def test_register_skill(self):
        from src.tools.learning.skill_registry import SkillRegistry

        reg = SkillRegistry()
        reg.register_skill("test_skill", "Test skill", ["test"], "semantic")
        skill = reg.get_skill("test_skill")
        assert skill is not None
        assert skill["name"] == "Test skill"

    def test_route_query(self):
        from src.tools.learning.skill_registry import SkillRegistry

        reg = SkillRegistry()
        reg.register_skill("search", "Search", ["search", "find"], "semantic")
        reg.register_skill("create", "Create", ["create", "add"], "semantic")
        routes = reg.route_query("search for something")
        assert len(routes) >= 1
        assert routes[0]["skill_id"] == "search"

    def test_update_performance(self):
        from src.tools.learning.skill_registry import SkillRegistry

        reg = SkillRegistry()
        import uuid
        skill_id = f"perf_test_{uuid.uuid4().hex[:8]}"
        reg.register_skill(skill_id, "Perf test", ["test"], "semantic")
        reg.update_performance(skill_id, True, 100.0)
        reg.update_performance(skill_id, False, 200.0)
        skill = reg.get_skill(skill_id)
        assert skill is not None
        assert skill.get("invocation_count", 0) == 2

    def test_list_skills(self):
        from src.tools.learning.skill_registry import SkillRegistry

        reg = SkillRegistry()
        reg.register_skill("list1", "Skill 1", ["test"], "semantic")
        reg.register_skill("list2", "Skill 2", ["test"], "semantic")
        skills = reg.list_skills()
        test_skills = [s for s in skills if s.get("name") in ("Skill 1", "Skill 2")]
        assert len(test_skills) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
