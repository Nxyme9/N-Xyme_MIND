#!/usr/bin/env python3
"""
GPU Orchestrator -- Unified GPU management for RTX 3080 Ti.

Combines preload, monitor, and hot-swap into a single daemon.
Runs as a background service to maintain optimal GPU utilization.

Usage:
    python scripts/gpu-orchestrator.py start      # Start daemon (preload + monitor)
    python scripts/gpu-orchestrator.py stop        # Stop daemon
    python scripts/gpu-orchestrator.py status      # Show status
    python scripts/gpu-orchestrator.py load <model>   # Load model (hot-swap)
    python scripts/gpu-orchestrator.py unload <model> # Unload model
    python scripts/gpu-orchestrator.py optimize    # Run one-time optimization
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# -- Configuration -----------------------------------------------------

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
SCRIPTS_DIR = Path(__file__).parent
PID_FILE = SCRIPTS_DIR / ".gpu-orchestrator.pid"
LOG_FILE = SCRIPTS_DIR / "gpu-orchestrator.log"
STATE_FILE = SCRIPTS_DIR / ".gpu-state.json"

# VRAM budget
VRAM_TOTAL_GB = 12.0
VRAM_RESERVED_GB = 2.0
VRAM_MAX_GB = VRAM_TOTAL_GB - VRAM_RESERVED_GB  # 10.2GB
VRAM_MAX_PERCENT = 85.0

# Safety limits
TEMP_WARNING = 75
TEMP_CRITICAL = 85

# Resident models (always loaded, pinned)
RESIDENT_MODELS = [
    {"name": "llama3.2:latest", "size_gb": 2.0, "purpose": "Fast tasks"},
    {"name": "qwen2.5-coder:7b", "size_gb": 4.7, "purpose": "Code tasks"},
    {"name": "nomic-embed-text:latest", "size_gb": 0.2, "purpose": "Embeddings"},
]


# -- GPU Queries -------------------------------------------------------


def get_gpu_status() -> Optional[Dict]:
    """Get GPU status via nvidia-smi."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.used,memory.total,temperature.gpu,utilization.gpu,"
                "power.draw,power.limit",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        parts = result.stdout.strip().split(", ")
        used_mb, total_mb = int(parts[0]), int(parts[1])
        used_gb = used_mb / 1000
        total_gb = total_mb / 1000
        temp_c = int(parts[2])
        return {
            "used_gb": used_gb,
            "total_gb": total_gb,
            "free_gb": total_gb - used_gb,
            "used_percent": (used_gb / total_gb) * 100,
            "temperature_c": temp_c,
            "utilization_percent": int(parts[3]),
            "power_draw_w": float(parts[4]),
            "power_limit_w": float(parts[5]),
            "throttle_thermal": temp_c > TEMP_CRITICAL,
            "headroom_gb": VRAM_MAX_GB - used_gb,
        }
    except Exception as e:
        logger.error(f"GPU query failed: {e}")
        return None


