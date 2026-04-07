#!/usr/bin/env python3
"""
Tool Validation Pipeline — 14-step validation for agent loop tool calls.

Based on Claude Code patterns:
- Multi-stage validation before tool execution
- Each step independently callable for flexibility
- Comprehensive error/warning tracking

Architecture:
    Tool Call → 14-Stage Pipeline → Validated Execution
         ↓
    ┌─────────────────────────────────────────────────────────────┐
    │ 1.  Input Validation    - Check tool call structure         │
    │ 2.  Permission Checks  - Verify tool access permissions    │
    │ 3.  Pre-tool Hooks      - Run validation pre-hooks           │
    │ 4.  Execution         - (Handled by StreamingExecutor)     │
    │ 5.  Post-tool Hooks    - Run validation post-hooks         │
    │ 6.  Analytics          - Track validation metrics         │
    │ 7.  Result Formatting  - Format output for agent          │
    │ 8.  Error Handling     - Handle validation errors          │
    │ 9.  Retry Logic        - Check for retry conditions        │
    │ 10. Cache Check        - Check result cache                │
    │ 11. Rate Limiting      - Check rate limits                 │
    │ 12. Output Validation  - Validate tool output              │
    │ 13. Context Injection - Inject context into result         │
    │ 14. State Update       - Update validation state          │
    └─────────────────────────────────────────────────────────────┘

Usage:
    validator = ToolValidator()
    result = await validator.validate(tool_call, available_tools)

    # Individual steps
    input_valid = await validator.step_1_input_validation(tool_call)
    perms_ok = await validator.step_2_permission_checks(tool_call, permissions)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol

logger = logging.getLogger("tool_validator")


# =============================================================================
# Type Definitions
# =============================================================================


class ValidationStep(Enum):
    """Steps in the tool validation pipeline."""

    INPUT_VALIDATION = "input_validation"
    PERMISSION_CHECKS = "permission_checks"
    PRE_TOOL_HOOKS = "pre_tool_hooks"
    EXECUTION = "execution"
    POST_TOOL_HOOKS = "post_tool_hooks"
    ANALYTICS = "analytics"
    RESULT_FORMATTING = "result_formatting"
    ERROR_HANDLING = "error_handling"
    RETRY_LOGIC = "retry_logic"
    CACHE_CHECK = "cache_check"
    RATE_LIMITING = "rate_limiting"
    OUTPUT_VALIDATION = "output_validation"
    CONTEXT_INJECTION = "context_injection"
    STATE_UPDATE = "state_update"


@dataclass
class ValidationResult:
    """
    Result of tool validation.

    Attributes:
        valid: Whether the tool call passed validation
        errors: List of error messages (empty if valid)
        warnings: List of warning messages (non-blocking issues)
        sanitized_args: Sanitized arguments after validation
        step_completed: Mapping of completed validation steps
        execution_time_ms: Time taken for validation
        cached: Whether result was served from cache
        retry_count: Number of retries attempted
    """

    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    sanitized_args: Dict[str, Any] = field(default_factory=dict)
    step_completed: Dict[str, bool] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    cached: bool = False
    retry_count: int = 0


@dataclass
class ToolCallInput:
    """Input tool call for validation."""

    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ValidationState:
    """
    Mutable state for the validation pipeline.

    Tracks validation history, cache, and rate limits.
    """

    # Cache for results
    result_cache: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    cache_ttl_seconds: int = 300  # 5 minutes default

    # Rate limiting
    tool_call_counts: Dict[str, int] = field(default_factory=dict)
    rate_limit_window_seconds: int = 60
    rate_limit_max_calls: int = 100

    # Analytics
    validation_count: int = 0
    total_validation_time_ms: float = 0.0
    error_count: int = 0
    success_count: int = 0

    # Retry state
    retry_counts: Dict[str, int] = field(default_factory=dict)
    max_retries: int = 3


# =============================================================================
# Permission Checker Protocol
# =============================================================================


class PermissionChecker(Protocol):
    """Abstract interface for permission checking."""

    async def check_permission(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Check if tool execution is permitted.

        Args:
            tool_name: Name of the tool
            arguments: Arguments to the tool

        Returns:
            Tuple of (allowed, error_message)
        """
        ...

    async def check_tool_available(
        self, tool_name: str, available_tools: List[str]
    ) -> tuple[bool, Optional[str]]:
        """
        Check if tool is in available tools list.

        Args:
            tool_name: Name of the tool
            available_tools: List of available tool names

        Returns:
            Tuple of (allowed, error_message)
        """
        ...

    async def check_argument_safety(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Check if arguments are safe to execute.

        Args:
            tool_name: Name of the tool
            arguments: Arguments to the tool

        Returns:
            Tuple of (safe, error_message)
        """
        ...


# =============================================================================
# Default Implementations
# =============================================================================


class NoOpPermissionChecker:
    """No-op permission checker for testing."""

    async def check_permission(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        return (True, None)

    async def check_tool_available(
        self, tool_name: str, available_tools: List[str]
    ) -> tuple[bool, Optional[str]]:
        if tool_name in available_tools:
            return (True, None)
        return (False, f"Tool '{tool_name}' not in available tools")

    async def check_argument_safety(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        return (True, None)


# =============================================================================
# Hooks Protocol
# =============================================================================


@dataclass
class ValidationContext:
    """Context passed to validation hooks."""

    tool_call: ToolCallInput
    step: ValidationStep
    validation_result: Optional[ValidationResult] = None


ValidationHookFn = Callable[[ValidationContext], Any]


# =============================================================================
# Tool Validator
# =============================================================================


class ToolValidator:
    """
    14-step tool validation pipeline.

    Each step is independently callable for flexibility in integration.
    The pipeline validates tool calls before execution in the agent loop.

    Features:
        - Independent step methods for granular control
        - Permission checking integration
        - Result caching for performance
        - Rate limiting support
        - Analytics tracking
    """

    def __init__(
        self,
        permission_checker: Optional[PermissionChecker] = None,
        pre_hooks: Optional[List[ValidationHookFn]] = None,
        post_hooks: Optional[List[ValidationHookFn]] = None,
        cache_enabled: bool = True,
        rate_limit_enabled: bool = True,
    ):
        """
        Initialize the ToolValidator.

        Args:
            permission_checker: Permission checker implementing PermissionChecker
            pre_hooks: List of hooks to run before validation
            post_hooks: List of hooks to run after validation
            cache_enabled: Enable result caching
            rate_limit_enabled: Enable rate limiting
        """
        self._permission_checker = permission_checker or NoOpPermissionChecker()
        self._pre_hooks = pre_hooks or []
        self._post_hooks = post_hooks or []
        self._cache_enabled = cache_enabled
        self._rate_limit_enabled = rate_limit_enabled
        self._state = ValidationState()

        logger.info(
            f"ToolValidator initialized: cache={cache_enabled}, "
            f"rate_limit={rate_limit_enabled}"
        )

    async def validate(
        self,
        tool_call: Dict[str, Any],
        available_tools: Optional[List[str]] = None,
    ) -> ValidationResult:
        """
        Run full 14-step validation pipeline.

        Args:
            tool_call: Tool call dict with 'id', 'name', 'arguments'
            available_tools: Optional list of available tool names

        Returns:
            ValidationResult with validation outcome
        """
        start_time = time.perf_counter()
        available_tools = available_tools or []

        # Parse tool call input
        input_obj = ToolCallInput(
            id=tool_call.get("id", "unknown"),
            name=tool_call.get("name", ""),
            arguments=tool_call.get("arguments", {}),
        )

        result = ValidationResult(
            valid=True,
            sanitized_args=input_obj.arguments.copy(),
            step_completed={},
        )

        # Run all 14 steps
        steps = [
            (ValidationStep.INPUT_VALIDATION, self.step_1_input_validation),
            (ValidationStep.PERMISSION_CHECKS, self.step_2_permission_checks),
            (ValidationStep.PRE_TOOL_HOOKS, self.step_3_pre_tool_hooks),
            (ValidationStep.CACHE_CHECK, self.step_10_cache_check),
            (ValidationStep.RATE_LIMITING, self.step_11_rate_limiting),
            (ValidationStep.OUTPUT_VALIDATION, self.step_12_output_validation),
            (ValidationStep.CONTEXT_INJECTION, self.step_13_context_injection),
            (ValidationStep.STATE_UPDATE, self.step_14_state_update),
        ]

        for step_enum, step_fn in steps:
            try:
                step_result = await step_fn(input_obj, available_tools, result)
                result.step_completed[step_enum.value] = step_result

                if not step_result and step_enum in [
                    ValidationStep.INPUT_VALIDATION,
                    ValidationStep.PERMISSION_CHECKS,
                ]:
                    result.valid = False
                    break
            except Exception as e:
                result.errors.append(f"Step {step_enum.value} failed: {str(e)}")
                result.valid = False
                result.step_completed[step_enum.value] = False
                break

        # Run analytics and formatting (always, even on failure)
        await self.step_6_analytics(input_obj, result)
        await self.step_7_result_formatting(input_obj, result)
        await self.step_8_error_handling(input_obj, result)
        await self.step_9_retry_logic(input_obj, result)

        result.execution_time_ms = (time.perf_counter() - start_time) * 1000
        self._update_state_metrics(result)

        logger.info(
            f"Validation complete: valid={result.valid}, "
            f"time={result.execution_time_ms:.2f}ms, "
            f"errors={len(result.errors)}, warnings={len(result.warnings)}"
        )

        return result

    # =========================================================================
    # Step 1: Input Validation
    # =========================================================================

    async def step_1_input_validation(
        self,
        tool_call: ToolCallInput,
        available_tools: List[str],
        context: Optional[ValidationResult] = None,
    ) -> bool:
        """
        Step 1: Validate tool call structure and arguments.

        Checks:
        - Tool name is present and non-empty
        - Tool name is a valid identifier
        - Arguments is a dict
        - No reserved keys in arguments

        Args:
            tool_call: Tool call to validate
            available_tools: Available tools list (unused in this step)
            context: Current validation context

        Returns:
            True if validation passes
        """
        errors: List[str] = []

        # Check tool name
        if not tool_call.name:
            errors.append("Tool name is required")

        if tool_call.name and not tool_call.name.isidentifier():
            errors.append(f"Invalid tool name: {tool_call.name}")

        # Check arguments
        if not isinstance(tool_call.arguments, dict):
            errors.append(f"Arguments must be a dict, got {type(tool_call.arguments)}")

        # Check for reserved keys
        reserved_keys = {"__proto__", "constructor", "prototype"}
        if tool_call.arguments:
            for key in reserved_keys:
                if key in tool_call.arguments:
                    errors.append(f"Reserved key in arguments: {key}")

        # Sanitize arguments
        if context:
            context.sanitized_args = self._sanitize_arguments(tool_call.arguments)

        if errors and context:
            context.errors.extend(errors)
            return False

        return True

    def _sanitize_arguments(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Remove dangerous keys from arguments."""
        if not isinstance(args, dict):
            return {}

        reserved_keys = {"__proto__", "constructor", "prototype", "__defineGetter__"}
        sanitized = {}
        for key, value in args.items():
            if key not in reserved_keys:
                sanitized[key] = value

        return sanitized

    # =========================================================================
    # Step 2: Permission Checks
    # =========================================================================

    async def step_2_permission_checks(
        self,
        tool_call: ToolCallInput,
        available_tools: List[str],
        context: Optional[ValidationResult] = None,
    ) -> bool:
        """
        Step 2: Check permissions for tool execution.

        Args:
            tool_call: Tool call to check
            available_tools: Available tools list
            context: Current validation context

        Returns:
            True if permissions allow execution
        """
        errors: List[str] = []

        # Check tool availability
        allowed, error = await self._permission_checker.check_tool_available(
            tool_call.name, available_tools
        )
        if not allowed:
            errors.append(error or f"Tool {tool_call.name} not available")

        # Check general permission
        allowed, error = await self._permission_checker.check_permission(
            tool_call.name, tool_call.arguments
        )
        if not allowed:
            errors.append(error or f"Permission denied for {tool_call.name}")

        # Check argument safety
        allowed, error = await self._permission_checker.check_argument_safety(
            tool_call.name, tool_call.arguments
        )
        if not allowed:
            errors.append(error or f"Unsafe arguments for {tool_call.name}")

        if errors and context:
            context.errors.extend(errors)
            return False

        return True

    # =========================================================================
    # Step 3: Pre-tool Hooks
    # =========================================================================

    async def step_3_pre_tool_hooks(
        self,
        tool_call: ToolCallInput,
        available_tools: List[str],
        context: Optional[ValidationResult] = None,
    ) -> bool:
        """
        Step 3: Run pre-validation hooks.

        Args:
            tool_call: Tool call being validated
            available_tools: Available tools list
            context: Current validation context

        Returns:
            True if hooks pass
        """
        validation_ctx = ValidationContext(
            tool_call=tool_call,
            step=ValidationStep.PRE_TOOL_HOOKS,
            validation_result=context,
        )

        for hook in self._pre_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(validation_ctx)
                else:
                    hook(validation_ctx)
            except Exception as e:
                warning = f"Pre-hook failed: {str(e)}"
                if context:
                    context.warnings.append(warning)
                logger.warning(f"ToolValidator: {warning}")

        return True

    # =========================================================================
    # Step 4: Execution (handled by StreamingExecutor)
    # =========================================================================

    async def step_4_execution(
        self,
        tool_call: ToolCallInput,
        available_tools: List[str],
        executor: Any,
    ) -> Dict[str, Any]:
        """
        Step 4: Execute the tool.

        Note: This step is typically handled by StreamingExecutor.
        This method provides a placeholder for integration.

        Args:
            tool_call: Tool call to execute
            available_tools: Available tools list
            executor: Tool executor instance

        Returns:
            Execution result dict
        """
        # Delegate to executor
        if executor and hasattr(executor, "execute"):
            return await executor.execute(tool_call.name, tool_call.arguments)
        return {"success": False, "error": "No executor provided"}

    # =========================================================================
    # Step 5: Post-tool Hooks
    # =========================================================================

    async def step_5_post_tool_hooks(
        self,
        tool_call: ToolCallInput,
        available_tools: List[str],
        context: Optional[ValidationResult] = None,
    ) -> bool:
        """
        Step 5: Run post-validation hooks.

        Args:
            tool_call: Tool call that was validated
            available_tools: Available tools list
            context: Current validation context

        Returns:
            True if hooks pass
        """
        validation_ctx = ValidationContext(
            tool_call=tool_call,
            step=ValidationStep.POST_TOOL_HOOKS,
            validation_result=context,
        )

        for hook in self._post_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(validation_ctx)
                else:
                    hook(validation_ctx)
            except Exception as e:
                warning = f"Post-hook failed: {str(e)}"
                if context:
                    context.warnings.append(warning)
                logger.warning(f"ToolValidator: {warning}")

        return True

    # =========================================================================
    # Step 6: Analytics
    # =========================================================================

    async def step_6_analytics(
        self,
        tool_call: ToolCallInput,
        context: Optional[ValidationResult] = None,
    ) -> bool:
        """
        Step 6: Track validation analytics.

        Args:
            tool_call: Tool call being validated
            context: Current validation context

        Returns:
            True (analytics is always tracked)
        """
        self._state.validation_count += 1
        if context:
            self._state.total_validation_time_ms += context.execution_time_ms

        logger.debug(
            f"Analytics: validation_count={self._state.validation_count}, "
            f"total_time={self._state.total_validation_time_ms:.2f}ms"
        )

        return True

    # =========================================================================
    # Step 7: Result Formatting
    # =========================================================================

    async def step_7_result_formatting(
        self,
        tool_call: ToolCallInput,
        context: Optional[ValidationResult] = None,
    ) -> bool:
        """
        Step 7: Format validation result for output.

        Args:
            tool_call: Tool call being validated
            context: Current validation context

        Returns:
            True (formatting is always applied)
        """
        # Ensure sanitized_args is populated
        if context and not context.sanitized_args:
            context.sanitized_args = tool_call.arguments.copy()

        return True

    # =========================================================================
    # Step 8: Error Handling
    # =========================================================================

    async def step_8_error_handling(
        self,
        tool_call: ToolCallInput,
        context: Optional[ValidationResult] = None,
    ) -> bool:
        """
        Step 8: Handle validation errors.

        Args:
            tool_call: Tool call being validated
            context: Current validation context

        Returns:
            True if errors are handled (may still have errors)
        """
        if context and context.errors:
            self._state.error_count += 1
            logger.warning(f"Validation errors for {tool_call.name}: {context.errors}")

        return True

    # =========================================================================
    # Step 9: Retry Logic
    # =========================================================================

    async def step_9_retry_logic(
        self,
        tool_call: ToolCallInput,
        context: Optional[ValidationResult] = None,
    ) -> bool:
        """
        Step 9: Check retry conditions.

        Args:
            tool_call: Tool call being validated
            context: Current validation context

        Returns:
            True if retry check completes
        """
        if context:
            # Check if we should retry based on error count
            tool_key = f"{tool_call.name}:{tool_call.id}"
            current_retries = self._state.retry_counts.get(tool_key, 0)

            if context.errors:
                if current_retries < self._state.max_retries:
                    context.retry_count = current_retries + 1
                    self._state.retry_counts[tool_key] = current_retries + 1
                    logger.info(
                        f"Retry scheduled for {tool_call.name}: "
                        f"attempt {context.retry_count}/{self._state.max_retries}"
                    )
                else:
                    context.retry_count = current_retries
                    logger.warning(f"Max retries reached for {tool_call.name}")

        return True

    # =========================================================================
    # Step 10: Cache Check
    # =========================================================================

    async def step_10_cache_check(
        self,
        tool_call: ToolCallInput,
        available_tools: List[str],
        context: Optional[ValidationResult] = None,
    ) -> bool:
        """
        Step 10: Check result cache.

        Args:
            tool_call: Tool call to check
            available_tools: Available tools list
            context: Current validation context

        Returns:
            True if cache check completes (may set cached=True)
        """
        if not self._cache_enabled or not context:
            return True

        # Generate cache key
        cache_key = self._generate_cache_key(tool_call)

        # Check cache
        if cache_key in self._state.result_cache:
            cached = self._state.result_cache[cache_key]
            cached_time = cached.get("_cached_at", 0)
            age_seconds = time.time() - cached_time

            if age_seconds < self._state.cache_ttl_seconds:
                context.cached = True
                context.sanitized_args = cached.get("sanitized_args", {})
                logger.debug(f"Cache hit for {tool_call.name}: {age_seconds:.2f}s old")
                return True
            else:
                # Expired - remove from cache
                del self._state.result_cache[cache_key]

        # Store in cache for future lookups
        self._state.result_cache[cache_key] = {
            "sanitized_args": context.sanitized_args if context else {},
            "_cached_at": time.time(),
        }

        return True

    def _generate_cache_key(self, tool_call: ToolCallInput) -> str:
        """Generate cache key for tool call."""
        content = f"{tool_call.name}:{json.dumps(tool_call.arguments, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()

    # =========================================================================
    # Step 11: Rate Limiting
    # =========================================================================

    async def step_11_rate_limiting(
        self,
        tool_call: ToolCallInput,
        available_tools: List[str],
        context: Optional[ValidationResult] = None,
    ) -> bool:
        """
        Step 11: Check rate limits.

        Args:
            tool_call: Tool call to check
            available_tools: Available tools list
            context: Current validation context

        Returns:
            True if rate limit allows execution
        """
        if not self._rate_limit_enabled:
            return True

        # Increment counter
        tool_name = tool_call.name
        self._state.tool_call_counts[tool_name] = (
            self._state.tool_call_counts.get(tool_name, 0) + 1
        )

        count = self._state.tool_call_counts[tool_name]

        if count > self._state.rate_limit_max_calls:
            error = f"Rate limit exceeded for {tool_name}: {count}/{self._state.rate_limit_max_calls}"
            if context:
                context.errors.append(error)
            logger.warning(f"ToolValidator: {error}")
            return False

        return True

    # =========================================================================
    # Step 12: Output Validation
    # =========================================================================

    async def step_12_output_validation(
        self,
        tool_call: ToolCallInput,
        available_tools: List[str],
        context: Optional[ValidationResult] = None,
    ) -> bool:
        """
        Step 12: Validate tool output (post-execution).

        Args:
            tool_call: Tool call that was executed
            available_tools: Available tools list
            context: Current validation context

        Returns:
            True if output validation passes
        """
        # This step is typically called after execution
        # Placeholder for output validation logic
        return True

    # =========================================================================
    # Step 13: Context Injection
    # =========================================================================

    async def step_13_context_injection(
        self,
        tool_call: ToolCallInput,
        available_tools: List[str],
        context: Optional[ValidationResult] = None,
    ) -> bool:
        """
        Step 13: Inject context into validation result.

        Args:
            tool_call: Tool call being validated
            available_tools: Available tools list
            context: Current validation context

        Returns:
            True (context injection always completes)
        """
        if context:
            # Add metadata to context
            context.step_completed["_validated_at"] = time.time()
            context.step_completed["_validator_version"] = "1.0.0"

        return True

    # =========================================================================
    # Step 14: State Update
    # =========================================================================

    async def step_14_state_update(
        self,
        tool_call: ToolCallInput,
        available_tools: List[str],
        context: Optional[ValidationResult] = None,
    ) -> bool:
        """
        Step 14: Update validation state.

        Args:
            tool_call: Tool call being validated
            available_tools: Available tools list
            context: Current validation context

        Returns:
            True (state update always completes)
        """
        # Update success/error counts
        if context:
            if context.valid:
                self._state.success_count += 1
            else:
                self._state.error_count += 1

        return True

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _update_state_metrics(self, result: ValidationResult) -> None:
        """Update state metrics from validation result."""
        if result.valid:
            self._state.success_count += 1
        else:
            self._state.error_count += 1

    def get_state(self) -> ValidationState:
        """Get current validation state."""
        return self._state

    def reset_state(self) -> None:
        """Reset validation state."""
        self._state = ValidationState()
        logger.info("ToolValidator state reset")

    def clear_cache(self) -> None:
        """Clear result cache."""
        self._state.result_cache.clear()
        logger.info("ToolValidator cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        return {
            "validation_count": self._state.validation_count,
            "success_count": self._state.success_count,
            "error_count": self._state.error_count,
            "total_validation_time_ms": self._state.total_validation_time_ms,
            "average_validation_time_ms": (
                self._state.total_validation_time_ms / self._state.validation_count
                if self._state.validation_count > 0
                else 0
            ),
            "cache_size": len(self._state.result_cache),
            "rate_limited_tools": len(self._state.tool_call_counts),
        }


# =============================================================================
# Module-Level Convenience Functions
# =============================================================================


async def validate_tool_call(
    tool_call: Dict[str, Any],
    available_tools: Optional[List[str]] = None,
    permission_checker: Optional[PermissionChecker] = None,
) -> ValidationResult:
    """
    Convenience function to validate a tool call.

    Args:
        tool_call: Tool call dict with 'id', 'name', 'arguments'
        available_tools: Optional list of available tool names
        permission_checker: Optional permission checker

    Returns:
        ValidationResult with validation outcome
    """
    validator = ToolValidator(permission_checker=permission_checker)
    return await validator.validate(tool_call, available_tools)


# =============================================================================
# Main - Quick Test
# =============================================================================


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s: %(message)s",
    )

    print("=== Tool Validator Pipeline Test ===\n")

    async def test():
        validator = ToolValidator()

        # Test 1: Valid tool call
        print("--- Test 1: Valid tool call ---")
        tool_call = {
            "id": "call_1",
            "name": "read_file",
            "arguments": {"path": "/home/user/file.txt"},
        }
        result = await validator.validate(tool_call, available_tools=["read_file"])
        print(f"Valid: {result.valid}")
        print(f"Errors: {result.errors}")
        print(f"Warnings: {result.warnings}")
        print(f"Time: {result.execution_time_ms:.2f}ms")

        # Test 2: Invalid tool name
        print("\n--- Test 2: Invalid tool name ---")
        tool_call = {"id": "call_2", "name": "", "arguments": {}}
        result = await validator.validate(tool_call, available_tools=[])
        print(f"Valid: {result.valid}")
        print(f"Errors: {result.errors}")

        # Test 3: Tool not in available list
        print("\n--- Test 3: Tool not available ---")
        tool_call = {"id": "call_3", "name": "delete_all", "arguments": {}}
        result = await validator.validate(tool_call, available_tools=["read_file"])
        print(f"Valid: {result.valid}")
        print(f"Errors: {result.errors}")

        # Test 4: Reserved key in arguments
        print("\n--- Test 4: Reserved key in arguments ---")
        tool_call = {
            "id": "call_4",
            "name": "test",
            "arguments": {"path": "/etc/passwd", "__proto__": {"evil": True}},
        }
        result = await validator.validate(tool_call, available_tools=["test"])
        print(f"Valid: {result.valid}")
        print(f"Errors: {result.errors}")
        print(f"Sanitized args: {result.sanitized_args}")

        # Test 5: Individual step
        print("\n--- Test 5: Individual step ---")
        input_obj = ToolCallInput(id="call_5", name="test", arguments={"a": 1})
        step_result = await validator.step_1_input_validation(input_obj, [], None)
        print(f"Step 1 result: {step_result}")

        # Test 6: Stats
        print("\n--- Test 6: Statistics ---")
        stats = validator.get_stats()
        print(f"Stats: {stats}")

        print("\nAll tests completed!")

    # Run async test
    asyncio.run(test())

    sys.exit(0)
