#!/usr/bin/env python3
"""
N-Xyme_MIND Real-Time Monitoring Dashboard

Usage:
    python3 scripts/monitor.py              # Single-shot mode
    python3 scripts/monitor.py --watch       # Refresh every 5 seconds
    python3 scripts/monitor.py --watch -i 10 # Custom interval (seconds)
"""

import argparse
import json
import sqlite3
import subprocess
import time
from pathlib import Path
from datetime import datetime

try:
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.panel import Panel
    from rich.layout import Layout
except ImportError:
    print("ERROR: rich not installed. Run: uv add rich")
    exit(1)

console = Console()
ROOT = Path(__file__).parent.parent.resolve()

# MCP Servers from opencode.json (6 Python MCPs + 3 external)
MCP_SERVERS = [
    ("sequential-thinking", "/usr/bin/mcp-server-sequential-thinking"),
    ("memory", "/usr/bin/mcp-server-memory"),
    ("context7", "/usr/bin/context7-mcp"),
    ("filesystem", "/usr/bin/mcp-server-filesystem"),
    ("git", "/usr/local/bin/mcp-server-git"),
    ("github", "/usr/local/bin/mcp-server-github"),
    ("athena (Python)", f"{ROOT}/athena/src/mcp_server.py"),
    ("nx-mind (Python)", f"{ROOT}/src/mcp/nxmind_mcp.py"),
    ("unified-memory (Python)", f"{ROOT}/src/mcp/unified_memory_mcp.py"),
]

# External MCPs from opencode.json
EXTERNAL_MCPS = [
    ("athena", f"{ROOT}/athena/src/mcp_server.py"),
    ("nx-mind", f"{ROOT}/src/mcp/nxmind_mcp.py"),
    ("unified-memory", f"{ROOT}/src/mcp/unified_memory_mcp.py"),
]


def check_mcp_servers():
    """Check MCP server binary existence."""
    results = []
    for name, path in MCP_SERVERS:
        exists = Path(path).exists()
        results.append((name, exists, path))
    return results


