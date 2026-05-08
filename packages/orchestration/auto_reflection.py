#!/usr/bin/env python3
"""Auto-Reflection Engine - Phase 5.2: Automatic reflection on failures.

This module implements the Stuck Protocol as an automatic feature -
agents反思 their failures and generate alternative approaches.

Usage:
    reflector = AutoReflector()
    reflection = reflector.reflect(failure_dict)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Session recovery state storage
_RECOVERY_STATE_DIR: Optional[Path] = None


def _get_recovery_dir() -> Path:
    """Get recovery state directory, fallback to /tmp if needed."""
    global _RECOVERY_STATE_DIR
    if _RECOVERY_STATE_DIR is None:
        try:
            # Try ~/.nxyme/recovery first
            _RECOVERY_STATE_DIR = Path.home() / ".nxyme" / "recovery"
            _RECOVERY_STATE_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            # Fallback to /tmp
            _RECOVERY_STATE_DIR = Path("/tmp/nxyme_recovery")
            _RECOVERY_STATE_DIR.mkdir(parents=True, exist_ok=True)
            logger.warning("Using fallback recovery directory /tmp/nxyme_recovery")
    return _RECOVERY_STATE_DIR


def _filter_sensitive(data: dict) -> dict:
    """Filter out sensitive data from state before saving."""
    sensitive_keys = {
        "token",
        "password",
        "secret",
        "api_key",
        "private_key",
        "credential",
        "auth",
        "bearer",
        "access_token",
        "refresh_token",
    }
    return {
        k: v for k, v in data.items() if not any(s in k.lower() for s in sensitive_keys)
    }


def _save_session_state(state: dict, task_id: str) -> str:
    """Save current session state for recovery.

    Args:
        state: Current task state to save (context, attempts, etc.)
        task_id: Unique task identifier

    Returns:
        Path to saved state file
    """
    # Filter sensitive data before saving
    safe_state = _filter_sensitive(state)
    safe_state["saved_at"] = datetime.now().isoformat()

    recovery_dir = _get_recovery_dir()
    state_file = (
        recovery_dir
        / f"session_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(state_file, "w") as f:
        json.dump(safe_state, f, indent=2)
    return str(state_file)


def _load_session_state(task_id: str) -> Optional[dict]:
    """Load most recent session state for task_id.

    Args:
        task_id: Unique task identifier

    Returns:
        State dict if found, None otherwise
    """
    recovery_dir = _get_recovery_dir()
    sessions = sorted(
        recovery_dir.glob(f"session_{task_id}_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if sessions:
        with open(sessions[0]) as f:
            return json.load(f)
    return None


def _clear_session_state(task_id: str) -> None:
    """Clear session state after successful recovery.

    Args:
        task_id: Unique task identifier
    """
    recovery_dir = _get_recovery_dir()
    for f in recovery_dir.glob(f"session_{task_id}_*.json"):
        f.unlink()


@dataclass
class Reflection:
    """A reflection on a failure."""

    what_tried: str
    what_failed: str
    why_it_failed: str
    what_will_do_differently: str
    alternative_agents: list[str] = field(default_factory=list)
    confidence: float = 0.5


class AutoReflector:
    """Automatic reflection on task failures."""

    def __init__(self):
        """Initialize auto-reflector."""
        self.reflection_history: list[Reflection] = []

    def on_stuck(self, task_id: str, state: dict) -> str:
        """Called when task gets stuck - save state for recovery.

        Args:
            task_id: Unique task identifier
            state: Current task state to save (context, attempts, etc.)

        Returns:
            Path to saved state file
        """
        state["stuck_at"] = datetime.now().isoformat()
        state["attempt_count"] = state.get("attempt_count", 0) + 1

        saved_path = _save_session_state(state, task_id)
        logger.warning(f"Task {task_id} stuck - state saved to {saved_path}")

        return saved_path

    def on_retry(self, task_id: str) -> Optional[dict]:
        """Called when retrying a stuck task - restore previous state.

        Args:
            task_id: Unique task identifier

        Returns:
            Restored state dict, or None if no state found
        """
        state = _load_session_state(task_id)
        if state:
            logger.info(f"Task {task_id} recovered state from previous attempt")
        return state

    def on_recovery_complete(self, task_id: str) -> None:
        """Called after successful recovery - clean up state.

        Args:
            task_id: Unique task identifier
        """
        _clear_session_state(task_id)
        logger.info(f"Task {task_id} recovery complete - state cleared")

    def track_attempt(self, task_id: str, attempt: int, context: dict) -> dict:
        """Track an attempt and check if stuck (3+ failures).

        Args:
            task_id: Unique task identifier
            attempt: Current attempt number
            context: Current context

        Returns:
            dict with is_stuck (bool) and recovery_state if stuck
        """
        is_stuck = attempt >= 3

        if is_stuck:
            safe_context = _filter_sensitive(context)
            state = safe_context.copy()
            state["attempt"] = attempt
            recovery_path = self.on_stuck(task_id, state)
            return {
                "is_stuck": True,
                "recovery_state": state,
                "saved_to": recovery_path,
            }

        return {"is_stuck": False, "recovery_state": None}

    def reflect(self, failure: dict[str, Any]) -> Reflection:
        """Generate a reflection on a failure.

        Args:
            failure: Dict with keys: attempted, error, task_type, agent

        Returns:
            Reflection object with analysis
        """
        attempted = failure.get("attempted", "unknown task")
        error = failure.get("error", "unknown error")
        task_type = failure.get("task_type", "general")
        agent = failure.get("agent", "unknown")

        # Root cause analysis
        why_failed = self._analyze_root_cause(attempted, error, task_type)

        # Generate alternative approach
        alternative = self._generate_alternative(attempted, task_type, agent)

        # Suggest alternative agents
        alt_agents = self._suggest_alternative_agents(task_type, agent)

        # Calculate confidence based on available data
        confidence = self._calculate_confidence(failure)

        reflection = Reflection(
            what_tried=attempted,
            what_failed=error,
            why_it_failed=why_failed,
            what_will_do_differently=alternative,
            alternative_agents=alt_agents,
            confidence=confidence,
        )

        self.reflection_history.append(reflection)
        return reflection

    def _analyze_root_cause(self, attempted: str, error: str, task_type: str) -> str:
        """Analyze root cause of failure."""
        attempted_lower = attempted.lower()
        error_lower = error.lower() if isinstance(error, str) else str(error)

        # Common patterns
        if "timeout" in error_lower or "took too long" in error_lower:
            return "Task was too complex for the allocated time. Should break into smaller steps."

        if "not found" in error_lower or "no such file" in error_lower:
            if any(k in attempted_lower for k in ["search", "find", "grep"]):
                return "Search pattern too specific or target doesn't exist. Need broader search."
            return "Path or resource doesn't exist. Need to verify target exists first."

        if "permission" in error_lower or "denied" in error_lower:
            return "Access denied. Check file permissions or paths."

        if "syntax" in error_lower or "parse" in error_lower:
            return "Input format incorrect. Check syntax or provide clearer format."

        if "ambiguous" in error_lower or "unclear" in error_lower:
            return "Task description was ambiguous. Need more specific instructions."

        if "retry" in error_lower or "attempt" in error_lower:
            return "Task was attempted but failed. May need different approach."

        # Default
        return "Unknown failure mode. Need more context to determine root cause."

    def _generate_alternative(self, attempted: str, task_type: str, agent: str) -> str:
        """Generate alternative approach."""
        alternatives = {
            "implementation": [
                "break task into smaller, atomic steps",
                "add more context and reference files",
                "use simpler, more explicit instructions",
            ],
            "research": [
                "use broader search terms",
                "start with explore before detailed search",
                "add file type filters to narrow results",
            ],
            "fix": [
                "first understand the code structure with explore",
                "narrow scope to specific file/line",
                "add error message to help diagnose",
            ],
            "review": [
                "specify specific areas to review",
                "provide clear evaluation criteria",
                "limit scope to single component",
            ],
        }

        options = alternatives.get(task_type, alternatives["implementation"])
        return options[0] if options else "try different approach"

    def _suggest_alternative_agents(
        self, task_type: str, current_agent: str
    ) -> list[str]:
        """Suggest alternative agents."""
        # Map task types to alternative agents
        alternatives = {
            "implementation": ["hephaestus", "sisyphus-junior", "atlas"],
            "research": ["explore", "librarian", "oracle"],
            "fix": ["hephaestus", "sisyphus-junior", "oracle"],
            "review": ["oracle", "momus", "atlas"],
        }

        options = alternatives.get(task_type, ["hephaestus", "explore"])
        return [a for a in options if a != current_agent][:2]

    def _calculate_confidence(self, failure: dict[str, Any]) -> float:
        """Calculate confidence in the reflection."""
        # Higher confidence if we have more failure details
        score = 0.5

        if failure.get("attempted"):
            score += 0.1
        if failure.get("error"):
            score += 0.1
        if failure.get("task_type"):
            score += 0.1
        if failure.get("agent"):
            score += 0.1

        return min(score, 0.9)

    def get_recent_reflections(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent reflections.

        Args:
            limit: Maximum reflections to return

        Returns:
            List of reflection dicts
        """
        recent = self.reflection_history[-limit:]
        return [
            {
                "what_tried": r.what_tried,
                "what_failed": r.what_failed,
                "why_it_failed": r.why_it_failed,
                "what_will_do_differently": r.what_will_do_differently,
                "alternative_agents": r.alternative_agents,
                "confidence": r.confidence,
            }
            for r in recent
        ]

    def auto_reflect_on_outcome(
        self,
        task: str,
        agent: str,
        success: bool,
        error_message: Optional[str] = None,
    ) -> Optional[Reflection]:
        """Auto-generate reflection based on task outcome.

        Args:
            task: Task description
            agent: Agent used
            success: Whether task succeeded
            error_message: Error message if failed

        Returns:
            Reflection if failed, None if succeeded
        """
        if success:
            return None

        failure = {
            "attempted": task,
            "error": error_message or "task failed",
            "task_type": self._infer_task_type(task),
            "agent": agent,
        }

        return self.reflect(failure)

    def _infer_task_type(self, task: str) -> str:
        """Infer task type from task description."""
        task_lower = task.lower()

        if any(k in task_lower for k in ["add", "implement", "create", "write", "fix"]):
            return "implementation"
        if any(k in task_lower for k in ["search", "find", "where", "look"]):
            return "research"
        if any(k in task_lower for k in ["bug", "error", "broken", "fails"]):
            return "fix"
        if any(k in task_lower for k in ["review", "check", "validate"]):
            return "review"

        return "general"


# Singleton
_reflector: Optional[AutoReflector] = None


def get_auto_reflector() -> AutoReflector:
    """Get or create singleton auto-reflector."""
    global _reflector
    if _reflector is None:
        _reflector = AutoReflector()
    return _reflector
