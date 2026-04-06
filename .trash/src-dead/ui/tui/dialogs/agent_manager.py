"""
Agent Manager Module for N-Xyme MIND Dashboard TUI.

Provides UI for managing agent configurations with status monitoring,
health metrics, and control actions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen, ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Header,
    Static,
    Label,
    Input,
    TextArea,
)
from textual.widgets import Button, DataTable, Header, Static, Label, Input


class AgentStatus(Enum):
    """Agent operational status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    STOPPED = "stopped"


class AgentCategory(Enum):
    """Agent category types."""

    ORCHESTRATOR = "orchestrator"
    IMPLEMENTER = "implementer"
    RESEARCHER = "researcher"
    REVIEWER = "reviewer"
    SPECIALIZED = "specialized"


@dataclass
class AgentConfig:
    """Represents an agent configuration."""

    name: str
    model: str
    category: str
    status: AgentStatus = AgentStatus.STOPPED
    last_health_check: float = field(default_factory=lambda: datetime.now().timestamp())
    tasks_completed: int = 0
    tasks_failed: int = 0
    uptime_seconds: int = 0

    def get_health_percentage(self) -> float:
        """Calculate health percentage based on task success rate."""
        total = self.tasks_completed + self.tasks_failed
        if total == 0:
            return 100.0
        return (self.tasks_completed / total) * 100

    def get_status_indicator(self) -> str:
        """Get status indicator string with color code."""
        status_map = {
            AgentStatus.HEALTHY: "[green]●[/green] Healthy",
            AgentStatus.DEGRADED: "[yellow]◐[/yellow] Degraded",
            AgentStatus.STOPPED: "[red]○[/red] Stopped",
        }
        return status_map[self.status]


@dataclass
class AgentMetrics:
    """Health metrics for an agent."""

    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    response_time_ms: float = 0.0
    active_tasks: int = 0
    queued_tasks: int = 0


