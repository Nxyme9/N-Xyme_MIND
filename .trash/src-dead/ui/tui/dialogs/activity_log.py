"""
Activity Log Module for N-Xyme MIND Dashboard TUI.

Provides logging functionality and UI for tracking dashboard activity events.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Header, Static, Label, Input
from textual.widgets import Button, DataTable, Header, Static, Label, Input


@dataclass
class LogEntry:
    """Represents a single log entry in the activity log."""

    timestamp: float
    event_type: str
    message: str
    level: str  # "info", "warning", "error"

    def __post_init__(self) -> None:
        """Validate log entry fields after initialization."""
        if self.level not in ("info", "warning", "error"):
            raise ValueError(
                f"Invalid level: {self.level}. Must be 'info', 'warning', or 'error'."
            )


class ActivityLogger:
    """
    Activity logger for dashboard events.

    Manages a collection of log entries with filtering, export, and statistics capabilities.
    """

    def __init__(self, max_entries: int = 1000) -> None:
        """
        Initialize the activity logger.

        Args:
            max_entries: Maximum number of entries to retain. Defaults to 1000.
        """
        self._entries: list[LogEntry] = []
        self._max_entries = max_entries

    def log(self, event_type: str, message: str, level: str = "info") -> None:
        """
        Add a new log entry.

        Args:
            event_type: The type/category of the event (e.g., "api", "user", "system").
            message: The log message content.
            level: The severity level - "info", "warning", or "error".
        """
        entry = LogEntry(
            timestamp=datetime.now().timestamp(),
            event_type=event_type,
            message=message,
            level=level,
        )
        self._entries.append(entry)

        # Trim old entries if over max_entries
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries :]

    def get_entries(self, limit: Optional[int] = None) -> list[LogEntry]:
        """
        Get log entries, optionally limited to the most recent entries.

        Args:
            limit: Maximum number of entries to return. None returns all.

        Returns:
            List of log entries, most recent last.
        """
        if limit is None:
            return list(self._entries)
        return list(self._entries[-limit:])

    def filter_by_type(self, event_type: str) -> list[LogEntry]:
        """
        Filter entries by event type.

        Args:
            event_type: The event type to filter by.

        Returns:
            List of matching log entries.
        """
        return [entry for entry in self._entries if entry.event_type == event_type]

    def export_to_file(self, path: str) -> bool:
        """
        Export log entries to a file.

        Args:
            path: File path to write to.

        Returns:
            True if export succeeded, False otherwise.
        """
        try:
            file_path = Path(path)
            with file_path.open("w", encoding="utf-8") as f:
                f.write("Timestamp,Event Type,Level,Message\n")
                for entry in self._entries:
                    timestamp_str = datetime.fromtimestamp(entry.timestamp).isoformat()
                    # Escape quotes in message
                    escaped_message = entry.message.replace('"', '""')
                    f.write(
                        f'"{timestamp_str}","{entry.event_type}","{entry.level}","{escaped_message}"\n'
                    )
            return True
        except Exception:
            return False

    def clear(self) -> None:
        """Clear all log entries."""
        self._entries.clear()

    def get_stats(self) -> dict:
        """
        Get statistics about logged entries.

        Returns:
            Dictionary with counts by type and level.
        """
        type_counts: dict[str, int] = {}
        level_counts: dict[str, int] = {"info": 0, "warning": 0, "error": 0}

        for entry in self._entries:
            # Count by type
            type_counts[entry.event_type] = type_counts.get(entry.event_type, 0) + 1
            # Count by level
            if entry.level in level_counts:
                level_counts[entry.level] += 1

        return {
            "total": len(self._entries),
            "by_type": type_counts,
            "by_level": level_counts,
        }


class ActivityLogScreen(Screen):
    """
    Textual Screen for displaying and managing activity log entries.

    Features:
    - DataTable displaying all log entries
    - Filter controls by event type
    - Export button to save logs
    - Clear button to reset logs
    """

    CSS = """
    ActivityLogScreen {
        background: $surface;
    }
    
    #header {
        height: auto;
        padding: 1;
        background: $primary;
    }
    
    #title {
        text-align: center;
        text-style: bold;
        color: $text;
    }
    
    #controls {
        height: auto;
        padding: 1;
        background: $panel;
    }
    
    #filter_row {
        height: auto;
        margin-bottom: 1;
    }
    
    #button_row {
        height: auto;
        align: center middle;
    }
    
    DataTable {
        margin: 1;
        border: solid $primary;
    }
    
    Button {
        margin: 0 1;
    }
    """

    def __init__(self, logger: Optional[ActivityLogger] = None) -> None:
        """
        Initialize the Activity Log Screen.

        Args:
            logger: Optional ActivityLogger instance. Creates new if not provided.
        """
        super().__init__()
        self._logger = logger or ActivityLogger()
        self._current_filter: Optional[str] = None

    def compose(self) -> ComposeResult:
        """Compose the screen widgets."""
        with Vertical():
            # Title
            yield Static("Activity Log", id="title")

            # Filter controls
            with Container(id="controls"):
                with Horizontal(id="filter_row"):
                    yield Label("Filter by type:")
                    yield Input(placeholder="Enter event type...", id="filter_input")
                    yield Button("Apply", variant="primary", id="btn_filter")
                    yield Button(
                        "Clear Filter", variant="default", id="btn_clear_filter"
                    )

                with Horizontal(id="button_row"):
                    yield Button("Export", variant="success", id="btn_export")
                    yield Button("Clear All", variant="error", id="btn_clear")
                    yield Button("Close", variant="default", id="btn_close")

            # Data table for entries
            yield DataTable(id="log_table")

    def on_mount(self) -> None:
        """Initialize the screen on mount."""
        table = self.query_one("#log_table", DataTable)

        # Add columns
        table.add_columns("Timestamp", "Event Type", "Level", "Message")

        # Populate with existing entries
        self._refresh_table()

    def _refresh_table(self) -> None:
        """Refresh the data table with current log entries."""
        table = self.query_one("#log_table", DataTable)
        table.clear()

        # Get entries based on filter
        if self._current_filter:
            entries = self._logger.filter_by_type(self._current_filter)
        else:
            entries = self._logger.get_entries()

        # Add rows (most recent at bottom)
        for entry in entries:
            timestamp_str = datetime.fromtimestamp(entry.timestamp).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            table.add_row(
                timestamp_str,
                entry.event_type,
                entry.level.upper(),
                entry.message[:50] + ("..." if len(entry.message) > 50 else ""),
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id

        if button_id == "btn_filter":
            self._apply_filter()
        elif button_id == "btn_clear_filter":
            self._clear_filter()
        elif button_id == "btn_export":
            self._export_logs()
        elif button_id == "btn_clear":
            self._clear_logs()
        elif button_id == "btn_close":
            self.app.pop_screen()

    def _apply_filter(self) -> None:
        """Apply the filter from input."""
        input_widget = self.query_one("#filter_input", Input)
        filter_value = input_widget.value.strip()

        if filter_value:
            self._current_filter = filter_value
            self._refresh_table()

    def _clear_filter(self) -> None:
        """Clear the current filter."""
        self._current_filter = None
        input_widget = self.query_one("#filter_input", Input)
        input_widget.value = ""
        self._refresh_table()

    def _export_logs(self) -> None:
        """Export logs to file."""
        # For now, export to a default location with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_path = f"activity_log_{timestamp}.csv"

        success = self._logger.export_to_file(default_path)

        if success:
            self.notify(f"Logs exported to {default_path}", severity="information")
        else:
            self.notify("Failed to export logs", severity="error")

    def _clear_logs(self) -> None:
        """Clear all log entries."""
        self._logger.clear()
        self._refresh_table()
        self.notify("All logs cleared", severity="information")


# Module-level logger instance for global use
_default_logger: Optional[ActivityLogger] = None


def get_logger() -> ActivityLogger:
    """
    Get the global logger instance.

    Returns:
        The global ActivityLogger instance.
    """
    global _default_logger
    if _default_logger is None:
        _default_logger = ActivityLogger()
    return _default_logger
