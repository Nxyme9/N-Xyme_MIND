"""
Fingerprint namespace tools for nx-brain-mcp.

This module contains all fingerprint-related MCP tools.
Functions are registered manually in __init__.py after MCP is available.
"""

from __future__ import annotations

import logging
import signal
import threading
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ============================================================================
# CIRCUIT BREAKER - Prevent hangs on slow context queries
# ============================================================================


class TimeoutError(Exception):
    """Raised when operation times out."""

    pass


def _timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")


def run_with_timeout(seconds: float, func, *args, **kwargs):
    """Run function with timeout to prevent hangs."""
    # Only works on Unix - skip on Windows
    if threading.current_thread().name == "MainThread":
        try:
            old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(int(seconds))
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
            return result
        except (signal.Signals, AttributeError):
            # Windows or signal not available - run without timeout
            return func(*args, **kwargs)
    else:
        # Can't use signals in non-main thread - run without timeout
        return func(*args, **kwargs)


INJECTION_TIMEOUT = 2.0  # 2 seconds max for context injection

# ============================================================================
# LAZY INITIALIZATION FLAG - Prevent hangs on startup
# ============================================================================
# Set to False to disable auto-injection on first message (prevents startup hangs)
# Set to True after you've verified the system works without hangs
AUTO_INJECT_ENABLED = True  # ENABLED - timeout protection prevents hangs


# ============================================================================
# SESSION FINGERPRINTING TOOLS (fingerprint.*) - Personal Brain Context
# ============================================================================


def fingerprint_get_session_context(
    current_task: str, max_sessions: int = 3
) -> dict[str, Any]:
    """Get contextual memory from past sessions for current task.

    This implements session fingerprinting - the system learns your patterns
    and injects relevant context before you even ask.

    Returns relevant context from previous sessions that relate to current task,
    user preferences, and ongoing work patterns.
    """
    try:
        from context_store import get_archive_context

        result = get_archive_context(query=current_task, max_sessions=max_sessions)
        return {
            "current_task": current_task,
            "context": result.get("content", ""),
            "sessions_found": result.get("sessions_found", 0),
            "status": "success",
        }
    except Exception as e:
        return {"error": str(e), "status": "error"}


def fingerprint_record_pattern(
    action_type: str, outcome: str, context: Optional[dict] = None
) -> dict[str, Any]:
    """Record a user action pattern for learning.

    Records action sequences (e.g., 'commit after tests') for pattern extraction.
    This feeds into the self-learning system for predictive routing.
    """
    try:
        from packages.learning_engine.outcome_logger import record_outcome

        success = outcome in ("success", "completed", "passed")
        record_outcome(
            task=action_type,
            agent="fingerprint",
            success=success,
            latency_ms=0,
            tokens_used=0,
        )

        # Also write to memory for semantic search
        from packages.memory_store.mcp_server import memory_write

        memory_write(
            content=f"User pattern: {action_type} -> {outcome}",
            kind="episodic",
            scope="global",
            metadata=context or {},
        )

        return {"status": "recorded", "action": action_type, "outcome": outcome}
    except Exception as e:
        return {"error": str(e), "status": "error"}


def fingerprint_get_user_preferences() -> dict[str, Any]:
    """Get learned user preferences and style context."""
    try:
        from context_store import get_style_context, get_user_profile

        style = get_style_context()
        profile = get_user_profile()

        return {
            "style": style,
            "profile": profile,
            "status": "success",
        }
    except Exception as e:
        return {"error": str(e), "status": "error"}


# ============================================================================
# PHASE 3.1: TOOL SEQUENCE LOGGING
# ============================================================================


def log_tool_sequence(
    task: str,
    sequence: list,
    outcome: str,
    duration_ms: float = 0.0,
) -> dict[str, Any]:
    """Log a sequence of tool calls for composite action analysis (Phase 3.1).

    This enables the system to learn common tool sequences like:
    - [grep → read → edit → lsp_diagnostics] = "code modification"
    - [explore → read → grep] = "research and verify"

    Args:
        task: Task description
        sequence: List of tool calls [{"tool": "name", "args": {...}}, ...]
        outcome: "success", "failed", or "partial"
        duration_ms: Total duration of the sequence

    Returns:
        Dict with sequence_id and count
    """
    try:
        from packages.learning_engine.outcome_logger import OutcomeLogger, ToolSequence

        logger = OutcomeLogger()
        seq = ToolSequence(
            task_id=f"seq_{int(time.time() * 1000)}",
            task_description=task,
            sequence=sequence,
            outcome=outcome,
            duration_ms=duration_ms,
        )
        seq_id = logger.log_sequence(seq)
        total = logger.get_sequence_count()

        return {
            "status": "logged",
            "sequence_id": seq_id,
            "total_sequences": total,
            "task": task,
            "tool_count": len(sequence),
        }
    except Exception as e:
        return {"error": str(e), "status": "error"}


