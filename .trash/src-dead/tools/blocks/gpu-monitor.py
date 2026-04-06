#!/usr/bin/env python3
"""
GPU Monitor -- Real-time VRAM/temperature/power monitoring for RTX 3080 Ti.

Monitors GPU at configurable intervals with safety alerts and auto-throttle.
Logs to CSV for historical analysis.

Usage:
    python scripts/gpu-monitor.py                # Monitor at 5s intervals
    python scripts/gpu-monitor.py --interval 2   # Custom interval
    python scripts/gpu-monitor.py --log gpu.csv  # Log to CSV
    python scripts/gpu-monitor.py --once         # Single check and exit
"""

import argparse
import csv
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import requests

logger = logging.getLogger(__name__)

# -- Configuration -----------------------------------------------------

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

# Safety limits
VRAM_MAX_PERCENT = 85.0
VRAM_MAX_GB = 10.2
TEMP_WARNING = 75
TEMP_CRITICAL = 85
POWER_MAX_W = 350

# Power profiles
POWER_PROFILES = {
    "eco": 200,
    "balanced": 300,
    "performance": 350,
}


# -- GPU Queries -------------------------------------------------------


def get_gpu_status() -> Optional[Dict]:
    """Get comprehensive GPU status via nvidia-smi."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.used,memory.total,temperature.gpu,"
                "utilization.gpu,utilization.memory,"
                "power.draw,power.limit,"
                "clocks.current.graphics,clocks.current.memory",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return None

        parts = result.stdout.strip().split(", ")

        used_mb = int(parts[1])
        total_mb = int(parts[2])
        used_gb = used_mb / 1000
        total_gb = total_mb / 1000

        return {
            "name": parts[0],
            "memory_used_mb": used_mb,
            "memory_total_mb": total_mb,
            "memory_used_gb": used_gb,
            "memory_free_gb": total_gb - used_gb,
            "memory_used_percent": (used_gb / total_gb) * 100,
            "temperature_c": int(parts[3]),
            "gpu_util_percent": int(parts[4]),
            "mem_util_percent": int(parts[5]),
            "power_draw_w": float(parts[6]),
            "power_limit_w": float(parts[7]),
            "throttle_thermal": int(parts[3]) > TEMP_CRITICAL,
            "clock_graphics_mhz": int(parts[8]),
            "clock_memory_mhz": int(parts[9]),
            "headroom_gb": VRAM_MAX_GB - used_gb,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"GPU query failed: {e}")
        return None


def get_ollama_models() -> list:
    """Get currently loaded Ollama models."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/ps", timeout=3)
        resp.raise_for_status()
        return resp.json().get("models", [])
    except Exception:
        return []


# -- Safety Checks -----------------------------------------------------


def check_safety(gpu: Dict) -> list:
    """Run safety checks and return list of warnings."""
    warnings = []

    if gpu["memory_used_percent"] > VRAM_MAX_PERCENT:
        warnings.append(f"VRAM CRITICAL: {gpu['memory_used_percent']:.1f}% > {VRAM_MAX_PERCENT}%")

    if gpu["temperature_c"] > TEMP_CRITICAL:
        warnings.append(f"TEMP CRITICAL: {gpu['temperature_c']}degC > {TEMP_CRITICAL}degC")
    elif gpu["temperature_c"] > TEMP_WARNING:
        warnings.append(f"TEMP WARNING: {gpu['temperature_c']}degC > {TEMP_WARNING}degC")

    if gpu["power_draw_w"] > POWER_MAX_W:
        warnings.append(f"POWER WARNING: {gpu['power_draw_w']:.0f}W > {POWER_MAX_W}W")

    if gpu["throttle_thermal"]:
        warnings.append("THERMAL THROTTLING ACTIVE")

    if gpu["headroom_gb"] < 0:
        warnings.append(f"VRAM OVER TARGET: {abs(gpu['headroom_gb']):.1f}GB over 85% limit")

    return warnings


def auto_throttle(gpu: Dict) -> Optional[str]:
    """Auto-adjust based on temperature. Evicts models instead of power limiting."""
    temp = gpu["temperature_c"]

    if temp > TEMP_CRITICAL:
        return f"EMERGENCY: Temp {temp}degC — evict models manually or cool GPU"
    elif temp > TEMP_WARNING:
        return f"WARNING: Temp {temp}degC — consider unloading heavy models"

    return None


# -- Display -----------------------------------------------------------


def format_bar(percent: float, width: int = 30) -> str:
    """Format a progress bar."""
    filled = int(percent / 100 * width)
    return "#" * filled + "." * (width - filled)


