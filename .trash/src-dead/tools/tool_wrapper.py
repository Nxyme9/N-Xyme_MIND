#!/usr/bin/env python3
"""Tool Wrapper — Wraps local models with tool calling capability.

Uses ReAct pattern to enable local models (Ollama) to use tools like cloud models.
Parses model output to extract tool calls and executes them.

Architecture:
    User Request → Tool Wrapper → Local Model → Parse Response → Execute Tool → Return Result

Key features:
- ReAct reasoning loop for multi-step tasks
- Tool call parsing from plain text responses
- Automatic fallback to cloud models on failure
- Dynamic delay calculation for rate limit handling
"""

import json
import re
import time
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union
from enum import Enum

logger = logging.getLogger(__name__)


# ── Tool Call Patterns ──────────────────────────────────────────────────────

# Regex patterns for extracting tool calls from model output
TOOL_CALL_PATTERNS = [
    # Pattern: tool_name(arg1="value1", arg2=123)
    r"(\w+)\(([^)]+)\)",
    # Pattern: [TOOL: tool_name] args
    r"\[TOOL:\s*(\w+)\]\s*(.+?)(?=\n|$)",
    # Pattern: Use tool_name with args
    r"use\s+(\w+)\s+with\s+(.+?)(?=\n|$)",
    # Pattern: Action: tool_name args
    r"action:\s*(\w+)\s+(.+?)(?=\n|$)",
]

# Tool name normalization
TOOL_ALIASES = {
    "read": "filesystem_read_text_file",
    "write": "filesystem_write_file",
    "edit": "filesystem_edit_file",
    "search": "grep_app_searchGitHub",
    "grep": "grep_app_searchGitHub",
    "bash": "bash",
    "run": "bash",
    "execute": "bash",
    "list": "filesystem_list_directory",
    "glob": "filesystem_search_files",
    "find": "filesystem_search_files",
}


class ToolCallStatus(Enum):
    """Status of a tool call attempt."""

    PARSED = "parsed"
    EXECUTED = "executed"
    FAILED = "failed"
    FALLBACK = "fallback"


@dataclass
class ParsedToolCall:
    """A parsed tool call from model output."""

    tool_name: str
    arguments: Dict[str, Any]
    raw_text: str
    confidence: float = 0.0


@dataclass
class ToolCallResult:
    """Result of a tool call execution."""

    tool_name: str
    arguments: Dict[str, Any]
    success: bool
    result: Any = None
    error: str = ""
    execution_time_ms: float = 0.0
    status: ToolCallStatus = ToolCallStatus.PARSED


