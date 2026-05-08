#!/usr/bin/env python3
"""CLI tool for worker pool management.

Usage:
    python bin/worker-cli.py status
    python bin/worker-cli.py start [--pool-size hephaestus:3,explore:2]
    python bin/worker-cli.py stop [--graceful]
    python bin/worker-cli.py submit --agent-type hephaestus --payload '{"key": "value"}'
    python bin/worker-cli.py health
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from packages.orchestration.agents.pool import WorkerPool, DEFAULT_POOL_SIZES
from packages.orchestration.agents.worker import WorkerTask


def cmd_status(pool: WorkerPool) -> None:
    """Show current pool status."""
    status = pool.get_pool_status()
    print(json.dumps(status.to_dict(), indent=2))


def cmd_start(pool: WorkerPool, args: argparse.Namespace) -> None:
    """Start the worker pool."""
    pool_sizes = dict(DEFAULT_POOL_SIZES)
    if args.pool_size:
        for pair in args.pool_size.split(","):
            if ":" in pair:
                agent_type, count = pair.split(":", 1)
                pool_sizes[agent_type.strip()] = int(count.strip())

    pool._pool_sizes = pool_sizes
    pool.start_pool()
    print(f"Pool started with {pool.worker_count} workers")
    print(json.dumps(pool.get_pool_status().to_dict(), indent=2))


def cmd_stop(pool: WorkerPool, args: argparse.Namespace) -> None:
    """Stop the worker pool."""
    graceful = not getattr(args, "force", False)
    pool.shutdown(graceful=graceful)
    print(f"Pool stopped (graceful={graceful})")


def cmd_submit(pool: WorkerPool, args: argparse.Namespace) -> None:
    """Submit a task to the pool."""
    if not pool.is_running:
        print("Error: Pool is not running. Start the pool first.", file=sys.stderr)
        sys.exit(1)

    payload = {}
    if args.payload:
        try:
            payload = json.loads(args.payload)
        except json.JSONDecodeError:
            payload = {"raw": args.payload}

    task = WorkerTask(
        id=args.task_id or None,
        agent_type=args.agent_type,
        payload=payload,
        priority=args.priority or "normal",
        timeout_seconds=args.timeout or 300.0,
        max_retries=args.max_retries or 3,
    )

    task_id = pool.submit_task(
        task, agent_type=args.agent_type, priority=args.priority or "normal"
    )
    print(f"Task submitted: {task_id}")


def cmd_health(pool: WorkerPool) -> None:
    """Show worker health status."""
    health = pool.get_worker_health()
    print(json.dumps(health, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Worker Pool Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("status", help="Show pool status")

    start_parser = subparsers.add_parser("start", help="Start the worker pool")
    start_parser.add_argument(
        "--pool-size",
        type=str,
        help="Comma-separated agent:count pairs (e.g., hephaestus:3,explore:2)",
    )

    stop_parser = subparsers.add_parser("stop", help="Stop the worker pool")
    stop_parser.add_argument(
        "--force", action="store_true", help="Force stop (non-graceful)"
    )

    submit_parser = subparsers.add_parser("submit", help="Submit a task")
    submit_parser.add_argument("--agent-type", required=True, help="Target agent type")
    submit_parser.add_argument("--payload", type=str, help="Task payload (JSON string)")
    submit_parser.add_argument("--task-id", type=str, help="Optional task ID")
    submit_parser.add_argument(
        "--priority", type=str, choices=["high", "normal", "low"], default="normal"
    )
    submit_parser.add_argument(
        "--timeout", type=float, default=300.0, help="Task timeout in seconds"
    )
    submit_parser.add_argument("--max-retries", type=int, default=3, help="Max retries")

    subparsers.add_parser("health", help="Show worker health")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    pool = WorkerPool()

    if args.command == "status":
        cmd_status(pool)
    elif args.command == "start":
        cmd_start(pool, args)
    elif args.command == "stop":
        cmd_stop(pool, args)
    elif args.command == "submit":
        cmd_submit(pool, args)
    elif args.command == "health":
        cmd_health(pool)


if __name__ == "__main__":
    main()
