"""
N-Xyme Mind Master Entry Point
Starts all services and verifies they are running.
"""

import os
import sys
import time
import json
import socket
import subprocess
import signal
import argparse
from pathlib import Path
from typing import Dict, List, Optional

# Import centralized configuration
try:
    from jarvis.config.graphiti_config import JARVIS_API_URL, GRAPHITI_URL, NEO4J_URL
except ImportError:
    JARVIS_API_URL = os.getenv("JARVIS_API_URL", "http://localhost:8088")
    GRAPHITI_URL = os.getenv("GRAPHITI_URL", "http://localhost:8001")
    NEO4J_URL = os.getenv("NEO4J_URL", "http://localhost:7474")

# Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Service definitions
SERVICES = [
    {
        "name": "Neo4j",
        "port": 7474,
        "health_path": "/",
        "start_cmd": None,  # Neo4j runs as Windows service
        "check_type": "http",
        "timeout": 30,
    },
    {
        "name": "Ollama",
        "port": 11434,
        "health_path": "/api/tags",
        "start_cmd": None,  # Ollama runs as Windows service
        "check_type": "http",
        "timeout": 30,
    },
    {
        "name": "Graphiti MCP",
        "port": 8001,
        "health_path": "/health",
        "start_cmd": ["node", "packages/graphiti-memory/src/index.js"],
        "env": {"NEO4J_PASSWORD": os.getenv("NEO4J_PASSWORD", "")},
        "check_type": "http",
        "timeout": 30,
    },
    {
        "name": "FastAPI",
        "port": 8088,
        "health_path": "/health",
        "start_cmd": ["python", "-m", "jarvis.api.server"],
        "check_type": "http",
        "timeout": 30,
    },
]

# Global process tracking
processes: Dict[str, subprocess.Popen] = {}


def check_port_open(port: int, host: str = "localhost") -> bool:
    """Check if a port is open."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            return result == 0
    except OSError:
        return False


def check_http_health(port: int, path: str = "/health", timeout: int = 5) -> bool:
    """Check HTTP health endpoint."""
    import http.client

    try:
        conn = http.client.HTTPConnection("localhost", port, timeout=timeout)
        conn.request("GET", path)
        response = conn.getresponse()
        conn.close()
        return response.status < 500
    except (OSError, http.client.HTTPException):
        return False


def check_service(service: dict) -> bool:
    """Check if a service is healthy."""
    port = service["port"]

    if service["check_type"] == "http":
        return check_http_health(port, service.get("health_path", "/health"))
    else:
        return check_port_open(port)


def start_service(service: dict) -> Optional[subprocess.Popen]:
    """Start a service process."""
    if service["start_cmd"] is None:
        return None  # Service is system-managed

    cmd = service["start_cmd"]
    env = os.environ.copy()
    if "env" in service:
        env.update(service["env"])

    try:
        proc = subprocess.Popen(
            cmd,
            env=env,
            cwd=str(Path(__file__).parent.parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
        )
        return proc
    except Exception as e:
        print(f"{RED}Failed to start {service['name']}: {e}{RESET}")
        return None


def wait_for_service(service: dict, timeout: int = 30) -> bool:
    """Wait for a service to become healthy."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if check_service(service):
            return True
        time.sleep(1)
    return False


def stop_all_services():
    """Stop all managed services."""
    print(f"\n{YELLOW}Stopping services...{RESET}")
    for name, proc in processes.items():
        if proc and proc.poll() is None:
            try:
                if sys.platform == "win32":
                    proc.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    proc.terminate()
                proc.wait(timeout=5)
                print(f"{GREEN}✓ Stopped {name}{RESET}")
            except Exception as e:
                print(f"{RED}Failed to stop {name}: {e}{RESET}")


