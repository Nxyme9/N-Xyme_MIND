"""Unified Pipeline — Integrates CATALYST, OpenCode, OMO, and BMAD.

This is the main orchestration pipeline that routes user input through:
1. Input parsing & intent detection
2. BMAD workflow detection
3. Agent delegation using DelegationOptimizer
4. Memory injection via nx_brain_mcp
5. Execution & result collection
6. Outcome logging for learning

Usage:
    from packages.orchestration.unified_pipeline import UnifiedPipeline

    pipeline = UnifiedPipeline()
    result = pipeline.execute("implement JWT auth middleware", optimization_target="success")
    print(result)
"""

import logging
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .delegation_optimizer import (
    DelegationOptimizer,
    OptimizationTarget,
    default_optimizer,
)

# Define logger early - before any conditional imports that might use it
logger = logging.getLogger(__name__)

# Import observability
try:
    from .observability import (
        get_logger,
        get_metrics,
        MetricsCollector,
    )

    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False
    get_metrics = None
    get_logger = None
    MetricsCollector = None
    logger.warning("observability not available")

# Try importing BMAD executor
try:
    from .bmad.executor import (
        BMADExecutor,
        WorkflowResult,
        execute_workflow,
        load_workflow,
    )

    BMAD_AVAILABLE = True
except ImportError:
    BMAD_AVAILABLE = False
    logger.warning("BMAD executor not available")


# Try importing nx_brain_mcp for memory injection (DIRECT imports - no wrapper module)
try:
    from packages.brain_mcp.namespaces.fingerprint import (
        get_full_injected_context as orchestration_get_injected_context,
    )

    MEMORY_INJECTION_AVAILABLE = True
except ImportError:
    MEMORY_INJECTION_AVAILABLE = False
    logger.warning("brain_mcp memory injection not available")


# Try importing orchestration spawn
try:
    from packages.orchestration import spawn, task_status

    ORCHESTRATION_AVAILABLE = True
except ImportError:
    ORCHESTRATION_AVAILABLE = False
    logger.warning("orchestration spawn not available")


class IntentType(Enum):
    """Detected intent types from user input."""

    IMPLEMENT = "implement"
    RESEARCH = "research"
    FIX = "fix"
    EXPLORE = "explore"
    REVIEW = "review"
    QUERY = "query"
    UNKNOWN = "unknown"


@dataclass
class PipelineStage:
    """A single stage in the unified pipeline."""

    name: str
    status: str = "pending"  # pending, running, completed, failed
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration_ms: int = 0
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class QualityGateResult:
    """Result of a single quality gate."""

    name: str
    passed: bool
    output: str = ""
    error: Optional[str] = None


@dataclass
class PipelineResult:
    """Result of executing the unified pipeline."""

    success: bool
    user_input: str
    intent_type: IntentType
    selected_agent: str
    workflow_name: Optional[str] = None
    workflow_confidence: float = 0.0  # Confidence score for BMAD detection
    pipeline_mode: str = "standard"  # standard, bmad, explore, implement
    stages: List[PipelineStage] = field(default_factory=list)
    injected_context: str = ""
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    total_duration_ms: int = 0
    quality_gate_results: List[QualityGateResult] = field(default_factory=list)


