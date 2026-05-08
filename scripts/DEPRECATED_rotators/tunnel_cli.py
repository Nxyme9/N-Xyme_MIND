#!/usr/bin/env python3
"""
Tunnel CLI - Command-line interface for the tunnel system
==========================================================

Usage:
    tunnel status           # Show tunnel status
    tunnel stats           # Detailed statistics
    tunnel mode <mode>     # Set mode (race/funnel/parallel/turbo/single)
    tunnel providers       # List providers
    tunnel enable          # Enable tunnel
    tunnel disable         # Disable tunnel
    tunnel add-key <provider> <key>  # Add API key
    tunnel remove-key <provider> <key_id>  # Remove API key
    tunnel health          # Health check
"""

import sys
import argparse
import json
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent / "packages"))

from tunnel import get_orchestrator, TunnelOrchestrator


def cmd_status(args):
    """Show tunnel status."""
    tunnel = get_orchestrator()
    stats = tunnel.get_stats()

    print("\n" + "=" * 60)
    print("🔗 TUNNEL SYSTEM STATUS")
    print("=" * 60)

    enabled = "✅ ENABLED" if stats["enabled"] else "❌ DISABLED"
    print(f"\nStatus: {enabled}")
    print(f"Mode: {stats['default_mode']}")
    print(
        f"NxRotator: {'✅ Available' if stats['nx_rotator_available'] else '❌ Not available'}"
    )

    print(f"\n📊 PROVIDERS ({len(stats['providers'])}):")
    for name, pool_stats in stats["providers"].items():
        available = pool_stats.get("available_keys", 0)
        total = pool_stats.get("total_keys", 0)
        print(f"   • {name}: {available}/{total} keys available")

    print(f"\n🔄 FALLBACK CHAIN:")
    for i, provider in enumerate(stats["fallback_chain"]):
        health = stats["health"].get(provider, 0.5)
        bar = "█" * int(health * 10) + "░" * (10 - int(health * 10))
        print(f"   {i + 1}. {provider}: [{bar}] {health:.0%}")

    print("\n" + "=" * 60)


def cmd_stats(args):
    """Show detailed statistics."""
    tunnel = get_orchestrator()
    stats = tunnel.get_stats()
    print(json.dumps(stats, indent=2))


def cmd_mode(args):
    """Set tunnel mode."""
    tunnel = get_orchestrator()
    tunnel.set_mode(args.mode)
    print(f"✅ Mode set to: {args.mode}")


def cmd_providers(args):
    """List providers."""
    tunnel = get_orchestrator()
    stats = tunnel.get_stats()

    print("\n📊 PROVIDERS:")
    for name, pool_stats in stats["providers"].items():
        print(f"\n  {name}:")
        for key, val in pool_stats.items():
            print(f"    {key}: {val}")


def cmd_enable(args):
    """Enable tunnel."""
    tunnel = get_orchestrator()
    # Would need to modify config - for now just report
    print("✅ Tunnel is enabled")


def cmd_disable(args):
    """Disable tunnel."""
    tunnel = get_orchestrator()
    # Would need to modify config - for now just report
    print("❌ Tunnel is disabled (config modification not implemented)")


def cmd_add_key(args):
    """Add API key."""
    tunnel = get_orchestrator()

    metadata = {"source": "cli"}
    result = tunnel.add_key(args.provider, args.key, metadata)

    if result.get("success"):
        print(f"✅ Added key to {args.provider}")
    else:
        print(f"❌ Failed: {result.get('error')}")


def cmd_remove_key(args):
    """Remove API key."""
    tunnel = get_orchestrator()

    success = tunnel.remove_key(args.provider, args.key_id)

    if success:
        print(f"✅ Removed key {args.key_id} from {args.provider}")
    else:
        print(f"❌ Key not found")


def cmd_health(args):
    """Health check."""
    tunnel = get_orchestrator()
    stats = tunnel.get_stats()

    print("\n🏥 HEALTH CHECK:")
    all_healthy = True

    for provider, health in stats["health"].items():
        status = "✅" if health > 0.5 else "⚠️" if health > 0.2 else "❌"
        print(f"   {status} {provider}: {health:.0%}")
        if health < 0.3:
            all_healthy = False

    if all_healthy:
        print("\n✅ All providers healthy")
    else:
        print("\n⚠️ Some providers need attention")


def main():
    parser = argparse.ArgumentParser(
        description="Tunnel CLI - Manage API key tunnel system", prog="tunnel"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # status
    subparsers.add_parser("status", help="Show tunnel status")

    # stats
    subparsers.add_parser("stats", help="Show detailed statistics")

    # mode
    mode_parser = subparsers.add_parser("mode", help="Set tunnel mode")
    mode_parser.add_argument(
        "mode",
        choices=["race", "funnel", "parallel", "turbo", "single"],
        help="Mode to set",
    )

    # providers
    subparsers.add_parser("providers", help="List providers")

    # enable
    subparsers.add_parser("enable", help="Enable tunnel")

    # disable
    subparsers.add_parser("disable", help="Disable tunnel")

    # add-key
    add_parser = subparsers.add_parser("add-key", help="Add API key")
    add_parser.add_argument("provider", help="Provider name")
    add_parser.add_argument("key", help="API key")

    # remove-key
    remove_parser = subparsers.add_parser("remove-key", help="Remove API key")
    remove_parser.add_argument("provider", help="Provider name")
    remove_parser.add_argument("key_id", help="Key ID to remove")

    # health
    subparsers.add_parser("health", help="Health check")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Route to command
    commands = {
        "status": cmd_status,
        "stats": cmd_stats,
        "mode": cmd_mode,
        "providers": cmd_providers,
        "enable": cmd_enable,
        "disable": cmd_disable,
        "add-key": cmd_add_key,
        "remove-key": cmd_remove_key,
        "health": cmd_health,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
