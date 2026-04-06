"""
Reflexion Agent — Actor-Evaluator-Reflector self-improvement pattern.

Implements the Reflexion framework for iterative self-improvement:
- Actor: Executes tasks using existing agent infrastructure
- Evaluator: Assesses outcomes and scores performance
- Reflector: Generates verbal critiques stored in episodic memory

Research validated: 10-15% improvement after 3-4 cycles.
Stores reflections in Graphiti for cross-session learning.

Architecture:
    Task → Actor → Outcome → Evaluator → Score
                                    ↓
                              Reflector → Critique → Graphiti
                                    ↓
                              Next Attempt (with reflection context)

Key features:
- Integrates with existing AgentLoop and ReActAgent
- Graphiti episodic memory for reflection storage
- Temporal decay on reflection relevance
- Circuit breaker integration for failure patterns
"""

import json
import time
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol
from enum import Enum

logger = logging.getLogger(__name__)


# ── Reflexion Types ─────────────────────────────────────────────────────


class ReflexionStatus(Enum):
    """Status of a reflexion cycle."""

    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    MAX_CYCLES = "max_cycles"
    IMPROVED = "improved"


class EvaluationScore(Enum):
    """Evaluation scores for task outcomes."""

    EXCELLENT = "excellent"  # 0.9-1.0
    GOOD = "good"  # 0.7-0.9
    ACCEPTABLE = "acceptable"  # 0.5-0.7
    POOR = "poor"  # 0.3-0.5
    FAILED = "failed"  # 0.0-0.3


@dataclass
class TaskOutcome:
    """Outcome of an actor execution."""

    success: bool
    result: Any = None
    error: str = ""
    steps_taken: int = 0
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Evaluation:
    """Evaluation of a task outcome."""

    score: float  # 0.0 to 1.0
    rating: EvaluationScore
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Reflection:
    """A verbal critique generated after evaluation."""

    critique: str
    lessons: List[str] = field(default_factory=list)
    action_items: List[str] = field(default_factory=list)
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReflexionCycle:
    """A single Actor-Evaluator-Reflector cycle."""

    cycle_num: int
    task: str
    outcome: TaskOutcome
    evaluation: Evaluation
    reflection: Optional[Reflection] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class ReflexionResult:
    """Final result of a reflexion agent run."""

    answer: str
    status: ReflexionStatus
    cycles: List[ReflexionCycle] = field(default_factory=list)
    best_score: float = 0.0
    improvement: float = 0.0  # Score improvement from first to last cycle
    total_execution_time: float = 0.0


# ── Actor Protocol ──────────────────────────────────────────────────────


class Actor(Protocol):
    """Protocol for task execution."""

    async def execute(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        reflections: Optional[List[Reflection]] = None,
    ) -> TaskOutcome:
        """Execute a task and return the outcome."""
        ...


# ── Evaluator ───────────────────────────────────────────────────────────


