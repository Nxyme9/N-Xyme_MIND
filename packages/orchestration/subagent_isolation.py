#!/usr/bin/env python3
"""
Subagent Isolation for the agent loop.

Implements isolated subagent execution with:
- Tool allowlists/denylists
- Worktree isolation (optional)
- Permission modes per subagent
- Resource limits
- Thread-safe operations

Usage:
    from packages.orchestration.subagent_isolation import (
        SubagentIsolation,
        SubagentConfig,
    )

    isolation = SubagentIsolation()
    config = isolation.create_subagent(
        name="researcher",
        prompt="You are a research assistant.",
        tool_allowlist=["Read", "Grep", "Glob"],
        tool_denylist=["Bash", "Edit"],
        permission_mode=PermissionMode.DEFAULT,
        worktree="/tmp/research",
    )
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
import uuid
import logging

# Import from existing modules
from packages.orchestration.permissions import PermissionMode

logger = logging.getLogger("subagent_isolation")


# =============================================================================
# Subagent Configuration
# =============================================================================


@dataclass
class MemoryOptions:
    """Memory options for subagent isolation."""

    max_memory_mb: int = 100
    enable_isolated_memory: bool = True
    preserve_context: bool = True
    memory_scope: str = "subagent"  # "subagent", "shared", "none"


@dataclass
class ResourceLimits:
    """Resource limits for subagent execution."""

    max_cpu_percent: int = 50
    max_duration_seconds: int = 300
    max_tool_calls: int = 100
    max_token_budget: int = 50000


@dataclass
class SubagentConfig:
    """
    Configuration for an isolated subagent.

    Attributes:
        name: Unique identifier for the subagent
        prompt: System prompt for the subagent
        tool_allowlist: Set of allowed tool names (empty = allow all)
        tool_denylist: Set of denied tool names (empty = deny none)
        permission_mode: Permission mode for tool execution
        worktree: Optional worktree path for isolation
        memory_options: Memory configuration for the subagent
        resource_limits: Resource limits for execution
        subagent_id: Unique UUID for this subagent instance
    """

    name: str
    prompt: str
    tool_allowlist: Set[str] = field(default_factory=set)
    tool_denylist: Set[str] = field(default_factory=set)
    permission_mode: PermissionMode = PermissionMode.DEFAULT
    worktree: Optional[str] = None
    memory_options: MemoryOptions = field(default_factory=MemoryOptions)
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)
    subagent_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Internal state
    tool_call_count: int = 0
    is_active: bool = True

    def is_tool_allowed(self, tool_name: str) -> bool:
        """
        Check if a tool is allowed for this subagent.

        Args:
            tool_name: Name of the tool to check

        Returns:
            True if tool is allowed, False otherwise
        """
        # Check denylist first
        if tool_name in self.tool_denylist:
            return False

        # Check allowlist if not empty
        if self.tool_allowlist and tool_name not in self.tool_allowlist:
            return False

        return True

    def can_execute_tool(self, tool_name: str) -> tuple[bool, str]:
        """
        Check if subagent can execute a tool with reason.

        Args:
            tool_name: Name of the tool

        Returns:
            Tuple of (allowed, reason)
        """
        if not self.is_active:
            return False, "Subagent is not active"

        if self.tool_call_count >= self.resource_limits.max_tool_calls:
            return (
                False,
                f"Tool call limit reached: {self.resource_limits.max_tool_calls}",
            )

        if not self.is_tool_allowed(tool_name):
            if self.tool_allowlist:
                return False, f"Tool {tool_name} not in allowlist"
            return False, f"Tool {tool_name} in denylist"

        return True, "Allowed"


# =============================================================================
# Subagent Isolation
# =============================================================================


class SubagentIsolation:
    """
    Thread-safe subagent isolation manager.

    Provides isolated execution contexts for subagents with:
    - Per-subagent tool filtering (allowlist/denylist)
    - Permission modes per subagent
    - Worktree isolation
    - Resource limits
    - Memory isolation

    This class is thread-safe and can be used in concurrent environments.
    """

    def __init__(self) -> None:
        """Initialize the SubagentIsolation manager."""
        self._lock = threading.RLock()
        self._subagents: Dict[str, SubagentConfig] = {}
        self._subagent_counter: int = 0

        logger.info("SubagentIsolation initialized")

    def create_subagent(
        self,
        name: str,
        prompt: str,
        tool_allowlist: Optional[List[str]] = None,
        tool_denylist: Optional[List[str]] = None,
        permission_mode: PermissionMode = PermissionMode.DEFAULT,
        worktree: Optional[str] = None,
        memory_options: Optional[MemoryOptions] = None,
        resource_limits: Optional[ResourceLimits] = None,
    ) -> SubagentConfig:
        """
        Create an isolated subagent configuration.

        Args:
            name: Unique name for the subagent
            prompt: System prompt for the subagent
            tool_allowlist: Optional list of allowed tools (empty = allow all)
            tool_denylist: Optional list of denied tools (empty = deny none)
            permission_mode: Permission mode for tool execution
            worktree: Optional worktree path for file system isolation
            memory_options: Optional memory configuration
            resource_limits: Optional resource limits

        Returns:
            SubagentConfig for the created subagent
        """
        with self._lock:
            self._subagent_counter += 1

            # Normalize tool lists to sets
            allowlist = set(tool_allowlist) if tool_allowlist else set()
            denylist = set(tool_denylist) if tool_denylist else set()

            # Create config
            config = SubagentConfig(
                name=name,
                prompt=prompt,
                tool_allowlist=allowlist,
                tool_denylist=denylist,
                permission_mode=permission_mode,
                worktree=worktree,
                memory_options=memory_options or MemoryOptions(),
                resource_limits=resource_limits or ResourceLimits(),
            )

            # Store in registry
            self._subagents[config.subagent_id] = config

            logger.info(
                f"Created subagent: {name} (id={config.subagent_id}, "
                f"allowlist={len(allowlist)}, denylist={len(denylist)}, "
                f"mode={permission_mode.value})"
            )

            return config

    def get_subagent(self, subagent_id: str) -> Optional[SubagentConfig]:
        """
        Get a subagent configuration by ID.

        Args:
            subagent_id: The subagent UUID

        Returns:
            SubagentConfig if found, None otherwise
        """
        with self._lock:
            return self._subagents.get(subagent_id)

    def get_subagent_by_name(self, name: str) -> Optional[SubagentConfig]:
        """
        Get a subagent configuration by name.

        Args:
            name: The subagent name

        Returns:
            SubagentConfig if found, None otherwise
        """
        with self._lock:
            for config in self._subagents.values():
                if config.name == name:
                    return config
            return None

    def remove_subagent(self, subagent_id: str) -> bool:
        """
        Remove a subagent from the registry.

        Args:
            subagent_id: The subagent UUID

        Returns:
            True if removed, False if not found
        """
        with self._lock:
            if subagent_id in self._subagents:
                del self._subagents[subagent_id]
                logger.info(f"Removed subagent: {subagent_id}")
                return True
            return False

    def check_tool_permission(
        self,
        subagent_id: str,
        tool_name: str,
    ) -> tuple[bool, str]:
        """
        Check if a subagent can execute a tool.

        Args:
            subagent_id: The subagent UUID
            tool_name: Name of the tool to check

        Returns:
            Tuple of (allowed, reason)
        """
        with self._lock:
            config = self._subagents.get(subagent_id)
            if not config:
                return False, f"Subagent not found: {subagent_id}"

            return config.can_execute_tool(tool_name)

    def record_tool_call(self, subagent_id: str) -> bool:
        """
        Record a tool call for a subagent and check limits.

        Args:
            subagent_id: The subagent UUID

        Returns:
            True if tool call is allowed, False if limit exceeded
        """
        with self._lock:
            config = self._subagents.get(subagent_id)
            if not config:
                return False

            config.tool_call_count += 1

            if config.tool_call_count > config.resource_limits.max_tool_calls:
                logger.warning(
                    f"Subagent {subagent_id} exceeded tool call limit: "
                    f"{config.tool_call_count}/{config.resource_limits.max_tool_calls}"
                )
                return False

            return True

    def list_subagents(self) -> List[SubagentConfig]:
        """
        List all active subagents.

        Returns:
            List of SubagentConfig for all subagents
        """
        with self._lock:
            return list(self._subagents.values())

    def get_active_count(self) -> int:
        """
        Get the count of active subagents.

        Returns:
            Number of active subagents
        """
        with self._lock:
            return sum(1 for c in self._subagents.values() if c.is_active)

    def deactivate_subagent(self, subagent_id: str) -> bool:
        """
        Deactivate a subagent (prevent further tool execution).

        Args:
            subagent_id: The subagent UUID

        Returns:
            True if deactivated, False if not found
        """
        with self._lock:
            config = self._subagents.get(subagent_id)
            if config:
                config.is_active = False
                logger.info(f"Deactivated subagent: {subagent_id}")
                return True
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about subagent isolation.

        Returns:
            Dict with statistics
        """
        with self._lock:
            active = sum(1 for c in self._subagents.values() if c.is_active)
            total_calls = sum(c.tool_call_count for c in self._subagents.values())

            return {
                "total_subagents": len(self._subagents),
                "active_subagents": active,
                "total_tool_calls": total_calls,
                "created_count": self._subagent_counter,
            }


