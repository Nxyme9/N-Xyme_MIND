#!/usr/bin/env python3
"""
Echo Hardware Daemon - Lightweight system monitor
Monitors GPU, RAM, CPU, NVMe and provides intelligent feedback.
"""

import time
import logging
import os
import json
import subprocess
import threading
import requests
from datetime import datetime
from typing import Optional

# ─── CONFIG ──────────────────────────────────────────────────────────────────
CHECK_INTERVAL = 5  # seconds

# Import centralized configuration
try:
    from jarvis.config.graphiti_config import GRAPHITI_RPC_URL as GRAPHITI_URL, OLLAMA_URL
except ImportError:
    GRAPHITI_URL = os.getenv("GRAPHITI_RPC_URL", "http://localhost:8001/json-rpc")
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

# ─── THRESHOLDS ──────────────────────────────────────────────────────────────
THRESHOLDS = {
    "gpu_temp_warn": 80,
    "gpu_temp_critical": 90,
    "gpu_vram_warn_pct": 90,
    "ram_warn_pct": 85,
    "ram_critical_pct": 95,
    "ram_warn_free_gb": 2,
    "cpu_warn_pct": 80,
    "cpu_sustained_seconds": 300,
    "nvme_warn_free_gb": 50,
    "nvme_critical_free_gb": 20,
}


# ─── HARDWARE MONITORS ───────────────────────────────────────────────────────
def get_gpu_status():
    """Get GPU status via nvidia-smi."""
    try:
        r = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=temperature.gpu,memory.used,memory.total,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0:
            parts = r.stdout.strip().split(", ")
            temp = int(parts[0])
            vram_used = int(parts[1])
            vram_total = int(parts[2])
            util = int(parts[3])
            return {
                "temp": temp,
                "vram_used_mb": vram_used,
                "vram_total_mb": vram_total,
                "vram_free_mb": vram_total - vram_used,
                "vram_used_pct": round(vram_used / vram_total * 100, 1) if vram_total > 0 else 0,
                "utilization": util,
            }
    except Exception as e:
        logging.error(f"Error getting GPU status: {e}")
    return {"temp": 0, "vram_free_mb": 0, "utilization": 0}


def get_ram_status():
    """Get RAM status via psutil."""
    try:
        import psutil

        mem = psutil.virtual_memory()
        return {
            "total_gb": round(mem.total / 1e9, 1),
            "used_gb": round(mem.used / 1e9, 1),
            "free_gb": round(mem.available / 1e9, 1),
            "used_pct": mem.percent,
        }
    except Exception as e:
        logging.error(f"Error getting RAM status: {e}")
        return {"free_gb": 0, "used_pct": 0}


def get_cpu_status():
    """Get CPU status via psutil."""
    try:
        import psutil

        return {
            "load_pct": psutil.cpu_percent(interval=1),
            "cores": psutil.cpu_count(False),
            "threads": psutil.cpu_count(True),
        }
    except Exception as e:
        logging.error(f"Error getting CPU status: {e}")
        return {"load_pct": 0}


def get_disk_status():
    """Get disk status."""
    try:
        import psutil

        c = psutil.disk_usage("C:/")
        d = psutil.disk_usage("D:/")
        return {
            "c_free_gb": round(c.free / 1e9, 1),
            "c_used_pct": round(c.used / c.total * 100, 1),
            "d_free_gb": round(d.free / 1e9, 1),
            "d_used_pct": round(d.used / d.total * 100, 1),
        }
    except Exception as e:
        logging.error(f"Error getting disk status: {e}")
        return {"c_free_gb": 0, "d_free_gb": 0}


def check_ollama_health():
    """Check if Ollama is responding."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        return r.status_code == 200
    except Exception as e:
        logging.error(f"Error checking Ollama health: {e}")
        return False


def get_ollama_models():
    """Get loaded Ollama models."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/ps", timeout=3)
        data = r.json()
        return [
            {
                "name": m["name"],
                "vram_gb": round(m.get("size_vram", 0) / 1e9, 1),
            }
            for m in data.get("models", [])
        ]
    except Exception as e:
        logging.error(f"Error getting Ollama models: {e}")
        return []


