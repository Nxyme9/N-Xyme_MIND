"""
Tool Hooks System for N-Xyme_MIND
================================
Based on leaked Anthropic source code patterns.

Reference: /home/nxyme/Documentos/CODE/source_code/ant-source-code-main/services/tools/toolHooks.ts

Features:
- PreToolUse hooks: Run before tool execution (permission, input modification)
- PostToolUse hooks: Run after successful execution (output modification, context)
- PostToolUseFailure hooks: Run on failure (error handling, retry logic)
- HookRegistry: Register hooks by tool name or pattern with priority ordering
- HookRunner: Async execution with cancellation support

Usage:
    from packages.nx_context_mcp.tool_hooks import (
        HookRegistry, HookRunner, PreToolUseHook, PostToolUseHook, HookResult
    )

    registry = HookRegistry()
    registry.register_pre_tool_hook("shell", my_pre_hook, priority=10)

    runner = HookRunner(registry)
    input, result = await runner.run_pre_tool_hooks("shell", {"cmd": "ls"}, context)
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)

# =============================================================================
# Hook Types
# =============================================================================


@dataclass
class HookResult:
    """
    Result returned by hook execution.

    Maps to TypeScript executePreToolHooks/PostToolHooks result structure.
    """

    # For blocking/prevention
    blocking_error: str | None = None
    stop_reason: str | None = None
    prevent_continuation: bool = False

    # For input modification
    updated_input: dict[str, Any] | None = None

    # For additional context
    additional_contexts: list[dict[str, Any]] | None = None

    # For permission behavior
    permission_behavior: str | None = None  # "allow", "deny", "ask"
    decision_reason: str | None = None

    # For output modification (PostToolUse only)
    updated_output: Any = None

    @classmethod
    def allow(cls, updated_input: dict[str, Any] | None = None) -> "HookResult":
        """Create an 'allow' result."""
        return cls(permission_behavior="allow", updated_input=updated_input)

    @classmethod
    def deny(cls, message: str = "") -> "HookResult":
        """Create a 'deny' result."""
        return cls(permission_behavior="deny", blocking_error=message)

    @classmethod
    def ask(cls, message: str = "") -> "HookResult":
        """Create an 'ask' result."""
        return cls(permission_behavior="ask", decision_reason=message)

    @classmethod
    def block(cls, error: str) -> "HookResult":
        """Create a blocking result."""
        return cls(blocking_error=error, permission_behavior="deny")

    @classmethod
    def add_context(cls, contexts: list[dict[str, Any]]) -> "HookResult":
        """Create a result that adds context."""
        return cls(additional_contexts=contexts)

    @classmethod
    def stop_chain(cls, reason: str = "") -> "HookResult":
        """Create a result that stops the execution chain."""
        return cls(prevent_continuation=True, stop_reason=reason)


@dataclass
class HookContext:
    """Context passed to hook functions."""

    tool_use_id: str
    permission_mode: str = "default"
    abort_signal: asyncio.Event | None = None
    request_prompt: str | None = None
    tool_use_summary: str | None = None
    messages: list[dict[str, Any]] = field(default_factory=list)


# Type aliases for hook functions
PreToolUseHookFn = Callable[
    [str, str, dict[str, Any], HookContext],
    Awaitable[HookResult],
]

PostToolUseHookFn = Callable[
    [str, str, dict[str, Any], Any, HookContext],
    Awaitable[HookResult],
]

PostToolUseFailureHookFn = Callable[
    [str, str, dict[str, Any], str, HookContext],
    Awaitable[HookResult],
]


# =============================================================================
# HookRegistry
# =============================================================================


@dataclass
class RegisteredHook:
    """Single registered hook with metadata."""

    pattern: str
    hook_type: str  # "pre", "post", "failure"
    hook_fn: Callable[..., Awaitable[HookResult]]
    priority: int = 0
    is_regex: bool = False


class HookRegistry:
    """
    Registry for tool hooks.

    Supports:
    - Exact tool name matching
    - Prefix matching (e.g., "shell*" matches "shell", "shell.run")
    - Regex matching (e.g., "^git-.*$" matches "git-commit")
    - Priority ordering (higher priority runs first)
    """

    def __init__(self):
        self._pre_hooks: list[RegisteredHook] = []
        self._post_hooks: list[RegisteredHook] = []
        self._failure_hooks: list[RegisteredHook] = []

    def register_pre_tool_hook(
        self,
        tool_pattern: str,
        hook_fn: PreToolUseHookFn,
        priority: int = 0,
    ) -> None:
        """Register a PreToolUse hook."""
        is_regex = _is_regex_pattern(tool_pattern)
        hook = RegisteredHook(
            pattern=tool_pattern,
            hook_type="pre",
            hook_fn=hook_fn,
            priority=priority,
            is_regex=is_regex,
        )
        self._pre_hooks.append(hook)
        self._pre_hooks.sort(key=lambda h: h.priority, reverse=True)
        logger.debug(
            f"Registered PreToolUse hook for '{tool_pattern}' (pri={priority})"
        )

    def register_post_tool_hook(
        self,
        tool_pattern: str,
        hook_fn: PostToolUseHookFn,
        priority: int = 0,
    ) -> None:
        """Register a PostToolUse hook."""
        is_regex = _is_regex_pattern(tool_pattern)
        hook = RegisteredHook(
            pattern=tool_pattern,
            hook_type="post",
            hook_fn=hook_fn,
            priority=priority,
            is_regex=is_regex,
        )
        self._post_hooks.append(hook)
        self._post_hooks.sort(key=lambda h: h.priority, reverse=True)
        logger.debug(
            f"Registered PostToolUse hook for '{tool_pattern}' (pri={priority})"
        )

    def register_failure_hook(
        self,
        tool_pattern: str,
        hook_fn: PostToolUseFailureHookFn,
        priority: int = 0,
    ) -> None:
        """Register a PostToolUseFailure hook."""
        is_regex = _is_regex_pattern(tool_pattern)
        hook = RegisteredHook(
            pattern=tool_pattern,
            hook_type="failure",
            hook_fn=hook_fn,
            priority=priority,
            is_regex=is_regex,
        )
        self._failure_hooks.append(hook)
        self._failure_hooks.sort(key=lambda h: h.priority, reverse=True)
        logger.debug(
            f"Registered PostToolUseFailure hook for '{tool_pattern}' (pri={priority})"
        )

    def get_pre_hooks(self, tool_name: str) -> list[RegisteredHook]:
        """Get matching PreToolUse hooks for a tool."""
        return self._match_hooks(tool_name, self._pre_hooks)

    def get_post_hooks(self, tool_name: str) -> list[RegisteredHook]:
        """Get matching PostToolUse hooks for a tool."""
        return self._match_hooks(tool_name, self._post_hooks)

    def get_failure_hooks(self, tool_name: str) -> list[RegisteredHook]:
        """Get matching PostToolUseFailure hooks for a tool."""
        return self._match_hooks(tool_name, self._failure_hooks)

    def _match_hooks(
        self,
        tool_name: str,
        hooks: list[RegisteredHook],
    ) -> list[RegisteredHook]:
        """Find hooks matching a tool name."""
        matches = []
        for hook in hooks:
            if self._tool_matches(tool_name, hook.pattern, hook.is_regex):
                matches.append(hook)
        return matches

    def _tool_matches(self, tool_name: str, pattern: str, is_regex: bool) -> bool:
        """Check if tool name matches pattern."""
        if is_regex:
            try:
                return bool(re.match(pattern, tool_name))
            except re.error:
                logger.warning(f"Invalid regex pattern: {pattern}")
                return False

        # Exact match
        if pattern == tool_name:
            return True

        # Prefix match (pattern ends with *)
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return tool_name.startswith(prefix)

        # Prefix match (tool_name starts with pattern*)
        if tool_name.startswith(pattern):
            return True

        return False

    def clear_hooks(self, tool_pattern: str | None = None) -> None:
        """Clear hooks for a pattern, or all if None."""
        if tool_pattern is None:
            self._pre_hooks.clear()
            self._post_hooks.clear()
            self._failure_hooks.clear()
            logger.info("Cleared all hooks")
            return

        # Clear matching hooks
        self._pre_hooks = [h for h in self._pre_hooks if h.pattern != tool_pattern]
        self._post_hooks = [h for h in self._post_hooks if h.pattern != tool_pattern]
        self._failure_hooks = [
            h for h in self._failure_hooks if h.pattern != tool_pattern
        ]
        logger.info(f"Cleared hooks for '{tool_pattern}'")

    def list_hooks(self) -> dict[str, list[str]]:
        """List all registered hooks by type."""
        return {
            "pre": [f"{h.pattern} (p={h.priority})" for h in self._pre_hooks],
            "post": [f"{h.pattern} (p={h.priority})" for h in self._post_hooks],
            "failure": [f"{h.pattern} (p={h.priority})" for h in self._failure_hooks],
        }


# =============================================================================
# HookRunner
# =============================================================================


class HookRunner:
    """
    Executes hooks in the proper order.

    Execution flow:
    1. run_pre_tool_hooks() → validate → execute → run_post_tool_hooks()
    2. Failure → run_post_tool_failure_hooks()
    """

    def __init__(self, registry: HookRegistry):
        self.registry = registry

    async def run_pre_tool_hooks(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        context: HookContext,
    ) -> tuple[dict[str, Any], HookResult | None]:
        """
        Run PreToolUse hooks for a tool.

        Args:
            tool_name: Name of the tool
            tool_input: Input parameters for the tool
            context: Hook execution context

        Returns:
            Tuple of (possibly modified input, permission result or None)
        """
        current_input = tool_input.copy()
        hooks = self.registry.get_pre_hooks(tool_name)

        for hook in hooks:
            # Check for cancellation
            if context.abort_signal and context.abort_signal.is_set():
                logger.debug(f"PreToolUse hooks cancelled for '{tool_name}'")
                break

            try:
                result = await hook.hook_fn(
                    tool_name,
                    context.tool_use_id,
                    current_input,
                    context,
                )

                # Handle blocking
                if result.blocking_error:
                    logger.info(
                        f"PreToolUse hook blocked '{tool_name}': {result.blocking_error}"
                    )
                    return current_input, result

                # Handle input modification
                if result.updated_input is not None:
                    current_input = result.updated_input
                    logger.debug(f"PreToolUse hook modified input for '{tool_name}'")

                # Handle additional context
                if result.additional_contexts:
                    logger.debug(f"PreToolUse hook added context for '{tool_name}'")

                # Handle chain prevention
                if result.prevent_continuation:
                    logger.info(
                        f"PreToolUse hook prevented continuation for '{tool_name}': {result.stop_reason}"
                    )
                    return current_input, HookResult.stop_chain(
                        result.stop_reason or "Execution stopped by hook"
                    )

            except Exception as e:
                logger.error(f"PreToolUse hook error for '{tool_name}': {e}")
                return current_input, HookResult.deny(str(e))

        return current_input, None

    async def run_post_tool_hooks(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_output: Any,
        context: HookContext,
    ) -> Any:
        """
        Run PostToolUse hooks for a tool.

        Args:
            tool_name: Name of the tool
            tool_input: Input parameters used
            tool_output: Output from tool execution
            context: Hook execution context

        Returns:
            Possibly modified output
        """
        current_output = tool_output
        hooks = self.registry.get_post_hooks(tool_name)

        for hook in hooks:
            # Check for cancellation
            if context.abort_signal and context.abort_signal.is_set():
                logger.debug(f"PostToolUse hooks cancelled for '{tool_name}'")
                break

            try:
                result = await hook.hook_fn(
                    tool_name,
                    context.tool_use_id,
                    tool_input,
                    current_output,
                    context,
                )

                # Handle output modification
                if result.updated_output is not None:
                    current_output = result.updated_output
                    logger.debug(f"PostToolUse hook modified output for '{tool_name}'")

                # Handle additional context
                if result.additional_contexts:
                    logger.debug(f"PostToolUse hook added context for '{tool_name}'")

                # Handle chain prevention
                if result.prevent_continuation:
                    logger.info(
                        f"PostToolUse hook prevented continuation for '{tool_name}'"
                    )
                    break

            except Exception as e:
                logger.error(f"PostToolUse hook error for '{tool_name}': {e}")

        return current_output

    async def run_failure_hooks(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        error: str,
        context: HookContext,
    ) -> str:
        """
        Run PostToolUseFailure hooks for a tool.

        Args:
            tool_name: Name of the tool
            tool_input: Input parameters used
            error: Error message from tool execution
            context: Hook execution context

        Returns:
            Possibly modified error message
        """
        current_error = error
        hooks = self.registry.get_failure_hooks(tool_name)

        for hook in hooks:
            # Check for cancellation
            if context.abort_signal and context.abort_signal.is_set():
                logger.debug(f"Failure hooks cancelled for '{tool_name}'")
                break

            try:
                result = await hook.hook_fn(
                    tool_name,
                    context.tool_use_id,
                    tool_input,
                    current_error,
                    context,
                )

                # Handle error modification
                if result.updated_input:
                    # Some hooks may provide corrected input for retry
                    logger.debug(f"Failure hook suggested retry for '{tool_name}'")

                # Handle additional context
                if result.additional_contexts:
                    logger.debug(f"Failure hook added context for '{tool_name}'")

                # Blocking overrides the error
                if result.blocking_error:
                    current_error = result.blocking_error

            except Exception as e:
                logger.error(f"Failure hook error for '{tool_name}': {e}")

        return current_error


# =============================================================================
# Helper Functions
# =============================================================================


def _is_regex_pattern(pattern: str) -> bool:
    """Check if a pattern looks like a regex."""
    # Regex patterns typically contain special chars
    special_chars = {"^", "$", "[", "]", "(", ")", "+", "?", ".", "|"}

    # Check for clear regex indicators
    if pattern.startswith("^") or pattern.endswith("$"):
        return True

    # Count special chars
    special_count = sum(1 for c in pattern if c in special_chars)
    if special_count > 1:
        return True

    return False


# =============================================================================
# Convenience Decorators
# =============================================================================


def pre_tool_hook(tool_pattern: str, priority: int = 0):
    """
    Decorator to register a PreToolUse hook.

    Usage:
        @pre_tool_hook("shell", priority=10)
        async def my_hook(tool_name: str, tool_use_id: str, input: dict, context: HookContext) -> HookResult:
            return HookResult.allow()
    """

    def decorator(fn: PreToolUseHookFn) -> PreToolUseHookFn:
        # This needs to be registered on the registry instance
        # Could return a wrapper that tracks registration state
        return fn

    return decorator


def post_tool_hook(tool_pattern: str, priority: int = 0):
    """Decorator to register a PostToolUse hook."""

    def decorator(fn: PostToolUseHookFn) -> PostToolUseHookFn:
        return fn

    return decorator


def failure_hook(tool_pattern: str, priority: int = 0):
    """Decorator to register a PostToolUseFailure hook."""

    def decorator(fn: PostToolUseFailureHookFn) -> PostToolUseFailureHookFn:
        return fn

    return decorator


# =============================================================================
# Example Hooks
# =============================================================================


async def log_pre_tool_hook(
    tool_name: str,
    tool_use_id: str,
    tool_input: dict[str, Any],
    context: HookContext,
) -> HookResult:
    """Example: Log tool inputs before execution."""
    logger.info(f"PreToolUse: {tool_name}({tool_use_id}) with {tool_input}")
    return HookResult.allow()


async def log_post_tool_hook(
    tool_name: str,
    tool_use_id: str,
    tool_input: dict[str, Any],
    tool_output: Any,
    context: HookContext,
) -> HookResult:
    """Example: Log tool outputs after execution."""
    logger.info(f"PostToolUse: {tool_name}({tool_use_id}) returned {type(tool_output)}")
    return HookResult.allow()


async def log_failure_hook(
    tool_name: str,
    tool_use_id: str,
    tool_input: dict[str, Any],
    error: str,
    context: HookContext,
) -> HookResult:
    """Example: Log tool failures."""
    logger.info(f"Failure: {tool_name}({tool_use_id}) failed: {error}")
    return HookResult.allow()


# =============================================================================
# Export
# =============================================================================


__all__ = [
    # Core classes
    "HookRegistry",
    "HookRunner",
    # Data classes
    "HookResult",
    "HookContext",
    "RegisteredHook",
    # Type aliases
    "PreToolUseHookFn",
    "PostToolUseHookFn",
    "PostToolUseFailureHookFn",
    # Decorators
    "pre_tool_hook",
    "post_tool_hook",
    "failure_hook",
    # Example hooks
    "log_pre_tool_hook",
    "log_post_tool_hook",
    "log_failure_hook",
]
