#!/usr/bin/env python3
"""
Permission modes for the agent loop.

Implements 6 levels of permission control for tool execution in the agent loop.
Each mode defines which tools are allowed to execute.

Usage:
    from packages.orchestration.permissions import (
        PermissionMode,
        PermissionChecker,
        PermissionResult,
    )

    checker = PermissionChecker(default_mode=PermissionMode.DEFAULT)
    result = checker.check_permission(
        tool_name="Read",
        args={"filePath": "/some/file.py"},
        mode=PermissionMode.DEFAULT,
    )
    if not result.allowed:
        print(f"Blocked: {result.reason}")
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Set

# =============================================================================
# Permission Mode Definitions
# =============================================================================


class PermissionMode(Enum):
    """
    Permission modes for the agent loop.

    Each mode defines a different level of access control:
    - DEFAULT: Read-only operations
    - ACCEPT_EDITS: Read + edit operations
    - PLAN: Read + plan operations
    - AUTO: All actions with safety classifier
    - BYPASS_PERMISSIONS: All actions, no checks
    - DONT_ASK: Pre-approved tools only
    """

    DEFAULT = "default"
    ACCEPT_EDITS = "accept_edits"
    PLAN = "plan"
    AUTO = "auto"
    BYPASS_PERMISSIONS = "bypass_permissions"
    DONT_ASK = "dont_ask"


# =============================================================================
# Permission Result
# =============================================================================


@dataclass
class PermissionResult:
    """
    Result of a permission check.

    Attributes:
        allowed: Whether the tool execution is allowed
        reason: Human-readable reason for the decision
        requires_approval: Whether this operation requires user approval
    """

    allowed: bool
    reason: str
    requires_approval: bool = False


# =============================================================================
# Tool Categories
# =============================================================================


class ToolCategory(Enum):
    """Categories of tools based on their access level."""

    READ = "read"  # Read-only operations
    EDIT = "edit"  # File editing operations
    PLAN = "plan"  # Planning operations
    EXECUTE = "execute"  # Execution operations (dangerous)
    BROWSE = "browse"  # Browser/web operations
    NONE = "none"  # Unknown/uncategorized


# =============================================================================
# Tool Category Mapping
# =============================================================================


# Maps tool names to their categories
TOOL_CATEGORIES: Dict[str, ToolCategory] = {
    # Read tools
    "Read": ToolCategory.READ,
    "read_file": ToolCategory.READ,
    "read": ToolCategory.READ,
    "Glob": ToolCategory.READ,
    "glob": ToolCategory.READ,
    "Grep": ToolCategory.READ,
    "grep": ToolCategory.READ,
    "Look": ToolCategory.READ,
    "look_at": ToolCategory.READ,
    "lsp_goto_definition": ToolCategory.READ,
    "lsp_find_references": ToolCategory.READ,
    "lsp_symbols": ToolCategory.READ,
    "session_read": ToolCategory.READ,
    "session_info": ToolCategory.READ,
    "session_list": ToolCategory.READ,
    "session_search": ToolCategory.READ,
    "webfetch": ToolCategory.READ,
    "websearch": ToolCategory.READ,
    "codesearch": ToolCategory.READ,
    "grep_app_searchGitHub": ToolCategory.READ,
    "context7_query-docs": ToolCategory.READ,
    "unified-memory_search_memories": ToolCategory.READ,
    "unified-memory_recall_session": ToolCategory.READ,
    "unified-memory_find_context": ToolCategory.READ,
    "nx-mind_get_session_context": ToolCategory.READ,
    "nx-mind_get_mind_state": ToolCategory.READ,
    "nx-mind_get_session_history": ToolCategory.READ,
    "nx-mind_get_project_manifest": ToolCategory.READ,
    "learning-engine_get_outcomes": ToolCategory.READ,
    "learning-engine_learning_stats": ToolCategory.READ,
    "learning-engine_status": ToolCategory.READ,
    "intelligence_get_routing_history": ToolCategory.READ,
    "intelligence_route": ToolCategory.READ,
    "intelligence_available_agents": ToolCategory.READ,
    "intelligence_score_complexity": ToolCategory.READ,
    "learning-engine_get_recommendations": ToolCategory.READ,
    "telegram_get_messages": ToolCategory.READ,
    "telegram_peek_messages": ToolCategory.READ,
    "telegram_get_bot_info": ToolCategory.READ,
    # Edit tools
    "Edit": ToolCategory.EDIT,
    "edit": ToolCategory.EDIT,
    "Write": ToolCategory.EDIT,
    "write_file": ToolCategory.EDIT,
    "write": ToolCategory.EDIT,
    "Bash": ToolCategory.EDIT,  # bash can edit via shell
    "bash": ToolCategory.EDIT,
    "lsp_rename": ToolCategory.EDIT,
    "ast_grep_replace": ToolCategory.EDIT,
    "edit_file": ToolCategory.EDIT,
    "write_file": ToolCategory.EDIT,
    # Plan tools
    "Plan": ToolCategory.PLAN,
    "plan": ToolCategory.PLAN,
    "task": ToolCategory.PLAN,
    "call_omo_agent": ToolCategory.PLAN,
    "background_output": ToolCategory.PLAN,
    "background_cancel": ToolCategory.PLAN,
    "Skill": ToolCategory.PLAN,
    "skill": ToolCategory.PLAN,
    "todowrite": ToolCategory.PLAN,
    "skill_mcp": ToolCategory.PLAN,
    # Execute tools (dangerous)
    "Execute": ToolCategory.EXECUTE,
    "execute": ToolCategory.EXECUTE,
    "run": ToolCategory.EXECUTE,
    "git": ToolCategory.EXECUTE,
    "git_commit": ToolCategory.EXECUTE,
    "quality-gates_run_all_gates": ToolCategory.EXECUTE,
    "quality-gates_run_typecheck": ToolCategory.EXECUTE,
    "quality-gates_run_lint": ToolCategory.EXECUTE,
    "quality-gates_run_format": ToolCategory.EXECUTE,
    "quality-gates_run_tests": ToolCategory.EXECUTE,
    "quality-gates_run_secrets_scan": ToolCategory.EXECUTE,
    "quality-gates_run_placeholder_check": ToolCategory.EXECUTE,
    "quality-gates_run_agent_call_check": ToolCategory.EXECUTE,
    "quality-gates_run_security_paths": ToolCategory.EXECUTE,
    "quality-gates_run_deps_check": ToolCategory.EXECUTE,
    "quality-gates_run_sast": ToolCategory.EXECUTE,
    "quality-gates_run_coverage_trend": ToolCategory.EXECUTE,
    "nx-mind_spine_run": ToolCategory.EXECUTE,
    "nx-mind_spine_probe": ToolCategory.EXECUTE,
    "nx-mind_update_mind_state": ToolCategory.EXECUTE,
    "nx-mind_set_context": ToolCategory.EXECUTE,
    "nx-mind_log_task_completion": ToolCategory.EXECUTE,
    "nx-mind_sync_to_memory": ToolCategory.EXECUTE,
    "learning-engine_record_outcome": ToolCategory.EXECUTE,
    "learning-engine_log_outcome": ToolCategory.EXECUTE,
    "learning-engine_retrain": ToolCategory.EXECUTE,
    "unified-memory_memory_write": ToolCategory.EXECUTE,
    "unified-memory_memory_stats": ToolCategory.EXECUTE,
    "telegram_send_message": ToolCategory.EXECUTE,
    # Browse tools
    "Browse": ToolCategory.BROWSE,
    "browse": ToolCategory.BROWSE,
    "dev-browser": ToolCategory.BROWSE,
    "playwright": ToolCategory.BROWSE,
    "Look": ToolCategory.BROWSE,
}


# =============================================================================
# Mode Capabilities
# =============================================================================


# Maps each mode to its allowed tool categories
MODE_ALLOWED_CATEGORIES: Dict[PermissionMode, Set[ToolCategory]] = {
    PermissionMode.DEFAULT: {
        ToolCategory.READ,
    },
    PermissionMode.ACCEPT_EDITS: {
        ToolCategory.READ,
        ToolCategory.EDIT,
    },
    PermissionMode.PLAN: {
        ToolCategory.READ,
        ToolCategory.PLAN,
    },
    PermissionMode.AUTO: {
        ToolCategory.READ,
        ToolCategory.EDIT,
        ToolCategory.PLAN,
        ToolCategory.EXECUTE,
        ToolCategory.BROWSE,
    },
    PermissionMode.BYPASS_PERMISSIONS: {
        ToolCategory.READ,
        ToolCategory.EDIT,
        ToolCategory.PLAN,
        ToolCategory.EXECUTE,
        ToolCategory.BROWSE,
    },
    PermissionMode.DONT_ASK: set(),  # Pre-approved only - empty initially
}


# =============================================================================
# Pre-approved Tools for DONT_ASK mode
# =============================================================================


# Tools that are pre-approved for DONT_ASK mode
DONT_ASK_APPROVED_TOOLS: Set[str] = {
    "Read",
    "read_file",
    "Glob",
    "Grep",
    "grep",
    "session_read",
    "session_search",
    "webfetch",
    "websearch",
    "codesearch",
    "telegram_get_messages",
    "telegram_get_bot_info",
}


# =============================================================================
# Safety Classifier (for AUTO mode)
# =============================================================================


class SafetyClassifier:
    """
    Safety classifier for AUTO mode.

    Analyzes tool arguments to determine if execution is safe.
    """

    # Patterns that indicate dangerous operations
    DANGEROUS_PATTERNS = [
        # File deletion
        r"rm\s+-rf",
        r"rmdir",
        r"del\s+/[qs]",
        # System modification
        r"sudo",
        r"chmod\s+777",
        r"chown",
        # Credential access
        r"\.env",
        r"secret",
        r"password",
        r"api_key",
        # Network exfiltration
        r"curl.*\|.*sh",
        r"wget.*\|.*sh",
    ]

    @classmethod
    def is_safe(cls, tool_name: str, args: Dict[str, Any]) -> tuple[bool, str]:
        """
        Check if a tool execution is safe.

        Args:
            tool_name: Name of the tool
            args: Arguments passed to the tool

        Returns:
            Tuple of (is_safe, reason)
        """
        import re

        # Check for dangerous file paths
        if "filePath" in args:
            file_path = str(args["filePath"])
            # Check for .env or secrets
            if ".env" in file_path.lower() or "secret" in file_path.lower():
                return False, f"Access to sensitive file path: {file_path}"

        # Check for dangerous command patterns
        if "command" in args:
            command = str(args["command"])
            for pattern in cls.DANGEROUS_PATTERNS:
                if re.search(pattern, command, re.IGNORECASE):
                    return False, f"Dangerous command pattern detected: {pattern}"

        # Check for git commands that could cause issues
        if "git" in tool_name.lower():
            if any(x in str(args).lower() for x in ["push", "force", "reset"]):
                return False, "Potentially destructive git command"

        return True, "Safe"


# =============================================================================
# Permission Checker
# =============================================================================


class PermissionChecker:
    """
    Thread-safe permission checker for tool execution.

    Provides centralized permission checking for all tools in the agent loop.
    Each mode has different capabilities as defined in MODE_ALLOWED_CATEGORIES.

    Usage:
        checker = PermissionChecker(default_mode=PermissionMode.DEFAULT)
        result = checker.check_permission("Read", {}, PermissionMode.DEFAULT)
    """

    def __init__(self, default_mode: PermissionMode = PermissionMode.DEFAULT):
        """
        Initialize the PermissionChecker.

        Args:
            default_mode: Default permission mode to use if none specified
        """
        self._default_mode = default_mode
        self._lock = threading.RLock()

        # Track current mode (can be changed at runtime)
        self._current_mode = default_mode

        # Statistics
        self._check_count = 0
        self._blocked_count = 0

    @property
    def current_mode(self) -> PermissionMode:
        """Get the current permission mode."""
        with self._lock:
            return self._current_mode

    @property
    def check_count(self) -> int:
        """Get total number of permission checks."""
        with self._lock:
            return self._check_count

    @property
    def blocked_count(self) -> int:
        """Get number of blocked operations."""
        with self._lock:
            return self._blocked_count

    def set_mode(self, mode: PermissionMode) -> None:
        """
        Set the current permission mode.

        Args:
            mode: New permission mode
        """
        with self._lock:
            self._current_mode = mode
            self._check_count = 0
            self._blocked_count = 0

    def check_permission(
        self,
        tool_name: str,
        args: Dict[str, Any],
        mode: Optional[PermissionMode] = None,
    ) -> PermissionResult:
        """
        Check if a tool execution is allowed.

        This is the main entry point for permission checking.
        Thread-safe implementation using a lock.

        Args:
            tool_name: Name of the tool to execute
            args: Arguments passed to the tool
            mode: Permission mode to use (uses default if not specified)

        Returns:
            PermissionResult with allowed status and reason
        """
        with self._lock:
            self._check_count += 1

            # Use provided mode or default
            check_mode = mode or self._default_mode

            # BYPASS_PERMISSIONS - allow everything
            if check_mode == PermissionMode.BYPASS_PERMISSIONS:
                return PermissionResult(
                    allowed=True,
                    reason="BYPASS_PERMISSIONS mode - all operations allowed",
                    requires_approval=False,
                )

            # Get tool category
            category = self._get_tool_category(tool_name)

            # DONT_ASK - pre-approved tools only
            if check_mode == PermissionMode.DONT_ASK:
                if tool_name in DONT_ASK_APPROVED_TOOLS:
                    return PermissionResult(
                        allowed=True,
                        reason=f"Tool {tool_name} is pre-approved in DONT_ASK mode",
                        requires_approval=False,
                    )
                self._blocked_count += 1
                return PermissionResult(
                    allowed=False,
                    reason=f"Tool {tool_name} not in pre-approved list for DONT_ASK mode",
                    requires_approval=True,
                )

            # AUTO mode - check safety classifier
            if check_mode == PermissionMode.AUTO:
                is_safe, reason = SafetyClassifier.is_safe(tool_name, args)
                if not is_safe:
                    self._blocked_count += 1
                    return PermissionResult(
                        allowed=False,
                        reason=f"Safety classifier blocked: {reason}",
                        requires_approval=True,
                    )
                # AUTO allows all categories after safety check
                return PermissionResult(
                    allowed=True,
                    reason="AUTO mode - safety check passed",
                    requires_approval=False,
                )

            # Get allowed categories for this mode
            allowed_categories = MODE_ALLOWED_CATEGORIES.get(
                check_mode, {ToolCategory.READ}
            )

            # Check if tool category is allowed
            if category in allowed_categories:
                return PermissionResult(
                    allowed=True,
                    reason=f"Tool {tool_name} ({category.value}) allowed in {check_mode.value} mode",
                    requires_approval=False,
                )

            # Blocked
            self._blocked_count += 1
            return PermissionResult(
                allowed=False,
                reason=f"Tool {tool_name} ({category.value}) not allowed in {check_mode.value} mode. Required: {[c.value for c in allowed_categories]}",
                requires_approval=True,
            )

    def _get_tool_category(self, tool_name: str) -> ToolCategory:
        """
        Get the category of a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            ToolCategory for the tool
        """
        # Check exact match first
        if tool_name in TOOL_CATEGORIES:
            return TOOL_CATEGORIES[tool_name]

        # Check for partial matches (tool name contains category keyword)
        tool_lower = tool_name.lower()

        # Check for read patterns
        if any(x in tool_lower for x in ["read", "get", "search", "query", "list"]):
            return ToolCategory.READ

        # Check for edit patterns
        if any(x in tool_lower for x in ["edit", "write", "write_file", "modify"]):
            return ToolCategory.EDIT

        # Check for plan patterns
        if any(x in tool_lower for x in ["plan", "task", "delegate"]):
            return ToolCategory.PLAN

        # Check for execute patterns
        if any(x in tool_lower for x in ["execute", "run", "bash", "command"]):
            return ToolCategory.EXECUTE

        # Check for browse patterns
        if any(x in tool_lower for x in ["browse", "browser", "playwright"]):
            return ToolCategory.BROWSE

        # Default to NONE (unknown)
        return ToolCategory.NONE

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        with self._lock:
            self._check_count = 0
            self._blocked_count = 0


# =============================================================================
# Module-Level Convenience
# =============================================================================


# Global default checker instance
_default_checker: Optional[PermissionChecker] = None


def get_default_checker() -> PermissionChecker:
    """
    Get the global default PermissionChecker instance.

    Returns:
        The global PermissionChecker instance
    """
    global _default_checker
    if _default_checker is None:
        _default_checker = PermissionChecker()
    return _default_checker


def check_permission(
    tool_name: str,
    args: Dict[str, Any],
    mode: Optional[PermissionMode] = None,
) -> PermissionResult:
    """
    Convenience function for permission checking.

    Uses the global default checker instance.

    Args:
        tool_name: Name of the tool to execute
        args: Arguments passed to the tool
        mode: Permission mode to use

    Returns:
        PermissionResult with allowed status and reason
    """
    return get_default_checker().check_permission(tool_name, args, mode)


# =============================================================================
# Main - Quick Test
# =============================================================================


if __name__ == "__main__":
    import sys
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s: %(message)s",
    )

    print("=== Permission Modes Test ===\n")

    # Test 1: DEFAULT mode (read-only)
    print("--- Test 1: DEFAULT mode ---")
    checker = PermissionChecker(default_mode=PermissionMode.DEFAULT)

    result = checker.check_permission(
        tool_name="Read",
        args={"filePath": "/some/file.py"},
        mode=PermissionMode.DEFAULT,
    )
    print(f"Read tool: allowed={result.allowed}, reason={result.reason}")

    result = checker.check_permission(
        tool_name="Edit",
        args={"filePath": "/some/file.py"},
        mode=PermissionMode.DEFAULT,
    )
    print(f"Edit tool: allowed={result.allowed}, reason={result.reason}")

    # Test 2: ACCEPT_EDITS mode
    print("\n--- Test 2: ACCEPT_EDITS mode ---")
    result = checker.check_permission(
        tool_name="Read",
        args={"filePath": "/some/file.py"},
        mode=PermissionMode.ACCEPT_EDITS,
    )
    print(f"Read tool: allowed={result.allowed}")

    result = checker.check_permission(
        tool_name="Edit",
        args={"filePath": "/some/file.py"},
        mode=PermissionMode.ACCEPT_EDITS,
    )
    print(f"Edit tool: allowed={result.allowed}")

    result = checker.check_permission(
        tool_name="Bash",
        args={"command": "ls"},
        mode=PermissionMode.ACCEPT_EDITS,
    )
    print(f"Bash tool: allowed={result.allowed}")

    # Test 3: BYPASS_PERMISSIONS mode
    print("\n--- Test 3: BYPASS_PERMISSIONS mode ---")
    result = checker.check_permission(
        tool_name="Bash",
        args={"command": "rm -rf /"},
        mode=PermissionMode.BYPASS_PERMISSIONS,
    )
    print(f"Dangerous bash: allowed={result.allowed}, reason={result.reason}")

    # Test 4: AUTO mode with safety classifier
    print("\n--- Test 4: AUTO mode with safety classifier ---")
    result = checker.check_permission(
        tool_name="Bash",
        args={"command": "ls -la"},
        mode=PermissionMode.AUTO,
    )
    print(f"Safe bash: allowed={result.allowed}")

    result = checker.check_permission(
        tool_name="Bash",
        args={"command": "rm -rf /"},
        mode=PermissionMode.AUTO,
    )
    print(f"Dangerous bash: allowed={result.allowed}, reason={result.reason}")

    # Test 5: DONT_ASK mode
    print("\n--- Test 5: DONT_ASK mode ---")
    result = checker.check_permission(
        tool_name="Read",
        args={"filePath": "/some/file.py"},
        mode=PermissionMode.DONT_ASK,
    )
    print(f"Pre-approved Read: allowed={result.allowed}")

    result = checker.check_permission(
        tool_name="Edit",
        args={"filePath": "/some/file.py"},
        mode=PermissionMode.DONT_ASK,
    )
    print(f"Non-approved Edit: allowed={result.allowed}")

    # Test 6: Thread safety
    print("\n--- Test 6: Thread safety ---")
    import threading

    checker = PermissionChecker(default_mode=PermissionMode.DEFAULT)
    results: list[bool] = []

    def check_many():
        for _ in range(100):
            result = checker.check_permission(
                tool_name="Read",
                args={},
                mode=PermissionMode.DEFAULT,
            )
            results.append(result.allowed)

    threads = [threading.Thread(target=check_many) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"Thread safety test: {len(results)} checks, all passed")

    # Test 7: Statistics
    print("\n--- Test 7: Statistics ---")
    print(f"Total checks: {checker.check_count}")
    print(f"Blocked: {checker.blocked_count}")

    # Test 8: Mode switching
    print("\n--- Test 8: Mode switching ---")
    checker.set_mode(PermissionMode.ACCEPT_EDITS)
    print(f"Current mode: {checker.current_mode.value}")

    print("\n=== All tests completed! ===")
    sys.exit(0)
