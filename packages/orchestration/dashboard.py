#!/usr/bin/env python3
"""
TUI Dashboard for Unified Pipeline

Displays: system health, recent tasks, stats, pipeline status
Auto-refresh: 5 seconds
Interactive: key bindings for running tasks, viewing details
"""

import os
import sys
import time
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

# Add project root to path for imports
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, PROJECT_ROOT)

# Try importing rich, fallback to basic stdlib if needed
try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.table import Table
    from rich.live import Live
    from rich.text import Text
    from rich.style import Style
    from rich.color import Color

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None


class DashboardState:
    """State management for dashboard."""

    def __init__(self):
        self.last_refresh = datetime.now()
        self.tasks: List[Dict[str, Any]] = []
        self.health: Dict[str, bool] = {}
        self.stats: Dict[str, Any] = {}
        self.pipeline_status: Dict[str, Any] = {}
        self.current_view = "main"  # main, stats, health, bmad
        self.running = True
        self.selected_task_index = 0

        # BMAD workflow state
        self.bmad_workflows: List[str] = []
        self.bmad_selected_index = 0
        self.bmad_output: Optional[str] = None
        self.bmad_running = False

        # Initialize with mock data for demo
        self._init_demo_data()

    def _init_demo_data(self):
        """Initialize with demo data for display."""
        self.health = {
            "orchestration": True,
            "memory": True,
            "intelligence": True,
            "learning": True,
            "mcp_servers": True,
        }

        self.stats = {
            "total_tasks": 127,
            "success_rate": 94.3,
            "avg_latency_ms": 1250,
            "active_agents": 8,
        }

        self.pipeline_status = {
            "current_stage": "idle",
            "stage_start": None,
            "tasks_in_queue": 3,
        }

        self.tasks = [
            {
                "id": "task_001",
                "description": "implement JWT auth",
                "status": "completed",
                "duration_ms": 3200,
            },
            {
                "id": "task_002",
                "description": "fix memory leak",
                "status": "completed",
                "duration_ms": 1500,
            },
            {
                "id": "task_003",
                "description": "add unit tests",
                "status": "completed",
                "duration_ms": 2800,
            },
            {
                "id": "task_004",
                "description": "refactor pipeline",
                "status": "failed",
                "duration_ms": 500,
            },
            {
                "id": "task_005",
                "description": "update docs",
                "status": "running",
                "duration_ms": None,
            },
        ]


