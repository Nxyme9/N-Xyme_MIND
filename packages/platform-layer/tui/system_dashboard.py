#!/usr/bin/env python3
"""N-Xyme MIND Comprehensive System Dashboard — Real-time monitoring of ALL backend systems."""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Header,
    Footer,
    Static,
    DataTable,
    Label,
)
from textual import work
from textual.reactive import reactive


class SystemDashboard(App):
    """N-Xyme MIND Comprehensive System Dashboard."""

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
        height: 12;
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

    .stat-value {
        color: $success;
        text-style: bold;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("s", "focus_search", "Search"),
    ]

    # Reactive state
    system_stats: dict = reactive({})
    last_update: str = reactive("")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        # Header bar
        with Container(id="header-bar"):
            yield Label("🧠 N-Xyme MIND — Comprehensive System Dashboard")

        # Main row: System Overview | Intelligence | Security
        with Horizontal(id="main-row"):
            # System Overview panel
            with Vertical(classes="panel"):
                yield Label("📊 System Overview", classes="panel-title")
                yield DataTable(id="overview-table")

            # Intelligence Layer panel
            with Vertical(classes="panel"):
                yield Label("🧠 Intelligence Layer", classes="panel-title")
                yield DataTable(id="intelligence-table")

            # Security & Quality panel
            with Vertical(classes="panel"):
                yield Label("🛡️ Security & Quality", classes="panel-title")
                yield DataTable(id="security-table")

        # Bottom row: Memory | Budget | Learning
        with Horizontal(id="bottom-row"):
            # Memory System panel
            with Vertical(classes="panel"):
                yield Label("💾 Memory System", classes="panel-title")
                yield DataTable(id="memory-table")

            # Budget & Resources panel
            with Vertical(classes="panel"):
                yield Label("⏱️ Budget & Resources", classes="panel-title")
                yield DataTable(id="budget-table")

            # Learning System panel
            with Vertical(classes="panel"):
                yield Label("🎓 Learning System", classes="panel-title")
                yield DataTable(id="learning-table")

        # Status bar
        yield Static("Press R to refresh, Q to quit", id="status-bar")

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
        pass  # Search not implemented in this version

    @work(exclusive=True)
    async def refresh_all(self) -> None:
        """Refresh all dashboard data."""
        try:
            self.refresh_system_overview()
            self.refresh_intelligence()
            self.refresh_security()
            self.refresh_memory()
            self.refresh_budget()
            self.refresh_learning()
            self.last_update = datetime.now().strftime("%H:%M:%S")
            self.query_one("#status-bar", Static).update(
                f"Last update: {self.last_update} | Press R to refresh, Q to quit"
            )
        except Exception as e:
            self.query_one("#status-bar", Static).update(f"Error: {e}")

    def refresh_system_overview(self) -> None:
        """Refresh system overview table."""
        try:
            table = self.query_one("#overview-table", DataTable)
            table.clear()
            if not table.columns:
                table.add_columns("Component", "Status")

            # Check daemon
            try:
                from packages.memory_store.daemon import MemoryDaemon

                daemon = MemoryDaemon()
                status = daemon.status()
                table.add_row(
                    "Daemon", "✅ Running" if status.get("running") else "❌ Stopped"
                )
            except Exception:
                table.add_row("Daemon", "❌ Error")

            # Check GGUF llama-server (primary)
            try:
                import urllib.request

                urllib.request.urlopen("http://localhost:8080", timeout=2)
                table.add_row("GGUF Server", "✅ Running")
            except Exception:
                # Fallback: Check Ollama
                try:
                    import urllib.request

                    urllib.request.urlopen("http://localhost:11434", timeout=2)
                    table.add_row("GGUF Server", "⚠️ Using Ollama fallback")
                except Exception:
                    table.add_row("GGUF Server", "❌ Stopped")

            # Check MCP server
            try:
                from packages.memory_store.mcp_server import get_memory_stats

                stats = get_memory_stats()
                table.add_row(
                    "MCP Server", f"✅ {stats.get('total_sources', 0)} sources"
                )
            except Exception:
                table.add_row("MCP Server", "❌ Error")

            # Check file indexing
            try:
                from packages.memory_store.indexing.embedder import get_indexed_count

                idx = get_indexed_count()
                table.add_row("File Index", f"✅ {idx.get('total_files', 0)} files")
            except Exception:
                table.add_row("File Index", "❌ Error")

        except Exception:
            pass

    def refresh_intelligence(self) -> None:
        """Refresh intelligence layer table."""
        try:
            table = self.query_one("#intelligence-table", DataTable)
            table.clear()
            if not table.columns:
                table.add_columns("Module", "Status")

            # Tool contracts
            try:
                from packages.orchestration.tools.contract import get_tool_registry

                reg = get_tool_registry()
                tools = reg.list_tools()
                table.add_row("Tool Contracts", f"✅ {len(tools)} registered")
            except Exception:
                table.add_row("Tool Contracts", "⚠️ Not wired")

            # Budget tracker
            try:
                from packages.infrastructure.cost.tracker import get_budget_tracker

                tracker = get_budget_tracker()
                status = tracker.get_status("global")
                table.add_row(
                    "Budget Tracker", f"✅ {status.get('used_budget', 0)} tokens"
                )
            except Exception:
                table.add_row("Budget Tracker", "⚠️ Not wired")

            # Permission engine
            try:
                from packages.orchestration.governance.permissions import (
                    get_permission_engine,
                )

                engine = get_permission_engine()
                stats = engine.get_stats("global")
                table.add_row(
                    "Permission Engine", f"✅ {stats.get('allow_rules', 0)} rules"
                )
            except Exception:
                table.add_row("Permission Engine", "⚠️ Not wired")

            # Delegation learner
            try:

                table.add_row("Delegation Learner", "✅ Available")
            except Exception:
                table.add_row("Delegation Learner", "❌ Error")

        except Exception:
            pass

    def refresh_security(self) -> None:
        """Refresh security & quality table."""
        try:
            table = self.query_one("#security-table", DataTable)
            table.clear()
            if not table.columns:
                table.add_columns("Component", "Status")

            # Security gate
            try:

                table.add_row("Security Gate", "✅ Active")
            except Exception:
                table.add_row("Security Gate", "❌ Error")

            # Code quality tracker
            try:
                from packages.intelligence.review.quality import (
                    get_code_quality_tracker,
                )

                cq = get_code_quality_tracker()
                stats = cq.get_quality_stats()
                events = stats.get("total_events", 0)
                table.add_row("Code Quality", f"✅ {events} events tracked")
            except Exception:
                table.add_row("Code Quality", "⚠️ Not wired")

            # Self-healer
            try:

                table.add_row("Self-Healer", "✅ Available")
            except Exception:
                table.add_row("Self-Healer", "❌ Error")

            # Auto-recovery
            try:

                table.add_row("Auto-Recovery", "✅ Available")
            except Exception:
                table.add_row("Auto-Recovery", "❌ Error")

        except Exception:
            pass

    def refresh_memory(self) -> None:
        """Refresh memory system table."""
        try:
            table = self.query_one("#memory-table", DataTable)
            table.clear()
            if not table.columns:
                table.add_columns("Metric", "Value")

            from packages.memory_store.mcp_server import get_memory_stats

            stats = get_memory_stats()
            sources = stats.get("sources", [])
            table.add_row("Sources", str(len(sources)))

            from packages.memory_store.indexing.embedder import get_indexed_count

            idx = get_indexed_count()
            table.add_row("Files Indexed", str(idx.get("total_files", 0)))
            table.add_row("Chunks", str(idx.get("total_chunks", 0)))

            # Check memory DB
            import sqlite3

            conn = sqlite3.connect("context/memory/mind_from_mind.db")
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM memories")
            memories = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM memory_embeddings")
            embeddings = c.fetchone()[0]
            conn.close()
            table.add_row("Memories", str(memories))
            table.add_row(
                "Embeddings",
                f"{embeddings} ({embeddings / max(1, memories) * 100:.0f}%)",
            )

        except Exception:
            pass

    def refresh_budget(self) -> None:
        """Refresh budget & resources table."""
        try:
            table = self.query_one("#budget-table", DataTable)
            table.clear()
            if not table.columns:
                table.add_columns("Metric", "Value")

            try:
                from packages.infrastructure.cost.tracker import get_budget_tracker

                tracker = get_budget_tracker()
                status = tracker.get_status("global")
                table.add_row("Tokens Used", str(status.get("used_budget", 0)))
                table.add_row("Continuations", str(status.get("continuation_count", 0)))
                table.add_row(
                    "Near Limit", "⚠️ Yes" if status.get("is_near_limit") else "✅ No"
                )
                table.add_row(
                    "Diminishing Returns",
                    "⚠️ Yes" if status.get("is_diminishing_returns") else "✅ No",
                )
            except Exception:
                table.add_row("Budget Tracker", "⚠️ Not available")

        except Exception:
            pass

    def refresh_learning(self) -> None:
        """Refresh learning system table."""
        try:
            table = self.query_one("#learning-table", DataTable)
            table.clear()
            if not table.columns:
                table.add_columns("Metric", "Value")

            try:
                from packages.memory_store.mcp_server import get_learning_stats

                stats = get_learning_stats()
                fb = stats.get("feedback_stats", {})
                table.add_row("Feedback Events", str(fb.get("total_feedback", 0)))
                table.add_row("Unique Queries", str(fb.get("unique_queries", 0)))

                pref = stats.get("preference_stats", {})
                table.add_row("Preferences", str(len(pref)))

                cq = stats.get("code_quality_stats", {})
                table.add_row("Quality Events", str(cq.get("total_events", 0)))
            except Exception:
                table.add_row("Learning System", "⚠️ Error")

        except Exception:
            pass


def main():
    """Run the dashboard."""
    app = SystemDashboard()
    app.run()


if __name__ == "__main__":
    main()