# ============================================================================
# PHASE 1.4: PRE-AGENT MEMORY INJECTOR (Token Budget: 500 tokens)
# ============================================================================


def memory_inject_context(
    agent: str,
    task: str,
    max_tokens: int = 500,
) -> dict[str, Any]:
    """Inject contextual memory BEFORE agent dispatch.

    This implements Phase 1.4 of the revised masterplan:
    - Search memory for relevant context to current task
    - Rank by importance (success * 1.0 + recency * 0.5 + similarity * 0.3)
    - Compress to fit token budget (default 500 tokens max)
    - Return formatted context block for injection into agent prompt

    This is the KEY MISSING PIECE - memory injection wasn't automatic before.
    """
    try:
        from packages.memory_store.mcp_server import search_memories

        # Step 1: Search memory for relevant context
        search_result = search_memories(query=task, limit=5, strict=False, rerank=True)

        if isinstance(search_result, dict) and "error" in search_result:
            return {"error": search_result.get("error"), "injected_context": ""}

        results = (
            search_result.get("results", []) if isinstance(search_result, dict) else []
        )

        if not results:
            return {
                "status": "no_context",
                "injected_context": "",
                "agent": agent,
                "task": task,
            }

        # Step 2: Rank by importance (already sorted, but ensure scoring)
        ranked = []
        for mem in results:
            importance = mem.get("metadata", {}).get("importance", 0.5)
            ranked.append(
                {
                    "content": mem.get("content", ""),
                    "importance": importance,
                }
            )

        # Sort by importance descending
        ranked.sort(key=lambda x: x["importance"], reverse=True)

        # Step 3: Compress to token budget
        # Estimate: ~4 characters per token, so max_tokens * 4 = max characters
        max_chars = max_tokens * 4
        compressed_parts = []

        for item in ranked[:3]:  # Top 3 memories
            content = item["content"]
            if len(content) > max_chars // 3:
                # Ellipsize if too long
                content = content[: max_chars // 3 - 10] + "..."
            compressed_parts.append(content)

        injected = "\n\n".join(compressed_parts)

        # Final truncate if still over
        if len(injected) > max_chars:
            injected = injected[: max_chars - 10] + "..."

        return {
            "status": "success",
            "injected_context": injected,
            "agent": agent,
            "task": task,
            "tokens_used": len(injected) // 4,  # Approximate token count
            "memories_injected": len(compressed_parts),
            "format": "[CONTEXT FROM MEMORY]\n{content}\n[/CONTEXT]",
        }
    except Exception as e:
        return {"error": str(e), "injected_context": ""}


# ============================================================================
# PHASE 1.5: ORCHESTRATION INTEGRATION
# ============================================================================


def orchestration_get_injected_context(agent: str, task: str) -> dict[str, Any]:
    """Get all injected context for agent dispatch (memory + fingerprint + preferences).

    This implements Phase 1.5 - combining:
    - Phase 1.4: Pre-agent memory injection
    - Phase 2: Session fingerprinting (existing tools)
    - User preferences

    Returns unified context block for orchestration layer to inject.
    """
    try:
        # Get memory context (Phase 1.4)
        memory_ctx = memory_inject_context(agent=agent, task=task, max_tokens=300)

        # Get session context (Phase 2 - existing tool)
        session_ctx = fingerprint_get_session_context(current_task=task, max_sessions=2)

        # Get user preferences (Phase 2 - existing tool)
        prefs = fingerprint_get_user_preferences()

        # Combine into unified context
        combined_parts = []

        # Add memory context
        if memory_ctx.get("injected_context"):
            combined_parts.append(
                f"[MEMORY]\n{memory_ctx.get('injected_context')}\n[/MEMORY]"
            )

        # Add session context
        if session_ctx.get("context"):
            combined_parts.append(
                f"[SESSION]\n{session_ctx.get('context')}\n[/SESSION]"
            )

        # Add user preferences summary (brief)
        if prefs.get("profile"):
            profile = prefs.get("profile", {})
            pref_summary = f"User: {profile.get('name', 'unknown')}, Style: {prefs.get('style', {}).get('preferred_language', 'not set')}"
            combined_parts.append(f"[PREFERENCES]\n{pref_summary}\n[/PREFERENCES]")

        # Combine with budget check
        full_context = "\n\n".join(combined_parts)

        # Enforce total budget: 500 tokens max
        max_total_tokens = 500
        max_total_chars = max_total_tokens * 4

        if len(full_context) > max_total_chars:
            # Prioritize: memory > session > preferences
            if len(combined_parts) > 1:
                full_context = full_context[: max_total_chars - 10] + "..."

        return {
            "status": "success",
            "injected_context": full_context,
            "components": {
                "memory": bool(memory_ctx.get("injected_context")),
                "session": bool(session_ctx.get("context")),
                "preferences": bool(prefs.get("profile")),
            },
            "tokens_approx": len(full_context) // 4,
            "agent": agent,
            "task": task,
        }
    except Exception as e:
        return {"error": str(e), "injected_context": ""}


# ============================================================================
# CROSS-SESSION GLOBAL CONTEXT (NEW)
# ============================================================================

# Global workspace memory cache - persists across all sessions
_GLOBAL_WORKSPACE_CONTEXT: dict = {
    "initialized": False,
    "project_summary": "",
    "active_files": [],
    "key_decisions": [],
    "architecture_notes": "",
}

# Thread lock for thread-safe access to _GLOBAL_WORKSPACE_CONTEXT
_GLOBAL_CONTEXT_LOCK = threading.Lock()


def get_global_context() -> dict[str, Any]:
    """Get global workspace context that persists across sessions.

    This provides cross-session awareness - information about the project
    that's visible to ALL sessions, not just the current one.

    Returns:
        dict with global context components
    """
    with _GLOBAL_CONTEXT_LOCK:
        return {
            "status": "success",
            "scope": "global",
            "components": _GLOBAL_WORKSPACE_CONTEXT.copy(),
        }


def update_global_context(
    project_summary: Optional[str] = None,
    active_files: Optional[list] = None,
    key_decisions: Optional[list] = None,
    architecture_notes: Optional[str] = None,
) -> dict[str, Any]:
    """Update global workspace context (cross-session visible).

    This updates context that's shared across ALL sessions.
    Use this to share important project state with future sessions.

    Args:
        project_summary: Brief summary of the project
        active_files: List of currently active/modified files
        key_decisions: Important architectural decisions
        architecture_notes: Technical architecture notes

    Returns:
        dict with update status
    """
    with _GLOBAL_CONTEXT_LOCK:
        if project_summary is not None:
            _GLOBAL_WORKSPACE_CONTEXT["project_summary"] = project_summary
        if active_files is not None:
            _GLOBAL_WORKSPACE_CONTEXT["active_files"] = active_files
        if key_decisions is not None:
            _GLOBAL_WORKSPACE_CONTEXT["key_decisions"] = key_decisions
        if architecture_notes is not None:
            _GLOBAL_WORKSPACE_CONTEXT["architecture_notes"] = architecture_notes

        _GLOBAL_WORKSPACE_CONTEXT["initialized"] = True

        return {
            "status": "updated",
            "scope": "global",
            "context": _GLOBAL_WORKSPACE_CONTEXT.copy(),
        }


def get_cross_session_context(task: str, max_tokens: int = 300) -> dict[str, Any]:
    """Get context from ALL past sessions, not just recent.

    This provides TRUE cross-session awareness - scanning memories
    from sessions days/weeks ago for relevant context.

    Args:
        task: Current task to find relevant memories for
        max_tokens: Maximum tokens for context (default 300)

    Returns:
        dict with cross-session context
    """
    try:
        from packages.memory_store.mcp_server import search_memories

        # Search with no time restriction - get ALL relevant memories
        search_result = search_memories(query=task, limit=10, strict=False, rerank=True)

        if isinstance(search_result, dict) and "error" in search_result:
            return {"error": search_result.get("error"), "cross_session_context": ""}

        results = (
            search_result.get("results", []) if isinstance(search_result, dict) else []
        )

        if not results:
            return {
                "status": "no_cross_session_context",
                "cross_session_context": "",
                "sessions_found": 0,
            }

        # Compress to token budget
        max_chars = max_tokens * 4
        context_parts = []

        for mem in results[:5]:  # Top 5 cross-session memories
            content = mem.get("content", "")[: max_chars // 5]
            scope = mem.get("scope", "unknown")
            context_parts.append(f"[{scope.upper()}] {content}")

        cross_context = "\n".join(context_parts)[:max_chars]

        return {
            "status": "success",
            "cross_session_context": cross_context,
            "sessions_found": len(results),
            "memories_scanned": len(results),
            "format": "[CROSS-SESSION CONTEXT]\n{content}\n[/CROSS-SESSION CONTEXT]",
        }
    except Exception as e:
        return {"error": str(e), "cross_session_context": ""}


# Enhanced orchestration with global + cross-session
def get_full_injected_context(
    agent: str,
    task: str,
    session_id: Optional[str] = None,
    max_tokens: int = 500,
) -> dict[str, Any]:
    """Get COMPLETE injected context: global + cross-session + session + preferences.

    This is the FULL context stack:
    1. Global workspace context (shared across ALL sessions)
    2. Cross-session memories (past sessions' relevant info)
    3. Current session context
    4. User preferences

    IMPORTANT: If AUTO_INJECT_ENABLED=False, returns empty context to prevent hangs.

    Args:
        agent: Agent name for context tailoring
        task: Current task
        session_id: Optional session ID for session-specific context
        max_tokens: Maximum total tokens (default 500)

    Returns:
        dict with complete injected context
    """
    # Early return if auto-injection is disabled (prevents startup hangs)
    if not AUTO_INJECT_ENABLED:
        return {
            "status": "disabled",
            "injected_context": "",
            "scope": "disabled",
            "global_initialized": False,
            "cross_session_count": 0,
            "tokens_approx": 0,
            "agent": agent,
            "task": task,
        }

    try:
        parts = []

        # 1. Global workspace context (HIGHEST priority - with timeout)
        try:
            global_ctx = run_with_timeout(INJECTION_TIMEOUT, get_global_context)
        except TimeoutError:
            logger.warning("get_global_context timed out, skipping")
            global_ctx = {}
        if global_ctx.get("components", {}).get("initialized"):
            g = global_ctx["components"]
            global_parts = []
            if g.get("project_summary"):
                global_parts.append(f"PROJECT: {g['project_summary']}")
            if g.get("active_files"):
                global_parts.append(f"ACTIVE FILES: {', '.join(g['active_files'][:5])}")
            if g.get("key_decisions"):
                global_parts.append(
                    f"KEY DECISIONS: {'; '.join(g['key_decisions'][-3:])}"
                )
            if global_parts:
                parts.append(f"[GLOBAL]\n" + "\n".join(global_parts) + "\n[/GLOBAL]")

        # 2. Cross-session memories - with timeout to prevent hang
        try:
            cross_ctx = run_with_timeout(
                INJECTION_TIMEOUT,
                get_cross_session_context,
                task,
                max_tokens=max_tokens // 4,
            )
        except TimeoutError:
            logger.warning("get_cross_session_context timed out, skipping")
            cross_ctx = {}
        if cross_ctx.get("cross_session_context"):
            parts.append(
                f"[CROSS-SESSION]\n{cross_ctx['cross_session_context']}\n[/CROSS-SESSION]"
            )

        # 3. Current session context - with timeout
        try:
            session_ctx = run_with_timeout(
                INJECTION_TIMEOUT,
                fingerprint_get_session_context,
                current_task=task,
                max_sessions=2,
            )
        except TimeoutError:
            logger.warning("fingerprint_get_session_context timed out, skipping")
            session_ctx = {}
        if session_ctx.get("context"):
            parts.append(f"[SESSION]\n{session_ctx['context']}\n[/SESSION]")

        # 4. User preferences (minimal) - with timeout
        try:
            prefs = run_with_timeout(
                INJECTION_TIMEOUT, fingerprint_get_user_preferences
            )
        except TimeoutError:
            logger.warning("fingerprint_get_user_preferences timed out, skipping")
            prefs = {}
        if prefs.get("profile"):
            parts.append(
                f"[PREFERENCES] Style: {prefs.get('style', {}).get('preferred_language', 'en')}[/PREFERENCES]"
            )

        # Combine with budget enforcement
        full_context = "\n\n".join(parts)
        max_chars = max_tokens * 4

        if len(full_context) > max_chars:
            # Prioritize: global > cross-session > session > preferences
            full_context = full_context[: max_chars - 10] + "..."

        return {
            "status": "success",
            "injected_context": full_context,
            "scope": "global+cross_session+session+preferences",
            "global_initialized": global_ctx.get("components", {}).get(
                "initialized", False
            ),
            "cross_session_count": cross_ctx.get("sessions_found", 0),
            "tokens_approx": len(full_context) // 4,
            "agent": agent,
            "task": task,
        }
    except Exception as e:
        return {"error": str(e), "injected_context": ""}
