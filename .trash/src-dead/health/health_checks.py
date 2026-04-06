"""
Health Checks — Built-in health check functions

Provides ready-to-use health checks for common components.

Usage:
    from health_core import HealthMonitor
    from health_checks import create_process_check, create_port_check, create_url_check

    monitor = HealthMonitor()
    monitor.register("ollama", create_process_check("ollama"))
    monitor.register("port_8001", create_port_check(8001))
    monitor.register("neo4j", create_url_check("http://localhost:7474"))
"""

import logging
import time
import socket
from typing import Callable, List, Optional

import httpx
import psutil

from src.health.health_core import ComponentHealth, ComponentStatus, HealthMetric

logger = logging.getLogger(__name__)


def create_process_check(process_name: str) -> Callable[[], ComponentStatus]:
    """Create a health check for a process."""
    start_time = time.time()

    def check() -> ComponentStatus:
        try:
            for proc in psutil.process_iter(["name", "status", "cpu_percent"]):
                if proc.info["name"] and process_name.lower() in proc.info["name"].lower():
                    return ComponentStatus(
                        name=f"process.{process_name}",
                        health=ComponentHealth.HEALTHY,
                        message=f"{process_name} is running",
                        uptime_seconds=time.time() - start_time,
                        metrics=[
                            HealthMetric(name="status", value=proc.info["status"], unit=""),
                            HealthMetric(
                                name="cpu", value=proc.info.get("cpu_percent", 0), unit="%"
                            ),
                        ],
                    )

            return ComponentStatus(
                name=f"process.{process_name}",
                health=ComponentHealth.UNHEALTHY,
                message=f"{process_name} not found",
            )
        except Exception as e:
            return ComponentStatus(
                name=f"process.{process_name}", health=ComponentHealth.UNHEALTHY, error=str(e)
            )

    return check


def create_port_check(port: int, name: str = None) -> Callable[[], ComponentStatus]:
    """Create a health check for a network port."""
    name = name or f"port.{port}"
    start_time = time.time()

    def check() -> ComponentStatus:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("127.0.0.1", port))
            sock.close()

            if result == 0:
                return ComponentStatus(
                    name=name,
                    health=ComponentHealth.HEALTHY,
                    message=f"Port {port} is open",
                    uptime_seconds=time.time() - start_time,
                )
            else:
                return ComponentStatus(
                    name=name, health=ComponentHealth.UNHEALTHY, message=f"Port {port} is closed"
                )
        except Exception as e:
            return ComponentStatus(name=name, health=ComponentHealth.UNHEALTHY, error=str(e))

    return check


def create_url_check(url: str, timeout: float = 3.0) -> Callable[[], ComponentStatus]:
    """Create a health check for a URL."""
    start_time = time.time()

    def check() -> ComponentStatus:
        try:
            client = httpx.Client(timeout=timeout)
            resp = client.get(url)
            client.close()

            if resp.status_code == 200:
                return ComponentStatus(
                    name=f"url.{url[:30]}",
                    health=ComponentHealth.HEALTHY,
                    message=f"{url} is accessible",
                    uptime_seconds=time.time() - start_time,
                    metrics=[
                        HealthMetric(name="status_code", value=resp.status_code, unit=""),
                        HealthMetric(
                            name="response_time",
                            value=round(resp.elapsed.total_seconds() * 1000, 1),
                            unit="ms",
                        ),
                    ],
                )
            else:
                return ComponentStatus(
                    name=f"url.{url[:30]}",
                    health=ComponentHealth.DEGRADED,
                    message=f"{url} returned {resp.status_code}",
                )
        except Exception as e:
            return ComponentStatus(
                name=f"url.{url[:30]}", health=ComponentHealth.UNHEALTHY, error=str(e)
            )

    return check


def create_callback_check(
    name: str,
    callback: Callable[[], bool],
    healthy_message: str = "OK",
    unhealthy_message: str = "Failed",
) -> Callable[[], ComponentStatus]:
    """Create a health check from a simple callback."""
    start_time = time.time()

    def check() -> ComponentStatus:
        try:
            result = callback()
            health = ComponentHealth.HEALTHY if result else ComponentHealth.UNHEALTHY
            message = healthy_message if result else unhealthy_message

            return ComponentStatus(
                name=name, health=health, message=message, uptime_seconds=time.time() - start_time
            )
        except Exception as e:
            return ComponentStatus(name=name, health=ComponentHealth.UNHEALTHY, error=str(e))

    return check


def create_system_check() -> Callable[[], ComponentStatus]:
    """Create a health check for system resources."""
    start_time = time.time()

    def check() -> ComponentStatus:
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            health = ComponentHealth.HEALTHY
            message = "System resources OK"

            if cpu > 90:
                health = ComponentHealth.DEGRADED
                message = f"CPU high: {cpu}%"
            elif memory.percent > 90:
                health = ComponentHealth.DEGRADED
                message = f"Memory high: {memory.percent}%"
            elif disk.percent > 90:
                health = ComponentHealth.DEGRADED
                message = f"Disk high: {disk.percent}%"

            return ComponentStatus(
                name="system",
                health=health,
                message=message,
                uptime_seconds=time.time() - start_time,
                metrics=[
                    HealthMetric(
                        name="cpu", value=cpu, unit="%", threshold_warning=80, threshold_critical=90
                    ),
                    HealthMetric(
                        name="memory",
                        value=memory.percent,
                        unit="%",
                        threshold_warning=80,
                        threshold_critical=90,
                    ),
                    HealthMetric(
                        name="disk",
                        value=disk.percent,
                        unit="%",
                        threshold_warning=80,
                        threshold_critical=90,
                    ),
                ],
            )
        except Exception as e:
            return ComponentStatus(name="system", health=ComponentHealth.UNHEALTHY, error=str(e))

    return check


def create_gpu_check() -> Callable[[], ComponentStatus]:
    """Create a health check for GPU."""
    start_time = time.time()

    def check() -> ComponentStatus:
        try:
            import subprocess

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

            if result.returncode == 0:
                parts = result.stdout.strip().split(", ")
                vram_used = int(parts[0])
                vram_total = int(parts[1])
                gpu_util = int(parts[2])
                gpu_temp = int(parts[3])

                vram_percent = round(vram_used / vram_total * 100, 1)

                health = ComponentHealth.HEALTHY
                message = f"GPU OK ({vram_percent}% VRAM, {gpu_temp}C)"

                if gpu_temp > 80:
                    health = ComponentHealth.DEGRADED
                    message = f"GPU hot: {gpu_temp}C"
                elif vram_percent > 90:
                    health = ComponentHealth.DEGRADED
                    message = f"VRAM high: {vram_percent}%"

                return ComponentStatus(
                    name="gpu",
                    health=health,
                    message=message,
                    uptime_seconds=time.time() - start_time,
                    metrics=[
                        HealthMetric(name="vram_used", value=vram_used, unit="MB"),
                        HealthMetric(name="vram_total", value=vram_total, unit="MB"),
                        HealthMetric(name="vram_percent", value=vram_percent, unit="%"),
                        HealthMetric(name="gpu_util", value=gpu_util, unit="%"),
                        HealthMetric(name="gpu_temp", value=gpu_temp, unit="C"),
                    ],
                )
            else:
                return ComponentStatus(
                    name="gpu", health=ComponentHealth.UNKNOWN, message="nvidia-smi not available"
                )
        except Exception as e:
            return ComponentStatus(name="gpu", health=ComponentHealth.UNKNOWN, error=str(e))

    return check
