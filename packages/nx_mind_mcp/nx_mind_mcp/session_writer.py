#!/usr/bin/env python3
"""SessionWriter — Auto-writes context on task completion.

Provides non-blocking, thread-safe session state updates after every task.
Updates session-state.json, activeContext.md, and session-log.jsonl.
"""

from __future__ import annotations

import fcntl
import json
import os
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


@dataclass
class TaskCompletion:
    """Represents a completed task for logging."""

    task_id: str
    description: str
    success: bool
    agent: str
    duration_ms: float
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict[str, Any] = field(default_factory=dict)


class SessionWriter:
    """Thread-safe, non-blocking session state updater.

    Writes to three destinations:
    - .sisyphus/session-state.json (atomic update)
    - .context/activeContext.md (append to Recent Decisions)
    - .sisyphus/session-log.jsonl (append-only event log)
    """

    def __init__(
        self,
        state_path: str = ".sisyphus/session-state.json",
        context_path: str = ".context/activeContext.md",
        log_path: str = ".sisyphus/session-log.jsonl",
    ):
        self.state_path = Path(state_path)
        self.context_path = Path(context_path)
        self.log_path = Path(log_path)
        self._lock = threading.Lock()
        self._initialized = False
        self._ensure_paths()

    def _ensure_paths(self):
        """Ensure all paths exist with defaults."""
        # Ensure directories exist
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.context_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        # Ensure state file exists with defaults
        if not self.state_path.exists():
            self._write_state(
                {
                    "last_agent": "none",
                    "last_action": "Session initialized",
                    "session_started": datetime.now(timezone.utc).isoformat(),
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "current_task": "No active task",
                    "pending_changes": [],
                    "completed_changes": [],
                    "memory_stats": {},
                }
            )

        # Ensure context file exists with defaults
        if not self.context_path.exists():
            self._write_context_default()

        self._initialized = True

    def _write_state(self, data: dict[str, Any]) -> None:
        """Write state atomically with file locking (write to temp, then rename)."""
        temp_path = self.state_path.with_suffix(".json.tmp")
        with open(temp_path, "w") as tf:
            json.dump(data, tf, indent=2)
        # Lock both files for atomic swap
        with open(self.state_path) as sf, open(temp_path) as tf:
            fcntl.flock(sf.fileno(), fcntl.LOCK_EX)
            try:
                fcntl.flock(tf.fileno(), fcntl.LOCK_EX)
                os.replace(temp_path, self.state_path)
            finally:
                fcntl.flock(sf.fileno(), fcntl.LOCK_UN)
                fcntl.flock(tf.fileno(), fcntl.LOCK_UN)

    def _read_state(self) -> dict[str, Any]:
        """Read current state, return defaults if missing/invalid."""
        try:
            if self.state_path.exists():
                with open(self.state_path) as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
        return {
            "last_agent": "none",
            "last_action": "Session initialized",
            "session_started": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "current_task": "No active task",
            "pending_changes": [],
            "completed_changes": [],
            "memory_stats": {},
        }

    def _write_context_default(self) -> None:
        """Write default activeContext.md."""
        default_content = """# Active Context

## Current Session
- **Started**: {date}
- **Focus**: Development session
- **Status**: Active

## Active Tasks
- (none)

## Recent Decisions
- (none yet)

## Unresolved Issues
- (none)
""".format(date=datetime.now().strftime("%Y-%m-%d"))
        self.context_path.write_text(default_content)

    def _append_to_context(self, task_desc: str, success: bool, agent: str) -> None:
        """Append completed task to activeContext.md Recent Decisions."""
        try:
            content = self.context_path.read_text()
            lines = content.split("\n")

            # Find "## Recent Decisions" section
            in_recent_decisions = False
            insertion_index = None
            for i, line in enumerate(lines):
                if line.strip() == "## Recent Decisions":
                    in_recent_decisions = False
                if in_recent_decisions and line.strip().startswith("- "):
                    insertion_index = i
                if "## Recent Decisions" in line:
                    in_recent_decisions = True
                    continue
                if in_recent_decisions and line.strip().startswith("## "):
                    # Next section, insert before it
                    insertion_index = i
                    break

            # Build new entry
            status = "✅" if success else "❌"
            new_entry = f"- {status} [{agent}] {task_desc}"

            if insertion_index is None:
                # Append at end of Recent Decisions section
                insertion_index = len(lines)

            # Insert new entry
            lines.insert(insertion_index, new_entry)
            self.context_path.write_text("\n".join(lines))
        except IOError:
            pass  # Non-blocking - don't fail on context write

    def _append_to_log(self, completion: TaskCompletion) -> None:
        """Append completion event to JSONL log with file locking."""
        try:
            with open(self.log_path, "a") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    f.write(json.dumps(asdict(completion)) + "\n")
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except IOError:
            pass  # Non-blocking - don't fail on log write

    def write_completion(
        self,
        task_id: str,
        description: str,
        success: bool,
        agent: str,
        duration_ms: float,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Write task completion to all session tracking files.

        This method is thread-safe and non-blocking. It spawns a background
        thread to perform the actual writes.

        Args:
            task_id: Unique identifier for the task
            description: What was accomplished
            success: Whether task succeeded
            agent: Agent that handled the task
            duration_ms: How long the task took
            metadata: Optional additional metadata
        """
        completion = TaskCompletion(
            task_id=task_id,
            description=description,
            success=success,
            agent=agent,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )

        # Spawn non-blocking thread for writes
        thread = threading.Thread(
            target=self._write_completion_internal,
            args=(completion,),
            daemon=True,
        )
        thread.start()

    def _write_completion_internal(self, completion: TaskCompletion) -> None:
        """Internal method to perform writes (runs in background thread)."""
        with self._lock:
            # Update session-state.json
            state = self._read_state()
            state["last_agent"] = completion.agent
            state["last_action"] = (
                f"Task {completion.task_id}: {'completed' if completion.success else 'failed'}"
            )
            state["last_updated"] = datetime.now(timezone.utc).isoformat()
            state["current_task"] = completion.description

            # Add to completed_changes if successful
            if completion.success:
                completed = state.get("completed_changes", [])
                entry = f"[{completion.agent}] {completion.description}"
                # Keep last 50 entries
                completed = [entry] + completed[:49]
                state["completed_changes"] = completed

            self._write_state(state)

            # Append to activeContext.md
            self._append_to_context(
                completion.description, completion.success, completion.agent
            )

            # Append to session-log.jsonl
            self._append_to_log(completion)

    def write_completion_sync(
        self,
        task_id: str,
        description: str,
        success: bool,
        agent: str,
        duration_ms: float,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Synchronous version of write_completion.

        Use this when you need to ensure writes complete before continuing.
        """
        completion = TaskCompletion(
            task_id=task_id,
            description=description,
            success=success,
            agent=agent,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )
        self._write_completion_internal(completion)

    def get_state(self) -> dict[str, Any]:
        """Get current session state."""
        with self._lock:
            return self._read_state()

    def get_recent_tasks(self, limit: int = 10) -> list[TaskCompletion]:
        """Get recent task completions from log."""
        completions = []
        try:
            if self.log_path.exists():
                with open(self.log_path) as f:
                    for line in f:
                        if line.strip():
                            try:
                                completions.append(TaskCompletion(**json.loads(line)))
                            except json.JSONDecodeError:
                                continue
        except IOError:
            pass
        return completions[:limit]


# Singleton instance for convenience
_default_writer: Optional[SessionWriter] = None
_default_lock = threading.Lock()


def get_session_writer() -> SessionWriter:
    """Get the default SessionWriter instance."""
    global _default_writer
    with _default_lock:
        if _default_writer is None:
            _default_writer = SessionWriter()
        return _default_writer
