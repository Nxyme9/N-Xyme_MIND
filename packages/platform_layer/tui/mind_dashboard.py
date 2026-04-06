#!/usr/bin/env python3
"""N-Xyme MIND TUI Dashboard — Real-time monitoring of memory system."""

import sys
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header,
    Footer,
    Static,
    DataTable,
    Label,
    Input,
    Button,
    Log,
    Sparkline,
)
from textual import work
from textual.reactive import reactive


class MemoryDashboard(App):
    """N-Xyme MIND Dashboard — Real-time memory system monitoring."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #header-bar {
        height: 3;
        background: $panel;
        content-align: center middle;
        border: solid $primary;
        margin: 0 1;
    }

    #header-bar Label {
        color: $text;
        text-style: bold;
    }

    #main-row {
        height: 1fr;
        margin: 0 1;
    }

    .panel {
        border: solid $primary;
        padding: 0 1;
        margin: 0 1;
    }

    .panel-title {
        text-style: bold;
        color: $warning;
        padding: 0 1;
    }

    #bottom-row {
        height: 10;
        margin: 0 1;
    }

    #search-row {
        height: 5;
        margin: 0 1;
    }

    #status-bar {
        height: 1;
        background: $panel;
        color: $text-muted;
        content-align: center middle;
    }

    DataTable {
        height: 100%;
    }

    .status-healthy {
        color: $success;
    }

    .status-error {
        color: $error;
    }

    .status-warning {
        color: $warning;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("s", "focus_search", "Search"),
    ]

    # Reactive state
    memory_sources: list = reactive([])
    drive_stats: dict = reactive({})
    learning_stats: dict = reactive({})
    search_results: list = reactive([])
    last_update: str = reactive("")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        # Header bar
        with Container(id="header-bar"):
            yield Label("🧠 N-Xyme MIND Dashboard — Real-time Memory System Monitoring")

        # Main row: Memory Sources | Drive Index | Learning
        with Horizontal(id="main-row"):
            # Memory Sources panel
            with Vertical(classes="panel"):
                yield Label("📊 Memory Sources", classes="panel-title")
                yield DataTable(id="sources-table")

            # Drive Index panel
            with Vertical(classes="panel"):
                yield Label("📁 Drive Index", classes="panel-title")
                yield DataTable(id="drive-table")

            # Learning panel
            with Vertical(classes="panel"):
                yield Label("🎓 Learning System", classes="panel-title")
                yield DataTable(id="learning-table")

        # Search row
        with Horizontal(id="search-row"):
            yield Label("🔍 Search: ", classes="panel-title")
            yield Input(placeholder="Type query and press Enter...", id="search-input")

        # Search results
        with Container(id="bottom-row"):
            yield DataTable(id="search-results-table")

        # Status bar
        yield Static("Press R to refresh, S to search, Q to quit", id="status-bar")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize dashboard on mount."""
        self.refresh_all()
        # Auto-refresh every 30 seconds
        self.set_interval(30.0, self.refresh_all)

    def action_refresh(self) -> None:
        """Manual refresh."""
        self.refresh_all()

    def action_focus_search(self) -> None:
        """Focus search input."""
        self.query_one("#search-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search input submission."""
        if event.input.id == "search-input":
            self.perform_search(event.value)

    @work(exclusive=True)
    async def refresh_all(self) -> None:
        """Refresh all dashboard data."""
        try:
            self.refresh_memory_sources()
            self.refresh_drive_stats()
            self.refresh_learning_stats()
            self.last_update = datetime.now().strftime("%H:%M:%S")
            self.query_one("#status-bar", Static).update(
                f"Last update: {self.last_update} | Press R to refresh, S to search, Q to quit"
            )
        except Exception as e:
            self.query_one("#status-bar", Static).update(f"Error: {e}")

    def refresh_memory_sources(self) -> None:
        """Refresh memory sources table."""
        try:
            from packages.memory_core.mcp_server import get_memory_stats

            stats = get_memory_stats()
            sources = stats.get("sources", [])

            table = self.query_one("#sources-table", DataTable)
            table.clear()
            if not table.columns:
                table.add_columns("Source", "Status", "Message")

            for s in sources:
                status = s.get("status", "unknown")
                status_style = (
                    "status-healthy" if status == "healthy" else "status-error"
                )
                table.add_row(
                    s.get("name", "unknown"),
                    f"[{status_style}]{status}[/{status_style}]",
                    s.get("message", "")[:50],
                )
        except Exception as e:
            pass  # Silently fail during refresh

    def refresh_drive_stats(self) -> None:
        """Refresh drive index table."""
        try:
            from packages.memory_core.indexing.embedder import get_indexed_count

            stats = get_indexed_count()

            table = self.query_one("#drive-table", DataTable)
            table.clear()
            if not table.columns:
                table.add_columns("Drive", "Files", "Type")

            # Show by drive
            for drive, count in stats.get("by_drive", {}).items():
                drive_name = drive.split("/")[-1] if "/" in drive else drive
                table.add_row(drive_name, str(count), "drive")

            # Show by type
            for ftype, count in stats.get("by_type", {}).items():
                table.add_row(ftype, str(count), "type")

            # Update drive_stats reactive
            self.drive_stats = stats
        except Exception as e:
            pass

    def refresh_learning_stats(self) -> None:
        """Refresh learning stats table."""
        try:
            from packages.memory_core.mcp_server import get_learning_stats

            stats = get_learning_stats()

            table = self.query_one("#learning-table", DataTable)
            table.clear()
            if not table.columns:
                table.add_columns("Metric", "Value")

            fb = stats.get("feedback_stats", {})
            table.add_row("Feedback events", str(fb.get("total_feedback", 0)))
            table.add_row("Unique queries", str(fb.get("unique_queries", 0)))

            pref = stats.get("preference_stats", {})
            if pref:
                table.add_row("Preferences", str(len(pref)))

            # Show top queries
            top_queries = fb.get("top_queries", [])
            for i, q in enumerate(top_queries[:3], 1):
                table.add_row(
                    f"Top query {i}", f"{q.get('query', '')} ({q.get('count', 0)})"
                )

            self.learning_stats = stats
        except Exception as e:
            pass

    @work(exclusive=True)
    async def perform_search(self, query: str) -> None:
        """Perform memory search."""
        if not query:
            return

        try:
            from packages.memory_core.mcp_server import search_memories

            result = search_memories(query, limit=10)

            table = self.query_one("#search-results-table", DataTable)
            table.clear()
            if not table.columns:
                table.add_columns("Source", "Score", "Content")

            for r in result.get("results", []):
                source = r.get("source", "unknown")
                score = r.get("score", 0)
                content = r.get("content", "")[:100].replace("\n", " ")
                table.add_row(source, f"{score:.3f}", content)

            self.search_results = result.get("results", [])
        except Exception as e:
            pass


def main():
    """Run the dashboard."""
    app = MemoryDashboard()
    app.run()


if __name__ == "__main__":
    main()
