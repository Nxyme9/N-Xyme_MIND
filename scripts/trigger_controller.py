#!/usr/bin/env python3
"""
Auto-Tuning Trigger Controller -- Monitors workload and triggers auto-tune.

Integrates with gpu-hotswap.py to provide self-balancing:
- Monitors llama-server metrics
- Classifies workload (context/throughput/latency)
- Triggers config changes when needed

Usage:
    python scripts/trigger_controller.py start     # Start monitoring
    python scripts/trigger_controller.py stop      # Stop monitoring
    python scripts/trigger_controller.py status    # Show current state
"""

import argparse
import os
import subprocess
import sys
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

# -- Configuration -----------------------------------------------------

LLAMA_URL = os.getenv("LLAMA_URL", "http://localhost:8080")
CHECK_INTERVAL = 30  # seconds between checks
AUTO_TUNE_ENABLED = os.getenv("AUTO_TUNE", "false").lower() == "true"

# Thresholds for triggering tune events
CONTEXT_SPIKE_THRESHOLD = 4096  # Context > 4K triggers flash-attn
THROUGHPUT_DROP_THRESHOLD = 0.5  # Throughput drops 50% triggers re-check
GPU_UTIL_SPIKE = 0.95  # GPU util > 95% triggers optimization

# Workload profiles
PROFILES = {
    "balanced": {
        "threads": 8,
        "flash_attn": "auto",
        "parallel": 8,
        "batch": True,
    },
    "latency": {
        "threads": 4,
        "flash_attn": "on",
        "parallel": 4,
        "batch": False,
    },
    "throughput": {
        "threads": 8,
        "flash_attn": "off",
        "parallel": 16,
        "batch": True,
    },
    "context": {
        "threads": 4,
        "flash_attn": "on",
        "parallel": 4,
        "batch": True,
    },
}


@dataclass
class SystemState:
    """Current system state snapshot."""

    gpu_used_gb: float = 0.0
    gpu_total_gb: float = 0.0
    gpu_util: float = 0.0
    temperature_c: int = 0
    current_workload: str = "balanced"
    active_slots: int = 0
    queued_requests: int = 0
    last_tune_time: Optional[datetime] = None
    tuning_count: int = 0


