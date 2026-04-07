#!/usr/bin/env python3
"""CLI tool for Golden Spine management.

Usage:
    spine-cli start [--config path]
    spine-cli stop
    spine-cli probe [--json]
    spine-cli run --prompt "text" [--model model_name] [--json]
    spine-cli status [--json]
    spine-cli config [--get] [--set key=value] [--json]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Optional

# Setup path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger("spine-cli")

# Import GoldenSpine lazily
GoldenSpine = None
SpineConfig = None


def _get_spine() -> Any:
    """Lazily import and return GoldenSpine class."""
    global GoldenSpine
    if GoldenSpine is None:
        from packages.infrastructure.spine.spine import GoldenSpine as GS
        GoldenSpine = GS
    return GoldenSpine


def _get_config() -> Any:
    """Lazily import and return SpineConfig class."""
    global SpineConfig
    if SpineConfig is None:
        from packages.infrastructure.spine.config import SpineConfig as SC
        SpineConfig = SC
    return SpineConfig


def _load_config_from_file(config_path: Optional[str]) -> Any:
    """Load configuration from JSON file or return default."""
    config_cls = _get_config()
    if config_path:
        path = Path(config_path)
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            return config_cls.from_dict(data)
    return config_cls()


# =============================================================================
# Command Implementations
# =============================================================================


def cmd_start(args: argparse.Namespace) -> None:
    """Start Golden Spine."""
    config = _load_config_from_file(args.config)
    spine_cls = _get_spine()
    spine = spine_cls(config=config)
    spine.start()

    if args.json:
        print(json.dumps({"status": "started", "config": config.to_dict()}))
    else:
        print(f"Golden Spine started")
        print(f"  Model: {config.model_path}")
        print(f"  Fallback: {config.fallback_models}")
        print(f"  Bind: {config.bind_host}:{config.port}")


def cmd_stop(args: argparse.Namespace) -> None:
    """Stop Golden Spine."""
    spine_cls = _get_spine()
    spine = spine_cls()
    spine.stop()

    if args.json:
        print(json.dumps({"status": "stopped"}))
    else:
        print("Golden Spine stopped (graceful shutdown)")


def cmd_probe(args: argparse.Namespace) -> None:
    """Run health check."""
    spine_cls = _get_spine()
    spine = spine_cls()
    report = spine.probe()

    result = {
        "overall_healthy": report.overall_healthy,
        "process": {
            "healthy": report.process.healthy,
            "message": report.process.message,
        },
        "model": {
            "healthy": report.model.healthy,
            "message": report.model.message,
        },
        "responsive": {
            "healthy": report.responsive.healthy,
            "message": report.responsive.message,
        },
    }

    if args.json:
        print(json.dumps(result))
    else:
        health_str = "HEALTHY" if report.overall_healthy else "UNHEALTHY"
        print(f"Health Check: {health_str}")
        print(f"  Process: {report.process.message}")
        print(f"  Model: {report.model.message}")
        print(f"  Responsive: {report.responsive.message}")


def cmd_run(args: argparse.Namespace) -> None:
    """Run inference."""
    spine_cls = _get_spine()
    spine = spine_cls()

    result = spine.run(prompt=args.prompt, model=args.model)

    if args.json:
        print(json.dumps(result.to_dict()))
    else:
        status_str = "SUCCESS" if result.success else "FAILED"
        print(f"Run: {status_str}")
        print(f"  Model: {result.model}")
        print(f"  Latency: {result.latency_ms:.0f}ms")
        print(f"  Fallback used: {result.fallback_used}")
        if result.error:
            print(f"  Error: {result.error}")


def cmd_status(args: argparse.Namespace) -> None:
    """Print current status."""
    spine_cls = _get_spine()
    spine = spine_cls()
    status = spine.status()

    if args.json:
        print(json.dumps(status, indent=2))
    else:
        running_str = "RUNNING" if status["running"] else "STOPPED"
        print(f"Status: {running_str}")
        print(f"  Run count: {status['run_count']}")

        if "health" in status:
            h = status["health"]
            health_ok = "OK" if h.get("overall_healthy") else "FAIL"
            print(f"  Health: {health_ok}")

        if "fallback_status" in status:
            fb = status["fallback_status"]
            print(f"  Fallback: {fb.get('primary_model', 'N/A')}")
            circuits = fb.get("circuit_states", {})
            print(f"    Circuits: {list(circuits.keys())}")

        if "run_stats" in status:
            rs = status["run_stats"]
            print(f"  Total runs: {rs.get('total_runs', 0)}")
            print(f"  Success rate: {rs.get('success_rate', 0):.1%}")


def cmd_config(args: argparse.Namespace) -> None:
    """Print or update configuration."""
    spine_cls = _get_spine()
    spine = spine_cls()

    # Handle --set updates
    if args.set:
        updates = {}
        for item in args.set:
            if "=" in item:
                key, value = item.split("=", 1)
                # Try to parse as int/bool/float, else keep string
                if value.lower() in ("true", "false"):
                    value = value.lower() == "true"
                elif value.isdigit():
                    value = int(value)
                elif value.replace(".", "", 1).isdigit():
                    value = float(value)
                updates[key] = value
        spine.config(**updates)

    # Get current config
    config_dict = spine._config.to_dict()

    if args.json:
        print(json.dumps(config_dict, indent=2))
    else:
        print("Configuration:")
        for key, value in config_dict.items():
            print(f"  {key}: {value}")


# =============================================================================
# Main
# =============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Golden Spine CLI - AI model serving orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON (machine readable)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # start
    start_parser = subparsers.add_parser("start", help="Start Golden Spine")
    start_parser.add_argument(
        "--config",
        type=str,
        help="Path to spine.config.json (default: use SpineConfig defaults)",
    )

    # stop
    subparsers.add_parser("stop", help="Stop Golden Spine gracefully")

    # probe
    probe_parser = subparsers.add_parser("probe", help="Run health check")

    # run
    run_parser = subparsers.add_parser("run", help="Run inference")
    run_parser.add_argument(
        "--prompt",
        type=str,
        required=True,
        help="Prompt text to send to model",
    )
    run_parser.add_argument(
        "--model",
        type=str,
        help="Model name (default: use config.model_path)",
    )

    # status
    subparsers.add_parser("status", help="Print current status")

    # config
    config_parser = subparsers.add_parser("config", help="Print or update configuration")
    config_parser.add_argument(
        "--get",
        action="store_true",
        help="Get current configuration",
    )
    config_parser.add_argument(
        "--set",
        action="append",
        metavar="key=value",
        help="Update configuration (can be repeated)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    try:
        if args.command == "start":
            cmd_start(args)
        elif args.command == "stop":
            cmd_stop(args)
        elif args.command == "probe":
            cmd_probe(args)
        elif args.command == "run":
            cmd_run(args)
        elif args.command == "status":
            cmd_status(args)
        elif args.command == "config":
            cmd_config(args)
    except Exception as e:
        logger.error(f"Command failed: {e}")
        if args.json:
            print(json.dumps({"error": str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()