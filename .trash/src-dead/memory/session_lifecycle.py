#!/usr/bin/env python3
"""Session lifecycle wrapper with automatic memory integration.

This script wraps OpenCode sessions to:
1. Load memory context BEFORE session starts (pre-response read)
2. Save session summary to memory AFTER session ends (post-task write)
3. Track session state and update active context

Usage:
    python3 src/memory/session_lifecycle.py [opencode args...]
"""

import json
import logging
import os
import sys
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
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
        from src.memory.mcp_server import search_memories, recall_session

        # Search for relevant context
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
        from src.memory.mcp_server import create_memory

        # Create memory entry for this session
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
    action: str, task: str, completed: list = None, pending: list = None
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

    # Load existing state if available
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
    with open(SESSION_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


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


def run_session(args: list = None):
    """Run a full session with memory integration.

    Args:
        args: Arguments to pass to OpenCode
    """
    # Step 1: Pre-session memory load
    logger.info("📖 Loading memory context...")
    memory_context = load_memory_context()
    if memory_context:
        logger.info(f"  Loaded {len(memory_context)} chars of memory context")
        # Save context to temp file for agent to read
        context_path = PROJECT_ROOT / ".context" / "session-memory-context.md"
        with open(context_path, "w") as f:
            f.write(memory_context)
        logger.info(f"  Saved to {context_path}")
    else:
        logger.info("  No relevant memory context found")

    # Step 2: Update session state
    logger.info("📝 Updating session state...")
    update_session_state(
        action="Session started",
        task="Active development",
        completed=[],
        pending=["Complete current tasks"],
    )

    # Step 3: Run OpenCode
    logger.info("🚀 Starting OpenCode session...")
    start_time = time.time()

    try:
        cmd = [str(PROJECT_ROOT / "venvs/athena/bin/python"), "-m", "opencode"]
        if args:
            cmd.extend(args)

        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
        exit_code = result.returncode
    except KeyboardInterrupt:
        logger.info("Session interrupted by user")
        exit_code = 0
    except Exception as e:
        logger.error(f"Session failed: {e}")
        exit_code = 1

    duration = time.time() - start_time

    # Step 4: Post-session memory save
    logger.info("💾 Saving session summary...")
    session_summary = {
        "date": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(duration, 1),
        "exit_code": exit_code,
        "focus": "Development session",
        "active_tasks": [],
        "decisions": [],
        "unresolved": [],
        "files_changed": 0,
        "memories_created": 0,
        "tasks_completed": 0,
        "completed": exit_code == 0,
    }

    save_session_summary(session_summary)
    update_active_context(session_summary)
    update_session_state(
        action="Session completed",
        task="Session ended",
        completed=[f"Session completed ({duration:.0f}s)"],
        pending=[],
    )

    logger.info(f"✅ Session ended — memory saved ({duration:.0f}s)")
    return exit_code


if __name__ == "__main__":
    sys.exit(run_session(sys.argv[1:]))
