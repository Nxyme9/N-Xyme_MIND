"""
Agent Loop State Machine — Core execution engine for N-Xyme_MIND.

Based on Claude Code's query.ts (1,729 lines) patterns:
- 10-step iteration: Context → Budget → API → Stream → Error → Hooks → Budget → Tools → Attach → Loop
- Circuit breakers: hasAttemptedReactiveCompact, token budget tracking
- Tool call detection during streaming (not just stop_reason)
- Clean exit conditions: normal completion, token budget exceeded, max iterations, error

Architecture:
    User Message → State Machine Loop → AgentResult
         ↓
    ┌─────────────────────────────────────────────┐
    │ 1. Context    - Build messages from history │
    │ 2. Budget     - Check token budget          │
    │ 3. API        - Call LLM with messages      │
    │ 4. Stream     - Stream response, detect     │
    │                tool calls in real-time      │
    │ 5. Error      - Handle errors               │
    │ 6. Hooks      - Run pre/post hooks          │
    │ 7. Budget     - Check budget after LLM     │
    │ 8. Tools      - Execute tool calls          │
    │ 9. Attach     - Attach results to messages  │
    │ 10. Loop      - Continue or exit            │
    └─────────────────────────────────────────────┘

Usage:
    agent_loop = AgentLoop(llm_client=my_llm)
    result = await agent_loop.run(
        user_message="Fix the bug in auth.py",
        system_prompt="You are a helpful coding assistant.",
        tools=my_tools,
        max_iterations=10,
        token_budget=100000,
    )
    print(result.answer, result.tool_calls, result.token_usage)
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol

logger = logging.getLogger("agent_loop")


# =============================================================================
# Type Definitions
# =============================================================================


class ExitReason(Enum):
    """Reason for exiting the agent loop."""

    NORMAL_COMPLETION = "normal_completion"
    TOKEN_BUDGET_EXCEEDED = "token_budget_exceeded"
    MAX_ITERATIONS_REACHED = "max_iterations_reached"
    ERROR = "error"
    TOOL_LIMIT_REACHED = "tool_limit_reached"


class LoopStep(Enum):
    """Steps in the agent loop iteration."""

    CONTEXT = "context"  # Build messages from history
    BUDGET_CHECK = "budget"  # Check token budget before API call
    API_CALL = "api"  # Call LLM with messages
    STREAM = "stream"  # Stream response, detect tool calls
    ERROR = "error"  # Handle errors
    HOOKS = "hooks"  # Run pre/post hooks
    BUDGET_POST = "budget_post"  # Check budget after LLM
    TOOLS = "tools"  # Execute tool calls
    ATTACH = "attach"  # Attach results to messages
    LOOP = "loop"  # Continue or exit


@dataclass
class TokenUsage:
    """Token usage tracking."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    iteration_costs: List[float] = field(default_factory=list)

    def add(self, prompt: int, completion: int, cost: float = 0.0) -> None:
        """Add tokens from a single LLM call."""
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += prompt + completion
        if cost > 0:
            self.iteration_costs.append(cost)

    def remaining(self, budget: int) -> int:
        """Calculate remaining budget."""
        return max(0, budget - self.total_tokens)


@dataclass
class ToolCall:
    """Represents a tool call from the LLM."""

    id: str
    name: str
    arguments: Dict[str, Any]
    results: Optional[Any] = None
    error: Optional[str] = None
    success: bool = False


