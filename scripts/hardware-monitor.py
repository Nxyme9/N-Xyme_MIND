#!/usr/bin/env python3
"""
Hardware Monitor - Real-time hardware utilization stats for N-Xyme Catalyst.

Monitors CPU, memory, GPU, and disk usage with clean output.

Usage:
    python scripts/hardware-monitor.py              # Show all stats
    python scripts/hardware-monitor.py --json       # JSON output
    python scripts/hardware-monitor.py --cpu        # CPU only
    python scripts/hardware-monitor.py --gpu        # GPU only
    python scripts/hardware-monitor.py --memory     # Memory only
    python scripts/hardware-monitor.py --disk       # Disk only
    python scripts/hardware-monitor.py --watch      # Continuous monitoring (5s interval)
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil


def get_cpu_stats() -> Dict[str, Any]:
    """Get CPU utilization stats."""
    freq = psutil.cpu_freq()
    load_per_core = psutil.cpu_percent(interval=0.5, percpu=True)

    return {
        "cores_physical": psutil.cpu_count(False),
        "cores_logical": psutil.cpu_count(True),
        "load_percent": psutil.cpu_percent(interval=0.1),
        "load_per_core": load_per_core,
        "freq_current_mhz": round(freq.current) if freq else 0,
        "freq_max_mhz": round(freq.max) if freq else 0,
    }


def get_memory_stats() -> Dict[str, Any]:
    """Get memory utilization stats."""
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()

    return {
        "total_gb": round(vm.total / 1e9, 2),
        "available_gb": round(vm.available / 1e9, 2),
        "used_gb": round(vm.used / 1e9, 2),
        "used_percent": vm.percent,
        "swap_total_gb": round(swap.total / 1e9, 2),
        "swap_used_gb": round(swap.used / 1e9, 2),
        "swap_percent": swap.percent,
    }


def get_gpu_stats() -> Optional[Dict[str, Any]]:
    """Get GPU utilization stats via nvidia-smi."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,utilization.memory,temperature.gpu,power.draw,power.limit",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(", ")
            return {
                "name": parts[0],
                "vram_total_mb": int(parts[1]),
                "vram_used_mb": int(parts[2]),
                "vram_free_mb": int(parts[3]),
                "gpu_util_percent": int(parts[4]),
                "mem_util_percent": int(parts[5]),
                "temperature_c": int(parts[6]),
                "power_draw_w": float(parts[7]),
                "power_limit_w": float(parts[8]),
                "vram_used_percent": round(int(parts[2]) / int(parts[1]) * 100, 1),
            }
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass
    return None


def get_disk_stats() -> List[Dict[str, Any]]:
    """Get disk utilization stats for all partitions."""
    disks = []

    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            disks.append(
                {
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "total_gb": round(usage.total / 1e9, 2),
                    "used_gb": round(usage.used / 1e9, 2),
                    "free_gb": round(usage.free / 1e9, 2),
                    "used_percent": usage.percent,
                }
            )
        except PermissionError:
            continue

    return disks


def make_bar(percent: float, width: int = 20) -> str:
    """Create a visual progress bar."""
    filled = int(percent / 100 * width)
    empty = width - filled
    return f"[{'#' * filled}{'.' * empty}]"


def format_cpu(stats: Dict[str, Any]) -> str:
    """Format CPU stats for display."""
    lines = [
        f"  Cores: {stats['cores_physical']} physical / {stats['cores_logical']} logical",
        f"  Load:  {stats['load_percent']}% {make_bar(stats['load_percent'])}",
        f"  Freq:  {stats['freq_current_mhz']} MHz / {stats['freq_max_mhz']} MHz",
    ]

    # Per-core breakdown if multi-core
    if len(stats["load_per_core"]) <= 16:
        lines.append("  Per-core:")
        for i, load in enumerate(stats["load_per_core"]):
            lines.append(f"    Core {i:2d}: {load:5.1f}% {make_bar(load, 10)}")

    return "\n".join(lines)


