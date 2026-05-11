"""Session lifecycle management.

Provides session lifecycle hooks for memory integration:
- Pre-session context loading
- Post-session summary saving
- Session state management
"""

import fcntl
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
SESSION_STATE_PATH = PROJECT_ROOT / ".sisyphus" / "session-state.json"
ACTIVE_CONTEXT_PATH = PROJECT_ROOT / ".context" / "activeContext.md"


def load_memory_context(query: str = "current project context", limit: int = 5) -> str:
    """Load relevant memory context before session starts.

    Args:
        query: Query to find relevant memories
        limit: Maximum memories to load

    Returns:
        Formatted memory context string
    """
    try:
        from packages.memory_core.mcp_server import search_memories, recall_session

        result = search_memories(query, limit=limit)
        memories = result.get("results", [])

        if not memories:
            return ""

        context_parts = [f"# Memory Context ({len(memories)} relevant memories)\n"]
        for i, m in enumerate(memories, 1):
            source = m.get("source", "unknown")
            content = m.get("content", "")[:500]
            context_parts.append(f"## Memory {i} [{source}]\n{content}\n")

        return "\n".join(context_parts)
    except Exception as e:
        logger.warning(f"Failed to load memory context: {e}")
        return ""


def save_session_summary(session_summary: dict) -> bool:
    """Save session summary to memory after session ends.

    Args:
        session_summary: Dict with session details

    Returns:
        True if saved successfully
    """
    try:
        from packages.memory_core.mcp_server import create_memory

        summary_text = json.dumps(session_summary, indent=2)
        result = create_memory(
            content=f"Session Summary:\n{summary_text}",
            kind="summary",
            scope="global",
            tags=["session", "summary"],
            metadata={"type": "session_summary"},
        )
        return result.get("status") == "ok"
    except Exception as e:
        logger.warning(f"Failed to save session summary: {e}")
        return False


def update_session_state(
    action: str,
    task: str,
    completed: Optional[list] = None,
    pending: Optional[list] = None,
):
    """Update session state file.

    Args:
        action: Last action performed
        task: Current task
        completed: List of completed changes
        pending: List of pending changes
    """
    state = {
        "last_agent": "Sisyphus",
        "last_action": action,
        "session_started": datetime.now(timezone.utc).isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "current_task": task,
        "pending_changes": pending or [],
        "completed_changes": completed or [],
    }

    if SESSION_STATE_PATH.exists():
        try:
            with open(SESSION_STATE_PATH) as f:
                existing = json.load(f)
            state["completed_changes"] = existing.get("completed_changes", []) + (
                completed or []
            )
            state["pending_changes"] = pending or existing.get("pending_changes", [])
        except Exception:
            pass

    SESSION_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = SESSION_STATE_PATH.with_suffix(".json.tmp")
    with open(temp_path, "w") as tf:
        json.dump(state, tf, indent=2)
    with open(SESSION_STATE_PATH) as sf, open(temp_path) as tf:
        fcntl.flock(sf.fileno(), fcntl.LOCK_EX)
        try:
            fcntl.flock(tf.fileno(), fcntl.LOCK_EX)
            os.replace(temp_path, SESSION_STATE_PATH)
        finally:
            fcntl.flock(sf.fileno(), fcntl.LOCK_UN)
            fcntl.flock(tf.fileno(), fcntl.LOCK_UN)


def update_active_context(session_summary: dict):
    """Update activeContext.md with session results.

    Args:
        session_summary: Dict with session details
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    content = f"""# Active Context

## Current Session
- **Started**: {now}
- **Focus**: {session_summary.get("focus", "General development")}
- **Status**: {"Completed" if session_summary.get("completed") else "Active"}

## Active Tasks
{chr(10).join(f"- {t}" for t in session_summary.get("active_tasks", []))}

## Recent Decisions
{chr(10).join(f"- {d}" for d in session_summary.get("decisions", []))}

## Unresolved Issues
{chr(10).join(f"- {i}" for i in session_summary.get("unresolved", []))}

## Session Summary
- Files changed: {session_summary.get("files_changed", 0)}
- Memories created: {session_summary.get("memories_created", 0)}
- Tasks completed: {session_summary.get("tasks_completed", 0)}
"""

    ACTIVE_CONTEXT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ACTIVE_CONTEXT_PATH, "w") as f:
        f.write(content)


class SessionLifecycle:
    """Session lifecycle manager for memory integration."""

    def __init__(self):
        self.start_time = datetime.now(timezone.utc)
        self.context_loaded = False

    def load_context(self, query: str = "current project context") -> str:
        """Load memory context before session."""
        context = load_memory_context(query)
        self.context_loaded = bool(context)
        return context

    def save_summary(self, summary: dict) -> bool:
        """Save session summary after session ends."""
        return save_session_summary(summary)

    def update_state(self, action: str, task: str, completed=None, pending=None):
        """Update session state."""
        update_session_state(action, task, completed, pending)

    def update_context(self, summary: dict):
        """Update active context."""
        update_active_context(summary)