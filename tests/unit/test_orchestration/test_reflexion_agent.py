"""Unit tests for orchestration.reflexion_agent."""

import time
import pytest
from unittest.mock import patch, MagicMock
from src.orchestration.reflexion_agent import (
    ReflexionStatus,
    EvaluationScore,
    TaskOutcome,
    Evaluation,
    Reflection,
    ReflexionCycle,
    ReflexionResult,
    Actor,
    Evaluator,
    Reflector,
    AgentActor,
    ReflexionAgent,
    run_reflexion_task,
    create_reflexion_agent,
)


class TestEnums:
    """Test enum values."""

    def test_reflexion_status_values(self):
        assert ReflexionStatus.RUNNING.value == "running"
        assert ReflexionStatus.SUCCESS.value == "success"
        assert ReflexionStatus.FAILED.value == "failed"
        assert ReflexionStatus.MAX_CYCLES.value == "max_cycles"
        assert ReflexionStatus.IMPROVED.value == "improved"

    def test_evaluation_score_values(self):
        assert EvaluationScore.EXCELLENT.value == "excellent"
        assert EvaluationScore.GOOD.value == "good"
        assert EvaluationScore.ACCEPTABLE.value == "acceptable"
        assert EvaluationScore.POOR.value == "poor"
        assert EvaluationScore.FAILED.value == "failed"


class TestDataclasses:
    """Test dataclass structures."""

    def test_task_outcome_creation(self):
        outcome = TaskOutcome(
            success=True,
            result="test result",
            error="",
            steps_taken=5,
            execution_time=1.5,
        )
        assert outcome.success is True
        assert outcome.result == "test result"
        assert outcome.steps_taken == 5

    def test_task_outcome_creation_with_error(self):
        outcome = TaskOutcome(
            success=False,
            result=None,
            error="test error",
            steps_taken=2,
            execution_time=0.5,
        )
        assert outcome.success is False
        assert outcome.error == "test error"

    def test_evaluation_creation(self):
        eval_obj = Evaluation(
            score=0.8,
            rating=EvaluationScore.GOOD,
            strengths=["strength1"],
            weaknesses=["weakness1"],
            suggestions=["suggestion1"],
        )
        assert eval_obj.score == 0.8
        assert eval_obj.rating == EvaluationScore.GOOD

    def test_reflection_creation(self):
        reflection = Reflection(
            critique="critique text",
            lessons=["lesson1"],
            action_items=["action1"],
            confidence=0.9,
        )
        assert reflection.critique == "critique text"
        assert reflection.confidence == 0.9

    def test_reflexion_cycle_creation(self):
        outcome = TaskOutcome(success=True, result="test")
        evaluation = Evaluation(score=0.8, rating=EvaluationScore.GOOD)
        reflection = Reflection(critique="test", lessons=[], action_items=[])
        cycle = ReflexionCycle(
            cycle_num=1,
            task="test task",
            outcome=outcome,
            evaluation=evaluation,
            reflection=reflection,
        )
        assert cycle.cycle_num == 1

    def test_reflexion_result_creation(self):
        result = ReflexionResult(
            answer="answer",
            status=ReflexionStatus.SUCCESS,
            cycles=[],
            best_score=0.9,
            improvement=0.1,
            total_execution_time=1.0,
        )
        assert result.status == ReflexionStatus.SUCCESS


class TestActor:
    """Test Actor class."""

    def test_actor_protocol_exists(self):
        """Test Actor protocol exists and is importable."""
        # Actor is a Protocol, cannot be instantiated directly
        assert Actor is not None


class TestEvaluator:
    """Test Evaluator class."""

    def test_evaluator_init(self):
        """Test Evaluator initialization."""
        evaluator = Evaluator(brain=None, use_llm=False)
        assert evaluator.use_llm is False

    def test_heuristic_evaluate_success(self):
        """Test heuristic evaluation for successful task."""
        evaluator = Evaluator(brain=None, use_llm=False)
        outcome = TaskOutcome(success=True, result="test", error=None)
        evaluation = evaluator._heuristic_evaluate("test task", outcome)
        assert evaluation.score > 0

    def test_heuristic_evaluate_failure(self):
        """Test heuristic evaluation for failed task."""
        evaluator = Evaluator(brain=None, use_llm=False)
        outcome = TaskOutcome(success=False, result=None, error="error message")
        evaluation = evaluator._heuristic_evaluate("test task", outcome)
        assert evaluation.score < 0.5

    def test_score_to_rating(self):
        """Test score to rating conversion."""
        evaluator = Evaluator(brain=None)
        assert evaluator._score_to_rating(0.9) == EvaluationScore.EXCELLENT
        assert evaluator._score_to_rating(0.7) == EvaluationScore.GOOD
        assert evaluator._score_to_rating(0.5) == EvaluationScore.ACCEPTABLE
        assert evaluator._score_to_rating(0.3) == EvaluationScore.POOR
        assert evaluator._score_to_rating(0.1) == EvaluationScore.FAILED


