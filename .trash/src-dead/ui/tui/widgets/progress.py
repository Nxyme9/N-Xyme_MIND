#!/usr/bin/env python3
"""
Progress indicator widgets for N-Xyme MIND Dashboard TUI.

Provides step-based and circular progress visualization widgets.
"""

from typing import List, Optional, Set

from textual.widgets import Static


class StepProgress(Static):
    """Multi-step progress indicator widget.
    
    Displays a sequence of steps with completion status indicators.
    Shows: [✓] Step 1 → [○] Step 2 → [ ] Step 3
    """

    def __init__(
        self,
        steps: Optional[List[str]] = None,
        current: int = 0,
        **kwargs,
    ):
        """Initialize the step progress widget.
        
        Args:
            steps: List of step labels. Defaults to empty list.
            current: Index of the current step (0-based). Default 0.
            **kwargs: Additional Static widget arguments.
        """
        super().__init__(**kwargs)
        self._steps: List[str] = steps or []
        self._current: int = max(0, min(current, len(self._steps) - 1)) if self._steps else 0
        self._completed: Set[int] = set()
        self._update_content()

    def set_steps(self, steps: List[str]) -> None:
        """Set the step labels.
        
        Args:
            steps: List of step label strings.
        """
        self._steps = list(steps)
        # Reset current if out of bounds
        if self._current >= len(self._steps):
            self._current = max(0, len(self._steps) - 1) if self._steps else 0
        self._completed = set()
        self._update_content()

    def set_current(self, step_index: int) -> None:
        """Set the current active step.
        
        Args:
            step_index: Index of the step to mark as current (0-based).
        """
        if not self._steps:
            return
        self._current = max(0, min(step_index, len(self._steps) - 1))
        self._update_content()

    def set_complete(self, step_index: int) -> None:
        """Mark a step as complete.
        
        Args:
            step_index: Index of the step to mark as complete (0-based).
        """
        if 0 <= step_index < len(self._steps):
            self._completed.add(step_index)
            self._update_content()

    def _update_content(self) -> None:
        """Update the widget content."""
        if not self._steps:
            self.update("")
            return

        parts: List[str] = []
        for i, step in enumerate(self._steps):
            if i in self._completed:
                indicator = "[$success]✓[/]"
            elif i == self._current:
                indicator = "[$warning]○[/]"
            else:
                indicator = "[$text-muted]○[/]"
            
            step_text = f"{indicator} {step}"
            
            # Add separator between steps (except last)
            if i < len(self._steps) - 1:
                step_text += " [$text-muted]→[/]"
            
            parts.append(step_text)

        self.update(" ".join(parts))


class CircularProgress(Static):
    """Circular/linear progress indicator widget.
    
    Displays progress as a filled bar with percentage.
    Shows: ▣▣▣▣▣▣▣▣▣ 75%
    """

    # Unicode block characters for filled segments
    FILLED = "▣"
    EMPTY = "○"
    FALLBACK_FILLED = "█"
    FALLBACK_EMPTY = "░"

    def __init__(
        self,
        percentage: float = 0.0,
        color: str = "$primary",
        label: str = "",
        segments: int = 10,
        **kwargs,
    ):
        """Initialize the circular progress widget.
        
        Args:
            percentage: Progress value 0-100. Default 0.
            color: Color name for filled segments. Default "$primary".
            label: Optional text label to display. Default "".
            segments: Number of progress segments. Default 10.
            **kwargs: Additional Static widget arguments.
        """
        super().__init__(**kwargs)
        self._percentage = max(0.0, min(100.0, percentage))
        self._color = color
        self._label = label
        self._segments = max(1, min(segments, 20))
        self._update_content()

    def set_percentage(self, value: float) -> None:
        """Set the progress percentage.
        
        Args:
            value: Progress value between 0 and 100.
        """
        self._percentage = max(0.0, min(100.0, value))
        self._update_content()

    def set_color(self, color: str) -> None:
        """Set the progress bar color.
        
        Args:
            color: Textual color name (e.g., "$primary", "$success", "$error").
        """
        self._color = color
        self._update_content()

    def set_label(self, text: str) -> None:
        """Set the label text.
        
        Args:
            text: Label text to display after the progress bar.
        """
        self._label = text
        self._update_content()

    def _update_content(self) -> None:
        """Update the widget content."""
        # Calculate filled segments
        filled_count = int((self._percentage / 100.0) * self._segments)
        empty_count = self._segments - filled_count

        # Build progress bar
        filled_bar = self.FILLED * filled_count + self.EMPTY * empty_count
        
        # Wrap with color
        progress_bar = f"[{self._color}]{filled_bar}[/]"
        
        # Add percentage and optional label
        percentage_str = f" {self._percentage:.0f}%"
        
        if self._label:
            content = f"{progress_bar}{percentage_str} {self._label}"
        else:
            content = f"{progress_bar}{percentage_str}"

        self.update(content)


__all__ = [
    "StepProgress",
    "CircularProgress",
]