def get_loaded_models() -> List[Dict]:
    """Get loaded Ollama models."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/ps", timeout=5)
        resp.raise_for_status()
        return resp.json().get("models", [])
    except Exception:
        return []


# -- Model Operations --------------------------------------------------


def load_model(model_name: str, keep_alive: str = "-1") -> bool:
    """Load model into VRAM."""
    try:
        logger.info(f"Loading {model_name} (keep_alive={keep_alive})")
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model_name,
                "prompt": "ready",
                "stream": False,
                "keep_alive": keep_alive,
                "options": {"num_predict": 1},
            },
            timeout=300,
        )
        resp.raise_for_status()
        logger.info(f"  OK {model_name} loaded")
        return True
    except Exception as e:
        logger.error(f"  FAIL {model_name} failed: {e}")
        return False


def unload_model(model_name: str) -> bool:
    """Unload model from VRAM."""
    try:
        logger.info(f"Unloading {model_name}")
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model_name,
                "prompt": "ready",
                "stream": False,
                "keep_alive": "0",
                "options": {"num_predict": 1},
            },
            timeout=60,
        )
        resp.raise_for_status()
        logger.info(f"  OK {model_name} unloaded")
        return True
    except Exception as e:
        logger.error(f"  FAIL {model_name} failed: {e}")
        return False


# -- Power Management --------------------------------------------------


def set_power_limit(watts: int) -> bool:
    """DEPRECATED: Power limiting disabled — conflicts with MSI Afterburner undervolt."""
    logger.warning(f"Power limit change to {watts}W SKIPPED — use MSI Afterburner instead")
    return False


def auto_power(gpu: Dict) -> int:
    """Determine optimal power based on temperature."""
    temp = gpu["temperature_c"]
    if temp > TEMP_CRITICAL:
        return 200
    elif temp > TEMP_WARNING:
        return 300
    else:
        return 300


# -- State Management --------------------------------------------------


def save_state(state: Dict) -> None:
    """Save orchestrator state to disk."""
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save state: {e}")


def load_state() -> Dict:
    """Load orchestrator state from disk."""
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {"started_at": None, "models_loaded": [], "last_optimize": None}


# -- Core Operations ---------------------------------------------------


def preload_resident() -> int:
    """Pre-load resident models."""
    loaded = 0
    gpu = get_gpu_status()

    for model in RESIDENT_MODELS:
        if not gpu or gpu["headroom_gb"] < model["size_gb"] * 1.2:
            logger.warning(f"Skipping {model['name']} -- insufficient VRAM")
            continue

        if gpu["temperature_c"] > TEMP_CRITICAL:
            logger.warning(f"GPU too hot -- pausing")
            time.sleep(30)
            gpu = get_gpu_status()
            continue

        if load_model(model["name"], keep_alive="-1"):
            loaded += 1
        gpu = get_gpu_status()

    return loaded


def optimize() -> None:
    """One-time optimization: set power, preload models."""
    print("=" * 60)
    print("GPU ORCHESTRATOR -- Optimization")
    print("=" * 60)

    # Check Ollama
    try:
        requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
    except Exception:
        print("ERROR: Ollama not reachable at {OLLAMA_URL}")
        sys.exit(1)

    gpu = get_gpu_status()
    if not gpu:
        print("ERROR: Cannot read GPU")
        sys.exit(1)

    print(f"\nGPU: {gpu['used_gb']:.1f}GB / {gpu['total_gb']:.1f}GB ({gpu['used_percent']:.0f}%)")
    print(f"Temp: {gpu['temperature_c']}degC | Power: {gpu['power_draw_w']:.0f}W")

    # Power management disabled — use MSI Afterburner for undervolt
    print(f"Power: {gpu['power_draw_w']:.0f}W (managed by MSI Afterburner)")

    # Preload
    print(f"\nPreloading {len(RESIDENT_MODELS)} resident models...")
    count = preload_resident()

    # Final status
    gpu = get_gpu_status()
    print(f"\nDone: {count}/{len(RESIDENT_MODELS)} models loaded")
    print(f"VRAM: {gpu['used_gb']:.1f}GB / {gpu['total_gb']:.1f}GB ({gpu['used_percent']:.0f}%)")
    print(f"Headroom: {gpu['headroom_gb']:.1f}GB to 85% target")
    print("=" * 60)


def monitor_daemon(interval: int = 5) -> None:
    """Continuous monitoring loop (runs as daemon)."""
    logger.info("GPU monitor daemon started")

    # Initial preload
    preload_resident()

    # Power management disabled — use MSI Afterburner
    gpu = get_gpu_status()

    # Save state
    save_state(
        {
            "started_at": datetime.now().isoformat(),
            "models_loaded": [m["name"] for m in RESIDENT_MODELS],
            "last_optimize": datetime.now().isoformat(),
        }
    )

    try:
        while True:
            gpu = get_gpu_status()
            if gpu:
                # Auto-throttle on high temp
                if gpu["temperature_c"] > TEMP_CRITICAL:
                    logger.critical(
                        f"GPU TEMP CRITICAL: {gpu['temperature_c']}degC — cool manually!"
                    )
                elif gpu["temperature_c"] > TEMP_WARNING:
                    logger.warning(f"GPU TEMP WARNING: {gpu['temperature_c']}degC")

                # Log warnings
                if gpu["used_percent"] > VRAM_MAX_PERCENT:
                    logger.warning(
                        f"VRAM at {gpu['used_percent']:.1f}% -- over {VRAM_MAX_PERCENT}% limit"
                    )

                if gpu["throttle_thermal"]:
                    logger.warning("GPU thermal throttling active")

            time.sleep(interval)

    except KeyboardInterrupt:
        logger.info("Monitor daemon stopped")


def show_status() -> None:
    """Show comprehensive status."""
    gpu = get_gpu_status()
    loaded = get_loaded_models()
    state = load_state()

    print()
    print("=" * 60)
    print("GPU ORCHESTRATOR STATUS")
    print("=" * 60)
    print()

    if gpu:
        bar_len = 30
        filled = int(gpu["used_percent"] / 100 * bar_len)
        bar = "#" * filled + "." * (bar_len - filled)

        print(f"VRAM:  {bar} {gpu['used_percent']:.1f}%")
        print(
            f"       {gpu['used_gb']:.1f}GB / {gpu['total_gb']:.1f}GB  "
            f"(headroom: {gpu['headroom_gb']:.1f}GB)"
        )
        print()
        print(f"Temp:      {gpu['temperature_c']}C", end="")
        if gpu["temperature_c"] > TEMP_CRITICAL:
            print(" [!!] CRITICAL")
        elif gpu["temperature_c"] > TEMP_WARNING:
            print(" [!] HOT")
        else:
            print(" [OK]")
        print(f"Power:     {gpu['power_draw_w']:.0f}W / {gpu['power_limit_w']:.0f}W")
        print(f"Throttle:  {'YES' if gpu['throttle_thermal'] else 'No'}")

    print()
    print(f"Loaded Models ({len(loaded)}):")
    for m in loaded:
        vram_mb = m.get("size_vram", 0) / 1e6
        expires = m.get("expires_at", "")
        keep = "PINNED" if "0001-01-01" in expires else f"TTL:{expires[:19]}"
        print(f"  * {m['name']:30s} {vram_mb:6.0f}MB  [{keep}]")

    if state.get("started_at"):
        print(f"\nDaemon started: {state['started_at']}")

    # Check if daemon is running
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            # Check if process exists (Windows)
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True,
            )
            if str(pid) in result.stdout:
                print(f"Daemon PID: {pid} (RUNNING)")
            else:
                print(f"Daemon PID: {pid} (STALE)")
        except Exception:
            print("Daemon: status unknown")
    else:
        print("Daemon: NOT RUNNING")

    print("=" * 60)


# -- Daemon Management -------------------------------------------------


def start_daemon() -> None:
    """Start the monitor daemon in background."""
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True,
            )
            if str(pid) in result.stdout:
                print(f"Daemon already running (PID {pid})")
                return
        except Exception:
            pass

    print("Starting GPU orchestrator daemon...")

    # Launch as background process
    script = Path(__file__).resolve()
    process = subprocess.Popen(
        [sys.executable, str(script), "_daemon"],
        stdout=open(LOG_FILE, "a"),
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )

    PID_FILE.write_text(str(process.pid))
    print(f"Daemon started (PID {process.pid})")
    print(f"Log: {LOG_FILE}")


def stop_daemon() -> None:
    """Stop the monitor daemon."""
    if not PID_FILE.exists():
        print("Daemon not running")
        return

    try:
        pid = int(PID_FILE.read_text().strip())
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
        else:
            subprocess.run(["kill", str(pid)], capture_output=True)
        PID_FILE.unlink()
        print(f"Daemon stopped (PID {pid})")
    except Exception as e:
        print(f"Error stopping daemon: {e}")
        PID_FILE.unlink(missing_ok=True)


# -- Main --------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="GPU Orchestrator for RTX 3080 Ti")
    subparsers = parser.add_subparsers(dest="command", help="Command")

    subparsers.add_parser("start", help="Start daemon")
    subparsers.add_parser("stop", help="Stop daemon")
    subparsers.add_parser("status", help="Show status")
    subparsers.add_parser("optimize", help="Run one-time optimization")

    load_p = subparsers.add_parser("load", help="Load model")
    load_p.add_argument("model", help="Model name")
    load_p.add_argument("--keep-alive", default="-1", help="Keep alive duration")

    unload_p = subparsers.add_parser("unload", help="Unload model")
    unload_p.add_argument("model", help="Model name")

    subparsers.add_parser("_daemon", help="Internal: run daemon loop")

    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_FILE, mode="a")
            if args.command == "_daemon"
            else logging.NullHandler(),
        ],
    )

    if args.command == "start":
        start_daemon()
    elif args.command == "stop":
        stop_daemon()
    elif args.command == "status":
        show_status()
    elif args.command == "optimize":
        optimize()
    elif args.command == "load":
        success = load_model(args.model, args.keep_alive)
        sys.exit(0 if success else 1)
    elif args.command == "unload":
        success = unload_model(args.model)
        sys.exit(0 if success else 1)
    elif args.command == "_daemon":
        monitor_daemon()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
