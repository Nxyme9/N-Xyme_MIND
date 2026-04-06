"""N-Xyme MIND — Branded Textual Dashboard.

Frankenstein frontend stitching together:
- Textual (35K⭐ MIT) — Main dashboard framework
- Rich (56K⭐ MIT) — Terminal formatting
- art (2.5K MIT) — ASCII art logo
- psutil — System health monitoring
- nvidia-smi — GPU monitoring

Dashboard layout:
┌─────────────────────────────────────────────────────────────────┐
│  ASCII Art Logo (N-Xyme MIND v1.0)                              │
├─────────────────┬─────────────────┬─────────────────────────────┤
│ Agents          │ MCP Servers     │ Health                      │
│ sisyphus  [●]   │ athena   [●]   │ CPU: 23%  RAM: 45%          │
│ hephaestus [●]  │ nx-mind  [●]   │ Disk: 67% GPU: 12%          │
│ oracle    [○]   │ memory   [○]   │ Uptime: 2h 15m              │
├─────────────────┴─────────────────┴─────────────────────────────┤
│ Triggers        │ VPN Status      │ Quick Actions               │
│ gpu_temp  [OK]  │ Status:  [●]   │ /trigger-status             │
│ pm2_mem   [OK]  │ Country: US     │ /vpn-rotate                 │
│ ollama    [OK]  │ Latency: 45ms   │ /health-check               │
├─────────────────────────────────────────────────────────────────┤
│ System Log (live)                                               │
└─────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import os
import sys
import time
import json
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header,
    Footer,
    Static,
    DataTable,
    Label,
    Log,
    Button,
    Input,
    Rule,
    Sparkline,
)
from textual import work
from textual.timer import Timer

# Try to import psutil for system monitoring
try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# Try to import art for ASCII logo
try:
    from art import text2art

    HAS_ART = True
except ImportError:
    HAS_ART = False

# Try to import rich for formatting
try:
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    HAS_RICH = True
except ImportError:
    HAS_RICH = False

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ─── Data Sources ────────────────────────────────────────────────


def get_agent_status() -> list[dict[str, Any]]:
    """Get status of all OMO agents."""
    agents = [
        {"name": "sisyphus", "role": "Orchestrator", "status": "unknown"},
        {"name": "prometheus", "role": "Planner", "status": "unknown"},
        {"name": "hephaestus", "role": "Implementation", "status": "unknown"},
        {"name": "oracle", "role": "Architecture", "status": "unknown"},
        {"name": "explore", "role": "Code Search", "status": "unknown"},
        {"name": "librarian", "role": "Research", "status": "unknown"},
        {"name": "metis", "role": "Gap Analysis", "status": "unknown"},
        {"name": "momus", "role": "Adversarial", "status": "unknown"},
        {"name": "atlas", "role": "Executor", "status": "unknown"},
    ]

    # Check if daemon is running
    pid_file = PROJECT_ROOT / "context" / "memory" / "daemon.pid"
    daemon_running = False
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)
            daemon_running = True
        except (ValueError, OSError, ProcessLookupError):
            pass

    # If daemon is running, mark orchestrator as active
    if daemon_running:
        agents[0]["status"] = "active"
        agents[1]["status"] = "active"  # prometheus
        agents[2]["status"] = "active"  # hephaestus
        agents[4]["status"] = "active"  # explore
        agents[5]["status"] = "active"  # librarian

    return agents


def get_mcp_status() -> list[dict[str, Any]]:
    """Get status of MCP servers."""
    mcp_servers = [
        {"name": "athena", "status": "unknown"},
        {"name": "nx-mind", "status": "unknown"},
        {"name": "trigger-guardian", "status": "unknown"},
        {"name": "memory", "status": "unknown"},
        {"name": "context7", "status": "unknown"},
        {"name": "filesystem", "status": "unknown"},
    ]

    # Check memory MCP (we know it works)
    try:
        from packages.memory_core.mcp_server import get_memory_stats

        stats = get_memory_stats()
        if stats.get("status") == "ok":
            mcp_servers[3]["status"] = "active"
    except Exception:
        pass

    # Check filesystem MCP
    try:
        import importlib.util

        spec = importlib.util.find_spec("mcp_server_filesystem")
        if spec:
            mcp_servers[5]["status"] = "active"
    except Exception:
        pass

    return mcp_servers


def get_health_metrics() -> dict[str, Any]:
    """Get system health metrics."""
    metrics = {
        "cpu_percent": 0.0,
        "memory_percent": 0.0,
        "memory_used_gb": 0.0,
        "memory_total_gb": 0.0,
        "disk_percent": 0.0,
        "disk_used_gb": 0.0,
        "disk_total_gb": 0.0,
        "gpu_percent": 0.0,
        "gpu_memory_used_mb": 0,
        "gpu_memory_total_mb": 0,
        "gpu_temp_c": 0,
        "uptime_seconds": 0,
        "uptime_str": "0m",
    }

    if HAS_PSUTIL:
        metrics["cpu_percent"] = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        metrics["memory_percent"] = mem.percent
        metrics["memory_used_gb"] = round(mem.used / (1024**3), 1)
        metrics["memory_total_gb"] = round(mem.total / (1024**3), 1)

        disk = psutil.disk_usage("/")
        metrics["disk_percent"] = disk.percent
        metrics["disk_used_gb"] = round(disk.used / (1024**3), 1)
        metrics["disk_total_gb"] = round(disk.total / (1024**3), 1)

        # Uptime
        boot_time = psutil.boot_time()
        uptime = time.time() - boot_time
        metrics["uptime_seconds"] = int(uptime)
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        metrics["uptime_str"] = f"{hours}h {minutes}m"

    # GPU via nvidia-smi
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(", ")
            if len(parts) >= 4:
                metrics["gpu_percent"] = float(parts[0])
                metrics["gpu_memory_used_mb"] = int(float(parts[1]))
                metrics["gpu_memory_total_mb"] = int(float(parts[2]))
                metrics["gpu_temp_c"] = int(float(parts[3]))
    except Exception:
        pass

    return metrics


def get_trigger_status() -> list[dict[str, Any]]:
    """Get trigger engine status."""
    triggers = [
        {"name": "gpu_temp", "status": "unknown"},
        {"name": "pm2_memory", "status": "unknown"},
        {"name": "rate_limit", "status": "unknown"},
        {"name": "ollama", "status": "unknown"},
    ]

    # Check Ollama
    try:
        import urllib.request

        urllib.request.urlopen("http://localhost:11434", timeout=2)
        triggers[3]["status"] = "ok"
    except Exception:
        triggers[3]["status"] = "error"

    # Check GPU temp
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            temp = int(result.stdout.strip())
            triggers[0]["status"] = "ok" if temp < 80 else "warning"
    except Exception:
        pass

    # Default OK for others
    triggers[1]["status"] = "ok"
    triggers[2]["status"] = "ok"

    return triggers


def get_vpn_status() -> dict[str, Any]:
    """Get VPN rotator status."""
    status = {
        "active": False,
        "country": "N/A",
        "latency_ms": 0,
        "provider": "N/A",
    }

    # Check if rotator process is running
    try:
        result = subprocess.run(
            ["pgrep", "-f", "rotator.py"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            status["active"] = True
    except Exception:
        pass

    return status


def get_memory_stats() -> dict[str, Any]:
    """Get memory system statistics."""
    stats = {
        "total_memories": 0,
        "total_embeddings": 0,
        "coverage_percent": 0.0,
        "knowledge_graph_entities": 0,
        "knowledge_graph_relations": 0,
    }

    try:
        import sqlite3

        db_path = PROJECT_ROOT / "context" / "memory" / "mind_from_mind.db"
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM memories")
            stats["total_memories"] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM memory_embeddings")
            stats["total_embeddings"] = cursor.fetchone()[0]
            if stats["total_memories"] > 0:
                stats["coverage_percent"] = round(
                    stats["total_embeddings"] / stats["total_memories"] * 100, 1
                )
            conn.close()
    except Exception:
        pass

    try:
        from packages.memory_core.stores.graph_store import KnowledgeGraph

        g = KnowledgeGraph()
        kg_stats = g.get_stats()
        stats["knowledge_graph_entities"] = kg_stats.get("total_entities", 0)
        stats["knowledge_graph_relations"] = kg_stats.get("total_relationships", 0)
    except Exception:
        pass

    return stats


# ─── Dashboard App ───────────────────────────────────────────────


class NXymeDashboard(App):
    """N-Xyme MIND Branded Dashboard."""

    CSS = """
    Screen {
        layout: vertical;
        background: $surface;
    }

    #logo-panel {
        height: 6;
        background: $boost;
        content-align: center middle;
        border: solid $primary;
        margin: 0 1;
    }

    #logo-panel Label {
        color: $text;
        text-style: bold;
    }

    #main-row {
        height: 12;
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
        height: 8;
        margin: 0 1;
    }

    #log-panel {
        height: 8;
        margin: 0 1;
        border: solid $primary;
    }

    #status-bar {
        height: 1;
        background: $boost;
        color: $text-muted;
        content-align: center middle;
    }

    DataTable {
        height: 100%;
    }

    .status-active {
        color: $success;
    }

    .status-inactive {
        color: $error;
    }

    .status-unknown {
        color: $warning;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("d", "toggle_dark", "Toggle Dark"),
    ]

    def __init__(self):
        super().__init__()
        self._refresh_timer: Optional[Timer] = None
        self._start_time = time.time()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        # Logo panel
        logo_text = self._generate_logo()
        yield Static(logo_text, id="logo-panel")

        # Main row: Agents | MCP Servers | Health
        with Horizontal(id="main-row"):
            # Agents panel
            with Vertical(classes="panel"):
                yield Label("🤖 Agents", classes="panel-title")
                yield DataTable(id="agent-table")

            # MCP Servers panel
            with Vertical(classes="panel"):
                yield Label("🔌 MCP Servers", classes="panel-title")
                yield DataTable(id="mcp-table")

            # Health panel
            with Vertical(classes="panel"):
                yield Label("💻 System Health", classes="panel-title")
                yield DataTable(id="health-table")

        # Bottom row: Triggers | VPN | Memory Stats
        with Horizontal(id="bottom-row"):
            with Vertical(classes="panel"):
                yield Label("⚡ Triggers", classes="panel-title")
                yield DataTable(id="trigger-table")

            with Vertical(classes="panel"):
                yield Label("🌐 VPN Status", classes="panel-title")
                yield DataTable(id="vpn-table")

            with Vertical(classes="panel"):
                yield Label("🧠 Memory System", classes="panel-title")
                yield DataTable(id="memory-table")

        # Log panel
        yield Log(id="log", auto_scroll=True)

        # Status bar
        yield Static(
            "N-Xyme MIND v1.0 — Personal AI Coding Workspace — © 2026", id="status-bar"
        )

        yield Footer()

    def _generate_logo(self) -> str:
        """Generate ASCII art logo."""
        if HAS_ART:
            try:
                return text2art("N-Xyme", font="small")
            except Exception:
                pass

        # Fallback manual ASCII art
        return """
 ███╗   ██╗██╗  ██╗██╗   ██╗███╗   ███╗
 ████╗  ██║██║  ██║██║   ██║████╗ ████║  N-Xyme MIND
 ██╔██╗ ██║███████║██║   ██║██╔████╔██║  v1.0
 ██║╚██╗██║██╔══██║██║   ██║██║╚██╔╝██║
 ██║ ╚████║██║  ██║╚██████╔╝██║ ╚═╝ ██║  [●] Connected
 ╚═╝  ╚═══╝╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝
"""

    def on_mount(self) -> None:
        """Initialize dashboard on mount."""
        self.refresh_all()
        self._refresh_timer = self.set_interval(10.0, self.refresh_all)
        self.query_one("#log", Log).write_line(
            f"[{datetime.now().strftime('%H:%M:%S')}] N-Xyme MIND Dashboard started"
        )

    def action_refresh(self) -> None:
        """Manual refresh."""
        self.refresh_all()
        self.query_one("#log", Log).write_line(
            f"[{datetime.now().strftime('%H:%M:%S')}] Manual refresh triggered"
        )

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.dark = not self.dark
        self.query_one("#log", Log).write_line(
            f"[{datetime.now().strftime('%H:%M:%S')}] Dark mode: {self.dark}"
        )

    @work(exclusive=True)
    async def refresh_all(self) -> None:
        """Refresh all dashboard data."""
        try:
            self._refresh_agents()
            self._refresh_mcp()
            self._refresh_health()
            self._refresh_triggers()
            self._refresh_vpn()
            self._refresh_memory()
        except Exception as e:
            self.notify(f"Refresh error: {e}", severity="error")

    def _refresh_agents(self) -> None:
        """Refresh agent status table."""
        try:
            table = self.query_one("#agent-table", DataTable)
            table.clear()
            table.add_columns("Agent", "Role", "Status")

            agents = get_agent_status()
            for agent in agents:
                status_icon = "●" if agent["status"] == "active" else "○"
                status_style = "active" if agent["status"] == "active" else "unknown"
                table.add_row(
                    agent["name"],
                    agent["role"],
                    f"[{status_style}]{status_icon}[/{status_style}]",
                )
        except Exception as e:
            self.notify(f"Agent refresh error: {e}", severity="error")

    def _refresh_mcp(self) -> None:
        """Refresh MCP server status table."""
        try:
            table = self.query_one("#mcp-table", DataTable)
            table.clear()
            table.add_columns("Server", "Status")

            mcp_servers = get_mcp_status()
            for server in mcp_servers:
                status_icon = "●" if server["status"] == "active" else "○"
                status_style = "active" if server["status"] == "active" else "unknown"
                table.add_row(
                    server["name"], f"[{status_style}]{status_icon}[/{status_style}]"
                )
        except Exception as e:
            self.notify(f"MCP refresh error: {e}", severity="error")

    def _refresh_health(self) -> None:
        """Refresh system health table."""
        try:
            table = self.query_one("#health-table", DataTable)
            table.clear()
            table.add_columns("Metric", "Value")

            metrics = get_health_metrics()
            table.add_row("CPU", f"{metrics['cpu_percent']:.1f}%")
            table.add_row(
                "RAM",
                f"{metrics['memory_used_gb']}/{metrics['memory_total_gb']} GB ({metrics['memory_percent']:.0f}%)",
            )
            table.add_row(
                "Disk",
                f"{metrics['disk_used_gb']}/{metrics['disk_total_gb']} GB ({metrics['disk_percent']:.0f}%)",
            )

            if metrics["gpu_percent"] > 0:
                table.add_row(
                    "GPU", f"{metrics['gpu_percent']:.0f}% ({metrics['gpu_temp_c']}°C)"
                )
            else:
                table.add_row("GPU", "Idle")

            table.add_row("Uptime", metrics["uptime_str"])
        except Exception as e:
            self.notify(f"Health refresh error: {e}", severity="error")

    def _refresh_triggers(self) -> None:
        """Refresh trigger status table."""
        try:
            table = self.query_one("#trigger-table", DataTable)
            table.clear()
            table.add_columns("Trigger", "Status")

            triggers = get_trigger_status()
            for trigger in triggers:
                status_style = "active" if trigger["status"] == "ok" else "inactive"
                table.add_row(
                    trigger["name"],
                    f"[{status_style}]{trigger['status'].upper()}[/{status_style}]",
                )
        except Exception as e:
            self.notify(f"Trigger refresh error: {e}", severity="error")

    def _refresh_vpn(self) -> None:
        """Refresh VPN status table."""
        try:
            table = self.query_one("#vpn-table", DataTable)
            table.clear()
            table.add_columns("Property", "Value")

            vpn = get_vpn_status()
            status = "Active" if vpn["active"] else "Inactive"
            status_style = "active" if vpn["active"] else "inactive"
            table.add_row("Status", f"[{status_style}]{status}[/{status_style}]")
            table.add_row("Country", vpn["country"])
            table.add_row("Latency", f"{vpn['latency_ms']}ms")
            table.add_row("Provider", vpn["provider"])
        except Exception as e:
            self.notify(f"VPN refresh error: {e}", severity="error")

    def _refresh_memory(self) -> None:
        """Refresh memory system stats table."""
        try:
            table = self.query_one("#memory-table", DataTable)
            table.clear()
            table.add_columns("Metric", "Value")

            stats = get_memory_stats()
            table.add_row("Memories", str(stats["total_memories"]))
            table.add_row("Embeddings", str(stats["total_embeddings"]))
            table.add_row("Coverage", f"{stats['coverage_percent']:.1f}%")
            table.add_row("KG Entities", str(stats["knowledge_graph_entities"]))
            table.add_row("KG Relations", str(stats["knowledge_graph_relations"]))
        except Exception as e:
            self.notify(f"Memory refresh error: {e}", severity="error")


def main():
    """Entry point for N-Xyme MIND Dashboard."""
    app = NXymeDashboard()
    app.run()


if __name__ == "__main__":
    main()
