#!/usr/bin/env python3
"""CLI tool to check model health and fallback status."""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from packages.orchestration.models.fallback import ModelFallbackManager, CircuitState


def load_omo_config():
    config_path = os.path.join(os.path.dirname(__file__), "..", "oh-my-opencode.json")
    if not os.path.exists(config_path):
        return {}
    with open(config_path) as f:
        return json.load(f)


def register_routes_from_config(manager, config):
    agents = config.get("agents", {})
    for agent_name, agent_config in agents.items():
        primary = agent_config.get("model")
        fallbacks = agent_config.get("fallback_models", [])
        if primary:
            manager.register_route(agent_name, primary, fallbacks)

    categories = config.get("categories", {})
    for cat_name, cat_config in categories.items():
        primary = cat_config.get("model")
        if primary:
            manager.register_route(f"category:{cat_name}", primary)


def cmd_status(manager, args):
    summary = manager.get_summary()
    print(json.dumps(summary, indent=2))


def cmd_health(manager, args):
    health = manager.get_all_health()
    if not health:
        print("No models tracked.")
        return

    print(
        f"{'Model':<40} {'State':<12} {'Failures':<10} {'Success Rate':<15} {'Available'}"
    )
    print("-" * 90)
    for model, h in sorted(health.items()):
        state_icon = {
            "closed": "✅",
            "open": "🔴",
            "half_open": "🟡",
        }.get(h["state"], "?")
        avail = "Yes" if h["is_available"] else "No"
        print(
            f"{model:<40} {h['state']:<12} {h['consecutive_failures']:<10} "
            f"{h['success_rate']:<15.2%} {avail} {state_icon}"
        )


def cmd_routes(manager, args):
    routes = manager.get_routes()
    if not routes:
        print("No routes registered.")
        return

    print(f"{'Route':<30} {'Primary':<35} {'Fallbacks'}")
    print("-" * 90)
    for name, route in sorted(routes.items()):
        fallbacks = ", ".join(route["fallbacks"]) if route["fallbacks"] else "(none)"
        print(f"{name:<30} {route['primary']:<35} {fallbacks}")


def cmd_test(manager, args):
    model = args.model
    failures = args.failures or 3

    print(f"Simulating {failures} failures for '{model}'...")
    for i in range(failures):
        manager.record_failure(model)
        health = manager.get_health(model)
        print(
            f"  Failure {i + 1}: state={health.state.value}, consecutive={health.consecutive_failures}"
        )

    health = manager.get_health(model)
    print(f"\nAfter {failures} failures:")
    print(f"  State: {health.state.value}")
    print(f"  Available: {health.is_available}")

    if not health.is_available:
        print("\n  Circuit is OPEN — testing recovery timeout...")
        print(f"  Recovery timeout: {manager.recovery_timeout}s")
        print("  (In production, circuit transitions to HALF_OPEN after timeout)")


def cmd_reset(manager, args):
    if args.model:
        manager.reset_model(args.model)
        print(f"Reset circuit breaker for '{args.model}'")
    else:
        manager.reset_all()
        print("Reset all circuit breakers")


def cmd_resolve(manager, args):
    name = args.name
    model = manager.get_model(name)
    if model:
        print(f"Resolved '{name}' -> {model}")
    else:
        print(f"No available model for '{name}'")
        route = manager.get_routes().get(name)
        if route:
            print(f"  Chain: {' -> '.join(route['chain'])}")


def main():
    parser = argparse.ArgumentParser(
        description="Check model health and fallback status"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    subparsers.add_parser("status", help="Show full system status (JSON)")

    subparsers.add_parser("health", help="Show health table for all models")

    subparsers.add_parser("routes", help="Show registered fallback routes")

    test_parser = subparsers.add_parser("test", help="Simulate circuit breaker")
    test_parser.add_argument("model", help="Model name to test")
    test_parser.add_argument(
        "--failures", type=int, default=3, help="Number of failures to simulate"
    )

    reset_parser = subparsers.add_parser("reset", help="Reset circuit breakers")
    reset_parser.add_argument("--model", help="Reset specific model (default: all)")

    resolve_parser = subparsers.add_parser("resolve", help="Resolve model for a route")
    resolve_parser.add_argument("name", help="Route name (e.g., sisyphus)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    config = load_omo_config()
    manager = ModelFallbackManager()
    register_routes_from_config(manager, config)

    commands = {
        "status": cmd_status,
        "health": cmd_health,
        "routes": cmd_routes,
        "test": cmd_test,
        "reset": cmd_reset,
        "resolve": cmd_resolve,
    }

    commands[args.command](manager, args)


if __name__ == "__main__":
    main()
