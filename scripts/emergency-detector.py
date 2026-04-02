#!/usr/bin/env python3
"""
Emergency Detector - Chernobyl Protocol
Monitors screen, GPU, and system health
Triggers emergency protocol on dangerous conditions
"""

import psutil
import subprocess
import time
import json
import requests
import logging

logger = logging.getLogger(__name__)


class EmergencyDetector:
    """Monitors system health and triggers emergency protocol"""

    def __init__(self):
        self.running = True
        self.last_check = time.time()

    def check_screen_health(self):
        """Check if screen is working"""
        try:
            # Check if display is responsive
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                gpu_usage = result.stdout.strip()
                return {"status": "ok", "gpu": gpu_usage}
            else:
                return {"status": "error", "gpu": "unknown"}
        except (subprocess.SubprocessError, OSError):
            return {"status": "error", "gpu": "unreachable"}

    def check_system_health(self):
        """Check system resources"""
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
        return {"cpu": cpu, "ram": ram, "status": "healthy" if cpu < 80 and ram < 85 else "warning"}

    def check_gpu_health(self):
        """Check GPU status"""
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=temperature.gpu,utilization.gpu,memory.used",
                    "--format=csv,noheader",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                data = result.stdout.strip().split(", ")
                return {
                    "temp": int(data[0]),
                    "util": int(data[1].replace("%", "")),
                    "memory": data[2],
                    "status": "healthy" if int(data[0]) < 80 else "hot",
                }
        except Exception as e:
            logger.debug(f"Failed to check GPU health: {e}")
        return {"status": "unknown"}

    def detect_emergency(self):
        """Detect emergency conditions"""
        screen = self.check_screen_health()
        system = self.check_system_health()
        gpu = self.check_gpu_health()

        emergencies = []

        # Screen blank
        if screen["status"] == "error":
            emergencies.append(("CODE_RED", "Screen blank or unreachable"))

        # CPU overloaded
        if system["cpu"] > 95:
            emergencies.append(("CODE_YELLOW", f"CPU overloaded: {system['cpu']}%"))

        # RAM critical
        if system["ram"] > 90:
            emergencies.append(("CODE_YELLOW", f"RAM critical: {system['ram']}%"))

        # GPU overheating
        if gpu["status"] == "hot":
            emergencies.append(("CODE_RED", f"GPU overheating: {gpu['temp']}C"))

        return emergencies

    def trigger_chernobyl(self, emergencies):
        """Trigger Chernobyl protocol"""
        print("CHERNOBYL EVENT DETECTED!")
        print("=" * 70)

        for code, message in emergencies:
            print(f"  {code}: {message}")

        print()
        print("EMERGENCY PROTOCOL ACTIVATED:")
        print("  1. All agents stopping")
        print("  2. Dedicated agents starting fix")
        print("  3. System recovery in progress")
        print("  4. Waiting for user confirmation")
        print()

        # Log to global memory
        try:
            requests.post(
                "http://localhost:8001/json-rpc",
                json={
                    "jsonrpc": "2.0",
                    "method": "memory/write",
                    "params": {
                        "key": f"emergency-{int(time.time())}",
                        "value": json.dumps(
                            {
                                "timestamp": time.time(),
                                "emergencies": emergencies,
                                "protocol": "chernobyl",
                            }
                        ),
                    },
                    "id": 1,
                },
            )
        except Exception as e:
            logger.debug(f"Failed to log emergency to memory: {e}")

    def run(self):
        """Main detection loop"""
        print("Emergency Detector started")
        print("Monitoring: Screen, GPU, CPU, RAM")
        print()

        while self.running:
            emergencies = self.detect_emergency()

            if emergencies:
                self.trigger_chernobyl(emergencies)
                break

            time.sleep(10)  # Check every 10 seconds


if __name__ == "__main__":
    detector = EmergencyDetector()
    detector.run()