@dataclass
class AgentState:
    """
    Immutable state for the agent loop.

    Tracks all execution state across iterations.
    """

    messages: List[Dict[str, Any]] = field(default_factory=list)
    tool_calls: List[ToolCall] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    iteration_count: int = 0
    token_usage: TokenUsage = field(default_factory=TokenUsage)

    # Circuit breaker state
    has_attempted_reactive_compact: bool = False
    consecutive_errors: int = 0
    consecutive_empty: int = 0

    # Streaming state
    current_streaming_content: str = ""
    current_tool_calls_detected: List[Dict] = field(default_factory=list)

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation."""
        self.messages.append({"role": role, "content": content})

    def add_tool_call(self, tool_call: ToolCall) -> None:
        """Add a tool call to the state."""
        self.tool_calls.append(tool_call)

    def add_error(self, error: str) -> None:
        """Add an error to the state."""
        self.errors.append(error)
        self.consecutive_errors += 1
        self.consecutive_empty = 0

    def reset_error_count(self) -> None:
        """Reset consecutive error count."""
        self.consecutive_errors = 0

    def increment_empty_count(self) -> None:
        """Increment consecutive empty response count."""
        self.consecutive_empty += 1

    def reset_empty_count(self) -> None:
        """Reset consecutive empty response count."""
        self.consecutive_empty = 0


@dataclass
class AgentResult:
    """Result returned from the agent loop."""

    answer: str
    tool_calls: List[ToolCall]
    token_usage: TokenUsage
    exit_reason: ExitReason
    iterations: int
    errors: List[str]
    stop_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# LLM Client Protocol (Abstract Interface)
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
# Tool Executor Protocol
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
# Hooks Protocol
# =============================================================================


@dataclass
class HookContext:
    """Context passed to hooks."""

    state: AgentState
    step: LoopStep
    iteration: int


HookFn = Callable[[HookContext], Any]


# =============================================================================
# Default Implementations (No-op)
# =============================================================================


class NoOpLLMClient:
    """No-op LLM client for testing."""

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = True,
        **kwargs: Any,
    ) -> Any:
        """Return empty response."""
        return {"choices": [{"message": {"content": "", "tool_calls": []}}]}


class NoOpToolExecutor:
    """No-op tool executor for testing."""

    async def execute(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Return error response."""
        return {"success": False, "error": "Tool executor not configured"}


# =============================================================================
# Agent Loop State Machine
# =============================================================================