class ToolWrapper:
    """Wraps local models with tool calling capability using ReAct pattern."""

    def __init__(
        self,
        local_model_call: Callable,  # Function to call local model
        tool_executor: Callable,  # Function to execute tools
        fallback_model_call: Optional[Callable] = None,  # Optional cloud fallback
        max_iterations: int = 10,
        delay_between_calls: float = 1.0,
    ):
        """
        Initialize tool wrapper.

        Args:
            local_model_call: Function that calls local model (Ollama)
                              Signature: (prompt: str) -> str
            tool_executor: Function that executes tools
                          Signature: (tool_name: str, args: dict) -> Any
            fallback_model_call: Optional cloud model for fallback
            max_iterations: Maximum ReAct iterations
            delay_between_calls: Delay between model calls (seconds)
        """
        self._local_model_call = local_model_call
        self._tool_executor = tool_executor
        self._fallback_model_call = fallback_model_call
        self._max_iterations = max_iterations
        self._delay = delay_between_calls

        # Metrics
        self._total_calls = 0
        self._successful_tool_calls = 0
        self._fallback_count = 0
        self._recent_failures = 0
        self._recent_successes = 0

        # Dynamic delay state
        self._base_delay = delay_between_calls
        self._last_failure_time = 0.0

        logger.info("ToolWrapper initialized")

    # ── Public API ───────────────────────────────────────────────────────────

    async def execute_with_tools(
        self,
        task: str,
        available_tools: List[Dict],
        context: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Execute a task using ReAct loop with tool calling.

        Args:
            task: The task description
            available_tools: List of available tool definitions
            context: Optional context to include in prompt

        Returns:
            Dict with result, steps, and metadata
        """
        self._total_calls += 1
        steps = []

        # Build system prompt with tool definitions
        system_prompt = self._build_system_prompt(available_tools)

        # Initial thought
        current_thought = f"Task: {task}"
        iteration = 0

        while iteration < self._max_iterations:
            iteration += 1

            # Build full prompt
            prompt = self._build_iteration_prompt(
                task, current_thought, steps, context, system_prompt
            )

            # Call model (with delay for rate limiting)
            await self._apply_delay()

            try:
                response = await self._call_model(prompt)
            except Exception as e:
                logger.warning(f"Local model failed: {e}")
                if self._fallback_model_call:
                    self._fallback_count += 1
                    response = await self._call_fallback(prompt)
                else:
                    return {
                        "success": False,
                        "error": f"Model call failed: {e}",
                        "steps": steps,
                    }

            # Parse tool calls from response
            tool_calls = self._parse_tool_calls(response)

            if not tool_calls:
                # No tool call - check if this is a final answer
                if self._is_final_answer(response):
                    return {
                        "success": True,
                        "result": response,
                        "steps": steps,
                        "iterations": iteration,
                    }
                else:
                    # Continue reasoning
                    current_thought = response
                    steps.append(
                        {
                            "iteration": iteration,
                            "thought": response,
                            "action": None,
                            "observation": None,
                        }
                    )
                    continue

            # Execute tool calls
            for tool_call in tool_calls:
                result = await self._execute_tool_call(tool_call)
                steps.append(
                    {
                        "iteration": iteration,
                        "thought": current_thought,
                        "action": tool_call.tool_name,
                        "arguments": tool_call.arguments,
                        "result": result.result if result.success else result.error,
                        "success": result.success,
                    }
                )

                if result.success:
                    self._successful_tool_calls += 1
                    self._recent_successes += 1
                    current_thought += f"\n\nObservation: {result.result}"
                else:
                    self._recent_failures += 1
                    current_thought += f"\n\nError: {result.error}"

                    # Check if fallback needed
                    if result.status == ToolCallStatus.FALLBACK:
                        return await self._execute_with_fallback(
                            task, available_tools, context
                        )

        # Max iterations reached
        return {
            "success": False,
            "error": "Max iterations reached",
            "steps": steps,
            "iterations": iteration,
        }

    def calculate_optimal_delay(self) -> float:
        """
        Calculate optimal delay based on recent success/failure rates.

        Dynamic delay formula:
        - Base delay: 1.0s
        - If failure rate > 30%: delay * 2 (max 12s)
        - If failure rate > 10%: delay * 1.5
        - If success rate high: delay * 0.8 (min 0.5s)
        """
        total = self._recent_failures + self._recent_successes

        if total == 0:
            return self._base_delay

        failure_rate = self._recent_failures / total

        if failure_rate > 0.3:
            return min(self._base_delay * 2, 12.0)
        elif failure_rate > 0.1:
            return self._base_delay * 1.5
        else:
            return max(self._base_delay * 0.8, 0.5)

    def get_metrics(self) -> Dict[str, Any]:
        """Get wrapper metrics."""
        return {
            "total_calls": self._total_calls,
            "successful_tool_calls": self._successful_tool_calls,
            "fallback_count": self._fallback_count,
            "recent_failures": self._recent_failures,
            "recent_successes": self._recent_successes,
            "success_rate": (
                self._successful_tool_calls / self._total_calls
                if self._total_calls > 0
                else 0
            ),
            "current_delay": self.calculate_optimal_delay(),
        }

    # ── Private Methods ──────────────────────────────────────────────────────

    async def _apply_delay(self):
        """Apply dynamic delay based on recent performance."""
        delay = self.calculate_optimal_delay()
        if delay > 0:
            await asyncio.sleep(delay)

    async def _call_model(self, prompt: str) -> str:
        """Call local model."""
        # Wrap in asyncio if needed
        if asyncio.iscoroutinefunction(self._local_model_call):
            return await self._local_model_call(prompt)
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._local_model_call, prompt)

    async def _call_fallback(self, prompt: str) -> str:
        """Call fallback cloud model."""
        if self._fallback_model_call:
            if asyncio.iscoroutinefunction(self._fallback_model_call):
                return await self._fallback_model_call(prompt)
            else:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None, self._fallback_model_call, prompt
                )
        raise Exception("No fallback model available")

    async def _execute_with_fallback(
        self,
        task: str,
        available_tools: List[Dict],
        context: Optional[Dict],
    ) -> Dict[str, Any]:
        """Execute task using fallback model."""
        logger.info("Switching to fallback model")
        self._fallback_count += 1

        if not self._fallback_model_call:
            return {
                "success": False,
                "error": "No fallback available",
            }

        # Rebuild prompt for fallback
        system_prompt = self._build_system_prompt(available_tools)
        prompt = f"{system_prompt}\n\nTask: {task}"

        await self._apply_delay()
        response = await self._call_fallback(prompt)

        return {
            "success": True,
            "result": response,
            "used_fallback": True,
        }

    def _build_system_prompt(self, available_tools: List[Dict]) -> str:
        """Build system prompt with tool definitions."""
        tool_descriptions = []

        for tool in available_tools:
            name = tool.get("name", "unknown")
            desc = tool.get("description", "")
            params = tool.get("parameters", {})

            param_str = (
                ", ".join(
                    f"{prop_name}: {prop.get('type', 'string')}"
                    for prop_name, prop in params.get("properties", {}).items()
                )
                or "none"
            )

            tool_descriptions.append(f"- {name}: {desc} (params: {param_str})")

        return f"""You are an AI assistant with access to tools.

Available tools:
{chr(10).join(tool_descriptions)}

Instructions:
1. Think about what to do
2. If you need to use a tool, respond with: [TOOL: tool_name] arguments
3. If you have the answer, provide it directly
4. Be concise and specific

Example:
Thought: I need to read a file
Action: [TOOL: filesystem_read_text_file] path="/path/to/file"
Observation: File contents..."""

    def _build_iteration_prompt(
        self,
        task: str,
        current_thought: str,
        steps: List[Dict],
        context: Optional[Dict],
        system_prompt: str,
    ) -> str:
        """Build prompt for current iteration."""
        history = ""

        if steps:
            history_lines = []
            for step in steps[-5:]:  # Last 5 steps
                if step.get("action"):
                    history_lines.append(
                        f"Iteration {step['iteration']}: {step.get('thought', '')[:100]}... "
                        f"→ Action: {step['action']} → Result: {step.get('result', '')[:100]}"
                    )
                else:
                    history_lines.append(
                        f"Iteration {step['iteration']}: {step.get('thought', '')[:150]}"
                    )
            history = "\n".join(history_lines)

        context_str = ""
        if context:
            context_str = f"\n\nContext:\n" + "\n".join(
                f"- {k}: {v}" for k, v in context.items()
            )

        return f"""{system_prompt}

{history}
{context_str}

Current Task: {task}
Your current thinking: {current_thought}

Respond with your next thought and any tool calls needed."""

    def _parse_tool_calls(self, response: str) -> List[ParsedToolCall]:
        """Parse tool calls from model response."""
        tool_calls = []

        # Try each pattern
        for pattern in TOOL_CALL_PATTERNS:
            matches = re.finditer(pattern, response, re.IGNORECASE | re.DOTALL)
            for match in matches:
                tool_name = match.group(1).strip()
                args_str = (
                    match.group(2).strip()
                    if (match.lastindex and match.lastindex >= 2)
                    else ""
                )

                # Normalize tool name
                tool_name = TOOL_ALIASES.get(tool_name.lower(), tool_name)

                # Parse arguments
                arguments = self._parse_arguments(args_str)

                tool_calls.append(
                    ParsedToolCall(
                        tool_name=tool_name,
                        arguments=arguments,
                        raw_text=match.group(0),
                        confidence=0.8,
                    )
                )

        return tool_calls

    def _parse_arguments(self, args_str: str) -> Dict[str, Any]:
        """Parse tool arguments from string."""
        args = {}

        if not args_str:
            return args

        # Try JSON format
        if args_str.strip().startswith("{"):
            try:
                return json.loads(args_str)
            except (json.JSONDecodeError, ValueError, OSError):
                pass

        # Try key=value format
        # Pattern: key="value" or key=value or key='value'
        pattern = r'(\w+)=(?:"([^"]*)"|\'([^\']*)\'|(\S+))'
        matches = re.finditer(pattern, args_str)

        for match in matches:
            key = match.group(1)
            # Group 2 = double quotes, 3 = single quotes, 4 = no quotes
            value = match.group(2) or match.group(3) or match.group(4)

            # Try to parse as number
            try:
                if "." in value:
                    value = float(value)
                else:
                    value = int(value)
            except (ValueError, TypeError):
                pass

            args[key] = value

        return args

    def _is_final_answer(self, response: str) -> bool:
        """Check if response is a final answer (no more tools needed)."""
        # Check for final answer indicators
        final_indicators = [
            "final answer:",
            "result:",
            "conclusion:",
            "the answer is:",
            "here is the",
        ]

        response_lower = response.lower()

        # No tool calls found
        if not self._parse_tool_calls(response):
            # Check for final answer language
            for indicator in final_indicators:
                if indicator in response_lower:
                    return True

            # If response is short and complete, consider it final
            if len(response.strip()) < 500 and len(response.strip()) > 20:
                return True

        return False

    async def _execute_tool_call(self, tool_call: ParsedToolCall) -> ToolCallResult:
        """Execute a parsed tool call."""
        start_time = time.time()

        try:
            # Execute tool
            if asyncio.iscoroutinefunction(self._tool_executor):
                result = await self._tool_executor(
                    tool_call.tool_name,
                    tool_call.arguments,
                )
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    self._tool_executor,
                    tool_call.tool_name,
                    tool_call.arguments,
                )

            execution_time = (time.time() - start_time) * 1000

            return ToolCallResult(
                tool_name=tool_call.tool_name,
                arguments=tool_call.arguments,
                success=True,
                result=result,
                execution_time_ms=execution_time,
                status=ToolCallStatus.EXECUTED,
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000

            # Check if should fallback
            if "rate limit" in str(e).lower() or "429" in str(e):
                return ToolCallResult(
                    tool_name=tool_call.tool_name,
                    arguments=tool_call.arguments,
                    success=False,
                    error=str(e),
                    execution_time_ms=execution_time,
                    status=ToolCallStatus.FALLBACK,
                )

            return ToolCallResult(
                tool_name=tool_call.tool_name,
                arguments=tool_call.arguments,
                success=False,
                error=str(e),
                execution_time_ms=execution_time,
                status=ToolCallStatus.FAILED,
            )


# ── Factory Function ─────────────────────────────────────────────────────────


def create_tool_wrapper(
    local_model_call: Callable,
    tool_executor: Callable,
    fallback_model_call: Optional[Callable] = None,
    max_iterations: int = 10,
    delay_between_calls: float = 1.0,
) -> ToolWrapper:
    """
    Create a configured ToolWrapper instance.

    Example:
        def call_local(prompt):
            return ollama.generate(model="qwen2.5-coder:7b", prompt=prompt).response

        def exec_tool(name, args):
            return TOOL_REGISTRY.execute(name, args)

        wrapper = create_tool_wrapper(call_local, exec_tool)
    """
    return ToolWrapper(
        local_model_call=local_model_call,
        tool_executor=tool_executor,
        fallback_model_call=fallback_model_call,
        max_iterations=max_iterations,
        delay_between_calls=delay_between_calls,
    )
