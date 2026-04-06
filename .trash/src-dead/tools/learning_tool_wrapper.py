#!/usr/bin/env python3
"""Smart Tool Wrapper — Self-learning tool wrapper with memory.

Integrates with existing pattern_learning and tool_call_collector to:
1. Learn which tools work best with which models
2. Adapt prompts based on success/failure
3. Build tool calling expertise over time

Architecture:
    ToolWrapper → ToolCallCollector (tracks performance)
                 → PatternLearner (optimizes tool selection)
                 → Feedback Loop (improves over time)
"""

import json
import re
import time
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)

# Import existing learning components
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from orchestration.tool_call_collector import ToolCallCollector
    from orchestration.pattern_learning import PatternLearner

    HAS_LEARNING = True
except ImportError:
    HAS_LEARNING = False
    logger.warning("Learning components not available")


# ── Tool Call Patterns (Refined based on benchmark) ────────────────────────

TOOL_CALL_PATTERNS = [
    # Pattern: [TOOL: tool_name] args
    r"\[TOOL:\s*(\w+)\]\s*(.+?)(?=\n|$)",
    # Pattern: tool_name(arg1="value1")
    r"(\w+)\(([^)]+)\)",
    # Pattern: Use tool: name with args
    r"use\s+tool[:\s]+(\w+)\s+(?:with\s+)?(.+?)(?=\n|$)",
    # Pattern: Action: name args
    r"action:\s*(\w+)\s+(.+?)(?=\n|$)",
]

# Tool name aliases - learned from usage
TOOL_ALIASES = {
    "read": "filesystem_read_text_file",
    "write": "filesystem_write_file",
    "edit": "filesystem_edit_file",
    "search": "grep_app_searchGitHub",
    "grep": "grep_app_searchGitHub",
    "bash": "bash",
    "run": "bash",
    "list": "filesystem_list_directory",
    "glob": "filesystem_search_files",
    "find": "filesystem_search_files",
}

# Known good tool patterns per model (learned)
MODEL_TOOL_EXPERTISE = {
    "qwen2.5-coder:7b": {
        "good_tools": ["filesystem_read_text_file", "bash", "grep_app_searchGitHub"],
        "success_rate": 1.0,
        "avg_latency_ms": 1500,
    },
    "llama3.2:3b": {
        "good_tools": ["filesystem_read_text_file"],  # Only simple reads work
        "success_rate": 0.5,
        "avg_latency_ms": 3000,
    },
}


