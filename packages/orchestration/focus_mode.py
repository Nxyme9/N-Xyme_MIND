"""
Focus Mode — ADHD-friendly focus and productivity tools (ported from LIVE)

Provides Pomodoro-style focus sessions with distraction blocking.

Usage:
    focus = FocusMode()
    session = focus.start("Work on RAG service", minutes=25)
    # ... work ...
    focus.complete()
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class FocusType(Enum):
    """Types of focus sessions."""

    POMODORO = "pomodoro"  # 25 min work, 5 min break
    DEEP_WORK = "deep_work"  # 90 min work, 15 min break
    SPRINT = "sprint"  # 50 min work, 10 min break
    FREE_FORM = "free_form"  # No time limit


class FocusState(Enum):
    """Focus session states."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    BREAK = "break"
    COMPLETED = "completed"


@dataclass
class FocusSession:
    """A focus session."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    focus_type: FocusType = FocusType.POMODORO
    duration_minutes: int = 25
    state: FocusState = FocusState.IDLE
    started_at: float = 0.0
    paused_at: float = 0.0
    completed_at: float = 0.0
    tasks_completed: int = 0
    distractions_blocked: int = 0


# Presets
FOCUS_PRESETS = {
    "pomodoro": {"work": 25, "break": 5},
    "deep_work": {"work": 90, "break": 15},
    "sprint": {"work": 50, "break": 10},
}


class FocusMode:
    """ADHD-friendly focus management."""

    def __init__(self):
        self.current_session: Optional[FocusSession] = None
        self.history: List[FocusSession] = []
        self._callbacks: Dict[str, List[Callable]] = {
            "on_start": [],
            "on_break": [],
            "on_complete": [],
            "on_distraction": [],
        }
        logger.info("FocusMode: Initialized")

    def start(
        self,
        title: str,
        minutes: int = 25,
        focus_type: str = "pomodoro",
    ) -> FocusSession:
        """Start a focus session."""
        session = FocusSession(
            title=title,
            focus_type=FocusType(focus_type),
            duration_minutes=minutes,
            state=FocusState.RUNNING,
            started_at=time.time(),
        )
        self.current_session = session
        self.history.append(session)

        self._notify("on_start", session)
        logger.info(f"FocusMode: Started '{title}' ({minutes}min)")
        return session

    def pause(self) -> bool:
        """Pause current session."""
        if self.current_session and self.current_session.state == FocusState.RUNNING:
            self.current_session.state = FocusState.PAUSED
            self.current_session.paused_at = time.time()
            logger.info("FocusMode: Paused")
            return True
        return False

    def resume(self) -> bool:
        """Resume paused session."""
        if self.current_session and self.current_session.state == FocusState.PAUSED:
            self.current_session.state = FocusState.RUNNING
            logger.info("FocusMode: Resumed")
            return True
        return False

    def complete(self) -> Optional[FocusSession]:
        """Complete current session."""
        if self.current_session:
            self.current_session.state = FocusState.COMPLETED
            self.current_session.completed_at = time.time()
            self._notify("on_complete", self.current_session)
            logger.info(f"FocusMode: Completed '{self.current_session.title}'")
            session = self.current_session
            self.current_session = None
            return session
        return None

    def block_distraction(self, source: str = "unknown") -> None:
        """Record a blocked distraction."""
        if self.current_session:
            self.current_session.distractions_blocked += 1
            self._notify("on_distraction", {"source": source})
            logger.info(f"FocusMode: Blocked distraction from {source}")

    def get_time_remaining(self) -> Optional[float]:
        """Get remaining time in minutes."""
        if self.current_session and self.current_session.state == FocusState.RUNNING:
            elapsed = (time.time() - self.current_session.started_at) / 60
            remaining = self.current_session.duration_minutes - elapsed
            return max(0, remaining)
        return None

    def get_stats(self) -> Dict:
        """Get focus statistics."""
        total_sessions = len(self.history)
        completed = sum(1 for s in self.history if s.state == FocusState.COMPLETED)
        total_minutes = sum(
            (s.completed_at - s.started_at) / 60
            for s in self.history
            if s.completed_at and s.started_at
        )
        total_distractions = sum(s.distractions_blocked for s in self.history)

        return {
            "total_sessions": total_sessions,
            "completed": completed,
            "total_minutes": round(total_minutes, 1),
            "total_distractions_blocked": total_distractions,
        }

    def on(self, event: str, callback: Callable):
        """Register event callback."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def _notify(self, event: str, data):
        """Notify event callbacks."""
        for callback in self._callbacks.get(event, []):
            try:
                callback(data)
            except Exception as e:
                logger.error(f"FocusMode: Callback error: {e}")
