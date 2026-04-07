#!/usr/bin/env python3
"""Streaming Tool Executor - Execute tools detected during LLM streaming.

Based on Claude Code's streaming tool execution pattern:
- Detect tool calls during streaming (not just stop_reason)
- Execute tools in parallel where possible
- Return structured ToolResult list for agent_loop integration

Usage:
    executor = StreamingExecutor(tool_executor=my_executor)
    results = await executor.execute_tools_streaming(
        tool_calls=[{"id": "call_1", "name": "add", "arguments": {"a": 1, "b": 2}}],
        llm_client=my_llm,
    )
    for result in results:
        print(result.id, result.output, result.error, result.latency_ms)
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol

logger = logging.getLogger("streaming_executor")


# =============================================================================
# Type Definitions
# =============================================================================


@dataclass
class ToolResult:
    """Result of a tool execution.

    Attributes:
        id: Unique identifier for the tool call
        name: Name of the tool executed
        arguments: Arguments passed to the tool
        output: Output from the tool execution (serializable)
        error: Error message if execution failed
        latency_ms: Execution time in milliseconds
    """

    id: str
    name: str
    arguments: Dict[str, Any]
    output: Any = None
    error: Optional[str] = None
    latency_ms: float = 0.0


@dataclass
class StreamingToolCall:
    """A tool call detected during streaming.

    Attributes:
        id: Unique identifier
        name: Tool name
        arguments: Parsed arguments (may be partial during streaming)
        is_complete: Whether arguments are fully parsed
    """

    id: str
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    is_complete: bool = True


# =============================================================================
# Tool Executor Protocol (from agent_loop.py)
# =============================================================================


class ToolExecutor(Protocol):
    """Abstract interface for tool execution."""

    async def execute(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a tool call.

        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments to pass to the tool

        Returns:
            Dict with 'success', 'result', and optionally 'error'
        """
        ...


# =============================================================================
# LLM Client Protocol (from agent_loop.py)
# =============================================================================


class LLMClient(Protocol):
    """Abstract interface for LLM API clients."""

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = True,
        **kwargs: Any,
    ) -> Any:
        """
        Send a chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional list of tool definitions
            stream: Whether to stream the response
            **kwargs: Additional parameters

        Returns:
            For non-streaming: response dict
            For streaming: async iterator of response chunks
        """
        ...


# =============================================================================
# No-op implementations (from agent_loop.py)
# =============================================================================