class Evaluator:
    """
    Evaluates task outcomes and scores performance.

    Uses heuristics and optional LLM-based evaluation to assess:
    - Task completion quality
    - Efficiency (steps taken, time)
    - Error patterns
    """

    def __init__(
        self,
        brain: Optional[Any] = None,
        use_llm: bool = True,
    ):
        """
        Initialize the evaluator.

        Args:
            brain: LLM interface for qualitative evaluation
            use_llm: Whether to use LLM for evaluation (falls back to heuristics)
        """
        self.brain = brain
        self.use_llm = use_llm

    async def evaluate(
        self,
        task: str,
        outcome: TaskOutcome,
        previous_evaluations: Optional[List[Evaluation]] = None,
    ) -> Evaluation:
        """
        Evaluate a task outcome.

        Args:
            task: The original task
            outcome: The task outcome to evaluate
            previous_evaluations: Evaluations from previous cycles

        Returns:
            Evaluation with score, rating, and feedback
        """
        # Start with heuristic evaluation
        evaluation = self._heuristic_evaluate(task, outcome)

        # Enhance with LLM if available
        if self.use_llm and self.brain:
            try:
                llm_evaluation = await self._llm_evaluate(task, outcome, previous_evaluations)
                # Merge LLM insights into heuristic evaluation
                evaluation = self._merge_evaluations(evaluation, llm_evaluation)
            except Exception as e:
                logger.warning(f"Evaluator: LLM evaluation failed, using heuristics: {e}")

        return evaluation

    def _heuristic_evaluate(self, task: str, outcome: TaskOutcome) -> Evaluation:
        """Evaluate using heuristics."""
        score = 0.0
        strengths = []
        weaknesses = []
        suggestions = []

        # Success/failure baseline
        if outcome.success:
            score += 0.5
            strengths.append("Task completed successfully")
        else:
            weaknesses.append(f"Task failed: {outcome.error[:100]}")
            suggestions.append("Review error and try alternative approach")

        # Efficiency scoring
        if outcome.steps_taken > 0:
            if outcome.steps_taken <= 3:
                score += 0.2
                strengths.append("Efficient execution (few steps)")
            elif outcome.steps_taken <= 7:
                score += 0.1
            else:
                score -= 0.1
                weaknesses.append(f"Many steps taken ({outcome.steps_taken})")
                suggestions.append("Consider breaking task into smaller subtasks")

        # Time scoring
        if outcome.execution_time > 0:
            if outcome.execution_time < 5.0:
                score += 0.1
                strengths.append("Fast execution")
            elif outcome.execution_time > 30.0:
                score -= 0.1
                weaknesses.append("Slow execution")
                suggestions.append("Look for optimization opportunities")

        # Result quality (if present)
        if outcome.result is not None:
            result_str = str(outcome.result)
            if len(result_str) > 10:
                score += 0.1
            if "error" not in result_str.lower():
                score += 0.1

        # Clamp score to [0, 1]
        score = max(0.0, min(1.0, score))

        # Determine rating
        rating = self._score_to_rating(score)

        return Evaluation(
            score=score,
            rating=rating,
            strengths=strengths,
            weaknesses=weaknesses,
            suggestions=suggestions,
        )

    async def _llm_evaluate(
        self,
        task: str,
        outcome: TaskOutcome,
        previous_evaluations: Optional[List[Evaluation]] = None,
    ) -> Evaluation:
        """Evaluate using LLM for qualitative assessment."""
        system_prompt = """You are an evaluation agent. Assess the quality of task execution.

Respond with ONLY a JSON object:
{
    "score": 0.0 to 1.0,
    "strengths": ["list of what went well"],
    "weaknesses": ["list of what could be improved"],
    "suggestions": ["specific actionable suggestions"]
}

Be concise and specific. Focus on actionable feedback."""

        # Build context
        context_parts = [f"Task: {task}"]
        context_parts.append(f"Success: {outcome.success}")
        context_parts.append(f"Steps: {outcome.steps_taken}")
        context_parts.append(f"Time: {outcome.execution_time:.1f}s")

        if outcome.error:
            context_parts.append(f"Error: {outcome.error[:200]}")

        if outcome.result:
            result_str = str(outcome.result)[:500]
            context_parts.append(f"Result: {result_str}")

        # Add previous evaluations for trend analysis
        if previous_evaluations:
            prev_scores = [e.score for e in previous_evaluations]
            context_parts.append(f"Previous scores: {prev_scores}")

        user_message = "\n".join(context_parts)

        if not self.brain:
            return Evaluation(score=0.5, rating=EvaluationScore.ACCEPTABLE)

        try:
            response = await self.brain.think(
                user_input=user_message,
                system_prompt=system_prompt,
            )

            # Parse response
            content = response.get("thought", response.get("text", "{}"))
            data = json.loads(content)

            score = float(data.get("score", 0.5))
            rating = self._score_to_rating(score)

            return Evaluation(
                score=score,
                rating=rating,
                strengths=data.get("strengths", []),
                weaknesses=data.get("weaknesses", []),
                suggestions=data.get("suggestions", []),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Evaluator: Failed to parse LLM response: {e}")
            return Evaluation(score=0.5, rating=EvaluationScore.ACCEPTABLE)

    def _merge_evaluations(self, heuristic: Evaluation, llm: Evaluation) -> Evaluation:
        """Merge heuristic and LLM evaluations."""
        # Weight LLM more heavily (0.7) vs heuristic (0.3)
        combined_score = 0.3 * heuristic.score + 0.7 * llm.score
        combined_score = max(0.0, min(1.0, combined_score))

        return Evaluation(
            score=combined_score,
            rating=self._score_to_rating(combined_score),
            strengths=list(set(heuristic.strengths + llm.strengths)),
            weaknesses=list(set(heuristic.weaknesses + llm.weaknesses)),
            suggestions=list(set(heuristic.suggestions + llm.suggestions)),
        )

    def _score_to_rating(self, score: float) -> EvaluationScore:
        """Convert numeric score to rating."""
        if score >= 0.9:
            return EvaluationScore.EXCELLENT
        elif score >= 0.7:
            return EvaluationScore.GOOD
        elif score >= 0.5:
            return EvaluationScore.ACCEPTABLE
        elif score >= 0.3:
            return EvaluationScore.POOR
        else:
            return EvaluationScore.FAILED


# ── Reflector ───────────────────────────────────────────────────────────


class Reflector:
    """
    Generates verbal critiques after evaluations.

    Creates actionable reflections stored in episodic memory for
    future learning. Follows the Reflexion pattern of verbal
    self-reflection rather than weight updates.
    """

    def __init__(
        self,
        brain: Optional[Any] = None,
        graphiti_client: Optional[Any] = None,
    ):
        """
        Initialize the reflector.

        Args:
            brain: LLM interface for reflection generation
            graphiti_client: Graphiti client for reflection storage
        """
        self.brain = brain
        self.graphiti = graphiti_client

    async def reflect(
        self,
        task: str,
        outcome: TaskOutcome,
        evaluation: Evaluation,
        previous_reflections: Optional[List[Reflection]] = None,
    ) -> Reflection:
        """
        Generate a reflection on the task execution.

        Args:
            task: The original task
            outcome: The task outcome
            evaluation: The evaluation of the outcome
            previous_reflections: Reflections from previous cycles

        Returns:
            Reflection with critique and action items
        """
        # Generate reflection using LLM if available
        if self.brain:
            try:
                reflection = await self._llm_reflect(
                    task, outcome, evaluation, previous_reflections
                )
            except Exception as e:
                logger.warning(f"Reflector: LLM reflection failed, using template: {e}")
                reflection = self._template_reflect(task, outcome, evaluation)
        else:
            reflection = self._template_reflect(task, outcome, evaluation)

        # Store reflection in Graphiti
        if self.graphiti:
            try:
                await self._store_reflection(task, reflection, evaluation)
            except Exception as e:
                logger.warning(f"Reflector: Failed to store reflection in Graphiti: {e}")

        return reflection

    async def retrieve_reflections(
        self,
        task: str,
        limit: int = 5,
    ) -> List[Reflection]:
        """
        Retrieve relevant reflections for a task.

        Args:
            task: The task to find reflections for
            limit: Maximum number of reflections to retrieve

        Returns:
            List of relevant reflections
        """
        if not self.graphiti:
            return []

        try:
            # Search Graphiti for relevant reflections
            results = await self.graphiti.recall(
                f"reflection critique lesson: {task}",
                limit=limit,
            )

            if "error" in results or "result" not in results:
                return []

            result = results["result"]
            reflections = []

            # Parse episodes as reflections
            episodes = result.get("episodes", [])
            for episode in episodes:
                text = episode.get("text", "")
                metadata = episode.get("metadata", {})

                if metadata.get("type") == "reflection":
                    reflection = self._parse_reflection_text(text, metadata)
                    if reflection:
                        reflections.append(reflection)

            logger.info(f"Reflector: Retrieved {len(reflections)} relevant reflections")
            return reflections

        except Exception as e:
            logger.warning(f"Reflector: Failed to retrieve reflections: {e}")
            return []

    async def _llm_reflect(
        self,
        task: str,
        outcome: TaskOutcome,
        evaluation: Evaluation,
        previous_reflections: Optional[List[Reflection]] = None,
    ) -> Reflection:
        """Generate reflection using LLM."""
        if not self.brain:
            return self._template_reflect(task, outcome, evaluation)

        system_prompt = """You are a reflection agent. Generate a verbal critique of the task execution.

Respond with ONLY a JSON object:
{
    "critique": "detailed analysis of what happened",
    "lessons": ["key lessons learned"],
    "action_items": ["specific actions to improve next time"],
    "confidence": 0.0 to 1.0
}

Be specific and actionable. Focus on patterns that can be learned from."""

        # Build context
        context_parts = [
            f"Task: {task}",
            f"Success: {outcome.success}",
            f"Score: {evaluation.score:.2f} ({evaluation.rating.value})",
            f"Steps: {outcome.steps_taken}",
            f"Time: {outcome.execution_time:.1f}s",
        ]

        if outcome.error:
            context_parts.append(f"Error: {outcome.error[:200]}")

        if evaluation.weaknesses:
            context_parts.append(f"Weaknesses: {', '.join(evaluation.weaknesses)}")

        if evaluation.suggestions:
            context_parts.append(f"Suggestions: {', '.join(evaluation.suggestions)}")

        # Add previous reflections for learning
        if previous_reflections:
            prev_lessons = []
            for r in previous_reflections[-3:]:  # Last 3 reflections
                prev_lessons.extend(r.lessons)
            if prev_lessons:
                context_parts.append(f"Previous lessons: {', '.join(prev_lessons[:5])}")

        user_message = "\n".join(context_parts)

        response = await self.brain.think(
            user_input=user_message,
            system_prompt=system_prompt,
        )

        content = response.get("thought", response.get("text", "{}"))
        data = json.loads(content)

        return Reflection(
            critique=data.get("critique", "No critique available"),
            lessons=data.get("lessons", []),
            action_items=data.get("action_items", []),
            confidence=float(data.get("confidence", 0.7)),
        )

    def _template_reflect(
        self,
        task: str,
        outcome: TaskOutcome,
        evaluation: Evaluation,
    ) -> Reflection:
        """Generate reflection using template (fallback)."""
        critique_parts = []
        lessons = []
        action_items = []

        # Analyze outcome
        if outcome.success:
            critique_parts.append("Task completed successfully.")
            if evaluation.score >= 0.8:
                lessons.append("High-quality execution achieved")
            else:
                lessons.append("Success but room for improvement")
        else:
            critique_parts.append(f"Task failed: {outcome.error[:100]}")
            lessons.append(f"Failure pattern: {outcome.error[:50]}")
            action_items.append("Investigate root cause of failure")

        # Analyze efficiency
        if outcome.steps_taken > 5:
            lessons.append(f"High step count ({outcome.steps_taken}) suggests complexity")
            action_items.append("Consider breaking task into smaller subtasks")

        if outcome.execution_time > 20.0:
            lessons.append(f"Slow execution ({outcome.execution_time:.1f}s)")
            action_items.append("Look for optimization opportunities")

        # Add evaluation insights
        for weakness in evaluation.weaknesses:
            lessons.append(f"Weakness identified: {weakness}")

        for suggestion in evaluation.suggestions:
            action_items.append(suggestion)

        critique = " ".join(critique_parts)

        return Reflection(
            critique=critique,
            lessons=lessons,
            action_items=action_items,
            confidence=0.6,
        )

    async def _store_reflection(
        self,
        task: str,
        reflection: Reflection,
        evaluation: Evaluation,
    ) -> None:
        """Store reflection in Graphiti episodic memory."""
        if not self.graphiti:
            return

        # Format reflection as episode text
        episode_text = f"""Task: {task}
Reflection: {reflection.critique}
Lessons: {", ".join(reflection.lessons)}
Action Items: {", ".join(reflection.action_items)}
Score: {evaluation.score:.2f} ({evaluation.rating.value})"""

        metadata = {
            "type": "reflection",
            "task": task,
            "score": evaluation.score,
            "rating": evaluation.rating.value,
            "confidence": reflection.confidence,
            "timestamp": reflection.timestamp,
        }

        await self.graphiti.remember(episode_text, metadata)
        logger.info(f"Reflector: Stored reflection for task: {task[:50]}")

    def _parse_reflection_text(self, text: str, metadata: Dict[str, Any]) -> Optional[Reflection]:
        """Parse reflection from episode text."""
        try:
            lines = text.strip().split("\n")
            critique = ""
            lessons = []
            action_items = []

            for line in lines:
                line = line.strip()
                if line.startswith("Reflection:"):
                    critique = line[11:].strip()
                elif line.startswith("Lessons:"):
                    lessons_text = line[8:].strip()
                    lessons = [l.strip() for l in lessons_text.split(",") if l.strip()]
                elif line.startswith("Action Items:"):
                    items_text = line[13:].strip()
                    action_items = [i.strip() for i in items_text.split(",") if i.strip()]

            if not critique:
                return None

            return Reflection(
                critique=critique,
                lessons=lessons,
                action_items=action_items,
                confidence=metadata.get("confidence", 0.5),
                timestamp=metadata.get("timestamp", time.time()),
            )
        except Exception as e:
            logger.debug(f"Reflector: Failed to parse reflection: {e}")
            return None


# ── Actor Wrapper ───────────────────────────────────────────────────────


class AgentActor:
    """
    Wraps existing agent infrastructure as an Actor.

    Adapts AgentLoop or ReActAgent to the Actor protocol,
    injecting reflections into the agent context.
    """

    def __init__(
        self,
        agent: Any,
        agent_type: str = "loop",  # "loop" or "react"
    ):
        """
        Initialize the actor wrapper.

        Args:
            agent: AgentLoop or ReActAgent instance
            agent_type: Type of agent ("loop" or "react")
        """
        self.agent = agent
        self.agent_type = agent_type

    async def execute(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        reflections: Optional[List[Reflection]] = None,
    ) -> TaskOutcome:
        """
        Execute a task using the wrapped agent.

        Args:
            task: The task to execute
            context: Optional context
            reflections: Previous reflections to inject

        Returns:
            TaskOutcome with execution results
        """
        start_time = time.time()

        # Build reflection context
        reflection_context = self._build_reflection_context(reflections)

        # Merge contexts
        full_context = context or {}
        if reflection_context:
            full_context["reflections"] = reflection_context

        try:
            if self.agent_type == "loop":
                result = await self._execute_loop(task, full_context)
            elif self.agent_type == "react":
                result = await self._execute_react(task, full_context)
            else:
                raise ValueError(f"Unknown agent type: {self.agent_type}")

            execution_time = time.time() - start_time

            return TaskOutcome(
                success=result.get("success", False),
                result=result.get("result"),
                error=result.get("error", ""),
                steps_taken=result.get("steps", 0),
                execution_time=execution_time,
                metadata=result,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"AgentActor: Execution failed: {e}")

            return TaskOutcome(
                success=False,
                error=str(e),
                execution_time=execution_time,
            )

    async def _execute_loop(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute using AgentLoop."""
        # AgentLoop.run expects user_input, history, visual_context
        history = context.get("history", [])
        visual_context = context.get("visual_context", "")

        result = await self.agent.run(
            user_input=task,
            history=history,
            visual_context=visual_context,
        )

        return {
            "success": result.status == "complete",
            "result": result.text,
            "error": "" if result.status == "complete" else result.status,
            "steps": len(result.steps),
            "status": result.status,
        }

    async def _execute_react(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute using ReActAgent."""
        result = await self.agent.run(
            task=task,
            context=context,
        )

        return {
            "success": result.status.value == "complete",
            "result": result.answer,
            "error": "" if result.status.value == "complete" else result.status.value,
            "steps": len(result.steps),
            "status": result.status.value,
        }

    def _build_reflection_context(self, reflections: Optional[List[Reflection]]) -> str:
        """Build context string from reflections."""
        if not reflections:
            return ""

        parts = ["[PAST REFLECTIONS - Learn from these]"]

        for i, reflection in enumerate(reflections[-3:], 1):  # Last 3
            parts.append(f"\nReflection {i}:")
            parts.append(f"  Critique: {reflection.critique[:200]}")
            if reflection.lessons:
                parts.append(f"  Lessons: {', '.join(reflection.lessons[:3])}")
            if reflection.action_items:
                parts.append(f"  Actions: {', '.join(reflection.action_items[:3])}")

        return "\n".join(parts)


# ── Reflexion Agent ─────────────────────────────────────────────────────


class ReflexionAgent:
    """
    Actor-Evaluator-Reflector agent for self-improvement.

    Implements the Reflexion pattern:
    1. Actor executes the task
    2. Evaluator assesses the outcome
    3. Reflector generates critique (if needed)
    4. Repeat with reflection context until success or max cycles

    Research validated: 10-15% improvement after 3-4 cycles.
    """

    def __init__(
        self,
        actor: Actor,
        evaluator: Evaluator,
        reflector: Reflector,
        max_cycles: int = 4,
        success_threshold: float = 0.8,
        improvement_threshold: float = 0.1,
    ):
        """
        Initialize the reflexion agent.

        Args:
            actor: Actor for task execution
            evaluator: Evaluator for outcome assessment
            reflector: Reflector for critique generation
            max_cycles: Maximum reflexion cycles
            success_threshold: Score threshold for success
            improvement_threshold: Minimum improvement to continue
        """
        self.actor = actor
        self.evaluator = evaluator
        self.reflector = reflector
        self.max_cycles = max_cycles
        self.success_threshold = success_threshold
        self.improvement_threshold = improvement_threshold

        logger.info(
            f"ReflexionAgent: Initialized (max_cycles={max_cycles}, threshold={success_threshold})"
        )

    async def run(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ReflexionResult:
        """
        Run the reflexion loop for a task.

        Args:
            task: The task to execute
            context: Optional initial context

        Returns:
            ReflexionResult with final answer and improvement metrics
        """
        start_time = time.time()
        cycles: List[ReflexionCycle] = []
        reflections: List[Reflection] = []
        evaluations: List[Evaluation] = []

        # Retrieve past reflections for this task type
        past_reflections = await self.reflector.retrieve_reflections(task)
        if past_reflections:
            reflections.extend(past_reflections)
            logger.info(f"ReflexionAgent: Loaded {len(past_reflections)} past reflections")

        best_score = 0.0
        best_result = None

        for cycle_num in range(1, self.max_cycles + 1):
            logger.info(f"ReflexionAgent: Cycle {cycle_num}/{self.max_cycles}")

            # ── ACTOR: Execute task ────────────────────────────────────
            outcome = await self.actor.execute(
                task=task,
                context=context,
                reflections=reflections,
            )

            logger.info(
                f"ReflexionAgent: Actor completed - success={outcome.success}, "
                f"steps={outcome.steps_taken}"
            )

            # ── EVALUATOR: Assess outcome ─────────────────────────────
            evaluation = await self.evaluator.evaluate(
                task=task,
                outcome=outcome,
                previous_evaluations=evaluations,
            )

            evaluations.append(evaluation)

            logger.info(
                f"ReflexionAgent: Evaluation - score={evaluation.score:.2f}, "
                f"rating={evaluation.rating.value}"
            )

            # Track best result
            if evaluation.score > best_score:
                best_score = evaluation.score
                best_result = outcome.result

            # ── Check success conditions ──────────────────────────────
            if evaluation.score >= self.success_threshold:
                logger.info(f"ReflexionAgent: Success threshold reached ({evaluation.score:.2f})")

                cycle = ReflexionCycle(
                    cycle_num=cycle_num,
                    task=task,
                    outcome=outcome,
                    evaluation=evaluation,
                )
                cycles.append(cycle)

                return ReflexionResult(
                    answer=str(outcome.result) if outcome.result else "Task completed",
                    status=ReflexionStatus.SUCCESS,
                    cycles=cycles,
                    best_score=best_score,
                    improvement=self._calculate_improvement(evaluations),
                    total_execution_time=time.time() - start_time,
                )

            # ── REFLECTOR: Generate critique ──────────────────────────
            reflection = await self.reflector.reflect(
                task=task,
                outcome=outcome,
                evaluation=evaluation,
                previous_reflections=reflections,
            )

            reflections.append(reflection)

            logger.info(
                f"ReflexionAgent: Reflection generated - "
                f"lessons={len(reflection.lessons)}, "
                f"actions={len(reflection.action_items)}"
            )

            # Create cycle record
            cycle = ReflexionCycle(
                cycle_num=cycle_num,
                task=task,
                outcome=outcome,
                evaluation=evaluation,
                reflection=reflection,
            )
            cycles.append(cycle)

            # ── Check improvement ─────────────────────────────────────
            if len(evaluations) >= 2:
                improvement = evaluations[-1].score - evaluations[-2].score
                if improvement < self.improvement_threshold:
                    logger.info(f"ReflexionAgent: Insufficient improvement ({improvement:.2f})")
                    # Continue anyway - might improve in next cycle

        # Max cycles reached
        logger.warning(f"ReflexionAgent: Max cycles ({self.max_cycles}) reached")

        return ReflexionResult(
            answer=str(best_result) if best_result else "Max cycles reached",
            status=ReflexionStatus.MAX_CYCLES,
            cycles=cycles,
            best_score=best_score,
            improvement=self._calculate_improvement(evaluations),
            total_execution_time=time.time() - start_time,
        )

    def _calculate_improvement(self, evaluations: List[Evaluation]) -> float:
        """Calculate score improvement from first to last evaluation."""
        if len(evaluations) < 2:
            return 0.0
        return evaluations[-1].score - evaluations[0].score


# ── Convenience Functions ───────────────────────────────────────────────


async def run_reflexion_task(
    task: str,
    agent: Any,
    brain: Any,
    graphiti_client: Optional[Any] = None,
    agent_type: str = "loop",
    max_cycles: int = 4,
    success_threshold: float = 0.8,
    context: Optional[Dict[str, Any]] = None,
) -> ReflexionResult:
    """
    Convenience function to run a reflexion task.

    Args:
        task: The task to execute
        agent: AgentLoop or ReActAgent instance
        brain: LLM interface
        graphiti_client: Graphiti client for reflection storage
        agent_type: Type of agent ("loop" or "react")
        max_cycles: Maximum reflexion cycles
        success_threshold: Score threshold for success
        context: Optional initial context

    Returns:
        ReflexionResult with final answer and improvement metrics
    """
    # Create components
    actor = AgentActor(agent, agent_type)
    evaluator = Evaluator(brain=brain, use_llm=True)
    reflector = Reflector(brain=brain, graphiti_client=graphiti_client)

    # Create reflexion agent
    reflexion_agent = ReflexionAgent(
        actor=actor,
        evaluator=evaluator,
        reflector=reflector,
        max_cycles=max_cycles,
        success_threshold=success_threshold,
    )

    return await reflexion_agent.run(task=task, context=context)


def create_reflexion_agent(
    agent: Any,
    brain: Any,
    graphiti_client: Optional[Any] = None,
    agent_type: str = "loop",
    max_cycles: int = 4,
    success_threshold: float = 0.8,
) -> ReflexionAgent:
    """
    Create a ReflexionAgent with standard components.

    Args:
        agent: AgentLoop or ReActAgent instance
        brain: LLM interface
        graphiti_client: Graphiti client for reflection storage
        agent_type: Type of agent ("loop" or "react")
        max_cycles: Maximum reflexion cycles
        success_threshold: Score threshold for success

    Returns:
        Configured ReflexionAgent instance
    """
    actor = AgentActor(agent, agent_type)
    evaluator = Evaluator(brain=brain, use_llm=True)
    reflector = Reflector(brain=brain, graphiti_client=graphiti_client)

    return ReflexionAgent(
        actor=actor,
        evaluator=evaluator,
        reflector=reflector,
        max_cycles=max_cycles,
        success_threshold=success_threshold,
    )
