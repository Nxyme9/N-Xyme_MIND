#!/usr/bin/env python3
"""
N-Xyme MIND TUI Dashboard — System monitoring for all subsystems.
Monitors: System, GPU, Systemd Services, Dictation, Ralph Loop,
Token Usage, Notification Queue, Auto-Start Services, Service Control.
Refresh: 2 seconds.
"""

import json
import os
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

from rich.live import Live
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.console import Console
import psutil

# === Configuration ===
ROOT = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
REFRESH_INTERVAL = 2

# === System Monitoring ===
def get_system_info() -> Dict[str, Any]:
    """Get system CPU, memory, disk, load average, network I/O."""
    cpu = psutil.cpu_percent(interval=0.3)
    cpu_count = psutil.cpu_count()
    try:
        load = os.getloadavg()
    except Exception:
        load = (0.0, 0.0, 0.0)

    mem = psutil.virtual_memory()
    disk = psutil.disk_usage(str(ROOT))
    net = psutil.net_io_counters()

    return {
        "cpu": cpu,
        "cpu_count": cpu_count,
        "load_1": load[0],
        "load_5": load[1],
        "load_15": load[2],
        "mem_used": mem.percent,
        "mem_total_gb": mem.total / (1024**3),
        "mem_available_gb": mem.available / (1024**3),
        "disk_percent": disk.percent,
        "disk_total_gb": disk.total / (1024**3),
        "disk_free_gb": disk.free / (1024**3),
        "net_sent_mb": net.bytes_sent / (1024**2),
        "net_recv_mb": net.bytes_recv / (1024**2),
    }

# === GPU Monitoring ===
def get_gpu_info() -> Dict[str, Any]:
    """Get GPU info via nvidia-smi."""
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,name,memory.used,memory.total,temperature.gpu,utilization.gpu,utilization.memory",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        lines = [l.strip() for l in r.stdout.strip().split("\n") if l.strip()]
        if not lines:
            return {"error": "No GPU detected"}

        parts = [p.strip() for p in lines[0].split(",")]
        return {
            "index": parts[0],
            "name": parts[1],
            "mem_used_mb": int(parts[2]),
            "mem_total_mb": int(parts[3]),
            "temp_c": int(parts[4]),
            "gpu_util_pct": int(parts[5]),
            "mem_util_pct": int(parts[6]),
        }
    except FileNotFoundError:
        return {"error": "nvidia-smi not found"}
    except Exception as e:
        return {"error": str(e)}

def get_gpu_processes() -> List[Dict[str, str]]:
    """Get GPU compute processes."""
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        lines = [l.strip() for l in r.stdout.strip().split("\n") if l.strip()]
        processes = []
        for line in lines:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3:
                processes.append({
                    "pid": parts[0],
                    "name": parts[1],
                    "mem_mb": parts[2],
                })
        return processes
    except Exception:
        return []

# === Systemd Services ===
def get_systemd_services() -> Dict[str, str]:
    """Check status of user systemd services."""
    service_names = [
        "nx-dictate", "jarvis-bridge", "nx-memory-watcher",
        "nx-guardian", "nx-heartbeat", "nx-meta-monitor",
        "gpu-server", "event-daemon", "jarvis-pc"
    ]
    result = {}
    for name in service_names:
        try:
            r = subprocess.run(
                ["systemctl", "--user", "is-active", f"{name}.service"],
                capture_output=True, text=True, timeout=3
            )
            status = r.stdout.strip()
            if status == "active":
                result[name] = "active"
            elif status == "inactive":
                result[name] = "inactive"
            else:
                result[name] = status
        except Exception:
            result[name] = "unknown"
    return result

