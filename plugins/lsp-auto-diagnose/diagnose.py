#!/usr/bin/env python3
"""LSP Auto-Diagnose - Health check engine for LSP servers.

Monitors pyright, rust-analyzer, typescript-language-server, and
bash-language-server. Detects dead/stalled servers, auto-restarts them,
rate-limits restarts, logs to JSONL files, and sends desktop notifications.
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "lsp-diagnose"
HEALTH_LOG = DATA_DIR / "health.jsonl"
RESTART_LOG = DATA_DIR / "restarts.jsonl"

MAX_RESTARTS = 3
RESTART_WINDOW_SECONDS = 300
CPU_STALL_THRESHOLD = 90.0
CHECK_INTERVAL = 60

SERVERS = {
    "pyright": {
        "process_pattern": "pyright",
        "restart_command": ["pyright-langserver", "--stdio"],
        "language": "Python",
    },
    "rust-analyzer": {
        "process_pattern": "rust-analyzer",
        "restart_command": ["rust-analyzer"],
        "language": "Rust",
    },
    "typescript-language-server": {
        "process_pattern": "typescript-language-server",
        "restart_command": ["typescript-language-server", "--stdio"],
        "language": "TypeScript/JavaScript",
    },
    "bash-language-server": {
        "process_pattern": "bash-language-server",
        "restart_command": ["bash-language-server", "start"],
        "language": "Bash/Shell",
    },
}

restart_tracker: dict[str, list[float]] = {}


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def append_jsonl(path: Path, record: dict) -> None:
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")


def notify(title: str, message: str) -> None:
    try:
        subprocess.run(
            ["notify-send", title, message],
            capture_output=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass


def find_pids(pattern: str) -> list[int]:
    try:
        result = subprocess.run(
            ["pgrep", "-f", pattern],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return [int(pid) for pid in result.stdout.strip().split("\n")]
    except (subprocess.TimeoutExpired, ValueError):
        pass
    return []


def get_process_cpu(pid: int) -> float:
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "%cpu="],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except (subprocess.TimeoutExpired, ValueError):
        pass
    return 0.0


def check_server_health(name: str, config: dict) -> dict:
    pids = find_pids(config["process_pattern"])

    if not pids:
        return {"server": name, "status": "dead", "pids": [], "cpu": 0.0}

    max_cpu = 0.0
    for pid in pids:
        cpu = get_process_cpu(pid)
        if cpu > max_cpu:
            max_cpu = cpu

    if max_cpu >= CPU_STALL_THRESHOLD:
        return {
            "server": name,
            "status": "stalled",
            "pids": pids,
            "cpu": max_cpu,
        }

    return {"server": name, "status": "healthy", "pids": pids, "cpu": max_cpu}


def can_restart(name: str) -> bool:
    now = time.time()
    history = restart_tracker.get(name, [])
    window_start = now - RESTART_WINDOW_SECONDS
    recent = [t for t in history if t > window_start]
    restart_tracker[name] = recent
    return len(recent) < MAX_RESTARTS


def record_restart(name: str) -> None:
    now = time.time()
    if name not in restart_tracker:
        restart_tracker[name] = []
    restart_tracker[name].append(now)


def restart_server(name: str, config: dict) -> dict:
    if not can_restart(name):
        return {
            "server": name,
            "action": "skipped",
            "reason": "rate_limited",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    pids = find_pids(config["process_pattern"])
    for pid in pids:
        try:
            os.kill(pid, 9)
        except OSError:
            pass

    try:
        subprocess.Popen(
            config["restart_command"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        record_restart(name)
        result = {
            "server": name,
            "action": "restarted",
            "killed_pids": pids,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        notify(
            "LSP Restarted: " + name,
            config["language"] + " server restarted successfully",
        )
        return result
    except FileNotFoundError:
        result = {
            "server": name,
            "action": "failed",
            "reason": "binary_not_found",
            "command": config["restart_command"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        notify(
            "LSP Restart Failed: " + name,
            "Binary not found: " + config["restart_command"][0],
        )
        return result


def check_all() -> list[dict]:
    results = []
    for name, config in SERVERS.items():
        health = check_server_health(name, config)
        results.append(health)

        if health["status"] in ("dead", "stalled"):
            restart_result = restart_server(name, config)
            results.append(restart_result)

    return results


def run_diagnosis() -> list[dict]:
    ensure_data_dir()
    results = check_all()

    timestamp = datetime.now(timezone.utc).isoformat()
    for r in results:
        r["timestamp"] = r.get("timestamp", timestamp)
        if r.get("action"):
            append_jsonl(RESTART_LOG, r)
        else:
            append_jsonl(HEALTH_LOG, r)

    return results


def print_status() -> None:
    results = run_diagnosis()
    health_map = {r["server"]: r for r in results if not r.get("action")}

    print("{:<30} {:<12} {:<10} {:<8}".format("Server", "Status", "PIDs", "CPU%"))
    print("-" * 60)
    for name in SERVERS:
        h = health_map.get(name, {"status": "unknown", "pids": [], "cpu": 0.0})
        pids_str = ",".join(str(p) for p in h.get("pids", [])) or "none"
        print("{:<30} {:<12} {:<10} {:<8.1f}".format(
            name, h["status"], pids_str, h.get("cpu", 0.0)
        ))


def run_daemon() -> None:
    print("LSP Auto-Diagnose daemon started (interval={}s)".format(CHECK_INTERVAL))
    notify("LSP Monitor", "Background health check started")
    while True:
        try:
            results = run_diagnosis()
            for r in results:
                if r.get("action") == "restarted":
                    print("[{}] Restarted: {}".format(r["timestamp"], r["server"]))
                elif r.get("status") in ("dead", "stalled"):
                    print(
                        "[{}] {}: {} (CPU: {}%)".format(
                            r.get("timestamp", "?"),
                            r["server"],
                            r["status"],
                            r.get("cpu", 0),
                        )
                    )
        except KeyboardInterrupt:
            print("\nDaemon stopped.")
            notify("LSP Monitor", "Background health check stopped")
            break
        except Exception as e:
            print("Error in daemon loop: {}".format(e))
        time.sleep(CHECK_INTERVAL)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: diagnose.py <check|status|daemon>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "check":
        results = run_diagnosis()
        for r in results:
            print(json.dumps(r, indent=2))
    elif command == "status":
        print_status()
    elif command == "daemon":
        run_daemon()
    else:
        print("Unknown command: {}".format(command))
        sys.exit(1)


if __name__ == "__main__":
    main()