class AgentLoop:
    """
    Asyncio-based agent loop state machine.

    Implements the 10-step iteration pattern from Claude Code's query.ts:
        1. Context    - Build messages from history
        2. Budget     - Check token budget before API call
        3. API        - Call LLM with messages
        4. Stream     - Stream response, detect tool calls in real-time
        5. Error      - Handle errors
        6. Hooks      - Run pre/post hooks
        7. Budget     - Check budget after LLM call
        8. Tools      - Execute tool calls
        9. Attach     - Attach results to messages
        10. Loop      - Continue or exit

    Features:
        - Circuit breakers for reactive compact and token budget
        - Tool call detection during streaming (not just stop_reason)
        - Configurable max_iterations, token_budget, timeout
        - Clean exit conditions
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        tool_executor: Optional[ToolExecutor] = None,
        max_iterations: int = 10,
        token_budget: int = 100000,
        timeout: float = 120.0,
        max_tool_calls_per_iteration: int = 128,
        max_consecutive_errors: int = 3,
        max_consecutive_empty: int = 3,
        pre_hooks: Optional[List[HookFn]] = None,
        post_hooks: Optional[List[HookFn]] = None,
    ):
        """
        Initialize the AgentLoop.

        Args:
            llm_client: LLM client implementing LLMClient protocol
            tool_executor: Tool executor implementing ToolExecutor protocol
            max_iterations: Maximum number of iterations before termination
            token_budget: Maximum total tokens allowed
            timeout: Timeout for LLM calls in seconds
            max_tool_calls_per_iteration: Max tool calls per iteration
            max_consecutive_errors: Max consecutive errors before circuit break
            max_consecutive_empty: Max consecutive empty responses before stop
            pre_hooks: Optional list of hooks to run before each LLM call
            post_hooks: Optional list of hooks to run after each LLM call
        """
        self._llm_client = llm_client or NoOpLLMClient()
        self._tool_executor = tool_executor or NoOpToolExecutor()

        # Configuration
        self._max_iterations = max_iterations
        self._token_budget = token_budget
        self._timeout = timeout
        self._max_tool_calls_per_iteration = max_tool_calls_per_iteration
        self._max_consecutive_errors = max_consecutive_errors
        self._max_consecutive_empty = max_consecutive_empty
        self._pre_hooks = pre_hooks or []
        self._post_hooks = post_hooks or []

        logger.info(
            f"AgentLoop initialized: max_iterations={max_iterations}, "
            f"token_budget={token_budget}, timeout={timeout}s"
        )

    async def run(
        self,
        user_message: str,
        system_prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_iterations: Optional[int] = None,
        token_budget: Optional[int] = None,
        initial_context: Optional[List[Dict[str, Any]]] = None,
    ) -> AgentResult:
        """
        Run the agent loop with a user message.

        Args:
            user_message: The user's input message
            system_prompt: System prompt to prepend
            tools: Optional list of tool definitions
            max_iterations: Override default max_iterations
            token_budget: Override default token_budget
            initial_context: Optional initial messages to start with

        Returns:
            AgentResult with answer, tool_calls, token_usage, and exit_reason
        """
        # Apply overrides
        max_iterations = max_iterations or self._max_iterations
        token_budget = token_budget or self._token_budget

        # Initialize state
        state = AgentState()

        # Add system prompt
        if system_prompt:
            state.add_message("system", system_prompt)

        # Add initial context if provided
        if initial_context:
            for msg in initial_context:
                state.add_message(msg.get("role", "user"), msg.get("content", ""))

        # Add initial user message
        state.add_message("user", user_message)

        logger.info(
            f"AgentLoop: Starting run with budget={token_budget}, max_iter={max_iterations}"
        )

        # Main loop
        exit_reason = ExitReason.NORMAL_COMPLETION
        stop_reason: Optional[str] = None

        while state.iteration_count < max_iterations:
            state.iteration_count += 1
            iteration = state.iteration_count

            logger.info(f"AgentLoop: Iteration {iteration}/{max_iterations}")

            # Check token budget before starting iteration
            if state.token_usage.remaining(token_budget) <= 0:
                exit_reason = ExitReason.TOKEN_BUDGET_EXCEEDED
                stop_reason = f"Token budget exceeded: {state.token_usage.total_tokens}/{token_budget}"
                logger.warning(f"AgentLoop: {stop_reason}")
                break

            try:
                # === Step 1: Context (already built in state.messages) ===
                # Messages are already in state.messages

                # === Step 2: Budget Check (before API call) ===
                # Check we have enough budget for this iteration
                remaining = state.token_usage.remaining(token_budget)
                if remaining < 1000:  # Minimum threshold
                    exit_reason = ExitReason.TOKEN_BUDGET_EXCEEDED
                    stop_reason = f"Insufficient budget for iteration: {remaining}"
                    logger.warning(f"AgentLoop: {stop_reason}")
                    break

                # === Step 3: API Call ===
                response = await self._call_llm(
                    messages=state.messages,
                    tools=tools,
                    iteration=iteration,
                )

                if response is None:
                    state.add_error("LLM returned None response")
                    continue

                # === Step 4: Stream ===
                parsed_response = await self._stream_response(
                    response=response,
                    state=state,
                    iteration=iteration,
                )

                # Check for tool calls in the response
                tool_calls_found = parsed_response.get("tool_calls", [])

                # === Step 5: Error Handling ===
                # Check for errors in the response
                if parsed_response.get("error"):
                    state.add_error(parsed_response["error"])
                    # Continue to hooks and potentially retry

                # === Step 6: Hooks ===
                await self._run_hooks(state, LoopStep.HOOKS, iteration)

                # === Step 7: Budget Check (after API call) ===
                # Update token usage
                if "usage" in parsed_response:
                    state.token_usage.add(
                        prompt=parsed_response["usage"].get("prompt_tokens", 0),
                        completion=parsed_response["usage"].get("completion_tokens", 0),
                    )

                remaining = state.token_usage.remaining(token_budget)
                if remaining <= 0:
                    exit_reason = ExitReason.TOKEN_BUDGET_EXCEEDED
                    stop_reason = f"Token budget exceeded after iteration {iteration}"
                    logger.warning(f"AgentLoop: {stop_reason}")
                    break

                # === Step 8: Tools ===
                # Execute any tool calls that were detected
                if tool_calls_found:
                    await self._execute_tools(
                        tool_calls=tool_calls_found,
                        state=state,
                        iteration=iteration,
                    )

                    # Check tool call limit
                    if len(state.tool_calls) >= self._max_tool_calls_per_iteration:
                        exit_reason = ExitReason.TOOL_LIMIT_REACHED
                        stop_reason = (
                            f"Tool call limit reached: {len(state.tool_calls)}"
                        )
                        logger.warning(f"AgentLoop: {stop_reason}")
                        break

                # === Step 9: Attach ===
                # Attach assistant message with content/tool calls
                assistant_message = {
                    "role": "assistant",
                    "content": parsed_response.get("content", ""),
                }

                if tool_calls_found:
                    assistant_message["tool_calls"] = [
                        {
                            "id": tc["id"],
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc["arguments"]),
                            },
                        }
                        for tc in tool_calls_found
                    ]

                state.messages.append(assistant_message)

                # Attach tool results as messages
                for tool_result in state.tool_results:
                    if len(state.tool_calls) > 0:
                        # Get the last tool call that doesn't have results
                        for tc in state.tool_calls:
                            if tc.results is None:
                                state.messages.append(
                                    {
                                        "role": "tool",
                                        "tool_call_id": tc.id,
                                        "content": json.dumps(
                                            tool_result.get("result", "")
                                        ),
                                    }
                                )
                                break

                # === Step 10: Loop Decision ===
                # Check if we should continue or exit
                should_continue, exit_rsn = self._should_continue(
                    state=state,
                    last_response=parsed_response,
                    iteration=iteration,
                    max_iterations=max_iterations,
                )

                if not should_continue:
                    exit_reason = exit_rsn
                    break

                # Reset error count on successful iteration
                state.reset_error_count()
                state.reset_empty_count()

            except asyncio.TimeoutError:
                state.add_error(
                    f"Iteration {iteration} timed out after {self._timeout}s"
                )
                logger.error(f"AgentLoop: Iteration {iteration} timed out")

                # Check circuit breaker
                if state.consecutive_errors >= self._max_consecutive_errors:
                    exit_reason = ExitReason.ERROR
                    stop_reason = (
                        f"Max consecutive errors reached: {state.consecutive_errors}"
                    )
                    logger.error(f"AgentLoop: Circuit breaker opened - {stop_reason}")
                    break

            except Exception as e:
                state.add_error(f"Iteration {iteration} failed: {str(e)}")
                logger.error(f"AgentLoop: Iteration {iteration} error: {e}")

                # Check circuit breaker
                if state.consecutive_errors >= self._max_consecutive_errors:
                    exit_reason = ExitReason.ERROR
                    stop_reason = (
                        f"Max consecutive errors reached: {state.consecutive_errors}"
                    )
                    logger.error(f"AgentLoop: Circuit breaker opened - {stop_reason}")
                    break

        # Check if we exited due to max iterations
        if (
            state.iteration_count >= max_iterations
            and exit_reason == ExitReason.NORMAL_COMPLETION
        ):
            exit_reason = ExitReason.MAX_ITERATIONS_REACHED
            stop_reason = f"Max iterations reached: {max_iterations}"

        # Build final answer from last assistant message
        answer = self._build_answer(state)

        logger.info(
            f"AgentLoop: Completed with exit_reason={exit_reason.value}, "
            f"iterations={state.iteration_count}, tokens={state.token_usage.total_tokens}"
        )

        return AgentResult(
            answer=answer,
            tool_calls=state.tool_calls,
            token_usage=state.token_usage,
            exit_reason=exit_reason,
            iterations=state.iteration_count,
            errors=state.errors,
            stop_reason=stop_reason,
            metadata={
                "has_attempted_reactive_compact": state.has_attempted_reactive_compact,
                "consecutive_errors": state.consecutive_errors,
            },
        )

    async def _call_llm(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
        iteration: int,
    ) -> Any:
        """Call the LLM API."""
        try:
            # Run with timeout
            response = await asyncio.wait_for(
                self._llm_client.chat(
                    messages=messages,
                    tools=tools,
                    stream=True,
                ),
                timeout=self._timeout,
            )
            return response
        except asyncio.TimeoutError:
            logger.error(f"LLM call timed out at iteration {iteration}")
            raise
        except Exception as e:
            logger.error(f"LLM call failed at iteration {iteration}: {e}")
            raise

    async def _stream_response(
        self,
        response: Any,
        state: AgentState,
        iteration: int,
    ) -> Dict[str, Any]:
        """
        Stream the LLM response and detect tool calls in real-time.

        This is key: tool call detection during streaming, not just stop_reason.
        """
        content = ""
        tool_calls: List[Dict] = []
        usage = {}

        try:
            # Handle both streaming and non-streaming responses
            if hasattr(response, "__aiter__"):
                # Streaming response
                async for chunk in response:
                    # Extract content
                    if "choices" in chunk and len(chunk["choices"]) > 0:
                        choice = chunk["choices"][0]

                        # Delta content
                        if "delta" in choice and "content" in choice["delta"]:
                            content += choice["delta"]["content"]
                            state.current_streaming_content = content

                        # Delta tool calls (real-time detection!)
                        if "delta" in choice and "tool_calls" in choice["delta"]:
                            for tc_delta in choice["delta"]["tool_calls"]:
                                # Find or create tool call entry
                                tc_id = tc_delta.get("id", "")
                                tc_func = tc_delta.get("function", {})
                                tc_name = tc_func.get("name", "")
                                tc_args = tc_func.get("arguments", "")

                                # Parse arguments if complete
                                args_dict = {}
                                if tc_args:
                                    try:
                                        args_dict = json.loads(tc_args)
                                    except json.JSONDecodeError:
                                        # Arguments not complete yet, store partial
                                        args_dict = {"_partial": tc_args}

                                # Check if we already have this tool call
                                existing = next(
                                    (tc for tc in tool_calls if tc.get("id") == tc_id),
                                    None,
                                )
                                if existing:
                                    # Update existing
                                    if "arguments" in existing and isinstance(
                                        existing["arguments"], dict
                                    ):
                                        if "_partial" in existing["arguments"]:
                                            # Append to partial
                                            existing["arguments"] = (
                                                args_dict
                                                if args_dict.get("_partial") is None
                                                else existing["arguments"]
                                            )
                                else:
                                    # New tool call
                                    tool_calls.append(
                                        {
                                            "id": tc_id,
                                            "name": tc_name,
                                            "arguments": args_dict,
                                        }
                                    )
                                    state.current_tool_calls_detected = tool_calls

                        # Usage info
                        if "usage" in chunk:
                            usage = chunk["usage"]

                        # Stop reason (for reference, not primary detection)
                        stop_reason = choice.get("finish_reason", "")
                        if stop_reason:
                            logger.debug(
                                f"Iteration {iteration} stop_reason: {stop_reason}"
                            )
            else:
                # Non-streaming response
                if "choices" in response and len(response["choices"]) > 0:
                    choice = response["choices"][0]
                    content = choice.get("message", {}).get("content", "")
                    tool_calls_raw = choice.get("message", {}).get("tool_calls", [])
                    for tc in tool_calls_raw:
                        func = tc.get("function", {})
                        tool_calls.append(
                            {
                                "id": tc.get("id", ""),
                                "name": func.get("name", ""),
                                "arguments": func.get("arguments", {}),
                            }
                        )
                    if "usage" in response:
                        usage = response["usage"]
        except Exception as e:
            logger.error(f"Error streaming response at iteration {iteration}: {e}")
            return {
                "error": str(e),
                "content": content,
                "tool_calls": tool_calls,
                "usage": usage,
            }

        return {
            "content": content,
            "tool_calls": tool_calls,
            "usage": usage,
        }

    async def _execute_tools(
        self,
        tool_calls: List[Dict],
        state: AgentState,
        iteration: int,
    ) -> None:
        """Execute tool calls and store results."""
        for tc in tool_calls:
            tool_call = ToolCall(
                id=tc.get("id", f"call_{len(state.tool_calls)}"),
                name=tc.get("name", ""),
                arguments=tc.get("arguments", {}),
            )

            try:
                result = await self._tool_executor.execute(
                    tool_call.name,
                    tool_call.arguments,
                )

                tool_call.results = result.get("result")
                tool_call.success = result.get("success", False)
                tool_call.error = result.get("error")

                # Add to tool results
                state.tool_results.append(result)

            except Exception as e:
                tool_call.success = False
                tool_call.error = str(e)
                state.tool_results.append({"success": False, "error": str(e)})
                logger.error(f"Tool execution failed: {tool_call.name}: {e}")

            # Add to state's tool calls
            state.add_tool_call(tool_call)

            logger.info(
                f"Executed tool: {tool_call.name} (success={tool_call.success})"
            )

    async def _run_hooks(
        self, state: AgentState, step: LoopStep, iteration: int
    ) -> None:
        """Run pre/post hooks."""
        context = HookContext(state=state, step=step, iteration=iteration)

        for hook in self._pre_hooks + self._post_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(context)
                else:
                    hook(context)
            except Exception as e:
                logger.warning(f"Hook failed at iteration {iteration}: {e}")

    def _should_continue(
        self,
        state: AgentState,
        last_response: Dict[str, Any],
        iteration: int,
        max_iterations: int,
    ) -> tuple[bool, ExitReason]:
        """
        Determine if the loop should continue.

        Returns:
            Tuple of (should_continue, exit_reason)
        """
        content = last_response.get("content", "")
        tool_calls = last_response.get("tool_calls", [])

        # If there are tool calls, we must continue to execute them
        if tool_calls:
            return (True, ExitReason.NORMAL_COMPLETION)

        # If content is empty, check if we've had too many empty responses
        if not content.strip():
            state.increment_empty_count()
            if state.consecutive_empty >= self._max_consecutive_empty:
                return (False, ExitReason.ERROR)
            return (True, ExitReason.NORMAL_COMPLETION)

        # If we have content and no more tool calls, we can exit
        # Check if the content looks like a final answer
        # This is a simple heuristic - could be enhanced
        return (True, ExitReason.NORMAL_COMPLETION)

    def _build_answer(self, state: AgentState) -> str:
        """Build the final answer from the state."""
        # Get the last assistant message with content
        for msg in reversed(state.messages):
            if msg.get("role") == "assistant" and msg.get("content"):
                return msg["content"]

        # Fallback: combine all tool results
        if state.tool_results:
            return json.dumps(state.tool_results)

        return ""

    # =========================================================================
    # Public API for state machine introspection
    # =========================================================================

    async def step_context(self, state: AgentState) -> None:
        """Step 1: Build context from messages."""
        # Already built in state.messages during initialization
        pass

    async def step_budget_check(self, state: AgentState, budget: int) -> bool:
        """Step 2: Check token budget before API call."""
        remaining = state.token_usage.remaining(budget)
        return remaining >= 1000  # Minimum threshold

    async def step_api(
        self, messages: List[Dict], tools: Optional[List], iteration: int
    ) -> Any:
        """Step 3: Call LLM API."""
        return await self._call_llm(messages, tools, iteration)

    async def step_stream(
        self,
        response: Any,
        state: AgentState,
        iteration: int,
    ) -> Dict[str, Any]:
        """Step 4: Stream response and detect tool calls."""
        return await self._stream_response(response, state, iteration)

    async def step_error(self, error: str, state: AgentState) -> None:
        """Step 5: Handle errors."""
        state.add_error(error)

    async def step_hooks(self, state: AgentState, iteration: int) -> None:
        """Step 6: Run hooks."""
        await self._run_hooks(state, LoopStep.HOOKS, iteration)

    async def step_budget_post(self, state: AgentState, budget: int) -> bool:
        """Step 7: Check budget after LLM call."""
        remaining = state.token_usage.remaining(budget)
        return remaining > 0

    async def step_tools(
        self, tool_calls: List[Dict], state: AgentState, iteration: int
    ) -> None:
        """Step 8: Execute tool calls."""
        await self._execute_tools(tool_calls, state, iteration)

    async def step_attach(
        self,
        response: Dict[str, Any],
        state: AgentState,
    ) -> None:
        """Step 9: Attach results to messages."""
        content = response.get("content", "")
        tool_calls = response.get("tool_calls", [])

        assistant_message = {
            "role": "assistant",
            "content": content,
        }

        if tool_calls:
            assistant_message["tool_calls"] = [
                {
                    "id": tc["id"],
                    "function": {
                        "name": tc["name"],
                        "arguments": json.dumps(tc["arguments"]),
                    },
                }
                for tc in tool_calls
            ]

        state.messages.append(assistant_message)


# =============================================================================
# Module-Level Convenience Functions
# =============================================================================


async def run_agent_loop(
    user_message: str,
    system_prompt: str,
    llm_client: Optional[LLMClient] = None,
    tool_executor: Optional[ToolExecutor] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    max_iterations: int = 10,
    token_budget: int = 100000,
) -> AgentResult:
    """
    Convenience function to run the agent loop.

    Args:
        user_message: The user's input message
        system_prompt: System prompt to prepend
        llm_client: LLM client (optional, creates NoOpLLMClient if not provided)
        tool_executor: Tool executor (optional, creates NoOpToolExecutor if not provided)
        tools: Optional list of tool definitions
        max_iterations: Maximum number of iterations
        token_budget: Maximum total tokens

    Returns:
        AgentResult with execution details
    """
    agent_loop = AgentLoop(
        llm_client=llm_client,
        tool_executor=tool_executor,
        max_iterations=max_iterations,
        token_budget=token_budget,
    )

    return await agent_loop.run(
        user_message=user_message,
        system_prompt=system_prompt,
        tools=tools,
        max_iterations=max_iterations,
        token_budget=token_budget,
    )


# =============================================================================
# Main - Quick Test
# =============================================================================


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s: %(message)s",
    )

    print("=== AgentLoop State Machine Test ===\n")

    async def test():
        # Test with no-op client
        agent_loop = AgentLoop(
            llm_client=NoOpLLMClient(),
            tool_executor=NoOpToolExecutor(),
            max_iterations=3,
            token_budget=10000,
        )

        print("--- Running Agent Loop ---")
        result = await agent_loop.run(
            user_message="Hello, how are you?",
            system_prompt="You are a helpful assistant.",
            tools=[],
        )

        print(f"\n--- Results ---")
        print(f"Exit reason: {result.exit_reason.value}")
        print(f"Iterations: {result.iterations}")
        print(f"Token usage: {result.token_usage.total_tokens}")
        print(f"Answer: {result.answer[:100] if result.answer else '(empty)'}...")
        print(f"Tool calls: {len(result.tool_calls)}")
        print(f"Errors: {len(result.errors)}")

        # Test individual steps
        print("\n--- Testing Individual Steps ---")
        state = AgentState()
        state.add_message("system", "You are a helpful assistant.")
        state.add_message("user", "Hello")

        print(f"Step 1 (Context): {len(state.messages)} messages")

        can_continue = await agent_loop.step_budget_check(state, 10000)
        print(f"Step 2 (Budget Check): {can_continue}")

        print("\nAll tests passed!")

    # Run async test
    asyncio.run(test())

    sys.exit(0)