def format_memory(stats: Dict[str, Any]) -> str:
    """Format memory stats for display."""
    return "\n".join(
        [
            f"  RAM:  {stats['used_gb']}GB / {stats['total_gb']}GB ({stats['used_percent']}%) {make_bar(stats['used_percent'])}",
            f"  Free: {stats['available_gb']}GB available",
            f"  Swap: {stats['swap_used_gb']}GB / {stats['swap_total_gb']}GB ({stats['swap_percent']}%)"
            if stats["swap_total_gb"] > 0
            else "  Swap: Not configured",
        ]
    )


def format_gpu(stats: Optional[Dict[str, Any]]) -> str:
    """Format GPU stats for display."""
    if not stats:
        return "  No NVIDIA GPU detected or nvidia-smi unavailable"

    return "\n".join(
        [
            f"  GPU:   {stats['name']}",
            f"  VRAM:  {stats['vram_used_mb']}MB / {stats['vram_total_mb']}MB ({stats['vram_used_percent']}%) {make_bar(stats['vram_used_percent'])}",
            f"  Free:  {stats['vram_free_mb']}MB",
            f"  Util:  {stats['gpu_util_percent']}% compute | {stats['mem_util_percent']}% memory",
            f"  Temp:  {stats['temperature_c']}°C",
            f"  Power: {stats['power_draw_w']:.1f}W / {stats['power_limit_w']:.1f}W",
        ]
    )


def format_disk(disks: List[Dict[str, Any]]) -> str:
    """Format disk stats for display."""
    lines = []
    for disk in disks:
        lines.append(f"  {disk['device']} ({disk['mountpoint']})")
        lines.append(
            f"    {disk['used_gb']}GB / {disk['total_gb']}GB ({disk['used_percent']}%) {make_bar(disk['used_percent'])}"
        )
        lines.append(f"    Free: {disk['free_gb']}GB")
    return "\n".join(lines) if lines else "  No disks found"


def show_all_stats(json_output: bool = False):
    """Show all hardware stats."""
    stats = {
        "timestamp": datetime.now().isoformat(),
        "cpu": get_cpu_stats(),
        "memory": get_memory_stats(),
        "gpu": get_gpu_stats(),
        "disk": get_disk_stats(),
    }

    if json_output:
        print(json.dumps(stats, indent=2))
        return

    print("=" * 60)
    print("  HARDWARE MONITOR - N-Xyme Catalyst")
    print(f"  {stats['timestamp']}")
    print("=" * 60)

    print("\n[CPU]")
    print(format_cpu(stats["cpu"]))

    print("\n[MEMORY]")
    print(format_memory(stats["memory"]))

    print("\n[GPU]")
    print(format_gpu(stats["gpu"]))

    print("\n[DISK]")
    print(format_disk(stats["disk"]))

    print("=" * 60)


def watch_mode(interval: int = 5):
    """Continuous monitoring mode."""
    try:
        while True:
            # Clear screen (works on Windows and Unix)
            print("\033[2J\033[H", end="")
            show_all_stats()
            print(f"\n  Refreshing every {interval}s... (Ctrl+C to stop)")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n\nStopped.")


def main():
    if "--watch" in sys.argv:
        interval = 5
        # Check for custom interval
        for i, arg in enumerate(sys.argv):
            if arg == "--interval" and i + 1 < len(sys.argv):
                try:
                    interval = int(sys.argv[i + 1])
                except ValueError:
                    pass
        watch_mode(interval)
    elif "--json" in sys.argv:
        show_all_stats(json_output=True)
    elif "--cpu" in sys.argv:
        stats = get_cpu_stats()
        if "--json" in sys.argv:
            print(json.dumps(stats, indent=2))
        else:
            print("[CPU]")
            print(format_cpu(stats))
    elif "--gpu" in sys.argv:
        stats = get_gpu_stats()
        if "--json" in sys.argv:
            print(json.dumps(stats, indent=2))
        else:
            print("[GPU]")
            print(format_gpu(stats))
    elif "--memory" in sys.argv:
        stats = get_memory_stats()
        if "--json" in sys.argv:
            print(json.dumps(stats, indent=2))
        else:
            print("[MEMORY]")
            print(format_memory(stats))
    elif "--disk" in sys.argv:
        stats = get_disk_stats()
        if "--json" in sys.argv:
            print(json.dumps(stats, indent=2))
        else:
            print("[DISK]")
            print(format_disk(stats))
    else:
        show_all_stats()


if __name__ == "__main__":
    main()
