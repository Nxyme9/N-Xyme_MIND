"""Unit tests for orchestration.react_agent."""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from src.orchestration.react_agent import (
    ReActStatus,
    Thought,
    Action,
    Observation,
    ReActStep,
    ReActResult,
    WorkingMemory,
    CircuitBreaker,
    CircuitBreakerState,
    ReActAgent,
    get_react_agent,
)


class TestEnums:
    """Test enum values."""

    def test_react_status_values(self):
        assert ReActStatus.THINKING.value == "thinking"
        assert ReActStatus.ACTING.value == "acting"
        assert ReActStatus.OBSERVING.value == "observing"
        assert ReActStatus.COMPLETE.value == "complete"
        assert ReActStatus.FAILED.value == "failed"
        assert ReActStatus.MAX_STEPS.value == "max_steps"


class TestDataclasses:
    """Test dataclass structures."""

    def test_thought_creation(self):
        thought = Thought(content="test thought", reasoning="reasoning", confidence=0.8)
        assert thought.content == "test thought"
        assert thought.confidence == 0.8

    def test_action_creation(self):
        action = Action(
            tool_name="test_tool",
            params={"key": "value"},
            is_final=True,
            final_answer="answer",
        )
        assert action.tool_name == "test_tool"
        assert action.is_final is True

    def test_observation_creation(self):
        obs = Observation(success=True, result="result", error="")
        assert obs.success is True
        assert obs.result == "result"

    def test_observation_failure(self):
        obs = Observation(success=False, result=None, error="error message")
        assert obs.success is False
        assert obs.error == "error message"

    def test_react_step_creation(self):
        thought = Thought(content="test")
        action = Action(tool_name="test")
        obs = Observation(success=True)
        step = ReActStep(
            step_num=1,
            thought=thought,
            action=action,
            observation=obs,
            status=ReActStatus.COMPLETE,
        )
        assert step.step_num == 1
        assert step.status == ReActStatus.COMPLETE

    def test_react_result_creation(self):
        result = ReActResult(
            answer="final answer",
            status=ReActStatus.COMPLETE,
            steps=[],
            total_llm_calls=5,
            total_tool_calls=3,
            execution_time=1.5,
        )
        assert result.answer == "final answer"
        assert result.total_llm_calls == 5


class TestWorkingMemory:
    """Test WorkingMemory class."""

    def test_memory_init(self):
        memory = WorkingMemory(goal="test goal")
        assert memory.goal == "test goal"
        assert memory.context == {}
        assert memory.observations == []

    def test_memory_set_get(self):
        memory = WorkingMemory()
        memory.set("key1", "value1")
        assert memory.get("key1") == "value1"
        assert memory.get("nonexistent", "default") == "default"

    def test_failure_tracking(self):
        memory = WorkingMemory()
        memory.record_failure("tool1")
        memory.record_failure("tool1")
        assert memory.get_failure_count("tool1") == 2
        assert memory.get_failure_count("tool2") == 0

    def test_to_context_string(self):
        memory = WorkingMemory(goal="test goal")
        memory.set("key1", "value1")
        memory.record_failure("tool1")
        context = memory.to_context_string()
        assert "test goal" in context
        assert "key1" in context


class TestCircuitBreaker:
    """Test CircuitBreaker class."""

    def test_circuit_breaker_init(self):
        cb = CircuitBreaker(failure_threshold=5, time_window=30.0, cooldown=60.0)
        assert cb.failure_threshold == 5
        assert cb.time_window == 30.0

    def test_is_allowed_initially(self):
        cb = CircuitBreaker()
        assert cb.is_allowed("tool1") is True

    def test_record_success(self):
        cb = CircuitBreaker()
        cb.record_failure("tool1")
        cb.record_success("tool1")
        assert cb.is_allowed("tool1") is True

    def test_circuit_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=2, time_window=60.0, cooldown=30.0)
        cb.record_failure("tool1")
        assert cb.is_allowed("tool1") is True
        cb.record_failure("tool1")
        assert cb.is_allowed("tool1") is False

    def test_cooldown_resets(self):
        import time

        cb = CircuitBreaker(failure_threshold=1, time_window=60.0, cooldown=0.1)
        cb.record_failure("tool1")
        assert cb.is_allowed("tool1") is False
        time.sleep(0.2)
        assert cb.is_allowed("tool1") is True


class TestCircuitBreakerState:
    """Test CircuitBreakerState dataclass."""

    def test_state_creation(self):
        state = CircuitBreakerState(
            failure_count=3, first_failure_time=1000.0, is_open=True, open_until=2000.0
        )
        assert state.failure_count == 3
        assert state.is_open is True


class TestReActAgent:
    """Test ReActAgent class."""

    @pytest.fixture
    def mock_brain(self):
        brain = MagicMock()
        brain.think = AsyncMock(return_value={"thought": "Test response"})
        return brain

    @pytest.fixture
    def react_agent(self, mock_brain):
        return ReActAgent(brain=mock_brain, max_steps=3)

    def test_agent_init(self, react_agent):
        assert react_agent.max_steps == 3
        assert react_agent.brain is not None
        assert react_agent.circuit_breaker is not None
        assert react_agent.tool_registry is not None
        assert react_agent.model_classifier is not None

    def test_default_classifier(self, react_agent):
        route = react_agent.model_classifier.classify("general", "test task")
        assert route.model_name == "default"
        assert route.confidence == 0.5

    def test_default_tool_registry(self, react_agent):
        assert react_agent.tool_registry.has_tool("any_tool") is False


class TestFunctions:
    """Test module-level functions."""

    def test_get_react_agent_cached(self):
        # Clear any existing instance
        import src.orchestration.react_agent as ra_module

        ra_module.REACT_AGENT = None

        mock_brain = MagicMock()
        agent1 = get_react_agent(brain=mock_brain)
        agent2 = get_react_agent(brain=mock_brain)
        # Both should be the same cached instance
        assert agent1 is agent2