class UnifiedPipeline:
    """Main orchestration pipeline integrating all systems.

    Routes user input through the full pipeline:
    1. Input parsing & intent detection
    2. BMAD workflow detection
    3. Agent delegation using DelegationOptimizer
    4. Memory injection
    5. Execution & result collection
    6. Outcome logging

    Usage:
        pipeline = UnifiedPipeline()
        result = pipeline.execute("implement JWT auth middleware")
        print(result.success, result.output)
    """

    # Memory injection settings
    MEMORY_INJECTION_TIMEOUT_MS = 3000  # 3 second timeout (reduced for faster fallback)
    MEMORY_CACHE_TTL_SECONDS = 300  # 5 minute cache TTL
    MAX_TOKENS_BY_COMPLEXITY = {
        "L1": 0,  # No injection for trivial tasks
        "L2": 100,  # Minimal injection for simple tasks
        "L3": 300,  # Standard injection for moderate tasks
        "L4": 500,  # Full injection for complex tasks
        "L5": 600,  # Full injection for architect tasks
    }

    def __init__(self):
        """Initialize the unified pipeline."""
        self.optimizer = default_optimizer or DelegationOptimizer()
        self._stage_times: Dict[str, float] = {}

        # Components availability
        self.bmad_available = BMAD_AVAILABLE
        self.memory_available = MEMORY_INJECTION_AVAILABLE
        self.orchestration_available = ORCHESTRATION_AVAILABLE
        self.observability_available = OBSERVABILITY_AVAILABLE

        # Metrics tracking
        self._metrics = get_metrics() if OBSERVABILITY_AVAILABLE else None
        self._logger = get_logger("pipeline") if OBSERVABILITY_AVAILABLE else None
        self._current_trace_id: Optional[str] = None

        # Session-level memory cache
        self._memory_cache: Dict[
            str, tuple[str, float]
        ] = {}  # task_key -> (context, timestamp)

    def health_check(self) -> Dict[str, Any]:
        """Health check for all pipeline components.

        Returns:
            Dict with health status of each component
        """
        components = {
            "delegation_optimizer": "healthy",
            "bmad_executor": "healthy" if self.bmad_available else "unavailable",
            "memory_injection": "healthy" if self.memory_available else "unavailable",
            "orchestration": "healthy"
            if self.orchestration_available
            else "unavailable",
            "observability": "healthy"
            if self.observability_available
            else "unavailable",
        }

        # Check orchestration module
        orch_status = "healthy"
        try:

            result = health_check()
            if result.get("status") != "healthy":
                orch_status = "degraded"
        except Exception as e:
            orch_status = f"error: {e}"
            components["orchestration"] = orch_status

        # Check BMAD
        bmad_status = "healthy"
        if self.bmad_available:
            try:
                from .bmad.executor import get_executor

                executor = get_executor()
                workflows = executor.list_workflows()
                if not workflows:
                    bmad_status = "no_workflows"
            except Exception as e:
                bmad_status = f"error: {e}"
        else:
            bmad_status = "unavailable"
        components["bmad_executor"] = bmad_status

        # Overall status
        all_healthy = all(s == "healthy" for s in components.values())
        overall = "healthy" if all_healthy else "degraded"

        return {
            "status": overall,
            "components": components,
            "message": "All components operational"
            if all_healthy
            else "Some components degraded",
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline execution statistics.

        Returns:
            Dict with:
            - total_tasks_executed: Total number of tasks executed
            - success_rate: Ratio of successful tasks (0.0-1.0)
            - average_latency_ms: Average task latency in milliseconds
            - stage_timing_breakdown: Timing for each stage
        """
        stats = {
            "total_tasks_executed": 0,
            "success_rate": 0.0,
            "average_latency_ms": 0,
            "stage_timing_breakdown": {},
        }

        if not self.observability_available or self._metrics is None:
            # Return from internal tracking if observability unavailable
            stats["total_tasks_executed"] = (
                int(self._metrics.get_counter("tasks_total")) if self._metrics else 0
            )
            stats["success_rate"] = self._calculate_internal_success_rate()
            return stats

        # Get metrics from observability
        try:
            total = self._metrics.get_counter("tasks_total")
            success = self._metrics.get_counter("tasks_success")
            failed = self._metrics.get_counter("tasks_failed")

            stats["total_tasks_executed"] = int(total)
            stats["success_rate"] = success / total if total > 0 else 0.0

            # Get latency stats
            lat_stats = self._metrics.get_histogram_stats("task_latency_ms")
            if lat_stats.get("count", 0) > 0:
                stats["average_latency_ms"] = int(lat_stats["sum"] / lat_stats["count"])
                stats["latency_p50"] = int(lat_stats.get("p50", 0))
                stats["latency_p99"] = int(lat_stats.get("p99", 0))

            # Stage timing breakdown from internal tracking
            stats["stage_timing_breakdown"] = self._stage_times.copy()

        except Exception as e:
            logger.warning(f"Failed to get metrics stats: {e}")

        return stats

    def _calculate_internal_success_rate(self) -> float:
        """Calculate success rate from internal counters."""
        if self._metrics is None:
            return 0.0
        try:
            total = self._metrics.get_counter("tasks_total")
            success = self._metrics.get_counter("tasks_success")
            return success / total if total > 0 else 0.0
        except Exception:
            return 0.0

    def detect_intent(self, user_input: str) -> IntentType:
        """Detect intent type from user input.

        Args:
            user_input: Raw user input string

        Returns:
            Detected IntentType
        """
        user_lower = user_input.lower()

        # Intent keyword mapping
        intent_keywords = {
            IntentType.IMPLEMENT: [
                "implement",
                "create",
                "build",
                "add",
                "write",
                "code",
            ],
            IntentType.RESEARCH: [
                "research",
                "lookup",
                "find documentation",
                "search docs",
            ],
            IntentType.FIX: ["fix", "bug", "error", "typo", "patch"],
            IntentType.EXPLORE: ["explore", "find", "search", "list", "analyze"],
            IntentType.REVIEW: ["review", "check", "verify", "validate"],
            IntentType.QUERY: ["what", "how", "explain", "show", "get"],
        }

        # Find matching intent
        for intent_type, keywords in intent_keywords.items():
            for kw in keywords:
                if kw in user_lower:
                    return intent_type

        return IntentType.UNKNOWN

    def detect_bmad_workflow(self, user_input: str) -> tuple[Optional[str], float]:
        """Detect if input matches a BMAD workflow trigger.

        Enhanced to check:
        - Explicit /bmad prefix
        - Workflow metadata (description, tags)
        - Returns confidence score alongside workflow name

        Args:
            user_input: User input string

        Returns:
            Tuple of (workflow_name, confidence_score) where confidence is 0.0-1.0
        """
        if not self.bmad_available:
            return None, 0.0

        user_lower = user_input.lower()

        try:
            from .bmad.executor import get_executor

            executor = get_executor()
            registry = executor.get_registry()

            # Check 1: Explicit /bmad prefix in input (highest confidence)
            if user_lower.startswith("/bmad "):
                # Extract potential workflow name after /bmad prefix
                potential = user_lower.replace("/bmad ", "").strip()
                if potential:
                    for workflow_name in registry.keys():
                        wf_key = workflow_name.replace("bmad-", "").replace("_", " ")
                        # Direct match
                        if wf_key == potential or wf_key in potential:
                            return workflow_name, 1.0
                        # Partial match
                        if any(
                            part in potential
                            for part in workflow_name.split("-")
                            if len(part) > 2
                        ):
                            return workflow_name, 0.8

            # Check 2: Workflow name match in input (CONSERVATIVE - exact match only)
            for workflow_name in registry.keys():
                # Direct name match (exact, not partial)
                wf_key = workflow_name.replace("bmad-", "").replace("_", " ")
                if wf_key == user_lower.strip():  # EXACT match only
                    return workflow_name, 0.95

                # Partial matches (word by word) - ONLY with HIGH confidence
                name_parts = workflow_name.split("-")
                matches = sum(
                    1 for part in name_parts if len(part) > 2 and part in user_lower
                )
                # INCREASED threshold: Require 80%+ parts match (was 50%)
                if matches >= len(name_parts) * 0.8:
                    confidence = 0.8 + (matches / len(name_parts)) * 0.15
                    return workflow_name, min(confidence, 0.95)

            # Check 3: DISABLED - Too aggressive, triggers on any keyword like "audit"
            # Keeping block for reference but NOT executed
            # for workflow_name, workflow_data in registry.items():
            #     if not isinstance(workflow_data, dict):
            #         continue
            #     # This was matching "audit" → bmad-catalyst-orchestration too easily
            pass

        except Exception as e:
            logger.warning(f"BMAD workflow detection failed: {e}")

        return None, 0.0

    def execute(
        self,
        user_input: str,
        optimization_target: str = "success",
    ) -> PipelineResult:
        """Execute the unified pipeline for user input.

        Args:
            user_input: Raw user input string
            optimization_target: "success", "speed", or "cost"

        Returns:
            PipelineResult with execution details
        """
        start_time = time.time()

        # Generate trace_id for observability
        trace_id = str(uuid.uuid4())
        self._current_trace_id = trace_id

        # Log task start with trace_id
        if self._logger:
            self._logger.info(
                f"Task started: {trace_id}",
                task_id=trace_id,
                agent="pipeline",
                event="task_started",
            )

        result = PipelineResult(
            success=False,
            user_input=user_input,
            intent_type=IntentType.UNKNOWN,
            selected_agent="",
            pipeline_mode="standard",
        )

        # Stage 0: Trigger detection (new stage)
        stage = PipelineStage(name="stage_0_trigger_detection")
        stage.status = "running"
        stage.start_time = time.time()

        try:
            # Parse command prefix
            user_lower = user_input.lower().strip()
            pipeline_mode = "standard"
            selected_agent = ""

            if user_lower.startswith("/bmad "):
                # BMAD workflow execution mode
                pipeline_mode = "bmad"
                stage.output = {
                    "mode": "bmad",
                    "trigger": "Detected /bmad prefix - using BMAD workflow execution",
                }
                # Extract the actual task after /bmad prefix
                user_input = user_input[5:].strip()  # Remove "/bmad " prefix
                result.pipeline_mode = pipeline_mode

            elif user_lower.startswith("/explore "):
                # Direct explore agent mode
                pipeline_mode = "explore"
                selected_agent = "explore"
                stage.output = {
                    "mode": "explore",
                    "trigger": "Detected /explore prefix - using explore agent directly",
                }
                # Extract the actual task
                user_input = user_input[8:].strip()  # Remove "/explore "
                result.pipeline_mode = pipeline_mode

            elif user_lower.startswith("/implement "):
                # Direct hephaestus agent mode
                pipeline_mode = "implement"
                selected_agent = "hephaestus"
                stage.output = {
                    "mode": "implement",
                    "trigger": "Detected /implement prefix - using hephaestus directly",
                }
                # Extract the actual task
                user_input = user_input[11:].strip()  # Remove "/implement "
                result.pipeline_mode = pipeline_mode

            else:
                # Standard pipeline - no trigger prefix detected
                stage.output = {
                    "mode": "standard",
                    "trigger": "No trigger prefix - using standard pipeline",
                }

            stage.status = "completed"

        except Exception as e:
            stage.error = str(e)
            stage.status = "failed"

        stage.end_time = time.time()
        stage.duration_ms = int((stage.end_time - stage.start_time) * 1000)
        result.stages.append(stage)

        # Log stage completion
        if self._logger:
            self._logger.info(
                f"Stage completed: {stage.name}",
                trace_id=trace_id,
                stage=stage.name,
                duration_ms=stage.duration_ms,
            )

        # Track stage timing
        self._stage_times[stage.name] = stage.duration_ms

        # Log stage completion
        if self._logger:
            self._logger.info(
                f"Stage completed: {stage.name}",
                trace_id=trace_id,
                stage=stage.name,
                duration_ms=stage.duration_ms,
            )

        # Early return for direct agent commands
        if result.pipeline_mode in ("explore", "implement"):
            # For direct agent modes, execute immediately
            result.selected_agent = selected_agent
            result.intent_type = self.detect_intent(user_input)
            result.total_duration_ms = int((time.time() - start_time) * 1000)

            if self.orchestration_available and user_input:
                try:
                    task_id = spawn(
                        agent=selected_agent,
                        task=user_input,
                        context={},
                        inject_memory=True,  # Memory injection enabled by default
                        log_sequence=True,
                    )
                    result.output["task_id"] = task_id
                    result.success = True
                except Exception as e:
                    result.error = f"Direct execution failed: {e}"
            else:
                result.success = True  # Mark success even without orchestration

            return result

        # Stage 1: Input parsing & intent detection
        stage = PipelineStage(name="stage_1_intent_detection")
        stage.status = "running"
        stage.start_time = time.time()

        try:
            intent = self.detect_intent(user_input)
            result.intent_type = intent
            stage.output = {"intent": intent.value}

            # Get optimization target enum
            target = (
                OptimizationTarget.SUCCESS
                if optimization_target == "success"
                else OptimizationTarget.SPEED
                if optimization_target == "speed"
                else OptimizationTarget.COST
            )

            # Use DelegationOptimizer to select agent
            delegation_score = self.optimizer.optimize(user_input, target)
            selected_agent = delegation_score.agent

            # PRE-DELEGATION: Get routing from learning system (NOT keyword matching)
            try:
                from packages.learning_engine.mcp_server import route_task
                import asyncio

                # FIX: Use asyncio to await in non-async function
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()

                routing_result = loop.run_until_complete(
                    route_task(task_description=user_input)
                )
                if routing_result:
                    # Use learning system's routing
                    suggested_agent = routing_result.get("agent", "")
                    suggested_level = routing_result.get("level", 3)
                    logger.info(
                        f"Learning routing: {suggested_agent} (L{suggested_level})"
                    )
                    # Override only if valid (not empty, known agent)
                    if suggested_agent and suggested_agent in [
                        "hephaestus",
                        "sisyphus",
                        "oracle",
                        "explore",
                        "librarian",
                    ]:
                        selected_agent = suggested_agent
            except Exception as e:
                logger.warning(f"Learning routing failed, using fallback: {e}")

            result.selected_agent = selected_agent
            stage.output["selected_agent"] = selected_agent
            stage.output["complexity"] = self.optimizer.detect_complexity(user_input)
            stage.status = "completed"

        except Exception as e:
            stage.error = str(e)
            stage.status = "failed"
            result.error = f"Intent detection failed: {e}"
            result.total_duration_ms = int((time.time() - start_time) * 1000)
            return result

        stage.end_time = time.time()
        stage.duration_ms = int((stage.end_time - stage.start_time) * 1000)
        result.stages.append(stage)

        # Log stage completion
        if self._logger:
            self._logger.info(
                f"Stage completed: {stage.name}",
                trace_id=trace_id,
                stage=stage.name,
                duration_ms=stage.duration_ms,
            )
        self._stage_times[stage.name] = stage.duration_ms

        # Stage 2: BMAD workflow detection (enhanced with confidence)
        stage = PipelineStage(name="stage_2_bmad_detection")
        stage.status = "running"
        stage.start_time = time.time()

        workflow_name = None
        confidence = 0.0
        try:
            workflow_name, confidence = self.detect_bmad_workflow(user_input)
            if workflow_name:
                result.workflow_name = workflow_name
                result.workflow_confidence = confidence
                stage.output = {"workflow": workflow_name, "confidence": confidence}
            stage.status = "completed"

        except Exception as e:
            stage.error = str(e)
            stage.status = "failed"

        stage.end_time = time.time()
        stage.duration_ms = int((stage.end_time - stage.start_time) * 1000)
        result.stages.append(stage)

        # Log stage completion
        if self._logger:
            self._logger.info(
                f"Stage completed: {stage.name}",
                trace_id=trace_id,
                stage=stage.name,
                duration_ms=stage.duration_ms,
            )
        self._stage_times[stage.name] = stage.duration_ms

        # Stage 3: Agent delegation (already done in Stage 1)
        stage = PipelineStage(name="stage_3_delegation")
        stage.status = "completed"
        stage.start_time = time.time()
        stage.end_time = time.time()
        stage.output = {
            "agent": selected_agent,
            "target": optimization_target,
        }
        result.stages.append(stage)

        # Stage 4: Memory injection (OPTIMIZED - lazy, cached, with timeout)
        stage = PipelineStage(name="stage_4_memory_injection")
        stage.status = "running"
        stage.start_time = time.time()

        injected_context = ""
        inject_memory = True  # Always inject memory, not conditional on speed

        try:
            if self.memory_available and inject_memory:
                # Detect task complexity
                complexity = self.optimizer.detect_complexity(user_input)
                max_tokens = self.MAX_TOKENS_BY_COMPLEXITY.get(complexity, 300)

                # Skip injection for trivial tasks (L1)
                if max_tokens == 0:
                    stage.output = {
                        "injected": False,
                        "reason": "trivial_task",
                        "complexity": complexity,
                    }
                    logger.info(
                        f"Skipping memory injection for L1 task: {user_input[:50]}"
                    )
                else:
                    # Check cache first (use deterministic hash)
                    cache_key = f"{selected_agent}:{hash(user_input) % 1000000}"
                    cached_context, cache_time = self._memory_cache.get(
                        cache_key, ("", 0)
                    )

                    if (
                        cached_context
                        and (time.time() - cache_time) < self.MEMORY_CACHE_TTL_SECONDS
                    ):
                        # Use cached context
                        injected_context = cached_context
                        stage.output = {
                            "injected": True,
                            "from_cache": True,
                            "length": len(injected_context),
                            "complexity": complexity,
                        }
                        logger.info(
                            f"Using cached memory context for: {user_input[:50]}"
                        )
                    else:
                        # Call memory injection with TIMEOUT using threading
                        result_holder: Dict[str, Any] = {}
                        exception_holder: Dict[str, Optional[Exception]] = {}

                        def _call_injection():
                            try:
                                result_holder["context"] = (
                                    orchestration_get_injected_context(
                                        agent=selected_agent,
                                        task=user_input,
                                    )
                                )
                            except Exception as e:
                                exception_holder["error"] = e

                        injection_thread = threading.Thread(target=_call_injection)
                        injection_thread.start()
                        injection_thread.join(
                            timeout=self.MEMORY_INJECTION_TIMEOUT_MS / 1000.0
                        )

                        if injection_thread.is_alive():
                            # Timeout - skip injection and continue
                            stage.error = "Memory injection timeout - skipped"
                            stage.output = {
                                "injected": False,
                                "reason": "timeout",
                                "complexity": complexity,
                            }
                            logger.warning(
                                f"Memory injection timed out for: {user_input[:50]}"
                            )
                        elif exception_holder.get("error"):
                            raise exception_holder["error"]
                        else:
                            # Success
                            injected_context = result_holder.get("context", {}).get(
                                "injected_context", ""
                            )

                            # Cache the result
                            self._memory_cache[cache_key] = (
                                injected_context,
                                time.time(),
                            )

                            stage.output = {
                                "injected": bool(injected_context),
                                "from_cache": False,
                                "length": len(injected_context),
                                "complexity": complexity,
                                "max_tokens": max_tokens,
                            }

            else:
                # Memory injection disabled (speed optimization or unavailable)
                stage.output = {
                    "injected": False,
                    "reason": "disabled" if not inject_memory else "unavailable",
                }

            result.injected_context = injected_context
            stage.status = "completed"

        except Exception as e:
            stage.error = str(e)
            stage.status = "failed"
            logger.warning(f"Memory injection failed: {e}")

        stage.end_time = time.time()
        stage.duration_ms = int((stage.end_time - stage.start_time) * 1000)
        result.stages.append(stage)

        # Log stage completion
        if self._logger:
            self._logger.info(
                f"Stage completed: {stage.name}",
                trace_id=trace_id,
                stage=stage.name,
                duration_ms=stage.duration_ms,
            )
        self._stage_times[stage.name] = stage.duration_ms

        # Stage 5: Execution using orchestration spawn
        stage = PipelineStage(name="stage_5_execution")
        stage.status = "running"
        stage.start_time = time.time()

        try:
            if self.orchestration_available:
                task_id = spawn(
                    agent=selected_agent,
                    task=user_input,
                    context={"injected_context": injected_context},
                    inject_memory=True,  # Memory injection enabled by default
                    log_sequence=True,
                )

                # Get task result (synchronous for now)
                task_info = task_status(task_id)
                stage.output = {
                    "task_id": task_id,
                    "status": task_info.get("status"),
                }
                result.output["task_id"] = task_id

            stage.status = "completed"

        except Exception as e:
            stage.error = str(e)
            stage.status = "failed"
            result.error = f"Execution failed: {e}"

        stage.end_time = time.time()
        stage.duration_ms = int((stage.end_time - stage.start_time) * 1000)
        result.stages.append(stage)

        # Log stage completion
        if self._logger:
            self._logger.info(
                f"Stage completed: {stage.name}",
                trace_id=trace_id,
                stage=stage.name,
                duration_ms=stage.duration_ms,
            )
        self._stage_times[stage.name] = stage.duration_ms

        # Stage 6: Outcome logging
        stage = PipelineStage(name="stage_6_outcome_logging")
        stage.status = "running"
        stage.start_time = time.time()

        try:
            # Record outcome for learning
            outcome = "success" if result.success else "failed"

            # MANDATORY outcome logging for Q-Learning (NOT optional)
            try:
                from packages.learning_engine.mcp_server import record_outcome
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                
                def sync_record():
                    return record_outcome(
                        task=user_input[:200],  # Truncate for DB
                        agent=selected_agent,
                        success=result.success,
                        latency_ms=result.total_duration_ms or 0,
                        tokens_used=result.output.get("tokens_used", 0) if result.output else 0,
                    )

                loop.run_until_complete(sync_record())
                logger.info(
                    f"Outcome logged: agent={selected_agent}, success={result.success}"
                )
            except Exception as e:
                logger.error(f"FAILED to log outcome: {e}")  # NEVER silently fail

            # Also use the orchestration module's log_task_sequence as backup
            if self.orchestration_available and result.output.get("task_id"):
                from packages.orchestration import log_task_sequence

                log_task_sequence(
                    task_id=result.output["task_id"],
                    outcome=outcome,
                    duration_ms=result.total_duration_ms,
                )

            stage.output = {"logged": True}
            stage.status = "completed"

        except Exception as e:
            stage.error = str(e)
            stage.status = "failed"

        stage.end_time = time.time()
        stage.duration_ms = int((stage.end_time - stage.start_time) * 1000)
        result.stages.append(stage)

        # Log stage completion
        if self._logger:
            self._logger.info(
                f"Stage completed: {stage.name}",
                trace_id=trace_id,
                stage=stage.name,
                duration_ms=stage.duration_ms,
            )
        self._stage_times[stage.name] = stage.duration_ms

        # Stage 7: Quality gates (runs only if execution produced modified files)
        stage = PipelineStage(name="stage_7_quality_gates")
        stage.status = "running"
        stage.start_time = time.time()

        try:
            quality_results = self._run_quality_gates(result)
            result.quality_gate_results = quality_results

            stage.output = {
                "gates_run": len(quality_results),
                "passed": sum(1 for r in quality_results if r.passed),
                "failed": sum(1 for r in quality_results if not r.passed),
            }
            stage.status = "completed"

        except Exception as e:
            stage.error = str(e)
            stage.status = "failed"
            logger.warning(f"Quality gates failed: {e}")

        stage.end_time = time.time()
        stage.duration_ms = int((stage.end_time - stage.start_time) * 1000)
        result.stages.append(stage)

        # Log stage completion
        if self._logger:
            self._logger.info(
                f"Stage completed: {stage.name}",
                trace_id=trace_id,
                stage=stage.name,
                duration_ms=stage.duration_ms,
            )
        self._stage_times[stage.name] = stage.duration_ms

        # Calculate total duration
        result.total_duration_ms = int((time.time() - start_time) * 1000)

        # Mark success based on stages
        result.success = all(s.status == "completed" for s in result.stages)

        # Record metrics (task completion)
        if self._metrics and trace_id:
            self._metrics.record_task(
                task_id=trace_id,
                agent=result.selected_agent or "unknown",
                success=result.success,
                latency_ms=float(result.total_duration_ms),
            )

        # Log task completion with duration and success/failure
        if self._logger:
            status = "success" if result.success else "failed"
            self._logger.info(
                f"Task {status}: {trace_id}",
                task_id=trace_id,
                agent=result.selected_agent or "unknown",
                success=result.success,
                latency_ms=float(result.total_duration_ms),
                event="task_completed",
            )

        return result

    def _run_quality_gates(self, result: PipelineResult) -> List[QualityGateResult]:
        """Run quality gates based on modified files in git diff.

        Args:
            result: PipelineResult with execution output

        Returns:
            List of QualityGateResult for each gate run
        """
        gate_results: List[QualityGateResult] = []
        project_root = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")

        # Get modified files from git diff
        modified_files = self._get_modified_files()
        if not modified_files:
            # No modified files, skip quality gates
            gate_results.append(
                QualityGateResult(
                    name="skipped",
                    passed=True,
                    output="No modified files to check",
                )
            )
            return gate_results

        # Check file extensions
        has_python = any(f.suffix == ".py" for f in modified_files)
        has_js_ts = any(
            f.suffix in (".js", ".ts", ".jsx", ".tsx") for f in modified_files
        )

        # Run Python gates if .py files modified
        if has_python:
            gate_results.append(
                self._run_gate_script("gate-1-py-typecheck.sh", project_root)
            )
            gate_results.append(
                self._run_gate_script("gate-2-py-lint.sh", project_root)
            )

        # Run JS/TS gates if .js/.ts files modified
        if has_js_ts:
            gate_results.append(
                self._run_gate_script("gate-1-typecheck.sh", project_root)
            )
            gate_results.append(self._run_gate_script("gate-2-lint.sh", project_root))

        # Always run secrets scan
        gate_results.append(self._run_gate_script("gate-5-secrets.sh", project_root))

        return gate_results

    def _get_modified_files(self) -> List[Path]:
        """Get list of modified files from git diff.

        Returns:
            List of Path objects for modified files
        """
        project_root = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
        try:
            # Get list of modified/untracked files
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return []

            files = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                # Format: "XY filename" where XY is status
                # Modified: " M", Added: "A", etc.
                parts = line[3:].strip() if len(line) > 3 else line
                if parts:
                    file_path = project_root / parts
                    if file_path.exists():
                        files.append(file_path)
            return files

        except Exception:
            return []

    def _run_gate_script(
        self, script_name: str, project_root: Path
    ) -> QualityGateResult:
        """Run a single quality gate script.

        Args:
            script_name: Name of the gate script
            project_root: Project root directory

        Returns:
            QualityGateResult with pass/fail and output
        """
        script_path = project_root / "bin" / "quality-gates" / script_name
        if not script_path.exists():
            return QualityGateResult(
                name=script_name,
                passed=True,
                output=f"[SKIP] {script_name} not found",
            )

        try:
            result = subprocess.run(
                ["bash", str(script_path)],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return QualityGateResult(
                name=script_name,
                passed=result.returncode == 0,
                output=result.stdout + result.stderr,
            )
        except subprocess.TimeoutExpired:
            return QualityGateResult(
                name=script_name,
                passed=False,
                error="Timeout running gate",
            )
        except Exception as e:
            return QualityGateResult(
                name=script_name,
                passed=False,
                error=str(e),
            )


# Module-level convenience function


def execute(
    user_input: str,
    optimization_target: str = "success",
) -> PipelineResult:
    """Execute user input through unified pipeline.

    Args:
        user_input: Raw user input string
        optimization_target: "success", "speed", or "cost"

    Returns:
        PipelineResult with execution details
    """
    pipeline = UnifiedPipeline()
    return pipeline.execute(user_input, optimization_target)


def health_check() -> Dict[str, Any]:
    """Health check for the unified pipeline.

    Returns:
        Dict with health status
    """
    pipeline = UnifiedPipeline()
    return pipeline.health_check()


# Convenience exports
__all__ = [
    "UnifiedPipeline",
    "PipelineResult",
    "PipelineStage",
    "QualityGateResult",
    "IntentType",
    "execute",
    "health_check",
]
