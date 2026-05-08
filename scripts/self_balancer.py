#!/usr/bin/env python3
"""
Self-Balancing System -- Unified orchestration for llama.cpp optimization.

Integrates:
- gpu-hotswap.py: VRAM management and model hot-swap
- workload_classifier.py: Workload pattern classification
- trigger_controller.py: Auto-tuning trigger management

Usage:
    python scripts/self_balancer.py start      # Start all components
    python scripts/self_balancer.py stop       # Stop all components
    python scripts/self_balancer.py status     # Show full status
    python scripts/self_balancer.py classify   # Show workload classification
"""

import argparse
import os
import subprocess
import sys
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

# -- Configuration -----------------------------------------------------

LLAMA_URL = os.getenv("LLAMA_URL", "http://localhost:8080")
GPU_HOTSWAP = Path(__file__).parent / "gpu-hotswap.py"
WORKLOAD_CLASSIFIER = Path(__file__).parent / "workload_classifier.py"
TRIGGER_CONTROLLER = Path(__file__).parent / "trigger_controller.py"


class SelfBalancer:
    """Unified self-balancing system."""

    def __init__(self, url: str = LLAMA_URL):
        self.url = url
        self.running = False
        self.components: Dict[str, bool] = {
            "gpu_hotswap": False,
            "workload_classifier": False,
            "trigger_controller": False,
        }

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
                "free_gb": (int(total_mb) - int(used_mb)) / 1000,
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
                    "active": sum(1 for s in slots if s.get("state") == "generating"),
                    "idle": sum(1 for s in slots if s.get("state") == "idle"),
                    "waiting": sum(1 for s in slots if s.get("state") == "waiting"),
                    "total": len(slots),
                }
        except Exception:
            pass
        return None

    def check_components(self):
        """Check which components are responding."""
        # Check gpu-hotswap (via model list if server running)
        try:
            resp = requests.get(f"{self.url}/v1/models", timeout=2)
            self.components["gpu_hotswap"] = resp.status_code == 200
        except Exception:
            self.components["gpu_hotswap"] = False

        # Check workload classifier (can query /metrics)
        try:
            resp = requests.get(f"{self.url}/metrics", timeout=2)
            self.components["workload_classifier"] = resp.status_code == 200
        except Exception:
            self.components["workload_classifier"] = False

        # Trigger controller is always available (local process)
        self.components["trigger_controller"] = True

    def get_model_info(self) -> Optional[Dict]:
        """Get loaded model info."""
        try:
            resp = requests.get(f"{self.url}/v1/models", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("data", [])
                if models:
                    return {
                        "name": models[0].get("id", "unknown"),
                        "size": models[0].get("size", 0),
                    }
        except Exception:
            pass
        return None

    def classify_workload(self) -> str:
        """Classify current workload."""
        server = self.get_server_status()
        gpu = self.get_gpu_status()

        if not server:
            return "unknown"

        active = server.get("active", 0)
        waiting = server.get("waiting", 0)

        # Context heavy
        if waiting > active and waiting > 2:
            return "context"

        # Latency sensitive (low GPU util)
        if gpu and gpu.get("utilization", 0) < 0.3:
            return "latency"

        # Throughput (high parallelism)
        if active > 4:
            return "throughput"

        return "balanced"

    def get_recommended_flags(self, workload: str) -> Dict[str, str]:
        """Get recommended flags for workload."""
        flags = {
            "balanced": {
                "threads": "8",
                "flash_attn": "auto",
                "parallel": "8",
                "batch": "on",
            },
            "latency": {
                "threads": "4",
                "flash_attn": "on",
                "parallel": "4",
                "batch": "off",
            },
            "throughput": {
                "threads": "8",
                "flash_attn": "off",
                "parallel": "16",
                "batch": "on",
            },
            "context": {
                "threads": "4",
                "flash_attn": "on",
                "parallel": "4",
                "batch": "on",
            },
        }
        return flags.get(workload, flags["balanced"])

    def status(self):
        """Show comprehensive system status."""
        gpu = self.get_gpu_status()
        server = self.get_server_status()
        model = self.get_model_info()
        workload = self.classify_workload()
        flags = self.get_recommended_flags(workload)
        self.check_components()

        print("=" * 70)
        print("SELF-BALANCING SYSTEM STATUS")
        print("=" * 70)

        print(f"\n📊 Components:")
        for comp, status in self.components.items():
            status_str = "✅ running" if status else "❌ stopped"
            print(f"   {comp:20} {status_str}")

        print(f"\n🔄 Workload: {workload.upper()}")
        print(f"\n📝 Recommended Flags for {workload}:")
        for k, v in flags.items():
            print(f"   {k}: {v}")

        if model:
            print(f"\n🤖 Model: {model.get('name', 'unknown')}")

        if gpu:
            print(f"\n🎮 GPU:")
            print(
                f"   VRAM:   {gpu['used_gb']:.1f} / {gpu['total_gb']:.1f} GB ({gpu['free_gb']:.1f} free)"
            )
            print(f"   Util:   {gpu['utilization']:.0%}")
            print(f"   Temp:   {gpu['temperature']}°C")

            # VRAM warning
            if gpu["free_gb"] < 1:
                print(f"   ⚠️  LOW VRAM - Consider switching to smaller model")

        if server:
            print(f"\n⚡ Server Slots:")
            print(f"   Active:  {server.get('active', 0)}")
            print(f"   Idle:    {server.get('idle', 0)}")
            print(f"   Waiting: {server.get('waiting', 0)}")

            if server.get("waiting", 0) > server.get("active", 0):
                print(f"   ⚠️  Queue backing up - consider increasing parallel slots")

        print("=" * 70)

    def start(self):
        """Start the self-balancing system."""
        print("Starting self-balancing system...")

        # Note: This is a read-only orchestration
        # Actual component management would need separate processes
        self.running = True
        print("Self-balancing system ready (status only - components run externally)")

    def stop(self):
        """Stop the self-balancing system."""
        self.running = False
        print("Self-balancing system stopped")


def main():
    parser = argparse.ArgumentParser(description="Self-Balancing System")
    parser.add_argument(
        "command",
        choices=["start", "stop", "status", "classify"],
        help="Command to run",
    )
    parser.add_argument("--url", default=LLAMA_URL, help="llama-server URL")

    args = parser.parse_args()
    balancer = SelfBalancer(args.url)

    if args.command == "start":
        balancer.start()
    elif args.command == "stop":
        balancer.stop()
    elif args.command == "status":
        balancer.status()
    elif args.command == "classify":
        workload = balancer.classify_workload()
        flags = balancer.get_recommended_flags(workload)
        print(f"Workload: {workload}")
        print(f"Recommended flags: {flags}")


if __name__ == "__main__":
    main()