class AgentManager:
    """
    Agent manager for tracking and controlling agents.

    Manages a collection of agent configurations with status updates,
    metrics tracking, and control operations.
    """

    def __init__(self) -> None:
        """Initialize the agent manager with mock data."""
        self._agents: dict[str, AgentConfig] = {}
        self._metrics: dict[str, AgentMetrics] = {}
        self._load_mock_agents()

    def _load_mock_agents(self) -> None:
        """Load mock agent data for demonstration."""
        mock_agents = [
            AgentConfig(
                name="Sisyphus",
                model="mimo-v2-pro-free",
                category="orchestrator",
                status=AgentStatus.HEALTHY,
                tasks_completed=156,
                tasks_failed=3,
                uptime_seconds=86400,
            ),
            AgentConfig(
                name="Hephaestus",
                model="mimo-v2-omni-free",
                category="implementer",
                status=AgentStatus.HEALTHY,
                tasks_completed=234,
                tasks_failed=8,
                uptime_seconds=86400,
            ),
            AgentConfig(
                name="Oracle",
                model="mimo-v2-pro-free",
                category="reviewer",
                status=AgentStatus.DEGRADED,
                tasks_completed=89,
                tasks_failed=12,
                uptime_seconds=43200,
            ),
            AgentConfig(
                name="Explore",
                model="minimax-m2.5-free",
                category="researcher",
                status=AgentStatus.HEALTHY,
                tasks_completed=445,
                tasks_failed=5,
                uptime_seconds=86400,
            ),
            AgentConfig(
                name="Librarian",
                model="minimax-m2.5-free",
                category="researcher",
                status=AgentStatus.STOPPED,
                tasks_completed=0,
                tasks_failed=0,
                uptime_seconds=0,
            ),
            AgentConfig(
                name="Metis",
                model="mimo-v2-pro-free",
                category="specialized",
                status=AgentStatus.HEALTHY,
                tasks_completed=67,
                tasks_failed=1,
                uptime_seconds=72000,
            ),
            AgentConfig(
                name="Momus",
                model="opencode/kimi-k2.5-free",
                category="reviewer",
                status=AgentStatus.HEALTHY,
                tasks_completed=34,
                tasks_failed=0,
                uptime_seconds=86400,
            ),
        ]

        for agent in mock_agents:
            self._agents[agent.name] = agent
            # Generate mock metrics
            self._metrics[agent.name] = AgentMetrics(
                cpu_usage=15.0 + (hash(agent.name) % 30),
                memory_usage=120.0 + (hash(agent.name) % 200),
                response_time_ms=50.0 + (hash(agent.name) % 150),
                active_tasks=hash(agent.name) % 5,
                queued_tasks=hash(agent.name) % 10,
            )

    def get_agents(self) -> list[AgentConfig]:
        """
        Get all agent configurations.

        Returns:
            List of all agent configurations.
        """
        return list(self._agents.values())

    def get_agent(self, name: str) -> Optional[AgentConfig]:
        """
        Get a specific agent by name.

        Args:
            name: The agent name to retrieve.

        Returns:
            AgentConfig if found, None otherwise.
        """
        return self._agents.get(name)

    def get_metrics(self, name: str) -> Optional[AgentMetrics]:
        """
        Get metrics for a specific agent.

        Args:
            name: The agent name.

        Returns:
            AgentMetrics if found, None otherwise.
        """
        return self._metrics.get(name)

    def start_agent(self, name: str) -> bool:
        """
        Start an agent.

        Args:
            name: The agent name to start.

        Returns:
            True if successful, False otherwise.
        """
        agent = self._agents.get(name)
        if agent and agent.status == AgentStatus.STOPPED:
            agent.status = AgentStatus.HEALTHY
            agent.uptime_seconds = 0
            return True
        return False

    def stop_agent(self, name: str) -> bool:
        """
        Stop an agent.

        Args:
            name: The agent name to stop.

        Returns:
            True if successful, False otherwise.
        """
        agent = self._agents.get(name)
        if agent and agent.status != AgentStatus.STOPPED:
            agent.status = AgentStatus.STOPPED
            return True
        return False

    def restart_agent(self, name: str) -> bool:
        """
        Restart an agent.

        Args:
            name: The agent name to restart.

        Returns:
            True if successful, False otherwise.
        """
        agent = self._agents.get(name)
        if agent:
            agent.status = AgentStatus.HEALTHY
            agent.uptime_seconds = 0
            return True
        return False

    def add_agent(self, name: str, model: str, category: str) -> bool:
        """
        Add a new agent configuration.

        Args:
            name: The agent name.
            model: The model identifier.
            category: The agent category.

        Returns:
            True if successful, False if agent already exists.
        """
        if name in self._agents:
            return False

        agent = AgentConfig(
            name=name,
            model=model,
            category=category,
            status=AgentStatus.STOPPED,
        )
        self._agents[name] = agent
        self._metrics[name] = AgentMetrics()
        return True

    def get_summary(self) -> dict:
        """
        Get summary statistics for all agents.

        Returns:
            Dictionary with counts by status and totals.
        """
        status_counts = {
            AgentStatus.HEALTHY: 0,
            AgentStatus.DEGRADED: 0,
            AgentStatus.STOPPED: 0,
        }

        total_tasks = 0
        total_failures = 0

        for agent in self._agents.values():
            status_counts[agent.status] += 1
            total_tasks += agent.tasks_completed
            total_failures += agent.tasks_failed

        return {
            "total_agents": len(self._agents),
            "healthy": status_counts[AgentStatus.HEALTHY],
            "degraded": status_counts[AgentStatus.DEGRADED],
            "stopped": status_counts[AgentStatus.STOPPED],
            "total_tasks": total_tasks,
            "total_failures": total_failures,
        }


