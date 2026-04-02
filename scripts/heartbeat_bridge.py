"""
Heartbeat Bridge — Connects PowerShell .heartbeat/ with Python src/health_*.py

Runs Python health checks and writes results to health.json
for PowerShell to read.

Usage:
    python scripts/heartbeat_bridge.py
"""

import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from health_core import HealthMonitor, ComponentHealth, ComponentStatus
from health_checks import (
    create_process_check,
    create_port_check,
    create_url_check,
    create_system_check,
    create_gpu_check,
)
from health_ai import HealthAIDiagnostics
from health_recovery import HealthRecovery

logger = logging.getLogger(__name__)

HEARTBEAT_ROOT = Path(__file__).parent.parent / ".heartbeat"


def setup_health_monitor() -> HealthMonitor:
    """Setup health monitor with all checks."""
    monitor = HealthMonitor()

    # Core services
    monitor.register("ollama", create_url_check("http://localhost:11434/api/tags", timeout=3.0))
    monitor.register("neo4j", create_url_check("http://localhost:7474/", timeout=3.0))
    monitor.register("graphiti", create_url_check("http://localhost:8001/health", timeout=3.0))

    # MCP servers
    mcp_ports = {
        "playwright": 12010,
        "puppeteer": 12011,
        "fetch": 12012,
        "exa": 12014,
        "ollama-mcp": 11435,
        "github": 12001,
        "git": 12002,
        "sqlite": 12003,
        "context7": 12020,
        "grep-app": 12021,
        "obsidian": 12022,
        "shadcn": 12023,
        "graphiti-mcp": 8001,
    }
    for name, port in mcp_ports.items():
        monitor.register(f"mcp_{name}", create_port_check(port, name=f"mcp_{name}"))

    # System resources
    monitor.register("system", create_system_check())
    monitor.register("gpu", create_gpu_check())

    return monitor


def run_health_check() -> dict:
    """Run health check and return report."""
    monitor = setup_health_monitor()
    ai = HealthAIDiagnostics()
    recovery = HealthRecovery(monitor)
    recovery.set_ai_diagnostics(ai)

    # Run all checks
    statuses = monitor.check_all()
    overall = monitor.get_overall_health(statuses)
    system = monitor.get_system_metrics()

    # Build report
    report = {
        "status": overall.value,
        "timestamp": (time.time()),
        "checks": {},
    }

    # Add component checks
    for name, status in statuses.items():
        report["checks"][name] = {
            "status": status.health.value,
            "message": status.message,
            "error": status.error,
        }

    # Add system metrics
    report["system"] = {
        "cpu_percent": system.get("cpu_percent", 0),
        "memory_percent": system.get("memory_percent", 0),
        "memory_used_gb": system.get("memory_used_gb", 0),
        "memory_total_gb": system.get("memory_total_gb", 0),
        "disk_percent": system.get("disk_percent", 0),
    }

    # Get GPU info
    gpu_check = statuses.get("gpu")
    if gpu_check and gpu_check.metrics:
        report["gpu"] = {m.name: m.value for m in gpu_check.metrics}

    # Add MCP summary
    mcp_checks = {k: v for k, v in statuses.items() if k.startswith("mcp_")}
    report["mcp"] = {
        "total": len(mcp_checks),
        "healthy": sum(1 for s in mcp_checks.values() if s.health == ComponentHealth.HEALTHY),
    }

    return report


def save_health_report(report: dict):
    """Save report to health.json."""
    health_file = HEARTBEAT_ROOT / "health.json"
    health_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved to {health_file}")


def main():
    """Run health check and save."""
    print("=== HEARTBEAT BRIDGE ===")
    print("Running Python health checks...")

    report = run_health_check()

    status = report["status"]
    mcp = report.get("mcp", {})
    system = report.get("system", {})

    print(f"Status: {status}")
    print(f"MCP: {mcp.get('healthy', 0)}/{mcp.get('total', 0)} healthy")
    print(f"CPU: {system.get('cpu_percent', 0):.1f}%")
    print(f"RAM: {system.get('memory_percent', 0):.1f}%")

    save_health_report(report)
    print("=== DONE ===")


if __name__ == "__main__":
    main()
