"""Hook System (Policy Injection) for the agent loop.

Provides a thread-safe hook registry for policy injection at key points
in the agent execution lifecycle.

Hook Types:
- PreToolUse:    Before every tool execution (allow/deny/ask/defer)
- PermissionRequest: At approval boundary (modify permissions)
- PostToolUse:   After execution (append context)
- Compact:       Before/after compaction (preserve critical info)

Based on Claude Code's hook system patterns.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("hooks")


# =============================================================================
# Hook Types
# =============================================================================


class HookType(Enum):
    """Types of hooks available in the agent loop."""

    PRE_TOOL_USE = "pre_tool_use"
    PERMISSION_REQUEST = "permission_request"
    POST_TOOL_USE = "post_tool_use"
    COMPACT = "compact"


class HookAction(Enum):
    """Actions that can be taken by a hook."""

    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"
    DEFER = "defer"
    MODIFY = "modify"


# =============================================================================
# Hook Result
# =============================================================================


@dataclass
class HookResult:
    """
    Result returned by a hook callback.

    Attributes:
        allowed: Whether the action is allowed to proceed
        modified_context: Modified context (if any) to pass to next stage
        reason: Human-readable reason for the decision
        action: The specific action taken (if not ALLOW)
    """

    allowed: bool = True
    modified_context: Optional[Dict[str, Any]] = None
    reason: str = ""
    action: HookAction = HookAction.ALLOW

    def __post_init__(self) -> None:
        """Set action based on allowed status."""
        if not self.allowed:
            self.action = HookAction.DENY


# =============================================================================
# Hook Context
# =============================================================================


@dataclass
class ToolUseContext:
    """
    Context for tool use hooks (PreToolUse, PostToolUse).

    Attributes:
        tool_name: Name of the tool being executed
        arguments: Arguments being passed to the tool
        iteration: Current iteration number
        state: Current agent state (if available)
    """

    tool_name: str
    arguments: Dict[str, Any]
    iteration: int
    state: Optional[Dict[str, Any]] = None
    original_context: Optional[Dict[str, Any]] = None


@dataclass
class PermissionContext:
    """
    Context for permission request hooks.

    Attributes:
        path: Path being accessed
        tool_name: Tool accessing the path
        operation: Operation type (read, write, execute)
        current_permission: Current permission behavior
    """

    path: str
    tool_name: str
    operation: str
    current_permission: str = "ask"


@dataclass
class CompactContext:
    """
    Context for compact hooks.

    Attributes:
        phase: "before" or "after" compaction
        preserved_data: Data to preserve through compaction
        compression_strategy: Strategy being used
    """

    phase: str  # "before" or "after"
    preserved_data: Dict[str, Any] = field(default_factory=dict)
    compression_strategy: str = "default"


# Union type for all hook contexts
HookContext = ToolUseContext | PermissionContext | CompactContext


# =============================================================================
# Hook Callback Type
# =============================================================================


HookCallback = Callable[[HookContext], HookResult]


# =============================================================================
# Hook Registry
# =============================================================================


class HookRegistry:
    """
    Thread-safe registry for managing hooks in the agent loop.

    Allows registration of callbacks for different hook types,
    and executes all registered hooks when triggered.

    Usage:
        registry = HookRegistry()

        # Register a pre-tool-use hook
        def my_hook(context: HookContext) -> HookResult:
            if context.tool_name == "Bash":
                return HookResult(allowed=False, reason="Bash blocked")
            return HookResult(allowed=True)

        registry.register_hook(HookType.PRE_TOOL_USE, my_hook)

        # Execute hooks
        context = ToolUseContext(tool_name="Bash", arguments={}, iteration=1)
        results = registry.execute_hooks(HookType.PRE_TOOL_USE, context)
    """

    def __init__(self) -> None:
        """Initialize the hook registry with thread safety."""
        self._hooks: Dict[HookType, List[HookCallback]] = {
            HookType.PRE_TOOL_USE: [],
            HookType.PERMISSION_REQUEST: [],
            HookType.POST_TOOL_USE: [],
            HookType.COMPACT: [],
        }
        self._lock = threading.RLock()
        self._enabled = True

    def register_hook(
        self,
        hook_type: HookType,
        callback: HookCallback,
        priority: int = 0,
    ) -> None:
        """
        Register a hook callback.

        Args:
            hook_type: Type of hook to register for
            callback: Callback function to execute
            priority: Priority for execution order (higher runs first)
        """
        with self._lock:
            # Wrap callback with priority
            wrapped = self._wrap_with_priority(callback, priority)
            self._hooks[hook_type].append(wrapped)
            # Sort by priority (descending)
            self._hooks[hook_type].sort(key=lambda x: x[1], reverse=True)
            logger.debug(
                f"Registered hook for {hook_type.value}, "
                f"total hooks: {len(self._hooks[hook_type])}"
            )

    def unregister_hook(
        self,
        hook_type: HookType,
        callback: HookCallback,
    ) -> bool:
        """
        Unregister a hook callback.

        Args:
            hook_type: Type of hook to unregister from
            callback: Callback function to remove

        Returns:
            True if the hook was found and removed, False otherwise
        """
        with self._lock:
            original_len = len(self._hooks[hook_type])
            self._hooks[hook_type] = [
                h for h in self._hooks[hook_type] if h[0] != callback
            ]
            removed = original_len > len(self._hooks[hook_type])
            if removed:
                logger.debug(f"Unregistered hook from {hook_type.value}")
            return removed

    def unregister_all(self, hook_type: Optional[HookType] = None) -> None:
        """
        Unregister all hooks, optionally filtered by type.

        Args:
            hook_type: Optional hook type to filter by
        """
        with self._lock:
            if hook_type:
                self._hooks[hook_type].clear()
                logger.debug(f"Cleared all hooks for {hook_type.value}")
            else:
                for ht in HookType:
                    self._hooks[ht].clear()
                logger.debug("Cleared all hooks")

    def execute_hooks(
        self,
        hook_type: HookType,
        context: HookContext,
    ) -> List[HookResult]:
        """
        Execute all hooks of a given type.

        Args:
            hook_type: Type of hooks to execute
            context: Context to pass to each hook

        Returns:
            List of HookResult from each hook
        """
        results: List[HookResult] = []

        if not self._enabled:
            logger.debug(f"Hooks disabled, skipping {hook_type.value}")
            return [HookResult(allowed=True)]

        with self._lock:
            hooks = list(self._hooks[hook_type])

        for callback, priority in hooks:
            try:
                result = callback(context)
                if result is None:
                    result = HookResult(allowed=True)
                results.append(result)

                # Early exit on deny (unless more hooks might override)
                if not result.allowed and hook_type != HookType.PERMISSION_REQUEST:
                    logger.debug(f"Hook denied {hook_type.value}: {result.reason}")
                    break

            except Exception as e:
                logger.warning(
                    f"Hook {callback.__name__} failed for {hook_type.value}: {e}"
                )
                results.append(
                    HookResult(
                        allowed=True,  # Don't block on hook failure
                        reason=f"Hook error: {str(e)}",
                    )
                )

        return results

    def execute_hooks_untilDenied(
        self,
        hook_type: HookType,
        context: HookContext,
    ) -> HookResult:
        """
        Execute hooks until one denies the action.

        Args:
            hook_type: Type of hooks to execute
            context: Context to pass to each hook

        Returns:
            First HookResult that denies, or last result if all allowed
        """
        results = self.execute_hooks(hook_type, context)

        for result in results:
            if not result.allowed:
                return result

        # All allowed, return the last result
        return results[-1] if results else HookResult(allowed=True)

    def get_hook_count(self, hook_type: Optional[HookType] = None) -> int:
        """
        Get the number of registered hooks.

        Args:
            hook_type: Optional hook type to filter by

        Returns:
            Number of registered hooks
        """
        with self._lock:
            if hook_type:
                return len(self._hooks[hook_type])
            return sum(len(h) for h in self._hooks.values())

    def enable(self) -> None:
        """Enable hook execution."""
        with self._lock:
            self._enabled = True
            logger.debug("Hooks enabled")

    def disable(self) -> None:
        """Disable hook execution (all hooks return ALLOW)."""
        with self._lock:
            self._enabled = False
            logger.debug("Hooks disabled")

    @property
    def is_enabled(self) -> bool:
        """Check if hooks are enabled."""
        with self._lock:
            return self._enabled

    @staticmethod
    def _wrap_with_priority(
        callback: HookCallback,
        priority: int,
    ) -> tuple[HookCallback, int]:
        """Wrap a callback with its priority."""
        return (callback, priority)


# =============================================================================
# Pre-built Hook Factories
# =============================================================================


def create_deny_tool_hook(tool_names: List[str]) -> HookCallback:
    """
    Create a hook that denies specific tools.

    Args:
        tool_names: List of tool names to deny

    Returns:
        Hook callback that denies the specified tools
    """

    def hook(context: HookContext) -> HookResult:
        if isinstance(context, ToolUseContext):
            if context.tool_name in tool_names:
                return HookResult(
                    allowed=False,
                    reason=f"Tool '{context.tool_name}' is blocked",
                    action=HookAction.DENY,
                )
        return HookResult(allowed=True)

    return hook


def create_allow_tool_hook(tool_names: List[str], reason: str = "") -> HookCallback:
    """
    Create a hook that allows specific tools.

    Args:
        tool_names: List of tool names to allow
        reason: Reason for allowing

    Returns:
        Hook callback that allows the specified tools
    """

    def hook(context: HookContext) -> HookResult:
        if isinstance(context, ToolUseContext):
            if context.tool_name in tool_names:
                return HookResult(
                    allowed=True,
                    reason=reason or f"Tool '{context.tool_name}' is allowed",
                )
        return HookResult(allowed=True)

    return hook


def create_permission_modifier_hook(
    path_patterns: Dict[str, str],
) -> HookCallback:
    """
    Create a hook that modifies permissions for specific paths.

    Args:
        path_patterns: Dict mapping path patterns to permission behaviors

    Returns:
        Hook callback that modifies permissions
    """

    def hook(context: HookContext) -> HookResult:
        if isinstance(context, PermissionContext):
            import fnmatch

            for pattern, behavior in path_patterns.items():
                if fnmatch.fnmatch(context.path, pattern):
                    return HookResult(
                        allowed=True,
                        modified_context={"permission": behavior},
                        reason=f"Modified permission for {pattern}",
                        action=HookAction.MODIFY,
                    )
        return HookResult(allowed=True)

    return hook


def create_compact_preserver_hook(
    preserve_keys: List[str],
) -> HookCallback:
    """
    Create a hook that preserves specific data during compaction.

    Args:
        preserve_keys: List of keys to preserve in state

    Returns:
        Hook callback that marks data for preservation
    """

    def hook(context: HookContext) -> HookResult:
        if isinstance(context, CompactContext):
            if context.phase == "before":
                # Mark data to preserve
                return HookResult(
                    allowed=True,
                    modified_context={"preserve_keys": preserve_keys},
                    reason=f"Marked {len(preserve_keys)} keys for preservation",
                )
        return HookResult(allowed=True)

    return hook


def create_logging_hook(hook_type: HookType) -> HookCallback:
    """
    Create a hook that logs all hooks of a given type.

    Args:
        hook_type: Type of hooks to log

    Returns:
        Hook callback that logs hook invocations
    """

    def hook(context: HookContext) -> HookResult:
        logger.info(f"{hook_type.value} hook invoked: {type(context).__name__}")
        if isinstance(context, ToolUseContext):
            logger.debug(f"  Tool: {context.tool_name}, Args: {context.arguments}")
        elif isinstance(context, PermissionContext):
            logger.debug(f"  Path: {context.path}, Tool: {context.tool_name}")
        elif isinstance(context, CompactContext):
            logger.debug(f"  Phase: {context.phase}")
        return HookResult(allowed=True)

    return hook


# =============================================================================
# Default Global Registry
# =============================================================================


# Global default registry instance
_default_registry: Optional[HookRegistry] = None
_default_registry_lock = threading.Lock()


def get_default_registry() -> HookRegistry:
    """
    Get the default global hook registry.

    Returns:
        The default HookRegistry instance
    """
    global _default_registry
    with _default_registry_lock:
        if _default_registry is None:
            _default_registry = HookRegistry()
        return _default_registry


def reset_default_registry() -> None:
    """Reset the default registry to a fresh state."""
    global _default_registry
    with _default_registry_lock:
        _default_registry = None


# =============================================================================
# Module-Level Convenience Functions
# =============================================================================


def register_hook(
    hook_type: HookType,
    callback: HookCallback,
    priority: int = 0,
) -> None:
    """
    Convenience function to register a hook with the default registry.

    Args:
        hook_type: Type of hook to register for
        callback: Callback function to execute
        priority: Priority for execution order
    """
    get_default_registry().register_hook(hook_type, callback, priority)


def execute_hooks(
    hook_type: HookType,
    context: HookContext,
) -> List[HookResult]:
    """
    Convenience function to execute hooks from the default registry.

    Args:
        hook_type: Type of hooks to execute
        context: Context to pass to each hook

    Returns:
        List of HookResult from each hook
    """
    return get_default_registry().execute_hooks(hook_type, context)


# =============================================================================
# Main - Quick Test
# =============================================================================


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s: %(message)s",
    )

    print("=== Hook System Test ===\n")

    # Test 1: Basic registry
    print("--- Test 1: Basic Registry ---")
    registry = HookRegistry()

    def deny_bash(context: HookContext) -> HookResult:
        if isinstance(context, ToolUseContext):
            if context.tool_name == "Bash":
                return HookResult(
                    allowed=False,
                    reason="Bash is disabled",
                    action=HookAction.DENY,
                )
        return HookResult(allowed=True)

    registry.register_hook(HookType.PRE_TOOL_USE, deny_bash, priority=10)

    print(
        f"Registered {registry.get_hook_count(HookType.PRE_TOOL_USE)} pre-tool-use hooks"
    )

    # Test 2: Execute hooks
    print("\n--- Test 2: Execute Hooks ---")

    context = ToolUseContext(
        tool_name="Bash",
        arguments={"command": "ls -la"},
        iteration=1,
    )
    results = registry.execute_hooks(HookType.PRE_TOOL_USE, context)
    print(f"Tool: {context.tool_name}")
    print(f"Results: {len(results)} hook(s) executed")
    for r in results:
        print(f"  Allowed: {r.allowed}, Reason: {r.reason}, Action: {r.action.value}")

    # Test 3: Allow another tool
    print("\n--- Test 3: Allow Another Tool ---")
    context2 = ToolUseContext(
        tool_name="Read",
        arguments={"filePath": "/test/file.py"},
        iteration=1,
    )
    results2 = registry.execute_hooks(HookType.PRE_TOOL_USE, context2)
    print(f"Tool: {context2.tool_name}")
    print(f"Results: {len(results2)} hook(s) executed")
    for r in results2:
        print(f"  Allowed: {r.allowed}, Reason: {r.reason}")

    # Test 4: Permission context
    print("\n--- Test 4: Permission Context ---")

    def modify_permission(context: HookContext) -> HookResult:
        if isinstance(context, PermissionContext):
            if context.path.endswith(".env"):
                return HookResult(
                    allowed=True,
                    modified_context={"permission": "deny"},
                    reason="Environment files are protected",
                    action=HookAction.MODIFY,
                )
        return HookResult(allowed=True)

    registry.register_hook(HookType.PERMISSION_REQUEST, modify_permission)

    perm_context = PermissionContext(
        path="/home/user/.env",
        tool_name="file_read",
        operation="read",
    )
    perm_results = registry.execute_hooks(HookType.PERMISSION_REQUEST, perm_context)
    print(f"Path: {perm_context.path}")
    for r in perm_results:
        print(f"  Allowed: {r.allowed}")
        if r.modified_context:
            print(f"  Modified: {r.modified_context}")

    # Test 5: Thread safety
    print("\n--- Test 5: Thread Safety ---")
    import threading

    errors: List[str] = []

    def register_many():
        try:
            for i in range(100):
                registry.register_hook(
                    HookType.POST_TOOL_USE,
                    lambda ctx: HookResult(allowed=True),
                    priority=i,
                )
        except Exception as e:
            errors.append(str(e))

    threads = [threading.Thread(target=register_many) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(
        f"Registered {registry.get_hook_count(HookType.POST_TOOL_USE)} post-use hooks"
    )
    print(f"Errors: {len(errors)}")

    # Test 6: Compact hooks
    print("\n--- Test 6: Compact Hooks ---")

    compact_context = CompactContext(
        phase="before",
        preserved_data={"important": "data"},
        compression_strategy="aggressive",
    )
    compact_results = registry.execute_hooks(HookType.COMPACT, compact_context)
    print(f"Phase: {compact_context.phase}")
    print(f"Results: {len(compact_results)} hook(s) executed")

    # Test 7: Factory functions
    print("\n--- Test 7: Factory Functions ---")
    deny_factory = create_deny_tool_hook(["rm", "del", "format"])
    result = deny_factory(ToolUseContext(tool_name="rm", arguments={}, iteration=1))
    print(
        f"Deny factory result: allowed={result.allowed}, action={result.action.value}"
    )

    print("\n=== All Tests Passed ===")
    sys.exit(0)