def check_ollama():
    """Check Ollama model status and connectivity."""
    try:
        result = subprocess.run(
            ["curl", "-sf", "--max-time", "3", "http://localhost:11434/api/tags"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            models = data.get("models", [])
            return True, models
        return False, []
    except Exception:
        return False, []


def check_proxy():
    """Check proxy health (localhost:8080)."""
    try:
        result = subprocess.run(
            ["curl", "-sf", "--max-time", "2", "http://localhost:8080/health"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return True, "Healthy"
        return False, f"Code {result.returncode}"
    except Exception as e:
        return False, str(e)


def check_memory_stats():
    """Get memory system stats from SQLite databases."""
    stats = {"indexed_files": 0, "embeddings": 0, "routing_outcomes": 0}
    
    # Check context.db for indexed files
    ctx_db = ROOT / ".sisyphus" / "context.db"
    if ctx_db.exists():
        try:
            conn = sqlite3.connect(ctx_db)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM files")
            stats["indexed_files"] = cur.fetchone()[0]
            conn.close()
        except Exception:
            pass
    
    # Check memory.db for embeddings
    mem_db = ROOT / ".sisyphus" / "memory.db"
    if mem_db.exists():
        try:
            conn = sqlite3.connect(mem_db)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM embeddings")
            stats["embeddings"] = cur.fetchone()[0]
            conn.close()
        except Exception:
            pass
    
    # Check outcomes.db for routing outcomes
    outcomes_db = ROOT / ".sisyphus" / "outcomes.db"
    if outcomes_db.exists():
        try:
            conn = sqlite3.connect(outcomes_db)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM outcomes")
            stats["routing_outcomes"] = cur.fetchone()[0]
            conn.close()
        except Exception:
            pass
    
    return stats


def check_learning_stats():
    """Get learning engine stats from routing database."""
    stats = {"q_entries": 0, "success_rate": 0.0, "total_decisions": 0}
    
    routing_db = ROOT / ".sisyphus" / "routing_learning.db"
    if routing_db.exists():
        try:
            conn = sqlite3.connect(routing_db)
            cur = conn.cursor()
            
            # Count Q-table entries
            try:
                cur.execute("SELECT COUNT(*) FROM q_table")
                stats["q_entries"] = cur.fetchone()[0]
            except Exception:
                pass
            
            # Calculate success rate
            try:
                cur.execute("SELECT success FROM outcomes")
                outcomes = cur.fetchall()
                if outcomes:
                    success_count = sum(1 for o in outcomes if o[0])
                    stats["success_rate"] = round(success_count / len(outcomes) * 100, 1)
                    stats["total_decisions"] = len(outcomes)
            except Exception:
                pass
            
            conn.close()
        except Exception:
            pass
    
    return stats


def check_disk_and_process():
    """Check disk space and key processes."""
    # Disk space
    try:
        result = subprocess.run(
            ["df", "-h", str(ROOT)],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 2:
                parts = lines[1].split()
                disk_used = parts[2] if len(parts) > 2 else "?"
                disk_avail = parts[3] if len(parts) > 3 else "?"
                disk_info = f"{disk_used} used / {disk_avail} available"
            else:
                disk_info = "Unknown"
        else:
            disk_info = "Error"
    except Exception as e:
        disk_info = f"Error: {e}"
    
    # Key processes
    processes = []
    for name, cmd in [("ollama", "ollama"), ("opencode", "opencode"), ("model-router", "model-router")]:
        try:
            result = subprocess.run(
                ["pgrep", "-f", cmd],
                capture_output=True, text=True, timeout=2
            )
            running = result.returncode == 0 and result.stdout.strip()
            processes.append((name, running))
        except Exception:
            processes.append((name, False))
    
    return disk_info, processes


def build_dashboard():
    """Build all dashboard sections."""
    sections = {}
    
    # 1. MCP Server Status
    mcp_results = check_mcp_servers()
    mcp_table = Table(title="MCP Servers", show_header=True)
    mcp_table.add_column("Server", style="cyan")
    mcp_table.add_column("Status", style="bold")
    mcp_table.add_column("Path", style="dim")
    
    for name, exists, path in mcp_results:
        status = "[green]✓ Available[/green]" if exists else "[red]✗ Missing[/red]"
        mcp_table.add_row(name, status, path[:50] + "..." if len(path) > 50 else path)
    
    sections["mcp"] = mcp_table
    
    # 2. Ollama Model Status
    ollama_ok, models = check_ollama()
    ollama_table = Table(title="Ollama Models", show_header=True)
    ollama_table.add_column("Model", style="cyan")
    ollama_table.add_column("Size", style="dim")
    
    if ollama_ok:
        ollama_table.add_row("[green]Ollama Service[/green]", "[green]✓ Connected[/green]")
        for model in models:
            name = model.get("name", "unknown")
            size = model.get("size", 0)
            size_gb = round(size / (1024**3), 1) if size else 0
            ollama_table.add_row(name, f"{size_gb} GB")
    else:
        ollama_table.add_row("[red]Ollama Service[/red]", "[red]✗ Not Connected[/red]")
    
    sections["ollama"] = ollama_table
    
    # 3. Proxy Health
    proxy_ok, proxy_msg = check_proxy()
    proxy_table = Table(title="Proxy (localhost:8080)", show_header=False)
    if proxy_ok:
        proxy_table.add_row("[green]✓ Proxy Healthy[/green]", f"[dim]{proxy_msg}[/dim]")
    else:
        proxy_table.add_row("[red]✗ Proxy Unhealthy[/red]", f"[dim]{proxy_msg}[/dim]")
    sections["proxy"] = proxy_table
    
    # 4. Memory System Stats
    mem_stats = check_memory_stats()
    mem_table = Table(title="Memory System", show_header=True)
    mem_table.add_column("Metric", style="cyan")
    mem_table.add_column("Count", style="bold")
    mem_table.add_row("Indexed Files", str(mem_stats["indexed_files"]))
    mem_table.add_row("Embeddings", str(mem_stats["embeddings"]))
    mem_table.add_row("Routing Outcomes", str(mem_stats["routing_outcomes"]))
    sections["memory"] = mem_table
    
    # 5. Learning Engine Stats
    learn_stats = check_learning_stats()
    learn_table = Table(title="Learning Engine", show_header=True)
    learn_table.add_column("Metric", style="cyan")
    learn_table.add_column("Value", style="bold")
    learn_table.add_row("Q-Table Entries", str(learn_stats["q_entries"]))
    learn_table.add_row("Success Rate", f"{learn_stats['success_rate']}%")
    learn_table.add_row("Total Decisions", str(learn_stats["total_decisions"]))
    sections["learning"] = learn_table
    
    # 6. Disk & Process Status
    disk_info, procs = check_disk_and_process()
    sys_table = Table(title="System", show_header=True)
    sys_table.add_column("Metric", style="cyan")
    sys_table.add_column("Status", style="bold")
    sys_table.add_row("Disk", disk_info)
    for name, running in procs:
        status = "[green]✓ Running[/green]" if running else "[red]✗ Not Running[/red]"
        sys_table.add_row(f"Process: {name}", status)
    sections["system"] = sys_table
    
    return sections


def render_dashboard():
    """Render full dashboard to console."""
    console.clear()
    console.print(f"[bold cyan]N-Xyme_MIND Monitoring Dashboard[/bold cyan]")
    console.print(f"[dim]Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
    console.print()
    
    sections = build_dashboard()
    
    for section in ["mcp", "ollama", "proxy", "memory", "learning", "system"]:
        console.print(sections[section])
        console.print()


def main():
    parser = argparse.ArgumentParser(description="N-Xyme_MIND Real-Time Monitor")
    parser.add_argument("--watch", "-w", action="store_true", help="Watch mode (refresh every 5 seconds)")
    parser.add_argument("--interval", "-i", type=int, default=5, help="Refresh interval in seconds")
    args = parser.parse_args()
    
    if args.watch:
        with Live(refresh_per_second=1) as live:
            while True:
                live.update(render_dashboard())
                time.sleep(args.interval)
    else:
        render_dashboard()


if __name__ == "__main__":
    main()