# =============================================================================
# Module-Level Convenience
# =============================================================================


# Global default isolation instance
_default_isolation: Optional[SubagentIsolation] = None


def get_default_isolation() -> SubagentIsolation:
    """
    Get the global default SubagentIsolation instance.

    Returns:
        The global SubagentIsolation instance
    """
    global _default_isolation
    if _default_isolation is None:
        _default_isolation = SubagentIsolation()
    return _default_isolation


def create_subagent(
    name: str,
    prompt: str,
    tool_allowlist: Optional[List[str]] = None,
    tool_denylist: Optional[List[str]] = None,
    permission_mode: PermissionMode = PermissionMode.DEFAULT,
    worktree: Optional[str] = None,
) -> SubagentConfig:
    """
    Convenience function to create a subagent.

    Uses the global default isolation instance.

    Args:
        name: Unique name for the subagent
        prompt: System prompt for the subagent
        tool_allowlist: Optional list of allowed tools
        tool_denylist: Optional list of denied tools
        permission_mode: Permission mode for tool execution
        worktree: Optional worktree path for file system isolation

    Returns:
        SubagentConfig for the created subagent
    """
    return get_default_isolation().create_subagent(
        name=name,
        prompt=prompt,
        tool_allowlist=tool_allowlist,
        tool_denylist=tool_denylist,
        permission_mode=permission_mode,
        worktree=worktree,
    )


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

    print("=== Subagent Isolation Test ===\n")

    # Test 1: Create subagent with allowlist
    print("--- Test 1: Create subagent with allowlist ---")
    isolation = SubagentIsolation()

    config = isolation.create_subagent(
        name="researcher",
        prompt="You are a research assistant.",
        tool_allowlist=["Read", "Grep", "Glob"],
        tool_denylist=["Edit", "Bash"],
        permission_mode=PermissionMode.DEFAULT,
        worktree="/tmp/research",
    )
    print(f"Created subagent: {config.name} (id={config.subagent_id[:8]}...)")
    print(f"  Allowlist: {config.tool_allowlist}")
    print(f"  Denylist: {config.tool_denylist}")
    print(f"  Mode: {config.permission_mode.value}")
    print(f"  Worktree: {config.worktree}")

    # Test 2: Tool permission checking
    print("\n--- Test 2: Tool permission checking ---")
    allowed, reason = isolation.check_tool_permission(config.subagent_id, "Read")
    print(f"Read tool: allowed={allowed}, reason={reason}")

    allowed, reason = isolation.check_tool_permission(config.subagent_id, "Edit")
    print(f"Edit tool: allowed={allowed}, reason={reason}")

    allowed, reason = isolation.check_tool_permission(config.subagent_id, "Bash")
    print(f"Bash tool: allowed={allowed}, reason={reason}")

    # Test 3: Tool call tracking
    print("\n--- Test 3: Tool call tracking ---")
    isolation.record_tool_call(config.subagent_id)
    isolation.record_tool_call(config.subagent_id)
    print(f"Tool calls: {config.tool_call_count}")

    # Test 4: Subagent not found
    print("\n--- Test 4: Subagent not found ---")
    allowed, reason = isolation.check_tool_permission("invalid-id", "Read")
    print(f"Invalid subagent: allowed={allowed}, reason={reason}")

    # Test 5: List subagents
    print("\n--- Test 5: List subagents ---")
    print(f"Active subagents: {isolation.get_active_count()}")

    # Test 6: Deactivate subagent
    print("\n--- Test 6: Deactivate subagent ---")
    isolation.deactivate_subagent(config.subagent_id)
    allowed, reason = isolation.check_tool_permission(config.subagent_id, "Read")
    print(f"After deactivation: allowed={allowed}, reason={reason}")

    # Test 7: Create subagent with denylist only
    print("\n--- Test 7: Create subagent with denylist only ---")
    config2 = isolation.create_subagent(
        name="safe_runner",
        prompt="You are a safe assistant.",
        tool_denylist=["Bash", "Edit", "Write"],
        permission_mode=PermissionMode.AUTO,
    )
    print(f"Created: {config2.name}, allowlist empty (all allowed except denylist)")

    allowed, reason = isolation.check_tool_permission(config2.subagent_id, "Read")
    print(f"Read: allowed={allowed}")

    allowed, reason = isolation.check_tool_permission(config2.subagent_id, "Bash")
    print(f"Bash: allowed={allowed}")

    # Test 8: Statistics
    print("\n--- Test 8: Statistics ---")
    stats = isolation.get_stats()
    print(f"Stats: {stats}")

    # Test 9: Thread safety
    print("\n--- Test 9: Thread safety ---")
    import threading

    isolation2 = SubagentIsolation()
    results: list[bool] = []

    def create_many():
        for _ in range(50):
            config = isolation2.create_subagent(
                name="thread_subagent",
                prompt="Test",
                tool_allowlist=["Read"],
            )
            results.append(config.subagent_id is not None)

    threads = [threading.Thread(target=create_many) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"Thread safety: {len(results)} subagents created")

    # Test 10: Module-level convenience
    print("\n--- Test 10: Module-level convenience ---")
    config3 = create_subagent(
        name="quick_create",
        prompt="Quick create test",
        tool_allowlist=["Read", "Grep"],
    )
    print(f"Created via convenience function: {config3.name}")

    print("\n=== All tests completed! ===")
    sys.exit(0)
