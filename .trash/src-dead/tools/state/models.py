"""Data models for SQLite state management."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass
class Session:
    """Represents an agent session state."""

    session_id: str
    last_agent: str = ""
    last_action: str = ""
    session_started: str = ""
    last_updated: str = ""
    current_task: str = ""
    pending_changes: list[str] = field(default_factory=list)
    completed_changes: list[str] = field(default_factory=list)
    context: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Session:
        return cls(
            session_id=data.get("session_id", ""),
            last_agent=data.get("last_agent", ""),
            last_action=data.get("last_action", ""),
            session_started=data.get("session_started", ""),
            last_updated=data.get("last_updated", ""),
            current_task=data.get("current_task", ""),
            pending_changes=data.get("pending_changes", []),
            completed_changes=data.get("completed_changes", []),
            context=data.get("context", {}),
        )

    def to_json(self) -> str:
        d = self.to_dict()
        d["pending_changes"] = json.dumps(d["pending_changes"])
        d["completed_changes"] = json.dumps(d["completed_changes"])
        d["context"] = json.dumps(d["context"])
        return json.dumps(d)

    @classmethod
    def from_json(cls, json_str: str) -> Session:
        d = json.loads(json_str)
        d["pending_changes"] = json.loads(d.get("pending_changes", "[]"))
        d["completed_changes"] = json.loads(d.get("completed_changes", "[]"))
        d["context"] = json.loads(d.get("context", "{}"))
        return cls.from_dict(d)


@dataclass
class Delegation:
    """Represents a single delegation log entry."""

    task_id: str
    agent: str
    level: str
    status: str
    tokens: int = 0
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Delegation:
        return cls(
            task_id=data.get("task_id", ""),
            agent=data.get("agent", ""),
            level=data.get("level", ""),
            status=data.get("status", ""),
            tokens=data.get("tokens", 0),
            timestamp=data.get("timestamp", ""),
        )


@dataclass
class AgentPerformance:
    """Represents performance metrics for an agent on a task type."""

    agent_name: str
    task_type: str
    success: int = 0
    failure: int = 0
    last_failure_reason: str = ""
    last_updated: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentPerformance:
        return cls(
            agent_name=data.get("agent_name", ""),
            task_type=data.get("task_type", ""),
            success=data.get("success", 0),
            failure=data.get("failure", 0),
            last_failure_reason=data.get("last_failure_reason", ""),
            last_updated=data.get("last_updated", ""),
        )


@dataclass
class Result:
    """Represents a cached delegation result."""

    task_id: str
    task_description: str
    agent: str
    level: str
    success: bool
    result_path: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Result:
        return cls(
            task_id=data.get("task_id", ""),
            task_description=data.get("task_description", ""),
            agent=data.get("agent", ""),
            level=data.get("level", ""),
            success=data.get("success", False),
            result_path=data.get("result_path", ""),
            timestamp=data.get("timestamp", ""),
        )


# ─── Task ID System (from ant-source-code Task.ts) ───

TASK_ID_PREFIXES = {
    "bash": "b",
    "agent": "a",
    "workflow": "w",
    "delegation": "d",
    "memory": "m",
}

TASK_STATUSES = {
    "pending", "running", "completed", "failed", "cancelled", "timeout"
}
TERMINAL_STATUSES = {"completed", "failed", "cancelled", "timeout"}


def generate_task_id(task_type: str) -> str:
    """Generate a prefixed task ID."""
    import secrets
    prefix = TASK_ID_PREFIXES.get(task_type, "x")
    return f"{prefix}_{secrets.token_hex(4)}"


def is_terminal_task_status(status: str) -> bool:
    """Check if a task status is terminal (cannot transition further)."""
    return status in TERMINAL_STATUSES


def validate_task_status_transition(current: str, new: str) -> bool:
    """Validate a task status transition. Prevents injecting into dead tasks."""
    if is_terminal_task_status(current):
        return False
    if new not in TASK_STATUSES:
        return False
    return True