class TUIDashboard:
    """Terminal UI Dashboard using Rich."""

    def __init__(self):
        self.state = DashboardState()
        self.console = Console() if RICH_AVAILABLE else None
        self.refresh_interval = 5  # seconds
        self._input_thread: Optional[threading.Thread] = None

    def render_header(self) -> str:
        """Render the header panel."""
        status = "🟢 RUNNING" if self.state.running else "🔴 STOPPED"
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        header = f"""
╔══════════════════════════════════════════════════════════════╗
║              N-XYME UNIFIED PIPELINE DASHBOARD                ║
║                                                              ║
║  System: N-Xyme_MIND  │  Status: {status}  │  {current_time}
╚══════════════════════════════════════════════════════════════╝
"""
        return header

    def render_health_panel(self) -> str:
        """Render system health panel."""
        lines = ["[bold]SYSTEM HEALTH[/bold]", ""]

        for component, status in self.state.health.items():
            status_str = "🟢 OK" if status else "🔴 FAIL"
            lines.append(f"  {component:20} │ {status_str}")

        return "\n".join(lines)

    def render_stats_panel(self) -> str:
        """Render statistics panel."""
        stats = self.state.stats

        lines = [
            "[bold]STATISTICS[/bold]",
            "",
            f"  Total Tasks:       {stats.get('total_tasks', 0):>6}",
            f"  Success Rate:      {stats.get('success_rate', 0):>5.1f}%",
            f"  Avg Latency:       {stats.get('avg_latency_ms', 0):>5.0f}ms",
            f"  Active Agents:     {stats.get('active_agents', 0):>6}",
        ]

        return "\n".join(lines)

    def render_recent_tasks_panel(self) -> str:
        """Render recent tasks panel."""
        lines = ["[bold]RECENT TASKS (Last 5)[/bold]", ""]

        for i, task in enumerate(self.state.tasks[:5]):
            status_icon = {
                "completed": "✅",
                "failed": "❌",
                "running": "🔄",
                "pending": "⏳",
            }.get(task.get("status", "pending"), "❓")

            desc = task.get("description", "unknown")[:30]
            duration = task.get("duration_ms")
            dur_str = f"{duration}ms" if duration else "running..."

            prefix = "▶ " if i == self.state.selected_task_index else "  "
            lines.append(f"{prefix}{status_icon} {desc:<30} │ {dur_str}")

        return "\n".join(lines)

    def render_pipeline_panel(self) -> str:
        """Render pipeline status panel."""
        status = self.state.pipeline_status

        stage = status.get("current_stage", "idle")
        queue = status.get("tasks_in_queue", 0)

        lines = [
            "[bold]PIPELINE STATUS[/bold]",
            "",
            f"  Current Stage:     {stage}",
            f"  Tasks in Queue:    {queue}",
        ]

        return "\n".join(lines)

    def render_help_panel(self) -> str:
        """Render help panel with key bindings."""
        lines = [
            "[bold]KEY BINDINGS[/bold]",
            "",
            "  [r] Run new task    │  [s] Show stats",
            "  [h] Show health     │  [q] Quit",
            "  [w] BMAD workflow  │  [↑/↓] Select task",
        ]
        return "\n".join(lines)

    def render_main_view(self) -> str:
        """Render main dashboard view."""
        output = []
        output.append(self.render_header())
        output.append("")

        # Two-column layout
        left_col = []
        left_col.append(self.render_health_panel())
        left_col.append("")
        left_col.append(self.render_stats_panel())

        right_col = []
        right_col.append(self.render_pipeline_panel())
        right_col.append("")
        right_col.append(self.render_recent_tasks_panel())

        # Pad to match heights
        left_lines = "\n".join(left_col).split("\n")
        right_lines = "\n".join(right_col).split("\n")

        max_lines = max(len(left_lines), len(right_lines))
        left_lines.extend([""] * (max_lines - len(left_lines)))
        right_lines.extend([""] * (max_lines - len(right_lines)))

        # Print side by side
        for l, r in zip(left_lines, right_lines):
            output.append(f"{l:<40} │ {r}")

        output.append("")
        output.append(self.render_help_panel())

        return "\n".join(output)

    def render_stats_view(self) -> str:
        """Render detailed stats view."""
        output = []
        output.append(self.render_header())
        output.append("")
        output.append("[bold underline]DETAILED STATISTICS[/bold underline]")
        output.append("")

        stats = self.state.stats
        for key, value in stats.items():
            output.append(f"  {key}: {value}")

        output.append("")
        output.append("[bold]HISTORICAL DATA[/bold]")
        output.append("  (would show graphs in full version)")

        output.append("")
        output.append("Press [b]ack to return to main view")

        return "\n".join(output)

    def render_health_view(self) -> str:
        """Render detailed health view."""
        output = []
        output.append(self.render_header())
        output.append("")
        output.append("[bold underline]COMPONENT HEALTH DETAILS[/bold underline]")
        output.append("")

        for component, status in self.state.health.items():
            status_str = "🟢 HEALTHY" if status else "🔴 UNHEALTHY"
            output.append(f"  {component}: {status_str}")

        output.append("")
        output.append("[bold]LAST CHECK[/bold]")
        output.append(f"  {self.state.last_refresh.strftime('%Y-%m-%d %H:%M:%S')}")

        output.append("")
        output.append("Press [b]ack to return to main view")

        return "\n".join(output)

    def render_bmad_view(self) -> str:
        """Render BMAD workflow panel."""
        output = []
        output.append(self.render_header())
        output.append("")
        output.append("[bold underline]BMAD WORKFLOWS (49+ workflows)[/bold underline]")
        output.append("")

        # Try to load workflows
        if not self.state.bmad_workflows:
            try:
                from .bmad.executor import get_executor

                executor = get_executor()
                self.state.bmad_workflows = executor.list_workflows()
            except Exception:
                self.state.bmad_workflows = [
                    "bmad-catalyst-orchestration",
                    "consolidate-session",
                    "recall-agent-history",
                    "recall-project-context",
                    "bmad-create-product-brief",
                    "bmad-sprint-planning",
                    "bmad-validate-prd",
                ]

        # Show workflows list
        output.append("[bold]Available Workflows:[/bold]")
        for i, wf in enumerate(self.state.bmad_workflows[:20]):  # Show top 20
            prefix = "▶ " if i == self.state.bmad_selected_index else "  "
            output.append(f"{prefix}{wf}")

        if len(self.state.bmad_workflows) > 20:
            output.append(f"  ... and {len(self.state.bmad_workflows) - 20} more")

        output.append("")
        output.append("[bold]Instructions:[/bold]")
        output.append("  [↑/↓] Select workflow")
        output.append("  [Enter] Run selected workflow")
        output.append("  [b] Back to main view")

        # Show output if available
        if self.state.bmad_output:
            output.append("")
            output.append("[bold]Workflow Output:[/bold]")
            # Show last 15 lines of output
            output_lines = self.state.bmad_output.split("\n")[-15:]
            for line in output_lines:
                output.append(f"  {line}")

        output.append("")
        output.append("Press [b]ack to return to main view")

        return "\n".join(output)

    def _run_bmad_workflow(self, workflow_name: str) -> None:
        """Run a BMAD workflow from the dashboard."""
        if not RICH_AVAILABLE:
            return

        print("\n" + "=" * 60)
        print(f"Running BMAD Workflow: {workflow_name}")
        print("=" * 60)

        user_input = input("Enter input for workflow: ").strip()

        if not user_input:
            user_input = "run from dashboard"

        self.state.bmad_running = True

        try:
            from .bmad.executor import execute_workflow

            result = execute_workflow(
                workflow_name=workflow_name,
                phase="create",
                context={"user_input": user_input, "input": user_input},
            )

            if result.success:
                output = f"✅ Workflow '{workflow_name}' completed successfully!\n\n"
                output += "Steps completed:\n"
                for step in result.steps_completed:
                    output += f"  ✓ {step}\n"

                if result.output:
                    output += "\nOutput:\n"
                    for key, value in list(result.output.items())[:3]:
                        output += f"  {key}: {str(value)[:80]}...\n"
            else:
                output = f"❌ Workflow failed: {result.error}\n"
                if result.steps_failed:
                    output += "Steps failed:\n"
                    for step in result.steps_failed:
                        output += f"  ✗ {step}\n"

            self.state.bmad_output = output

        except Exception as e:
            self.state.bmad_output = f"Error running workflow: {e}"

        self.state.bmad_running = False
        print("")

    def refresh_data(self):
        """Refresh dashboard data."""
        self.state.last_refresh = datetime.now()
        # In real implementation, this would query actual pipeline state

    def handle_input(self):
        """Handle keyboard input in separate thread."""
        if not RICH_AVAILABLE:
            return

        try:
            while self.state.running:
                key = self.console.input("[bold](Press key)...[/bold] ")
                key = key.strip().lower()

                if key == "q":
                    self.state.running = False
                    print("\n👋 Shutting down dashboard...")
                    break
                elif key == "s":
                    self.state.current_view = "stats"
                elif key == "h":
                    self.state.current_view = "health"
                elif key == "w":
                    self.state.current_view = "bmad"
                elif key == "b":
                    self.state.current_view = "main"
                elif key == "r":
                    self._run_new_task()
                elif self.state.current_view == "bmad":
                    if key == "\x1b[A":  # Up arrow
                        self.state.bmad_selected_index = max(
                            0, self.state.bmad_selected_index - 1
                        )
                    elif key == "\x1b[B":  # Down arrow
                        self.state.bmad_selected_index = min(
                            len(self.state.bmad_workflows) - 1,
                            self.state.bmad_selected_index + 1,
                        )
                    elif key == "\n" or key == "enter":
                        # Run selected workflow
                        if self.state.bmad_workflows:
                            selected_wf = self.state.bmad_workflows[
                                self.state.bmad_selected_index
                            ]
                            self._run_bmad_workflow(selected_wf)
                elif key == "\x1b[A":  # Up arrow
                    self.state.selected_task_index = max(
                        0, self.state.selected_task_index - 1
                    )
                elif key == "\x1b[B":  # Down arrow
                    self.state.selected_task_index = min(
                        len(self.state.tasks) - 1, self.state.selected_task_index + 1
                    )

        except KeyboardInterrupt:
            self.state.running = False
        except Exception as e:
            print(f"Input error: {e}")

    def _run_new_task(self):
        """Prompt for and run a new task."""
        if not RICH_AVAILABLE:
            return

        print("\n" + "=" * 60)
        print("RUN NEW TASK")
        print("=" * 60)
        task_input = input("Enter task description: ").strip()

        if task_input:
            print(f"📤 Queuing task: {task_input}")
            # In real implementation, this would call the pipeline
            new_task = {
                "id": f"task_{len(self.state.tasks) + 1:03d}",
                "description": task_input,
                "status": "pending",
                "duration_ms": None,
            }
            self.state.tasks.insert(0, new_task)
            print("✅ Task queued!")
        else:
            print("⚠️  No task entered")
        print("")

    def run(self):
        """Run the dashboard."""
        print("Starting N-Xyme Dashboard...")

        if not RICH_AVAILABLE:
            self._run_fallback()
            return

        # Simple render loop (not using Live for better compatibility)
        try:
            while self.state.running:
                self.refresh_data()

                # Clear screen and render
                self.console.clear()

                if self.state.current_view == "stats":
                    content = self.render_stats_view()
                elif self.state.current_view == "health":
                    content = self.render_health_view()
                elif self.state.current_view == "bmad":
                    content = self.render_bmad_view()
                else:
                    content = self.render_main_view()

                self.console.print(content)

                # Wait for input with timeout
                self.console.print(
                    "\n[bold]Auto-refresh in 5s... Press key to interact[/bold]"
                )
                time.sleep(self.refresh_interval)

        except KeyboardInterrupt:
            print("\n👋 Dashboard stopped")

    def _run_fallback(self):
        """Fallback simple text display if Rich not available."""
        print("\n" + "=" * 60)
        print("N-XYME UNIFIED PIPELINE DASHBOARD (Fallback Mode)")
        print("=" * 60)
        print(f"Last refresh: {datetime.now()}")
        print("")
        print("Health:")
        for comp, status in self.state.health.items():
            print(f"  {comp}: {'OK' if status else 'FAIL'}")
        print("")
        print("Stats:")
        for k, v in self.state.stats.items():
            print(f"  {k}: {v}")
        print("")
        print("Recent tasks:")
        for task in self.state.tasks[:5]:
            print(f"  - {task['description']} ({task['status']})")
        print("")
        print("Press Ctrl+C to exit")


def main():
    """Main entry point."""
    dashboard = TUIDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()
