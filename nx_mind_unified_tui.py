#!/usr/bin/env python3
"""
N-Xyme MIND Unified TUI
=======================
Rich-based terminal UI with full MCP integration.
Connects to localhost:3000 for all MCP operations.

Usage:
    python3 nx_mind_unified_tui.py
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

ROOT = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.layout import Layout
    from rich.text import Text
    from rich import box
except ImportError:
    print("ERROR: Rich library not installed. Run: pip install rich")
    sys.exit(1)


class MCPClient:
    """HTTP client for N-Xyme MIND MCPs"""

    def __init__(self, base_url: str = "http://localhost:3000/api"):
        self.base_url = base_url
        self.console = Console()

    async def get_health(self) -> dict:
        """Get MCP health status"""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/health")
                return resp.json()
        except Exception as e:
            return {"error": str(e)}

    async def get_learning_status(self) -> dict:
        """Get learning engine status"""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/learning/status")
                return resp.json()
        except Exception as e:
            return {"error": str(e)}

    async def get_routing_stats(self) -> dict:
        """Get routing statistics"""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/routing/stats")
                return resp.json()
        except Exception as e:
            return {"error": str(e)}

    async def get_memory_stats(self) -> dict:
        """Get memory statistics"""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/memory/stats")
                return resp.json()
        except Exception as e:
            return {"error": str(e)}

    async def route_task(self, task: str) -> dict:
        """Route a task via intelligence MCP"""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{self.base_url}/intelligence/route",
                    params={"task_description": task}
                )
                return resp.json()
        except Exception as e:
            return {"error": str(e)}

    async def search_memory(self, query: str) -> dict:
        """Search memory via memory_store MCP"""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.base_url}/memory/search",
                    params={"query": query, "limit": 10}
                )
                return resp.json()
        except Exception as e:
            return {"error": str(e)}

    async def record_outcome(self, task: str, success: bool, latency_ms: int) -> dict:
        """Record outcome to learning MCP"""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{self.base_url}/learning/record",
                    json={
                        "task": task,
                        "success": success,
                        "latency_ms": latency_ms
                    }
                )
                return resp.json()
        except Exception as e:
            return {"error": str(e)}


class UnifiedTUI:
    """Main TUI application"""

    def __init__(self):
        self.console = Console()
        self.client = MCPClient()
        self.running = True

    async def get_mcp_status(self) -> dict:
        """Fetch all MCP status"""
        health = await self.client.get_health()
        return health.get("mcps", {})

    async def get_learning_stats(self) -> dict:
        """Fetch learning statistics"""
        status = await self.client.get_learning_status()
        return status.get("data", {})

    async def get_routing_stats(self) -> dict:
        """Fetch routing statistics"""
        return await self.client.get_routing_stats()

    def render_mcp_panel(self, mcps: dict) -> Panel:
        """Render MCP status panel"""
        table = Table(box=box.SIMPLE, show_header=False)
        table.add_column("MCP", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="dim")

        for name, info in mcps.items():
            status = info.get("status", "unknown")
            if status == "ok":
                status_text = Text("● OK", style="green")
            elif status == "degraded":
                status_text = Text("◐ DEGRADED", style="yellow")
            else:
                status_text = Text("○ ERROR", style="red")

            tools = info.get("tools", info.get("note", ""))
            details = str(tools) if tools else ""

            table.add_row(name, status_text, details)

        return Panel(table, title="[bold]MCP Status[/bold]", border_style="cyan")

    def render_learning_panel(self, stats: dict) -> Panel:
        """Render learning stats panel"""
        if not stats or "error" in stats:
            return Panel("[dim]No data available[/dim]", title="[bold]Learning Stats[/bold]")

        table = Table(box=box.SIMPLE, show_header=True)
        table.add_column("Agent", style="cyan")
        table.add_column("Success", style="green")
        table.add_column("Tasks", style="yellow")
        table.add_column("Avg Latency", style="magenta")

        weights = stats.get("routing_weights", {})
        for agent, data in weights.items():
            success_rate = data.get("success_rate", 0) * 100
            tasks = data.get("total_tasks", 0)
            latency = data.get("avg_latency_ms", 0)

            table.add_row(
                agent,
                f"{success_rate:.1f}%",
                str(tasks),
                f"{latency}ms"
            )

        return Panel(table, title="[bold]Learning Stats[/bold]", border_style="green")

    def render_routing_panel(self, stats: dict) -> Panel:
        """Render routing stats panel"""
        if not stats or "error" in stats:
            return Panel("[dim]No data available[/dim]", title="[bold]Routing Stats[/bold]")

        total = stats.get("total_delegations", 0)
        success_rate = stats.get("success_rate", 0) * 100
        avg_latency = stats.get("avg_latency_ms", 0)
        last_task = stats.get("last_delegation", "N/A")

        table = Table(box=box.SIMPLE, show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")

        table.add_row("Total Delegations", str(total))
        table.add_row("Success Rate", f"{success_rate:.1f}%")
        table.add_row("Avg Latency", f"{avg_latency}ms")
        table.add_row("Last Task", last_task[:40])

        return Panel(table, title="[bold]Routing Stats[/bold]", border_style="magenta")

    async def refresh_display(self):
        """Refresh all panels"""
        mcps = await self.get_mcp_status()
        learning = await self.get_learning_stats()
        routing = await self.get_routing_stats()

        self.console.clear()
        self.console.print(Panel(
            "[bold cyan]N-Xyme MIND Unified TUI[/bold cyan] - Press Ctrl+C to exit",
            style="cyan"
        ))
        self.console.print()

        if mcps:
            self.console.print(self.render_mcp_panel(mcps))
            self.console.print()

        if learning:
            self.console.print(self.render_learning_panel(learning))
            self.console.print()

        if routing:
            self.console.print(self.render_routing_panel(routing))

        self.console.print("\n[dim]Refreshing in 10 seconds...[/dim]")

    async def run(self):
        """Main run loop"""
        await self.refresh_display()

        while self.running:
            try:
                await asyncio.sleep(10)
                await self.refresh_display()
            except asyncio.CancelledError:
                break
            except KeyboardInterrupt:
                break


async def main():
    """Entry point"""
    console = Console()
    console.print("[bold cyan]Starting N-Xyme MIND Unified TUI...[/bold cyan]")

    tui = UnifiedTUI()
    try:
        await tui.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())