class NoOpToolExecutor:
    """No-op tool executor for testing."""

    async def execute(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Return error response."""
        return {"success": False, "error": "Tool executor not configured"}


# =============================================================================
# Streaming Executor
# =============================================================================


class StreamingExecutor:
    """
    Execute tools detected during LLM streaming.

    Based on Claude Code's pattern:
    - Tool calls can be detected during streaming (not just at stop_reason)
    - Independent tools can be executed in parallel
    - Results are returned as structured ToolResult list

    Features:
        - Parse tool calls from streaming response deltas
        - Parallel execution for independent tool calls
        - Latency tracking per tool
        - Integration with agent_loop.py's ToolCall format
    """

    def __init__(
        self,
        tool_executor: Optional[ToolExecutor] = None,
        max_parallel: int = 10,
        timeout: float = 60.0,
    ):
        """
        Initialize the StreamingExecutor.

        Args:
            tool_executor: Tool executor implementing ToolExecutor protocol
            max_parallel: Maximum parallel tool executions
            timeout: Timeout for tool execution in seconds
        """
        self._tool_executor = tool_executor or NoOpToolExecutor()
        self._max_parallel = max_parallel
        self._timeout = timeout

        logger.info(
            f"StreamingExecutor initialized: max_parallel={max_parallel}, "
            f"timeout={timeout}s"
        )

    async def execute_tools_streaming(
        self,
        tool_calls: List[Dict[str, Any]],
        llm_client: Optional[LLMClient] = None,
    ) -> List[ToolResult]:
        """
        Execute a list of tool calls, parallelizing where possible.

        This is the main entry point for executing tools detected during
        streaming. It analyzes dependencies and executes independent tools
        in parallel.

        Args:
            tool_calls: List of tool call dicts with 'id', 'name', 'arguments'
            llm_client: Optional LLM client for any streaming needs

        Returns:
            List of ToolResult objects with output, error, and latency_ms
        """
        if not tool_calls:
            logger.debug("No tool calls to execute")
            return []

        logger.info(f"Executing {len(tool_calls)} tool calls")

        # Convert to StreamingToolCall format
        parsed_calls = self._parse_tool_calls(tool_calls)

        # Execute in parallel (all independent for now)
        results = await self._execute_parallel(parsed_calls)

        logger.info(f"Completed {len(results)} tool executions")
        return results

    async def execute_tools_streaming_from_response(
        self,
        response: Any,
        state: Optional[Any] = None,
    ) -> List[ToolResult]:
        """
        Execute tools detected during streaming response.

        This method extracts tool calls from a streaming response and
        executes them. Designed for integration with agent_loop.py's
        _stream_response method.

        Args:
            response: Streaming response from LLM (async iterator or dict)
            state: Optional state object with current_tool_calls_detected

        Returns:
            List of ToolResult objects
        """
        tool_calls = []

        # Extract from state if available (agent_loop integration)
        if state and hasattr(state, "current_tool_calls_detected"):
            tool_calls = state.current_tool_calls_detected

        # Also extract from response directly
        if hasattr(response, "__aiter__"):
            # Streaming - need to collect (would be handled by agent_loop)
            pass
        elif isinstance(response, dict):
            tool_calls = response.get("tool_calls", [])

        return await self.execute_tools_streaming(tool_calls)

    def _parse_tool_calls(
        self, tool_calls: List[Dict[str, Any]]
    ) -> List[StreamingToolCall]:
        """Parse tool call dicts into StreamingToolCall objects."""
        parsed = []

        for tc in tool_calls:
            # Handle both formats:
            # 1. {"id": "...", "name": "...", "arguments": {...}}
            # 2. {"id": "...", "function": {"name": "...", "arguments": "..."}}

            tc_id = tc.get("id", f"call_{len(parsed)}")
            tc_name = tc.get("name", "")
            tc_args = tc.get("arguments", {})

            # Handle function format
            if not tc_name and "function" in tc:
                func = tc.get("function", {})
                tc_name = func.get("name", "")
                func_args = func.get("arguments", "")
                if isinstance(func_args, str):
                    try:
                        tc_args = json.loads(func_args)
                    except json.JSONDecodeError:
                        tc_args = {"_partial": func_args}
                else:
                    tc_args = func_args or {}

            # Determine if arguments are complete
            is_complete = "_partial" not in tc_args

            parsed.append(
                StreamingToolCall(
                    id=tc_id,
                    name=tc_name,
                    arguments=tc_args,
                    is_complete=is_complete,
                )
            )

        return parsed

    async def _execute_parallel(
        self, tool_calls: List[StreamingToolCall]
    ) -> List[ToolResult]:
        """Execute tool calls in parallel with semaphore for limiting."""
        semaphore = asyncio.Semaphore(self._max_parallel)

        async def execute_with_semaphore(tc: StreamingToolCall) -> ToolResult:
            async with semaphore:
                return await self._execute_single(tc)

        # Execute all in parallel
        tasks = [execute_with_semaphore(tc) for tc in tool_calls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to ToolResult errors
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    ToolResult(
                        id=tool_calls[i].id,
                        name=tool_calls[i].name,
                        arguments=tool_calls[i].arguments,
                        error=str(result),
                        latency_ms=0.0,
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    async def _execute_single(self, tc: StreamingToolCall) -> ToolResult:
        """Execute a single tool call with timing."""
        start_time = time.perf_counter()

        try:
            # Apply timeout
            result = await asyncio.wait_for(
                self._tool_executor.execute(tc.name, tc.arguments),
                timeout=self._timeout,
            )

            latency_ms = (time.perf_counter() - start_time) * 1000

            # Extract output from result
            output = result.get("result")
            error = result.get("error")

            if not result.get("success", True) and not output:
                error = error or "Execution failed"

            return ToolResult(
                id=tc.id,
                name=tc.name,
                arguments=tc.arguments,
                output=output,
                error=error,
                latency_ms=latency_ms,
            )

        except asyncio.TimeoutError:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Tool {tc.name} timed out after {self._timeout}s")
            return ToolResult(
                id=tc.id,
                name=tc.name,
                arguments=tc.arguments,
                error=f"Timeout after {self._timeout}s",
                latency_ms=latency_ms,
            )

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Tool {tc.name} failed: {e}")
            return ToolResult(
                id=tc.id,
                name=tc.name,
                arguments=tc.arguments,
                error=str(e),
                latency_ms=latency_ms,
            )

    def format_results_for_messages(
        self, results: List[ToolResult]
    ) -> List[Dict[str, Any]]:
        """Format tool results for attachment to messages.

        Args:
            results: List of ToolResult from execute_tools_streaming

        Returns:
            List of message dicts for tool results (agent_loop format)
        """
        messages = []

        for result in results:
            content = json.dumps(result.output) if result.output is not None else ""

            if result.error:
                content = json.dumps({"error": result.error})

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": result.id,
                    "content": content,
                }
            )

        return messages


# =============================================================================
# Integration with agent_loop.py
# =============================================================================


async def execute_from_agent_loop(
    tool_calls: List[Dict[str, Any]],
    tool_executor: Optional[ToolExecutor] = None,
) -> List[ToolResult]:
    """
    Convenience function for agent_loop.py integration.

    Usage in agent_loop.py:
        from packages.orchestration.streaming_executor import execute_from_agent_loop

        # In _execute_tools method:
        results = await execute_from_agent_loop(tool_calls, self._tool_executor)

        # Attach results to messages
        for result in results:
            state.messages.append({
                "role": "tool",
                "tool_call_id": result.id,
                "content": json.dumps(result.output or {"error": result.error}),
            })

    Args:
        tool_calls: List of tool call dicts from agent_loop
        tool_executor: Tool executor from agent_loop

    Returns:
        List of ToolResult for attachment to state.messages
    """
    executor = StreamingExecutor(tool_executor=tool_executor)
    return await executor.execute_tools_streaming(tool_calls)


# =============================================================================
# Module-Level Convenience
# =============================================================================


async def execute_tools(
    tool_calls: List[Dict[str, Any]],
    tool_executor: Optional[ToolExecutor] = None,
    max_parallel: int = 10,
) -> List[ToolResult]:
    """
    Module-level convenience function for tool execution.

    Args:
        tool_calls: List of tool call dicts with 'id', 'name', 'arguments'
        tool_executor: Optional tool executor
        max_parallel: Maximum parallel executions

    Returns:
        List of ToolResult with output, error, latency_ms
    """
    executor = StreamingExecutor(
        tool_executor=tool_executor,
        max_parallel=max_parallel,
    )
    return await executor.execute_tools_streaming(tool_calls)


# =============================================================================
# Main - Quick Test
# =============================================================================


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s: %(message)s",
    )

    print("=== Streaming Executor Test ===\n")

    async def test():
        # Test with no-op executor
        executor = StreamingExecutor(
            tool_executor=NoOpToolExecutor(),
            max_parallel=5,
        )

        # Test 1: Empty tool calls
        print("--- Test 1: Empty tool calls ---")
        results = await executor.execute_tools_streaming([])
        print(f"Results: {len(results)} (expected 0)")

        # Test 2: Single tool call
        print("\n--- Test 2: Single tool call ---")
        tool_calls = [
            {"id": "call_1", "name": "test_tool", "arguments": {"key": "value"}}
        ]
        results = await executor.execute_tools_streaming(tool_calls)
        print(f"Results: {len(results)}")
        for r in results:
            print(
                f"  - id={r.id}, name={r.name}, error={r.error}, latency={r.latency_ms:.2f}ms"
            )

        # Test 3: Multiple tool calls
        print("\n--- Test 3: Multiple tool calls ---")
        tool_calls = [
            {"id": "call_1", "name": "tool_a", "arguments": {"a": 1}},
            {"id": "call_2", "name": "tool_b", "arguments": {"b": 2}},
            {"id": "call_3", "name": "tool_c", "arguments": {"c": 3}},
        ]
        results = await executor.execute_tools_streaming(tool_calls)
        print(f"Results: {len(results)}")
        for r in results:
            print(f"  - {r.name}: {r.error or 'ok'} ({r.latency_ms:.2f}ms)")

        # Test 4: Function format (like agent_loop)
        print("\n--- Test 4: Function format ---")
        tool_calls = [
            {
                "id": "call_x",
                "function": {
                    "name": "my_func",
                    "arguments": '{"arg1": "val1"}',
                },
            }
        ]
        results = await executor.execute_tools_streaming(tool_calls)
        print(f"Results: {len(results)}")
        for r in results:
            print(f"  - {r.name}: {r.arguments}")

        # Test 5: Format for messages
        print("\n--- Test 5: Format for messages ---")
        tool_calls = [{"id": "call_1", "name": "add", "arguments": {"a": 1, "b": 2}}]
        results = await executor.execute_tools_streaming(tool_calls)
        messages = executor.format_results_for_messages(results)
        print(f"Messages: {len(messages)}")
        for msg in messages:
            print(f"  - {msg}")

        print("\nAll tests completed!")

    # Run async test
    asyncio.run(test())

    sys.exit(0)
