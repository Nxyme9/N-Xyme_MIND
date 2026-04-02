import time
import sys
from datetime import datetime
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text
from rich import box

# Import Client
try:
    from athena_client import AthenaClient
except ImportError:
    # Fallback for direct execution
    import sys
    import os

    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from athena_client import AthenaClient

client = AthenaClient()
console = Console()


def make_layout() -> Layout:
    """Define the grid layout."""
    layout = Layout(name="root")

    layout.split(
        Layout(name="header", size=3),
        Layout(name="main", ratio=1),
        Layout(name="footer", size=3),
    )

    layout["main"].split_row(
        Layout(name="left", ratio=2),  # Context
        Layout(name="right", ratio=1),  # Status/Logs
    )

    return layout


def get_header(health_data) -> Panel:
    """Create the header panel."""
    status = health_data.get("status", "offline")
    version = health_data.get("version", "unknown")

    if status == "online":
        status_text = Text("● ONLINE", style="bold green")
    else:
        status_text = Text("● OFFLINE", style="bold red")

    grid = Table.grid(expand=True)
    grid.add_column(justify="left", ratio=1)
    grid.add_column(justify="center", ratio=1)
    grid.add_column(justify="right", ratio=1)

    grid.add_row("🛡️  ATHENA KERNEL", Text(f"v{version}"), status_text)

    return Panel(grid, style="white on blue")


def get_context_panel() -> Panel:
    """Fetch and render active context."""
    content = client.get_active_context()
    if not content or "Error" in content:
        md = Markdown("*Waiting for context...*")
    else:
        # Truncate context for display if too long?
        # Rich Markdown handles scrolling/truncation naturally in some views, but here it might overflow.
        # We'll just show it.
        md = Markdown(content)

    return Panel(md, title="[bold]Active Memory Bank[/bold]", border_style="green")


def get_status_panel(health_data) -> Panel:
    """Render tools/components status."""
    components = health_data.get("components", {})

    table = Table(show_header=False, expand=True, box=None)
    table.add_column("Component")
    table.add_column("Status", justify="right")

    for name, is_active in components.items():
        status = "✅" if is_active else "❌"
        table.add_row(name.capitalize(), status)

    # Add dummy activity log
    table.add_row("", "")
    table.add_row("[bold]Recent Activity[/bold]", "")
    table.add_row(f"[{datetime.now().strftime('%H:%M:%S')}] Poll", "OK")

    return Panel(table, title="[bold]System Status[/bold]", border_style="cyan")


def run_dashboard():
    layout = make_layout()

    with Live(layout, refresh_per_second=1, screen=True):
        while True:
            # 1. Fetch Data
            health = client.get_health()

            # 2. Update Components
            layout["header"].update(get_header(health))
            layout["left"].update(get_context_panel())
            layout["right"].update(get_status_panel(health))
            layout["footer"].update(Panel(Text("Press Ctrl+C to exit"), style="dim"))

            # 3. Sleep
            time.sleep(2)


if __name__ == "__main__":
    try:
        run_dashboard()
    except KeyboardInterrupt:
        console.print("[bold red]Dashboard closed.[/bold red]")
