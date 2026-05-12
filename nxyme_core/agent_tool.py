"""AgentTool — Subagent spawning and lifecycle management."""

import logging
import uuid
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class SubagentState(Enum):
    """States for subagent lifecycle."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class SubagentConfig:
    """Configuration for a subagent."""
    name: str
    agent_type: str
    memory_snapshot: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Subagent:
    """Represents a spawned subagent."""
    id: str
    config: SubagentConfig
    state: SubagentState = SubagentState.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    pid: Optional[int] = None


class AgentTool:
    """Tool for spawning and managing subagents with memory snapshots."""

    def __init__(self):
        self._subagents: Dict[str, Subagent] = {}
        self._builtin_registry: Dict[str, Callable] = {}
        self._memory_snapshots: Dict[str, Dict[str, Any]] = {}
        self._register_builtin_subagents()

    def _register_builtin_subagents(self) -> None:
        """Register built-in subagent types."""
        self._builtin_registry = {
            "explore": self._spawn_explore,
            "plan": self._spawn_plan,
            "verify": self._spawn_verify,
            "general": self._spawn_general,
        }
        logger.info(f"Registered {len(self._builtin_registry)} built-in subagent types")

    def _spawn_explore(self, config: SubagentConfig) -> Dict[str, Any]:
        """Spawn an Explore subagent."""
        return {
            "agent_type": "explore",
            "prompt": f"Explore task: {config.metadata.get('query', 'search codebase')}",
            "tools": ["grep", "glob", "read", "lsp_symbols"],
        }

    def _spawn_plan(self, config: SubagentConfig) -> Dict[str, Any]:
        """Spawn a Plan subagent."""
        return {
            "agent_type": "plan",
            "prompt": f"Plan: {config.metadata.get('task', 'create implementation plan')}",
            "tools": ["read", "write"],
        }

    def _spawn_verify(self, config: SubagentConfig) -> Dict[str, Any]:
        """Spawn a Verify subagent."""
        return {
            "agent_type": "verify",
            "prompt": f"Verify: {config.metadata.get('check', 'validate implementation')}",
            "tools": ["lsp_diagnostics", "grep", "read"],
        }

    def _spawn_general(self, config: SubagentConfig) -> Dict[str, Any]:
        """Spawn a General subagent."""
        return {
            "agent_type": "hephaestus",
            "prompt": config.metadata.get("task", "execute task"),
            "tools": ["read", "write", "edit", "bash"],
        }

    def spawn_subagent(
        self,
        agent_type: str,
        task: str,
        memory_snapshot: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        **metadata
    ) -> str:
        """Spawn a new subagent.

        Args:
            agent_type: Type of subagent (explore, plan, verify, general)
            task: Task description for the subagent
            memory_snapshot: Optional memory context to pass to subagent
            timeout: Optional timeout in seconds
            **metadata: Additional metadata

        Returns:
            Subagent ID
        """
        if agent_type not in self._builtin_registry:
            raise ValueError(f"Unknown agent type: {agent_type}. Available: {list(self._builtin_registry.keys())}")

        subagent_id = str(uuid.uuid4())
        config = SubagentConfig(
            name=f"{agent_type}-{subagent_id[:8]}",
            agent_type=agent_type,
            memory_snapshot=memory_snapshot,
            timeout=timeout,
            metadata={"task": task, **metadata}
        )

        subagent = Subagent(id=subagent_id, config=config, state=SubagentState.RUNNING)
        self._subagents[subagent_id] = subagent
        self._memory_snapshots[subagent_id] = memory_snapshot or {}

        logger.info(f"Spawned subagent {subagent_id} (type: {agent_type}, task: {task})")
        return subagent_id

    def list_subagents(self, state_filter: Optional[SubagentState] = None) -> List[Dict[str, Any]]:
        """List all subagents, optionally filtered by state.

        Args:
            state_filter: Optional state to filter by

        Returns:
            List of subagent info dicts
        """
        result = []
        for subagent in self._subagents.values():
            if state_filter is None or subagent.state == state_filter:
                result.append({
                    "id": subagent.id,
                    "name": subagent.config.name,
                    "agent_type": subagent.config.agent_type,
                    "state": subagent.state.value,
                    "created_at": subagent.created_at.isoformat(),
                    "has_memory": subagent.id in self._memory_snapshots,
                })
        return result

    def kill_subagent(self, subagent_id: str) -> bool:
        """Kill a running subagent.

        Args:
            subagent_id: ID of subagent to kill

        Returns:
            True if killed, False if not found
        """
        if subagent_id not in self._subagents:
            logger.warning(f"Subagent not found: {subagent_id}")
            return False

        subagent = self._subagents[subagent_id]
        subagent.state = SubagentState.STOPPED
        subagent.completed_at = datetime.now()

        # Clean up memory snapshot
        if subagent_id in self._memory_snapshots:
            del self._memory_snapshots[subagent_id]

        logger.info(f"Killed subagent: {subagent_id}")
        return True

    def get_subagent_status(self, subagent_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific subagent.

        Args:
            subagent_id: ID of subagent

        Returns:
            Status dict or None if not found
        """
        if subagent_id not in self._subagents:
            return None

        subagent = self._subagents[subagent_id]
        return {
            "id": subagent.id,
            "name": subagent.config.name,
            "agent_type": subagent.config.agent_type,
            "state": subagent.state.value,
            "created_at": subagent.created_at.isoformat(),
            "completed_at": subagent.completed_at.isoformat() if subagent.completed_at else None,
            "result": subagent.result,
            "error": subagent.error,
            "memory_snapshot": self._memory_snapshots.get(subagent_id),
        }

    def complete_subagent(
        self,
        subagent_id: str,
        result: Any = None,
        error: Optional[str] = None
    ) -> None:
        """Mark a subagent as completed or failed.

        Args:
            subagent_id: ID of subagent
            result: Result data (if successful)
            error: Error message (if failed)
        """
        if subagent_id not in self._subagents:
            logger.warning(f"Subagent not found: {subagent_id}")
            return

        subagent = self._subagents[subagent_id]
        subagent.completed_at = datetime.now()

        if error:
            subagent.state = SubagentState.FAILED
            subagent.error = error
            logger.error(f"Subagent {subagent_id} failed: {error}")
        else:
            subagent.state = SubagentState.COMPLETED
            subagent.result = result
            logger.info(f"Subagent {subagent_id} completed")

    def get_memory_snapshot(self, subagent_id: str) -> Optional[Dict[str, Any]]:
        """Get the memory snapshot for a subagent.

        Args:
            subagent_id: ID of subagent

        Returns:
            Memory snapshot dict or None
        """
        return self._memory_snapshots.get(subagent_id)

    def health_check(self) -> Dict[str, Any]:
        """Health check for AgentTool."""
        states = {}
        for subagent in self._subagents.values():
            states[subagent.id] = subagent.state.value

        return {
            "status": "healthy",
            "active_subagents": len([s for s in self._subagents.values() if s.state == SubagentState.RUNNING]),
            "total_subagents": len(self._subagents),
            "builtin_types": list(self._builtin_registry.keys()),
            "states": states,
        }

    def shutdown(self) -> None:
        """Shutdown all subagents and clean up."""
        for subagent_id in list(self._subagents.keys()):
            self.kill_subagent(subagent_id)
        self._subagents.clear()
        self._memory_snapshots.clear()
        logger.info("AgentTool shutdown complete")


# Global instance
_agent_tool: Optional[AgentTool] = None


def get_agent_tool() -> AgentTool:
    """Get the global AgentTool instance."""
    global _agent_tool
    if _agent_tool is None:
        _agent_tool = AgentTool()
    return _agent_tool


__all__ = [
    "AgentTool",
    "Subagent",
    "SubagentConfig",
    "SubagentState",
    "get_agent_tool",
]