# ─── ALERT ENGINE ────────────────────────────────────────────────────────────
class AlertEngine:
    """Generates alerts based on hardware state."""

    def __init__(self):
        self.last_alerts = {}
        self.alert_cooldown = 60  # seconds between same alert
        self.cpu_high_start = None

    def check(self, state: dict) -> list:
        """Check state and return alerts."""
        alerts = []
        now = time.time()

        # GPU temperature
        gpu_temp = state.get("gpu", {}).get("temp", 0)
        if gpu_temp >= THRESHOLDS["gpu_temp_critical"]:
            alerts.append(
                self._make_alert(
                    "gpu_temp_critical",
                    now,
                    f"GPU at {gpu_temp}C! Throttling recommended.",
                    "critical",
                )
            )
        elif gpu_temp >= THRESHOLDS["gpu_temp_warn"]:
            alerts.append(
                self._make_alert("gpu_temp_warn", now, f"GPU warming up: {gpu_temp}C", "warning")
            )

        # RAM
        ram = state.get("ram", {})
        ram_free = ram.get("free_gb", 0)
        ram_pct = ram.get("used_pct", 0)
        if ram_pct >= THRESHOLDS["ram_critical_pct"]:
            alerts.append(
                self._make_alert(
                    "ram_critical",
                    now,
                    f"RAM critical: {ram_free}GB free ({ram_pct}% used)",
                    "critical",
                )
            )
        elif ram_free < THRESHOLDS["ram_warn_free_gb"]:
            alerts.append(
                self._make_alert("ram_warn", now, f"RAM tight: {ram_free}GB free", "warning")
            )

        # CPU sustained high
        cpu_load = state.get("cpu", {}).get("load_pct", 0)
        if cpu_load >= THRESHOLDS["cpu_warn_pct"]:
            if self.cpu_high_start is None:
                self.cpu_high_start = now
            elif now - self.cpu_high_start >= THRESHOLDS["cpu_sustained_seconds"]:
                alerts.append(
                    self._make_alert(
                        "cpu_sustained",
                        now,
                        f"CPU at {cpu_load}% for {int(now - self.cpu_high_start)}s",
                        "warning",
                    )
                )
        else:
            self.cpu_high_start = None

        # NVMe
        nvme_free = state.get("disk", {}).get("c_free_gb", 0)
        if nvme_free < THRESHOLDS["nvme_critical_free_gb"]:
            alerts.append(
                self._make_alert(
                    "nvme_critical",
                    now,
                    f"C: drive critical: {nvme_free}GB left",
                    "critical",
                )
            )
        elif nvme_free < THRESHOLDS["nvme_warn_free_gb"]:
            alerts.append(
                self._make_alert("nvme_warn", now, f"C: drive low: {nvme_free}GB left", "warning")
            )

        # Ollama health
        if not state.get("ollama_healthy", True):
            alerts.append(
                self._make_alert("ollama_down", now, "Ollama not responding!", "critical")
            )

        return alerts

    def _make_alert(self, key: str, now: float, message: str, priority: str) -> Optional[dict]:
        """Create alert with cooldown."""
        last = self.last_alerts.get(key, 0)
        if now - last < self.alert_cooldown:
            return None  # Cooldown
        self.last_alerts[key] = now
        return {"key": key, "message": message, "priority": priority, "time": now}


# ─── MAIN DAEMON ─────────────────────────────────────────────────────────────
class HardwareDaemon:
    """Main hardware monitoring daemon."""

    def __init__(self, callback=None):
        self.callback = callback
        self.alert_engine = AlertEngine()
        self.running = True
        self.state = {}

    def run(self):
        """Main monitoring loop."""
        print("=" * 50)
        print("  ECHO HARDWARE DAEMON")
        print(f"  Checking every {CHECK_INTERVAL}s")
        print("=" * 50)

        while self.running:
            try:
                # Gather state
                self.state = {
                    "gpu": get_gpu_status(),
                    "ram": get_ram_status(),
                    "cpu": get_cpu_status(),
                    "disk": get_disk_status(),
                    "ollama_healthy": check_ollama_health(),
                    "ollama_models": get_ollama_models(),
                    "timestamp": datetime.now().isoformat(),
                }

                # Check for alerts
                alerts = self.alert_engine.check(self.state)

                # Process alerts
                for alert in alerts:
                    if alert:
                        print(f"[{alert['priority'].upper()}] {alert['message']}")
                        if self.callback:
                            self.callback(alert)

                # Print status (compact)
                gpu = self.state["gpu"]
                ram = self.state["ram"]
                cpu = self.state["cpu"]
                print(
                    f"\rGPU:{gpu['util']}% {gpu['temp']}C | RAM:{ram['used_pct']}% | CPU:{cpu['load_pct']}%",
                    end="",
                )

            except Exception as e:
                print(f"\nError: {e}")

            time.sleep(CHECK_INTERVAL)

    def get_state(self) -> dict:
        """Get current state (thread-safe)."""
        return self.state.copy()

    def stop(self):
        """Stop monitoring."""
        self.running = False


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────
if __name__ == "__main__":

    def on_alert(alert):
        """Handle alerts."""
        # Could integrate with Echo TTS here
        pass

    daemon = HardwareDaemon(callback=on_alert)
    try:
        daemon.run()
    except KeyboardInterrupt:
        print("\nDaemon stopped.")
        daemon.stop()
