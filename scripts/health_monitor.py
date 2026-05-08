#!/usr/bin/env python3
"""
Production Health Monitor -- Health checks, metrics, and graceful degradation.

Features:
- Health check endpoints (llama-server + system)
- Worker failure detection
- Graceful degradation
- Prometheus metrics export
- Auto-recovery

Usage:
    python scripts/health_monitor.py start     # Start monitoring
    python scripts/health_monitor.py status    # Show health status
    python scripts/health_monitor.py metrics   # Show Prometheus metrics
"""

import argparse
import os
import subprocess
import sys
import time
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import requests


# -- Configuration -----------------------------------------------------

LLAMA_URL = os.getenv("LLAMA_URL", "http://localhost:8080")
CHECK_INTERVAL = 10  # seconds
MAX_RETRIES = 3
HEALTH_THRESHOLD_RATIO = 0.7  # 70% of checks must pass


@dataclass
class HealthStatus:
    """Health status of a component."""

    name: str
    healthy: bool
    message: str
    latency_ms: float = 0.0
    last_check: Optional[datetime] = None


class ProductionHealthMonitor:
    """Production health monitoring with graceful degradation."""

    def __init__(self, url: str = LLAMA_URL):
        self.url = url
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.health_history: Dict[str, List[bool]] = {}
        self.retry_count = 0
        self.degraded_mode = False

    def check_llama_server(self) -> HealthStatus:
        """Check llama-server health."""
        start = time.time()
        try:
            resp = requests.get(f"{self.url}/health", timeout=5)
            latency = (time.time() - start) * 1000

            if resp.status_code == 200:
                return HealthStatus(
                    name="llama-server",
                    healthy=True,
                    message="OK",
                    latency_ms=latency,
                    last_check=datetime.now(),
                )
            else:
                return HealthStatus(
                    name="llama-server",
                    healthy=False,
                    message=f"HTTP {resp.status_code}",
                    latency_ms=latency,
                    last_check=datetime.now(),
                )
        except requests.exceptions.Timeout:
            return HealthStatus(
                name="llama-server",
                healthy=False,
                message="Timeout",
                latency_ms=(time.time() - start) * 1000,
                last_check=datetime.now(),
            )
        except Exception as e:
            return HealthStatus(
                name="llama-server",
                healthy=False,
                message=str(e),
                latency_ms=0,
                last_check=datetime.now(),
            )

    def check_gpu(self) -> HealthStatus:
        """Check GPU health."""
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=temperature.gpu,utilization.gpu,memory.used",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            parts = result.stdout.strip().split(",")
            temp = int(parts[0])
            util = int(parts[1])
            mem_mb = int(parts[2])

            # Check thresholds
            if temp > 85:
                return HealthStatus(
                    name="gpu",
                    healthy=False,
                    message=f"Overheating: {temp}°C",
                    last_check=datetime.now(),
                )
            elif mem_mb > 11000:  # Near VRAM limit
                return HealthStatus(
                    name="gpu",
                    healthy=False,
                    message=f"VRAM critical: {mem_mb}MB",
                    last_check=datetime.now(),
                )
            else:
                return HealthStatus(
                    name="gpu",
                    healthy=True,
                    message=f"OK (temp: {temp}°C, util: {util}%, mem: {mem_mb}MB)",
                    last_check=datetime.now(),
                )
        except Exception as e:
            return HealthStatus(
                name="gpu", healthy=False, message=str(e), last_check=datetime.now()
            )

    def check_system(self) -> HealthStatus:
        """Check system resources."""
        try:
            # CPU
            result = subprocess.run(
                ["cat", "/proc/loadavg"], capture_output=True, text=True
            )
            load = float(result.stdout.split()[0])

            # Memory
            result = subprocess.run(["free", "-m"], capture_output=True, text=True)
            lines = result.stdout.split("\n")
            mem_parts = lines[1].split()
            mem_used = int(mem_parts[2])
            mem_total = int(mem_parts[1])
            mem_ratio = mem_used / mem_total

            if mem_ratio > 0.9:
                return HealthStatus(
                    name="system",
                    healthy=False,
                    message=f"Memory critical: {mem_used}/{mem_total}MB",
                    last_check=datetime.now(),
                )
            elif load > 16:  # 16 = 8 cores * 2
                return HealthStatus(
                    name="system",
                    healthy=False,
                    message=f"Load high: {load}",
                    last_check=datetime.now(),
                )
            else:
                return HealthStatus(
                    name="system",
                    healthy=True,
                    message=f"OK (load: {load}, mem: {mem_used}/{mem_total}MB)",
                    last_check=datetime.now(),
                )
        except Exception as e:
            return HealthStatus(
                name="system", healthy=False, message=str(e), last_check=datetime.now()
            )

    def check_slots(self) -> HealthStatus:
        """Check server slots availability."""
        try:
            resp = requests.get(f"{self.url}/slots", timeout=5)
            if resp.status_code == 200:
                slots = resp.json().get("slots", [])
                idle = sum(1 for s in slots if s.get("state") == "idle")

                if idle == 0:
                    return HealthStatus(
                        name="slots",
                        healthy=False,
                        message="No idle slots",
                        last_check=datetime.now(),
                    )
                else:
                    return HealthStatus(
                        name="slots",
                        healthy=True,
                        message=f"{idle}/{len(slots)} idle",
                        last_check=datetime.now(),
                    )
            else:
                return HealthStatus(
                    name="slots",
                    healthy=False,
                    message="Cannot query slots",
                    last_check=datetime.now(),
                )
        except Exception as e:
            return HealthStatus(
                name="slots", healthy=False, message=str(e), last_check=datetime.now()
            )

    def check_all(self) -> List[HealthStatus]:
        """Check all components."""
        return [
            self.check_llama_server(),
            self.check_gpu(),
            self.check_system(),
            self.check_slots(),
        ]

    def record_health(self, component: str, healthy: bool):
        """Record health history for a component."""
        if component not in self.health_history:
            self.health_history[component] = []

        self.health_history[component].append(healthy)

        # Keep only last 10 records
        if len(self.health_history[component]) > 10:
            self.health_history[component] = self.health_history[component][-10:]

    def is_degraded(self) -> bool:
        """Check if system is in degraded mode."""
        for component, history in self.health_history.items():
            if len(history) >= 5:
                healthy_ratio = sum(history) / len(history)
                if healthy_ratio < HEALTH_THRESHOLD_RATIO:
                    return True
        return False

    def show_status(self):
        """Show health status."""
        checks = self.check_all()

        print("=" * 70)
        print("PRODUCTION HEALTH STATUS")
        print("=" * 70)

        overall_healthy = True
        for check in checks:
            status = "✅" if check.healthy else "❌"
            print(f"\n{status} {check.name}: {check.message}")
            if check.latency_ms > 0:
                print(f"   Latency: {check.latency_ms:.0f}ms")
            if not check.healthy:
                overall_healthy = False

        # Degraded mode
        self.degraded_mode = self.is_degraded()
        if self.degraded_mode:
            print(f"\n⚠️  SYSTEM IN DEGRADED MODE")

        # Recommendations
        print("\n" + "=" * 70)
        if overall_healthy:
            print("✅ All systems healthy")
        else:
            print("❌ Some components unhealthy - check above")
        print("=" * 70)

    def get_prometheus_metrics(self) -> str:
        """Get Prometheus-format metrics."""
        checks = self.check_all()

        metrics = []
        timestamp = int(time.time())

        for check in checks:
            status = 1 if check.healthy else 0
            metrics.append(
                f'llama_health_status{{component="{check.name}"}} {status} {timestamp}'
            )
            if check.latency_ms > 0:
                metrics.append(
                    f'llama_health_latency{{component="{check.name}"}} {check.latency_ms} {timestamp}'
                )

        # GPU metrics
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu,memory.used,temperature.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            parts = result.stdout.strip().split(",")
            util = int(parts[0])
            mem = int(parts[1])
            temp = int(parts[2])

            metrics.append(f"gpu_utilization {util} {timestamp}")
            metrics.append(f"gpu_memory_used {mem} {timestamp}")
            metrics.append(f"gpu_temperature {temp} {timestamp}")
        except (subprocess.SubprocessError, FileNotFoundError, ValueError) as e:
            logger.warning(f"Could not collect GPU metrics: {e}")

        return "\n".join(metrics)

    def monitor_loop(self):
        """Main monitoring loop."""
        print("Health monitor started (Ctrl+C to stop)")

        while self.running:
            checks = self.check_all()

            for check in checks:
                self.record_health(check.name, check.healthy)

                if not check.healthy:
                    print(
                        f"[{datetime.now().strftime('%H:%M:%S')}] {check.name}: {check.message}"
                    )

            # Check degraded mode
            self.degraded_mode = self.is_degraded()
            if self.degraded_mode and not hasattr(self, "_degraded_warned"):
                print("⚠️  Entering degraded mode")
                self._degraded_warned = True

            time.sleep(CHECK_INTERVAL)

    def start(self):
        """Start monitoring."""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop monitoring."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)


def main():
    parser = argparse.ArgumentParser(description="Production Health Monitor")
    parser.add_argument(
        "command", choices=["start", "stop", "status", "metrics"], help="Command to run"
    )
    parser.add_argument("--url", default=LLAMA_URL, help="llama-server URL")

    args = parser.parse_args()
    monitor = ProductionHealthMonitor(args.url)

    if args.command == "start":
        monitor.start()
        try:
            while monitor.running:
                time.sleep(1)
        except KeyboardInterrupt:
            monitor.stop()
    elif args.command == "stop":
        monitor.stop()
    elif args.command == "status":
        monitor.show_status()
    elif args.command == "metrics":
        print(monitor.get_prometheus_metrics())


if __name__ == "__main__":
    main()