class AgentManagerDialog(ModalScreen):
    """
    Textual Modal Screen for managing agent configurations.

    Features:
    - DataTable displaying all agents with status
    - Action buttons per agent (start, stop, restart, configure)
    - Add new agent form
    - Health metrics display
    - Summary statistics
    """

    CSS = """
    AgentManagerDialog {
        align: center middle;
    }

    #dialog_container {
        width: 90%;
        height: 90%;
        border: solid $primary;
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

    #summary_bar {
        height: auto;
        padding: 1;
        background: $panel;
        margin-bottom: 1;
    }

    #metrics_panel {
        height: auto;
        padding: 1;
        background: $panel;
        margin-bottom: 1;
    }

    #agent_table_container {
        margin: 1;
        border: solid $primary;
    }

    #controls {
        height: auto;
        padding: 1;
        background: $panel;
    }

    #button_row {
        height: auto;
        align: center middle;
    }

    #add_agent_form {
        height: auto;
        padding: 1;
        background: $panel;
        display: none;
    }

    #add_form_visible {
        display: block;
    }

    DataTable {
        margin: 0;
    }

    Button {
        margin: 0 1;
    }

    .status_healthy {
        color: green;
    }

    .status_degraded {
        color: yellow;
    }

    .status_stopped {
        color: red;
    }
    """

    def __init__(self, manager: Optional[AgentManager] = None) -> None:
        """
        Initialize the Agent Manager Dialog.

        Args:
            manager: Optional AgentManager instance. Creates new if not provided.
        """
        super().__init__()
        self._manager = manager or AgentManager()
        self._selected_agent: Optional[str] = None
        self._show_add_form = False

    def compose(self) -> ComposeResult:
        """Compose the modal dialog widgets."""
        with Vertical(id="dialog_container"):
            # Title
            yield Static("Agent Manager", id="title")

            # Summary bar
            with Container(id="summary_bar"):
                yield Static("", id="summary_text")

            # Agent table
            with Container(id="agent_table_container"):
                yield DataTable(id="agent_table")

            # Metrics panel for selected agent
            with Container(id="metrics_panel"):
                yield Static("Select an agent to view metrics", id="metrics_text")

            # Controls
            with Container(id="controls"):
                with Horizontal(id="button_row"):
                    yield Button("Start", variant="success", id="btn_start")
                    yield Button("Stop", variant="error", id="btn_stop")
                    yield Button("Restart", variant="warning", id="btn_restart")
                    yield Button("Configure", variant="default", id="btn_configure")
                    yield Button("Add Agent", variant="primary", id="btn_add")
                    yield Button("Close", variant="default", id="btn_close")

            # Add agent form (hidden by default)
            with Container(id="add_agent_form"):
                with Horizontal():
                    yield Label("Name:")
                    yield Input(placeholder="Agent name...", id="input_name")
                with Horizontal():
                    yield Label("Model:")
                    yield Input(
                        placeholder="Model (e.g., minimax-m2.5-free)", id="input_model"
                    )
                with Horizontal():
                    yield Label("Category:")
                    yield Input(placeholder="Category...", id="input_category")
                with Horizontal(id="form_buttons"):
                    yield Button("Create", variant="primary", id="btn_create")
                    yield Button("Cancel", variant="default", id="btn_cancel")

    def on_mount(self) -> None:
        """Initialize the dialog on mount."""
        table = self.query_one("#agent_table", DataTable)

        # Add columns
        table.add_columns("Name", "Model", "Category", "Status", "Health %", "Tasks")

        # Set column widths
        # table.set_column_width("Name", 15)
        # table.set_column_width("Model", 25)
        # table.set_column_width("Category", 15)
        # table.set_column_width("Status", 12)
        # table.set_column_width("Health %", 10)
        # table.set_column_width("Tasks", 10)

        # Populate table
        self._refresh_table()
        self._update_summary()

    def _refresh_table(self) -> None:
        """Refresh the agent data table."""
        table = self.query_one("#agent_table", DataTable)
        table.clear()

        for agent in self._manager.get_agents():
            health_pct = f"{agent.get_health_percentage():.1f}%"
            tasks = f"{agent.tasks_completed}/{agent.tasks_failed}"
            table.add_row(
                agent.name,
                agent.model,
                agent.category,
                agent.status.value,
                health_pct,
                tasks,
            )

    def _update_summary(self) -> None:
        """Update the summary statistics bar."""
        summary = self._manager.get_summary()
        summary_text = (
            f"Total: {summary['total_agents']} | "
            f"Healthy: {summary['healthy']} | "
            f"Degraded: {summary['degraded']} | "
            f"Stopped: {summary['stopped']} | "
            f"Tasks: {summary['total_tasks']} completed, {summary['total_failures']} failed"
        )
        self.query_one("#summary_text", Static).update(summary_text)

    def _update_metrics(self, agent_name: str) -> None:
        """Update the metrics panel for selected agent."""
        agent = self._manager.get_agent(agent_name)
        metrics = self._manager.get_metrics(agent_name)

        if agent and metrics:
            metrics_text = (
                f"Agent: {agent.name} | "
                f"CPU: {metrics.cpu_usage:.1f}% | "
                f"Memory: {metrics.memory_usage:.1f}MB | "
                f"Response: {metrics.response_time_ms:.1f}ms | "
                f"Active Tasks: {metrics.active_tasks} | "
                f"Queued: {metrics.queued_tasks} | "
                f"Uptime: {agent.uptime_seconds}s"
            )
            self.query_one("#metrics_text", Static).update(metrics_text)
        else:
            self.query_one("#metrics_text", Static).update(
                "Select an agent to view metrics"
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the agent table."""
        table = self.query_one("#agent_table", DataTable)
        row = event.row_key

        if row:
            self._selected_agent = str(row.value)
            self._update_metrics(self._selected_agent)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id

        if button_id == "btn_start":
            self._start_agent()
        elif button_id == "btn_stop":
            self._stop_agent()
        elif button_id == "btn_restart":
            self._restart_agent()
        elif button_id == "btn_configure":
            self._configure_agent()
        elif button_id == "btn_add":
            self._toggle_add_form()
        elif button_id == "btn_create":
            self._create_agent()
        elif button_id == "btn_cancel":
            self._toggle_add_form()
        elif button_id == "btn_close":
            self.app.pop_screen()

    def _start_agent(self) -> None:
        """Start the selected agent."""
        if self._selected_agent:
            success = self._manager.start_agent(self._selected_agent)
            if success:
                self.notify(
                    f"Agent '{self._selected_agent}' started", severity="information"
                )
            else:
                self.notify(f"Failed to start agent", severity="error")
            self._refresh_table()
            self._update_summary()

    def _stop_agent(self) -> None:
        """Stop the selected agent."""
        if self._selected_agent:
            success = self._manager.stop_agent(self._selected_agent)
            if success:
                self.notify(
                    f"Agent '{self._selected_agent}' stopped", severity="information"
                )
            else:
                self.notify(f"Failed to stop agent", severity="error")
            self._refresh_table()
            self._update_summary()

    def _restart_agent(self) -> None:
        """Restart the selected agent."""
        if self._selected_agent:
            success = self._manager.restart_agent(self._selected_agent)
            if success:
                self.notify(
                    f"Agent '{self._selected_agent}' restarted", severity="information"
                )
            else:
                self.notify(f"Failed to restart agent", severity="error")
            self._refresh_table()
            self._update_summary()

    def _configure_agent(self) -> None:
        """Show configuration for the selected agent."""
        if self._selected_agent:
            agent = self._manager.get_agent(self._selected_agent)
            if agent:
                config_info = (
                    f"Configuration for {agent.name}:\n"
                    f"  Model: {agent.model}\n"
                    f"  Category: {agent.category}\n"
                    f"  Status: {agent.status.value}\n"
                    f"  Tasks: {agent.tasks_completed} completed, {agent.tasks_failed} failed\n"
                    f"  Uptime: {agent.uptime_seconds}s"
                )
                self.notify(config_info, severity="information")

    def _toggle_add_form(self) -> None:
        """Toggle the add agent form visibility."""
        self._show_add_form = not self._show_add_form
        form = self.query_one("#add_agent_form", Container)

        if self._show_add_form:
            form.add_class("add_form_visible")
        else:
            form.remove_class("add_form_visible")

        # Clear inputs
        if not self._show_add_form:
            self.query_one("#input_name", Input).value = ""
            self.query_one("#input_model", Input).value = ""
            self.query_one("#input_category", Input).value = ""

    def _create_agent(self) -> None:
        """Create a new agent from form input."""
        name = self.query_one("#input_name", Input).value.strip()
        model = self.query_one("#input_model", Input).value.strip()
        category = self.query_one("#input_category", Input).value.strip()

        if not name or not model or not category:
            self.notify("All fields are required", severity="error")
            return

        success = self._manager.add_agent(name, model, category)

        if success:
            self.notify(f"Agent '{name}' created", severity="information")
            self._refresh_table()
            self._update_summary()
            self._toggle_add_form()
        else:
            self.notify(f"Agent '{name}' already exists", severity="error")


# Module-level manager instance for global use
_default_manager: Optional[AgentManager] = None


def get_manager() -> AgentManager:
    """
    Get the global manager instance.

    Returns:
        The global AgentManager instance.
    """
    global _default_manager
    if _default_manager is None:
        _default_manager = AgentManager()
    return _default_manager
