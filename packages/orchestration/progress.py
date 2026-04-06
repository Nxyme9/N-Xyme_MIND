"""Tool Progress — Streaming progress callbacks for long-running tools."""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Callable
from enum import Enum
import time


class ProgressType(Enum):
    READING = "reading"
    WRITING = "writing"
    SEARCHING = "searching"
    PROCESSING = "processing"
    WAITING = "waiting"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class ToolProgress:
    """Progress update from a tool."""
    tool_name: str
    type: ProgressType
    message: str
    progress: float = 0.0  # 0.0 to 1.0
    data: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=time.time)


class ProgressTracker:
    """Tracks and broadcasts tool progress updates."""
    
    def __init__(self):
        self._listeners: list[Callable[[ToolProgress], None]] = []
        self._current_progress: Optional[ToolProgress] = None
    
    def add_listener(self, callback: Callable[[ToolProgress], None]) -> None:
        """Add a progress listener."""
        self._listeners.append(callback)
    
    def remove_listener(self, callback: Callable[[ToolProgress], None]) -> None:
        """Remove a progress listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def update(self, progress: ToolProgress) -> None:
        """Broadcast a progress update."""
        self._current_progress = progress
        for listener in self._listeners:
            try:
                listener(progress)
            except Exception:
                pass  # Don't let listener errors break progress
    
    def get_current(self) -> Optional[ToolProgress]:
        """Get current progress."""
        return self._current_progress
    
    def clear(self) -> None:
        """Clear current progress."""
        self._current_progress = None


# Global progress tracker
progress_tracker = ProgressTracker()