def display_status(gpu: Dict, models: list, warnings: list) -> None:
    """Display formatted GPU status."""
    # Clear screen (cross-platform)
    import subprocess; subprocess.run(["clear"], check=False)

    print("=" * 70)
    print(f"GPU MONITOR -- {gpu['timestamp'][:19]}")
    print("=" * 70)

    # VRAM
    vram_bar = format_bar(gpu["memory_used_percent"])
    vram_status = "WARN" if gpu["memory_used_percent"] > VRAM_MAX_PERCENT else "OK"
    print(f"\nVRAM:  {vram_bar} {gpu['memory_used_percent']:.1f}% {vram_status}")
    print(
        f"       {gpu['memory_used_gb']:.1f}GB / {gpu['memory_used_gb'] + gpu['memory_free_gb']:.1f}GB  "
        f"(headroom: {gpu['headroom_gb']:.1f}GB to 85%)"
    )

    # Temperature
    temp = gpu["temperature_c"]
    if temp > TEMP_CRITICAL:
        temp_icon = "[!!]"
    elif temp > TEMP_WARNING:
        temp_icon = "[!]"
    else:
        temp_icon = "[OK]"
    print(f"\nTemp:  {temp_icon} {temp}C", end="")
    if gpu["throttle_thermal"]:
        print("  [THROTTLING]", end="")
    print()

    # Power
    power_pct = (gpu["power_draw_w"] / gpu["power_limit_w"]) * 100
    power_bar = format_bar(power_pct, 20)
    print(f"Power: {power_bar} {gpu['power_draw_w']:.0f}W / {gpu['power_limit_w']:.0f}W")

    # Utilization
    print(f"GPU:   {gpu['gpu_util_percent']}%  |  VRAM Bus: {gpu['mem_util_percent']}%")
    print(f"Clocks: {gpu['clock_graphics_mhz']}MHz core / {gpu['clock_memory_mhz']}MHz mem")

    # Models
    print(f"\nLoaded Models ({len(models)}):")
    if models:
        total_vram = 0
        for m in models:
            vram_mb = m.get("size_vram", 0) / 1e6
            total_vram += vram_mb / 1000
            expires = m.get("expires_at", "")
            if "0001-01-01" in expires:
                keep = "PINNED"
            elif expires:
                keep = f"TTL:{expires[:19]}"
            else:
                keep = "?"
            print(f"  * {m['name']:30s} {vram_mb:6.0f}MB  [{keep}]")
        print(f"  {'Total:':30s} {total_vram:6.1f}GB")
    else:
        print("  (none)")

    # Warnings
    if warnings:
        print(f"\n{'WARNINGS':-^70}")
        for w in warnings:
            print(f"  ! {w}")

    print(f"\n{'-' * 70}")
    print(
        f"Target: {VRAM_MAX_PERCENT}% VRAM ({VRAM_MAX_GB}GB) | "
        f"Temp < {TEMP_CRITICAL}C | Power <= {POWER_MAX_W}W"
    )
    print("Press Ctrl+C to stop")


# -- CSV Logging -------------------------------------------------------


def init_csv(filepath: str) -> csv.writer:
    """Initialize CSV log file."""
    f = open(filepath, "a", newline="")
    writer = csv.writer(f)

    # Write header if file is empty
    if f.tell() == 0:
        writer.writerow(
            [
                "timestamp",
                "vram_used_gb",
                "vram_total_gb",
                "vram_percent",
                "temp_c",
                "gpu_util_percent",
                "power_draw_w",
                "power_limit_w",
                "throttle_thermal",
                "models_loaded",
                "warnings",
            ]
        )

    return writer, f


def log_to_csv(writer, gpu: Dict, models: list, warnings: list) -> None:
    """Log current status to CSV."""
    writer.writerow(
        [
            gpu["timestamp"],
            f"{gpu['memory_used_gb']:.2f}",
            f"{gpu['memory_total_gb']:.2f}",
            f"{gpu['memory_used_percent']:.1f}",
            gpu["temperature_c"],
            gpu["gpu_util_percent"],
            f"{gpu['power_draw_w']:.1f}",
            f"{gpu['power_limit_w']:.1f}",
            gpu["throttle_thermal"],
            len(models),
            "; ".join(warnings) if warnings else "",
        ]
    )


# -- Main Loop ---------------------------------------------------------


def monitor_loop(
    interval: int = 5, csv_path: Optional[str] = None, auto_throttle_enabled: bool = True
) -> None:
    """Main monitoring loop."""
    csv_file = None
    csv_writer = None

    if csv_path:
        csv_writer, csv_file = init_csv(csv_path)
        logger.info(f"Logging to {csv_path}")

    try:
        while True:
            gpu = get_gpu_status()
            if not gpu:
                print("ERROR: Cannot read GPU status")
                time.sleep(interval)
                continue

            models = get_ollama_models()
            warnings = check_safety(gpu)

            # Auto-throttle if enabled
            if auto_throttle_enabled:
                action = auto_throttle(gpu)
                if action:
                    warnings.append(action)

            # Display
            display_status(gpu, models, warnings)

            # Log to CSV
            if csv_writer:
                log_to_csv(csv_writer, gpu, models, warnings)
                csv_file.flush()

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\nMonitor stopped.")
    finally:
        if csv_file:
            csv_file.close()


def main():
    parser = argparse.ArgumentParser(description="GPU Monitor for RTX 3080 Ti")
    parser.add_argument(
        "--interval", "-i", type=int, default=5, help="Update interval in seconds (default: 5)"
    )
    parser.add_argument("--log", "-l", type=str, help="Log to CSV file")
    parser.add_argument("--once", action="store_true", help="Single check and exit")
    parser.add_argument("--no-throttle", action="store_true", help="Disable auto-throttle")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if args.once:
        gpu = get_gpu_status()
        if gpu:
            models = get_ollama_models()
            warnings = check_safety(gpu)
            display_status(gpu, models, warnings)
        else:
            print("ERROR: Cannot read GPU status")
            sys.exit(1)
    else:
        monitor_loop(
            interval=args.interval,
            csv_path=args.log,
            auto_throttle_enabled=not args.no_throttle,
        )


if __name__ == "__main__":
    main()