def check_status_only():
    """Check status only without starting services."""
    print(f"\n{BOLD}{CYAN}=== N-Xyme Mind Status ==={RESET}\n")

    results = []

    for service in SERVICES:
        name = service["name"]
        print(f"{BOLD}Checking {name}...{RESET}", end=" ", flush=True)

        if check_service(service):
            print(f"{GREEN}[OK] Running{RESET}")
            results.append((name, True, "Running"))
        elif service["start_cmd"] is None:
            print(f"{YELLOW}[!] Not running (system service){RESET}")
            results.append((name, False, "System service not running"))
        else:
            print(f"{RED}[FAIL] Not running{RESET}")
            results.append((name, False, "Not running"))

    print(f"\n{BOLD}{CYAN}=== Status Summary ==={RESET}\n")

    for name, ok, status in results:
        symbol = f"{GREEN}[OK]" if ok else f"{RED}[FAIL]"
        print(f"  {symbol} {name}: {status}{RESET}")

    return all(ok for _, ok, _ in results)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="N-Xyme Mind Master")
    parser.add_argument("--status", action="store_true", help="Check status only")
    args = parser.parse_args()

    if args.status:
        check_status_only()
        return

    print(f"\n{BOLD}{CYAN}=== N-Xyme Mind Startup ==={RESET}\n")

    results = []

    for service in SERVICES:
        name = service["name"]
        print(f"{BOLD}Checking {name}...{RESET}", end=" ", flush=True)

        # Check if already running
        if check_service(service):
            print(f"{GREEN}[OK] Running{RESET}")
            results.append((name, True, "Already running"))
            continue

        # Try to start
        if service["start_cmd"] is None:
            print(f"{YELLOW}[!] Not running (system service - manual start required){RESET}")
            results.append((name, False, "System service not running"))
            continue

        print(f"{YELLOW}Starting...{RESET}", end=" ", flush=True)
        proc = start_service(service)

        if proc:
            processes[name] = proc

            if wait_for_service(service, service.get("timeout", 30)):
                print(f"{GREEN}[OK] Started{RESET}")
                results.append((name, True, "Started"))
            else:
                print(f"{RED}[FAIL] Failed to start{RESET}")
                results.append((name, False, "Failed to start"))
        else:
            print(f"{RED}[FAIL] Failed to start{RESET}")
            results.append((name, False, "Failed to start"))

    # Print summary
    print(f"\n{BOLD}{CYAN}=== Status Summary ==={RESET}\n")

    all_ok = True
    for name, ok, status in results:
        symbol = f"{GREEN}[OK]" if ok else f"{RED}[FAIL]"
        print(f"  {symbol} {name}: {status}{RESET}")
        if not ok:
            all_ok = False

    print()

    if all_ok:
        print(f"{GREEN}{BOLD}All services are running!{RESET}")
        print(f"\n{CYAN}Next steps:{RESET}")
        print(f"  - Phone app: {JARVIS_API_URL}")
        print(f"  - Graphiti memory: {GRAPHITI_URL}")
        print(f"  - Neo4j browser: {NEO4J_URL}")
        print(f"  - Start hub: python scripts/nxyme-hub.py")
    else:
        print(f"{YELLOW}{BOLD}Some services failed to start.{RESET}")
        print(f"\n{CYAN}Troubleshooting:{RESET}")
        print(f"  - Check if Neo4j and Ollama Windows services are running")
        print(f"  - Check logs in the respective service directories")

    print(f"\n{CYAN}Press Ctrl+C to stop all services.{RESET}\n")

    # Keep running and handle shutdown
    try:
        while True:
            time.sleep(1)
            # Check if any process died
            for name, proc in list(processes.items()):
                if proc and proc.poll() is not None:
                    print(f"{RED}{name} process died (exit code: {proc.returncode}){RESET}")
                    del processes[name]
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Shutdown requested...{RESET}")
    finally:
        stop_all_services()
        print(f"{GREEN}All services stopped.{RESET}")


if __name__ == "__main__":
    main()