# === Dictation Process ===
def get_dictation_status() -> Dict[str, Any]:
    """Check if nx_dictate process is running."""
    for proc in psutil.process_iter(["pid", "name", "cmdline", "cpu_percent", "memory_info"]):
        try:
            cmdline = proc.info.get("cmdline") or []
            if any("nx_dictate" in (c or "") for c in cmdline):
                cpu = proc.cpu_percent(interval=0.1)
                mem_mb = proc.info["memory_info"].rss / (1024 * 1024)
                return {
                    "running": True,
                    "pid": proc.info["pid"],
                    "cpu_pct": f"{cpu:.1f}",
                    "mem_mb": f"{mem_mb:.0f}",
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return {"running": False}

# === Ralph Loop State ===
def get_ralph_state() -> Dict[str, Any]:
    """Check Ralph Loop state from data/ralph-state/active.md."""
    state_file = ROOT / "data" / "ralph-state" / "active.md"
    if not state_file.exists():
        return {"active": False, "iteration": None}

    try:
        content = state_file.read_text()
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 2:
                frontmatter = parts[1]
                for line in frontmatter.split("\n"):
                    if line.startswith("iteration:"):
                        return {"active": True, "iteration": line.split(":", 1)[1].strip()}
        return {"active": True, "iteration": None}
    except Exception:
        return {"active": "error", "iteration": None}

# === Token Usage ===
def get_token_usage() -> Dict[str, Any]:
    """Get token usage from token-guard state."""
    state_file = ROOT / "data" / "token-guard" / "state" / "quota_state.json"
    if not state_file.exists():
        return {}

    try:
        data = json.loads(state_file.read_text())
        return data
    except Exception:
        return {}

def format_token_usage(tokens: Dict[str, Any]) -> str:
    """Format token usage for display."""
    if not tokens:
        return "(no data)"

    daily = tokens.get("daily_total_by_model", {})
    if not daily:
        usage = tokens.get("usage", {})
        daily = usage.get("by_model", {}) if isinstance(usage, dict) else {}

    if not daily:
        return "(no daily data)"

    lines = []
    for model, count in sorted(daily.items(), key=lambda x: x[1], reverse=True):
        lines.append(f"  {model}: {count:,} tokens")

    total = sum(daily.values())
    if total > 0:
        lines.append(f"\n  Total: {total:,} tokens today")

    return "\n".join(lines)

# === Notification Queue ===
def get_notification_queue_count() -> int:
    """Count queued notifications."""
    queue_file = ROOT / "data" / "notifications" / "queue.jsonl"
    if not queue_file.exists():
        return 0

    try:
        content = queue_file.read_text().strip()
        if not content:
            return 0
        lines = content.split("\n")
        return sum(1 for line in lines if line.strip())
    except Exception:
        return 0

# === Auto-Start Services ===
def get_auto_start_services() -> List[str]:
    """Get list of enabled user services."""
    try:
        r = subprocess.run(
            ["systemctl", "--user", "list-unit-files", "--type=service", "--state=enabled"],
            capture_output=True, text=True, timeout=5
        )
        lines = r.stdout.strip().split("\n")
        services = []
        for line in lines[1:]:
            line = line.strip()
            if line and not line.startswith("UNIT FILE"):
                parts = line.split()
                if parts:
                    svc = parts[0].replace(".service", "")
                    services.append(svc)
        return sorted(services)
    except Exception:
        return []

# === Service Control ===
def get_service_restart_policy(service_name: str) -> Optional[str]:
    """Check if service has Restart=always in its unit file."""
    service_file = Path.home() / ".config" / "systemd" / "user" / f"{service_name}.service"
    if not service_file.exists():
        service_file = Path(f"/etc/systemd/user/{service_name}.service")
    if not service_file.exists():
        return None

    try:
        content = service_file.read_text()
        for line in content.split("\n"):
            if line.strip().startswith("Restart="):
                return line.strip().split("=", 1)[1]
    except Exception:
        pass
    return None

def get_active_timers() -> List[str]:
    """Get active user timers."""
    try:
        r = subprocess.run(
            ["systemctl", "--user", "list-timers", "--type=timer"],
            capture_output=True, text=True, timeout=5
        )
        lines = r.stdout.strip().split("\n")
        timers = []
        for line in lines[1:]:
            line = line.strip()
            if line and not line.startswith("NEXT") and not line.startswith("-"):
                parts = line.split()
                if parts:
                    timers.append(parts[0].replace(".timer", ""))
        return timers
    except Exception:
        return []

# === Compiled Agent ===
def get_compiled_agent_status() -> Dict[str, Any]:
    """Query the compiled hephaestus-agent MCP binary for its context."""
    agent_bin = ROOT / "bins" / "hephaestus-agent"
    result = {"status": "unknown", "agent": "n/a", "patterns": 0, "success_rate": 0.0, "error": ""}
    if not agent_bin.exists():
        result["error"] = "binary not found"
        return result
    try:
        import subprocess, json
        p = subprocess.Popen(
            [str(agent_bin)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True
        )
        # Initialize MCP
        p.stdin.write('{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n')
        p.stdin.flush()
        p.stdout.readline()
        # Call get_context
        p.stdin.write('{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_context"}}\n')
        p.stdin.flush()
        resp = json.loads(p.stdout.readline())
        ctx = json.loads(resp["result"]["content"][0]["text"])
        result["status"] = "running"
        result["agent"] = ctx.get("agent", "?")
        result["patterns"] = ctx.get("patterns_loaded", 0)
        result["success_rate"] = ctx.get("success_rate", 0.0)
        p.kill()
    except Exception as e:
        result["error"] = str(e)[:60]
    return result


def get_memory_vector_stats() -> Dict[str, Any]:
    """Get stats about the embedded memory vectors."""
    vec_dir = ROOT / "data" / "memory" / "vectors"
    stats = {"total_agents": 0, "total_vectors": 0, "agents": {}}
    if not vec_dir.exists():
        return stats
    for agent_dir in sorted(vec_dir.iterdir()):
        if not agent_dir.is_dir():
            continue
        count = sum(1 for f in agent_dir.glob("*.jsonl") for _ in open(f))
        if count > 0:
            stats["agents"][agent_dir.name] = count
            stats["total_vectors"] += count
    stats["total_agents"] = len(stats["agents"])
    return stats


def get_mcp_server_status() -> Dict[str, str]:
    """Check which MCP servers are configured and their status."""
    config_file = ROOT / "opencode.json"
    mcp_status = {}
    if not config_file.exists():
        return mcp_status
    try:
        import json as j
        cfg = j.loads(config_file.read_text())
        for name, mcp_cfg in cfg.get("mcp", {}).items():
            enabled = mcp_cfg.get("enabled", False)
            cmd = " ".join(mcp_cfg.get("command", []))[:40]
            status = "enabled" if enabled else "disabled"
            mcp_status[name] = f"[{'green' if enabled else 'red'}]{status}[/]"
            if enabled and name == "hephaestus-agent":
                # Check if binary exists
                import os as os_mod
                bin_path = mcp_cfg["command"][0]
                if os_mod.path.exists(bin_path):
                    mcp_status[name] += f" [green]● {os_mod.path.getsize(bin_path)//1024}K[/]"
                else:
                    mcp_status[name] += f" [red]✗ missing[/]"
    except: pass
    return mcp_status


# === Build Dashboard Layout ===
def build_dashboard() -> Layout:
    """Build the complete dashboard layout."""
    sys_info = get_system_info()
    gpu_info = get_gpu_info()
    gpu_procs = get_gpu_processes()
    services = get_systemd_services()
    dictate = get_dictation_status()
    ralph = get_ralph_state()
    notify_count = get_notification_queue_count()
    tokens = get_token_usage()
    auto_start = get_auto_start_services()
    active_timers = get_active_timers()

    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
    )

    # Header
    header = Table.grid(padding=(0, 1))
    header.add_column(justify="left")
    header.add_column(justify="left")
    header.add_column(justify="left")
    header.add_column(justify="left")
    header.add_column(justify="left")
    header.add_column(justify="right")

    header.add_row(
        f"[bold cyan]N-Xyme MIND Dashboard[/]",
        f"[bold]CPU:[/] {sys_info['cpu']:.1f}% ({sys_info['cpu_count']} cores)",
        f"[bold]RAM:[/] {sys_info['mem_used']:.0f}% ({sys_info['mem_available_gb']:.1f}GB avail)",
        f"[bold]Load:[/] {sys_info['load_1']:.1f} / {sys_info['load_5']:.1f} / {sys_info['load_15']:.1f}",
        f"[bold]Disk:[/] {sys_info['disk_percent']:.0f}% ({sys_info['disk_free_gb']:.1f}GB free)",
        f"[dim]{datetime.now().strftime('%H:%M:%S')}[/]",
    )
    layout["header"].update(Panel(header, style="white on black", box=box.HEAVY, padding=(0, 1)))

    # Main body
    main = Layout()
    main.split_row(
        Layout(name="left", ratio=1),
        Layout(name="right", ratio=1),
    )

    # Left column
    left = Layout()
    left.split_column(
        Layout(name="system_details", size=6),
        Layout(name="gpu", size=10),
        Layout(name="gpu_procs", ratio=1),
    )

    sys_table = Table.grid(padding=(0, 0))
    sys_table.add_row(f"[bold]Network I/O:[/] ↓ {sys_info['net_recv_mb']:.0f}MB  ↑ {sys_info['net_sent_mb']:.0f}MB")
    sys_table.add_row(f"[bold]Memory:[/] {sys_info['mem_total_gb']:.1f}GB total")
    left["system_details"].update(Panel(sys_table, title="System", border_style="blue", padding=(0, 0)))

    if "error" in gpu_info:
        gpu_text = f"[red]GPU Error: {gpu_info['error']}[/]"
        gpu_border = "red"
    else:
        temp = gpu_info.get("temp_c", 0)
        if temp > 80:
            temp_color = "red"
        elif temp > 65:
            temp_color = "yellow"
        else:
            temp_color = "green"

        gpu_border = temp_color
        gpu_text = (
            f"[bold]{gpu_info.get('name', 'GPU')}[/]\n"
            f"Memory: [cyan]{gpu_info['mem_used_mb']}[/] / [cyan]{gpu_info['mem_total_mb']}[/] MiB\n"
            f"Temp: [{temp_color}]{gpu_info['temp_c']}°C[/{temp_color}]  "
            f"GPU Util: [yellow]{gpu_info['gpu_util_pct']}%[/]  "
            f"Mem Util: [magenta]{gpu_info['mem_util_pct']}%[/]"
        )
    left["gpu"].update(Panel(gpu_text, title="GPU", border_style=gpu_border, padding=(0, 1)))

    if gpu_procs:
        proc_lines = []
        for p in gpu_procs[:10]:
            proc_lines.append(f"  PID {p['pid']:>5} | {p['name'][:25]:<25} | {p['mem_mb']} MiB")
        proc_text = "\n".join(proc_lines) if proc_lines else "  (none)"
    else:
        proc_text = "  (no processes)"
    left["gpu_procs"].update(Panel(proc_text, title="GPU Compute Processes", border_style="blue"))

    # Right column
    right = Layout()
    right.split_column(
        Layout(name="services", ratio=1),
        Layout(name="dictate", size=4),
        Layout(name="ralph", size=4),
        Layout(name="tokens", ratio=1),
        Layout(name="notifications", size=3),
        Layout(name="autostart", ratio=1),
        Layout(name="control", ratio=1),
    )

    svc_table = Table(show_header=False, padding=0)
    svc_table.add_column("status", justify="left")
    for name, status in sorted(services.items()):
        if status == "active":
            status_icon = "[green]●[/]"
        elif status in ("inactive", "failed"):
            status_icon = "[red]●[/]"
        else:
            status_icon = "[yellow]●[/]"
        svc_table.add_row(f"{status_icon} {name}")
    right["services"].update(Panel(svc_table, title="Systemd Services", border_style="cyan"))

    if dictate.get("running"):
        dictate_text = (
            f"[green]● RUNNING[/]\n"
            f"  PID: {dictate['pid']}\n"
            f"  CPU: {dictate['cpu_pct']}%\n"
            f"  Mem: {dictate['mem_mb']}MB"
        )
        dictate_border = "green"
    else:
        dictate_text = "[dim]○ stopped[/]"
        dictate_border = "red"
    right["dictate"].update(Panel(dictate_text, title="Dictation (nx_dictate)", border_style=dictate_border))

    if ralph.get("active"):
        ralph_text = f"[yellow]● ACTIVE[/]\n  Iteration: {ralph.get('iteration', '?')}"
        ralph_border = "yellow"
    else:
        ralph_text = "[dim]○ idle[/]"
        ralph_border = "dim"
    right["ralph"].update(Panel(ralph_text, title="Ralph Loop", border_style=ralph_border))

    token_text = format_token_usage(tokens)
    right["tokens"].update(Panel(token_text, title="Token Usage (Daily)", border_style="magenta"))

    if notify_count > 0:
        notify_text = f"[yellow]● {notify_count} queued[/]"
        notify_border = "yellow"
    else:
        notify_text = "[dim]○ empty[/]"
        notify_border = "dim"
    right["notifications"].update(Panel(notify_text, title="Notification Queue", border_style=notify_border))

    if auto_start:
        autostart_text = "\n".join(f"  • {s}" for s in auto_start)
    else:
        autostart_text = "  (none enabled)"
    right["autostart"].update(Panel(autostart_text, title="Auto-Start Services", border_style="green"))

    control_lines = []
    control_lines.append("[bold]Restart=always services:[/]")
    restart_services = []
    for svc in services.keys():
        policy = get_service_restart_policy(svc)
        if policy == "always":
            restart_services.append(svc)
    if restart_services:
        control_lines.append("  " + ", ".join(restart_services))
    else:
        control_lines.append("  (none)")

    control_lines.append("\n[bold]Active timers:[/]")
    if active_timers:
        control_lines.append("  " + ", ".join(active_timers))
    else:
        control_lines.append("  (none)")

    control_text = "\n".join(control_lines)
    right["control"].update(Panel(control_text, title="Service Control", border_style="blue"))

    main["left"].update(left)
    main["right"].update(right)
    layout["main"].update(main)

    return layout

# === Main Loop ===
def main():
    """Run the dashboard."""
    console = Console()
    console.clear()

    try:
        with Live(build_dashboard(), refresh_per_second=0.5, screen=True) as live:
            while True:
                live.update(build_dashboard())
                time.sleep(REFRESH_INTERVAL)
    except KeyboardInterrupt:
        console.print("\n[dim]Dashboard stopped.[/]")


if __name__ == "__main__":
    main()