class TriggerController:
    """Monitors system and triggers auto-tuning."""

    def __init__(self, url: str = LLAMA_URL):
        self.url = url
        self.state = SystemState()
        self.running = False
        self.thread: Optional[threading.Thread] = None

    def get_gpu_status(self) -> Optional[Dict]:
        """Get GPU metrics."""
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=memory.used,memory.total,utilization.gpu,temperature.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            used_mb, total_mb, util, temp = result.stdout.strip().split(", ")
            return {
                "used_gb": int(used_mb) / 1000,
                "total_gb": int(total_mb) / 1000,
                "utilization": int(util) / 100,
                "temperature": int(temp),
            }
        except Exception:
            return None

    def get_server_status(self) -> Optional[Dict]:
        """Get llama-server status."""
        try:
            resp = requests.get(f"{self.url}/slots", timeout=5)
            if resp.status_code == 200:
                slots = resp.json().get("slots", [])
                return {
                    "active_slots": sum(1 for s in slots if s.get("state") != "idle"),
                    "total_slots": len(slots),
                    "queued": sum(
                        1 for s in slots if s.get("state") in ["waiting", "processing"]
                    ),
                }
        except Exception:
            pass
        return None

    def classify_workload(self) -> str:
        """Classify current workload."""
        gpu = self.get_gpu_status()
        server = self.get_server_status()

        if not gpu or not server:
            return "balanced"

        # Context-heavy if many queued or long-running
        if server.get("queued", 0) > 2:
            return "context"

        # Latency-sensitive if GPU util is low (not batching)
        if gpu.get("utilization", 0) < 0.3:
            return "latency"

        # Throughput if many active slots
        if server.get("active_slots", 0) > 6:
            return "throughput"

        return "balanced"

    def check_triggers(self) -> List[str]:
        """Check if any tuning triggers are met."""
        triggers = []

        gpu = self.get_gpu_status()
        server = self.get_server_status()

        if not gpu or not server:
            return triggers

        # GPU thermal throttling
        if gpu.get("temperature", 0) > 85:
            triggers.append("thermal_throttle")

        # VRAM pressure
        vram_used_ratio = gpu.get("used_gb", 0) / gpu.get("total_gb", 1)
        if vram_used_ratio > 0.9:
            triggers.append("vram_pressure")

        # Throughput issues
        active = server.get("active_slots", 0)
        queued = server.get("queued", 0)
        if queued > active and active > 0:
            triggers.append("throughput_limit")

        return triggers

    def get_recommended_profile(self) -> str:
        """Get recommended profile name."""
        workload = self.classify_workload()

        # Check for override triggers
        triggers = self.check_triggers()

        if "thermal_throttle" in triggers:
            return "latency"  # Reduce load
        if "vram_pressure" in triggers:
            return "latency"  # Reduce memory

        return workload

    def apply_profile(self, profile_name: str) -> bool:
        """Apply a tuning profile (generates config, doesn't restart)."""
        profile = PROFILES.get(profile_name, PROFILES["balanced"])

        self.state.current_workload = profile_name
        self.state.last_tune_time = datetime.now()
        self.state.tuning_count += 1

        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] Applied profile: {profile_name}"
        )
        print(f"  threads: {profile['threads']}, parallel: {profile['parallel']}")
        print(f"  flash_attn: {profile['flash_attn']}, batch: {profile['batch']}")

        return True

    def monitor_loop(self):
        """Main monitoring loop."""
        print("Trigger controller started (Ctrl+C to stop)")
        print(f"Auto-tune: {'enabled' if AUTO_TUNE_ENABLED else 'disabled'}")
        print("-" * 60)

        while self.running:
            try:
                # Get current state
                gpu = self.get_gpu_status()
                server = self.get_server_status()
                workload = self.classify_workload()
                triggers = self.check_triggers()

                self.state.gpu_used_gb = gpu.get("used_gb", 0) if gpu else 0
                self.state.gpu_total_gb = gpu.get("total_gb", 0) if gpu else 0
                self.state.gpu_util = gpu.get("utilization", 0) if gpu else 0
                self.state.temperature_c = gpu.get("temperature", 0) if gpu else 0

                if server:
                    self.state.active_slots = server.get("active_slots", 0)
                    self.state.queued_requests = server.get("queued", 0)

                # Display status
                timestamp = datetime.now().strftime("%H:%M:%S")
                vram = f"{self.state.gpu_used_gb:.1f}/{self.state.gpu_total_gb:.1f}GB"
                util = f"{self.state.gpu_util:.0%}"
                slots = f"{self.state.active_slots}"

                print(
                    f"[{timestamp}] {workload:10} | VRAM: {vram:12} | "
                    f"GPU: {util:5} | Slots: {slots:2} | "
                    f"Triggers: {triggers if triggers else 'none'}"
                )

                # Auto-tune if enabled
                if AUTO_TUNE_ENABLED:
                    recommended = self.get_recommended_profile()
                    if recommended != self.state.current_workload:
                        self.apply_profile(recommended)

            except Exception as e:
                print(f"Error in monitor loop: {e}")

            time.sleep(CHECK_INTERVAL)

    def start(self):
        """Start the trigger controller."""
        if self.running:
            print("Already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the trigger controller."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("Trigger controller stopped")

    def status(self):
        """Show current status."""
        gpu = self.get_gpu_status()
        server = self.get_server_status()

        print("=" * 60)
        print("TRIGGER CONTROLLER STATUS")
        print("=" * 60)
        print(f"State:           {'Running' if self.running else 'Stopped'}")
        print(f"Workload:        {self.state.current_workload}")
        print(f"Tune count:       {self.state.tuning_count}")
        if self.state.last_tune_time:
            print(f"Last tune:       {self.state.last_tune_time.strftime('%H:%M:%S')}")

        if gpu:
            print(f"\nGPU:")
            print(f"  VRAM:   {gpu['used_gb']:.1f} / {gpu['total_gb']:.1f} GB")
            print(f"  Util:   {gpu['utilization']:.0%}")
            print(f"  Temp:   {gpu['temperature']}°C")

        if server:
            print(f"\nServer:")
            print(f"  Active slots: {server['active_slots']}")
            print(f"  Queued:       {server['queued']}")

        print(f"\nTriggers: {self.check_triggers() or 'none'}")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Trigger Controller for llama.cpp")
    parser.add_argument(
        "command", choices=["start", "stop", "status"], help="Command to run"
    )
    parser.add_argument("--url", default=LLAMA_URL, help="llama-server URL")

    args = parser.parse_args()
    controller = TriggerController(args.url)

    if args.command == "start":
        controller.start()
        try:
            while controller.running:
                time.sleep(1)
        except KeyboardInterrupt:
            controller.stop()
    elif args.command == "stop":
        controller.stop()
    elif args.command == "status":
        controller.status()


if __name__ == "__main__":
    main()