class TestReflector:
    """Test Reflector class."""

    def test_reflector_init(self):
        """Test Reflector initialization."""
        reflector = Reflector(brain=None, graphiti_client=None)
        assert reflector.brain is None

    def test_template_reflect(self):
        """Test template-based reflection."""
        reflector = Reflector(brain=None)
        outcome = TaskOutcome(success=True, result="test")
        evaluation = Evaluation(
            score=0.8,
            rating=EvaluationScore.GOOD,
            strengths=[],
            weaknesses=[],
            suggestions=[],
        )
        reflection = reflector._template_reflect("task", outcome, evaluation)
        assert reflection is not None


class TestAgentActor:
    """Test AgentActor class."""

    def test_agent_actor_init(self):
        """Test AgentActor initialization."""
        actor = AgentActor(agent=None, agent_type="test")
        assert actor.agent_type == "test"

    def test_build_reflection_context(self):
        """Test reflection context building."""
        actor = AgentActor(agent=None)
        reflections = [
            Reflection(
                critique="c1", lessons=["l1"], action_items=["a1"], confidence=0.5
            ),
            Reflection(
                critique="c2", lessons=["l2"], action_items=["a2"], confidence=0.7
            ),
        ]
        context = actor._build_reflection_context(reflections)
        assert "c1" in context or "l1" in context


class TestReflexionAgent:
    """Test ReflexionAgent class."""

    @pytest.fixture
    def reflexion_agent(self):
        """Create ReflexionAgent with mocked dependencies."""
        # Create mock objects
        mock_actor = MagicMock(spec=["execute"])
        mock_evaluator = MagicMock(spec=["evaluate"])
        mock_reflector = MagicMock(spec=["reflect", "retrieve_reflections"])
        
        # Create agent instance without calling __init__
        agent = object.__new__(ReflexionAgent)
        agent.actor = mock_actor
        agent.evaluator = mock_evaluator
        agent.reflector = mock_reflector
        agent.max_cycles = 3
        agent.success_threshold = 0.7
        agent.improvement_threshold = 0.1
        return agent

    def test_calculate_improvement_no_evaluations(self, reflexion_agent):
        """Test improvement calculation with no evaluations."""
        improvement = reflexion_agent._calculate_improvement([])
        assert improvement == 0.0

    def test_calculate_improvement_single_evaluation(self, reflexion_agent):
        """Test improvement calculation with single evaluation."""
        evaluations = [Evaluation(score=0.8, rating=EvaluationScore.GOOD)]
        improvement = reflexion_agent._calculate_improvement(evaluations)
        assert improvement == 0.0

    def test_calculate_improvement_multiple_evaluations(self, reflexion_agent):
        """Test improvement calculation with multiple evaluations."""
        evaluations = [
            Evaluation(score=0.5, rating=EvaluationScore.ACCEPTABLE),
            Evaluation(score=0.7, rating=EvaluationScore.GOOD),
        ]
        improvement = reflexion_agent._calculate_improvement(evaluations)
        assert improvement > 0


class TestFunctions:
    """Test module-level functions."""

    def test_run_reflexion_task_import(self):
        """Test run_reflexion_task is importable."""
        assert run_reflexion_task is not None
        assert callable(run_reflexion_task)

    def test_create_reflexion_agent(self):
        """Test create_reflexion_agent factory."""
        mock_agent = MagicMock()
        with patch("src.orchestration.reflexion_agent.AgentActor") as mock_actor_cls:
            with patch("src.orchestration.reflexion_agent.Evaluator") as mock_eval_cls:
                with patch("src.orchestration.reflexion_agent.Reflector") as mock_refl_cls:
                    # Set up return values
                    mock_actor_cls.return_value = MagicMock()
                    mock_eval_cls.return_value = MagicMock()
                    mock_refl_cls.return_value = MagicMock()
                    
                    agent = create_reflexion_agent(agent=mock_agent, brain=None)
                    assert agent is not None
                    assert isinstance(agent, ReflexionAgent)