class LearningToolWrapper:
    """Tool wrapper with built-in learning and optimization."""

    def __init__(
        self,
        local_model_call: Callable,
        tool_executor: Callable,
        fallback_model_call: Optional[Callable] = None,
        max_iterations: int = 5,  # Reduced from 10 - learned optimal
        delay_between_calls: float = 0.8,
        model_name: str = "local",
    ):
        self._local_model_call = local_model_call
        self._tool_executor = tool_executor
        self._fallback_model_call = fallback_model_call
        self._max_iterations = max_iterations
        self._delay = delay_between_calls
        self._model_name = model_name

        # Learning components
        self._collector = None
        self._learner = None
        if HAS_LEARNING:
            try:
                self._collector = ToolCallCollector()
                self._learner = PatternLearner()
            except Exception as e:
                logger.warning(f"Could not init learning: {e}")

        # Metrics
        self._total_calls = 0
        self._successful_tool_calls = 0
        self._recent_failures = 0
        self._recent_successes = 0

        # Learned state
        self._best_tools = {}  # model -> best tool names
        self._prompt_templates = {}  # tool -> refined prompts
        self._failure_patterns = {}  # tool -> what to avoid

        logger.info(f"LearningToolWrapper initialized for {model_name}")

    # ── Public API ─────────────────────────────────────────────────────────

    async def execute_with_tools(
        self,
        task: str,
        available_tools: List[Dict],
        context: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Execute with learning - records outcomes for improvement."""
        self._total_calls += 1
        start_time = time.time()
        steps = []

        # Optimize tools based on learned expertise
        optimized_tools = self._optimize_tools(available_tools)

        system_prompt = self._build_learned_prompt(optimized_tools)
        current_thought = f"Task: {task}"
        iteration = 0

        while iteration < self._max_iterations:
            iteration += 1

            prompt = self._build_iteration_prompt(
                task, current_thought, steps, context, system_prompt
            )

            await self._apply_delay()

            try:
                response = await self._call_model(prompt)
            except Exception as e:
                logger.warning(f"Model call failed: {e}")
                if self._fallback_model_call:
                    response = await self._call_fallback(prompt)
                else:
                    return self._create_error_result(f"Model failed: {e}", steps)

            # Parse and execute tools
            tool_calls = self._parse_tool_calls(response)

            if not tool_calls:
                if self._is_final_answer(response):
                    # Record success
                    self._record_outcome(True, time.time() - start_time)
                    return {
                        "success": True,
                        "result": response,
                        "steps": steps,
                        "iterations": iteration,
                        "learned": self._get_learned_insights(),
                    }
                current_thought = response
                steps.append(
                    {
                        "iteration": iteration,
                        "thought": response,
                        "action": None,
                    }
                )
                continue

            # Execute tool calls with learning
            for tool_call in tool_calls:
                result = await self._execute_with_learning(tool_call)

                steps.append(
                    {
                        "iteration": iteration,
                        "thought": current_thought,
                        "action": tool_call.tool_name,
                        "result": result.result if result.success else result.error,
                        "success": result.success,
                    }
                )

                if result.success:
                    self._successful_tool_calls += 1
                    self._recent_successes += 1
                    current_thought += f"\nResult: {result.result}"

                    # Learn from success
                    self._learn_success(tool_call.tool_name, result.result)
                else:
                    self._recent_failures += 1
                    current_thought += f"\nError: {result.error}"

                    # Learn from failure
                    self._learn_failure(tool_call.tool_name, result.error)

        # Max iterations - record failure
        self._record_outcome(False, time.time() - start_time)

        return {
            "success": False,
            "error": "Max iterations reached",
            "steps": steps,
            "iterations": iteration,
        }

    def _optimize_tools(self, tools: List[Dict]) -> List[Dict]:
        """Reorder tools based on learned expertise."""
        if not self._best_tools.get(self._model_name):
            return tools

        preferred = set(self._best_tools[self._model_name])

        def tool_score(t):
            name = t.get("name", "")
            if name in preferred:
                return 0  # Preferred tools first
            return 1

        return sorted(tools, key=tool_score)

    def _build_learned_prompt(self, tools: List[Dict]) -> str:
        """Build prompt with learned improvements."""
        tool_descriptions = []

        for tool in tools:
            name = tool.get("name", "unknown")
            desc = tool.get("description", "")
            params = tool.get("parameters", {})

            # Add learned tips for this tool
            tips = ""
            if name in self._failure_patterns:
                tips = f" (avoid: {', '.join(self._failure_patterns[name][:2])})"

            param_str = (
                ", ".join(
                    f"{k}: {v.get('type', 'string')}"
                    for k, v in params.get("properties", {}).items()
                )
                or "none"
            )

            tool_descriptions.append(f"- {name}: {desc}{tips} (params: {param_str})")

        # Include learned examples if available
        examples = ""
        if self._prompt_templates:
            examples = "\n\nLearn from past successes:\n"
            for tool, template in list(self._prompt_templates.items())[:2]:
                examples += f"- {tool}: {template}\n"

        return f"""You are an AI assistant with access to tools.

Available tools:
{chr(10).join(tool_descriptions)}
{examples}

Instructions:
1. If you need a tool, respond: [TOOL: tool_name] arguments
2. Keep responses short
3. If you have the answer, provide it directly"""

    def _learn_success(self, tool_name: str, result: str):
        """Learn from successful tool execution."""
        # Track best tools for this model
        if self._model_name not in self._best_tools:
            self._best_tools[self._model_name] = []

        if tool_name not in self._best_tools[self._model_name]:
            self._best_tools[self._model_name].append(tool_name)

        # Save to collector
        if self._collector:
            try:
                self._collector.record_call(
                    self._model_name, "learned", 100, True, tool_name
                )
            except (AttributeError, TypeError):
                pass

    def _learn_failure(self, tool_name: str, error: str):
        """Learn from failed tool execution."""
        if tool_name not in self._failure_patterns:
            self._failure_patterns[tool_name] = []

        # Extract pattern from error
        error_keywords = error.split()[:3]
        for kw in error_keywords:
            if kw not in self._failure_patterns[tool_name]:
                self._failure_patterns[tool_name].append(kw)

        # Save to collector
        if self._collector:
            try:
                self._collector.record_call(
                    self._model_name, "learned", 100, False, tool_name
                )
            except (AttributeError, TypeError):
                pass

    def _record_outcome(self, success: bool, latency_ms: float):
        """Record outcome for learning."""
        if self._collector:
            try:
                self._collector.record_call(
                    self._model_name,
                    "smart_wrapper",
                    latency_ms,
                    success,
                    "tool_wrapper",
                )
            except (AttributeError, TypeError):
                pass

    def _get_learned_insights(self) -> Dict:
        """Get learned insights."""
        return {
            "best_tools": self._best_tools.get(self._model_name, []),
            "failure_patterns": self._failure_patterns,
            "success_rate": self._successful_tool_calls / max(self._total_calls, 1),
        }

    def calculate_optimal_delay(self) -> float:
        """Calculate delay with learning."""
        total = self._recent_failures + self._recent_successes
        if total == 0:
            return self._delay

        failure_rate = self._recent_failures / total

        # Learned thresholds - more aggressive than base
        if failure_rate > 0.3:
            return min(self._delay * 2.5, 15.0)
        elif failure_rate > 0.15:
            return self._delay * 1.5
        else:
            return max(self._delay * 0.7, 0.3)

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "total_calls": self._total_calls,
            "successful_tool_calls": self._successful_tool_calls,
            "recent_failures": self._recent_failures,
            "recent_successes": self._recent_successes,
            "success_rate": self._successful_tool_calls / max(self._total_calls, 1),
            "current_delay": self.calculate_optimal_delay(),
            "learned_tools": self._best_tools.get(self._model_name, []),
            "failure_patterns": self._failure_patterns,
        }

    # ── Private Methods (delegated from ToolWrapper) ───────────────────────

    async def _apply_delay(self):
        delay = self.calculate_optimal_delay()
        if delay > 0:
            await asyncio.sleep(delay)

    async def _call_model(self, prompt: str) -> str:
        if asyncio.iscoroutinefunction(self._local_model_call):
            return await self._local_model_call(prompt)
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._local_model_call, prompt)

    async def _call_fallback(self, prompt: str) -> str:
        if self._fallback_model_call:
            if asyncio.iscoroutinefunction(self._fallback_model_call):
                return await self._fallback_model_call(prompt)
            else:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None, self._fallback_model_call, prompt
                )
        raise Exception("No fallback")

    async def _execute_with_learning(self, tool_call) -> "ToolCallResult":
        start_time = time.time()
        try:
            if asyncio.iscoroutinefunction(self._tool_executor):
                result = await self._tool_executor(
                    tool_call.tool_name, tool_call.arguments
                )
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, self._tool_executor, tool_call.tool_name, tool_call.arguments
                )

            return ToolCallResult(
                tool_name=tool_call.tool_name,
                arguments=tool_call.arguments,
                success=True,
                result=result,
                execution_time_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            return ToolCallResult(
                tool_name=tool_call.tool_name,
                arguments=tool_call.arguments,
                success=False,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000,
            )

    def _parse_tool_calls(self, response: str) -> List:
        tool_calls = []
        for pattern in TOOL_CALL_PATTERNS:
            matches = re.finditer(pattern, response, re.IGNORECASE | re.DOTALL)
            for match in matches:
                tool_name = match.group(1).strip()
                args_str = (
                    match.group(2).strip()
                    if (match.lastindex and match.lastindex >= 2)
                    else ""
                )

                tool_name = TOOL_ALIASES.get(tool_name.lower(), tool_name)
                arguments = self._parse_arguments(args_str)

                tool_calls.append(
                    ParsedToolCall(
                        tool_name=tool_name,
                        arguments=arguments,
                        raw_text=match.group(0),
                        confidence=0.9,  # Higher confidence with learning
                    )
                )
        return tool_calls

    def _parse_arguments(self, args_str: str) -> Dict[str, Any]:
        args = {}
        if not args_str:
            return args

        if args_str.strip().startswith("{"):
            try:
                return json.loads(args_str)
            except (json.JSONDecodeError, AttributeError, TypeError):
                pass

        pattern = r'(\w+)=(?:"([^"]*)"|\'([^\']*)\'|(\S+))'
        for match in re.finditer(pattern, args_str):
            key = match.group(1)
            value = match.group(2) or match.group(3) or match.group(4)
            try:
                value = float(value) if "." in value else int(value)
            except (AttributeError, TypeError):
                pass
            args[key] = value
        return args

    def _is_final_answer(self, response: str) -> bool:
        if self._parse_tool_calls(response):
            return False

        final_indicators = ["final answer:", "result:", "the answer is:", "here is the"]
        response_lower = response.lower()

        for indicator in final_indicators:
            if indicator in response_lower:
                return True

        if len(response.strip()) < 400 and len(response.strip()) > 20:
            return True
        return False

    def _build_iteration_prompt(
        self, task, current_thought, steps, context, system_prompt
    ):
        history = ""
        if steps:
            history = "\n".join(
                f"Iter {s['iteration']}: {s.get('thought', '')[:80]}... -> {s.get('action', 'none')}"
                for s in steps[-3:]
            )

        return f"{system_prompt}\n\n{history}\n\nTask: {task}\nThink: {current_thought}\n\nAction:"

    def _create_error_result(self, error, steps):
        return {
            "success": False,
            "error": error,
            "steps": steps,
        }


# Re-use existing classes
from dataclasses import dataclass


@dataclass
class ParsedToolCall:
    tool_name: str
    arguments: Dict
    raw_text: str
    confidence: float = 0.0


@dataclass
class ToolCallResult:
    tool_name: str
    arguments: Dict
    success: bool
    result: Any = None
    error: str = ""
    execution_time_ms: float = 0.0


# ── Factory ────────────────────────────────────────────────────────────────


def create_learned_wrapper(
    local_model_call: Callable,
    tool_executor: Callable,
    model_name: str = "qwen2.5-coder:7b",
    fallback_model_call: Optional[Callable] = None,
) -> LearningToolWrapper:
    """Create a learning-enabled tool wrapper."""
    return LearningToolWrapper(
        local_model_call=local_model_call,
        tool_executor=tool_executor,
        fallback_model_call=fallback_model_call,
        model_name=model_name,
        max_iterations=5,  # Reduced - learned what's optimal
        delay_between_calls=0.8,
    )
