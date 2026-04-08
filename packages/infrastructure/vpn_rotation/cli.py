#!/usr/bin/env python3
"""CLI for unified VPN/IP rotation module."""

import argparse
import asyncio
import json
import sys
import time

from .manager import VPNRotationManager
from .models import ProviderConfig, ProviderType


async def cmd_status(args) -> int:
    """Show status of VPN rotation manager."""
    manager = VPNRotationManager()
    await manager.initialize()
    
    if args.json:
        print(json.dumps(manager.get_status(), indent=2))
    else:
        status = manager.get_status()
        print(f"Running: {status['running']}")
        print(f"Endpoints: {status['endpoints']['total']} total, "
              f"{status['endpoints']['healthy']} healthy")
        print(f"Requests: {status['stats']['total_requests']} total, "
              f"{status['stats']['success_rate']*100:.1f}% success")
        print(f"Router: {status['router']['states_learned']} states, "
              f"{status['router']['q_table_size']} Q-values")
        if status.get('wireproxy'):
            print(f"WireProxy: {status['wireproxy']['running']} running, "
                  f"{status['wireproxy']['total_instances']} total")
    
    await manager.stop()
    return 0


async def cmd_endpoints(args) -> int:
    """List all endpoints."""
    manager = VPNRotationManager()
    await manager.initialize()
    
    if args.json:
        print(manager.get_endpoints_json())
    else:
        print(f"{'Host':<25} {'Port':<6} {'Provider':<12} {'Country':<6} "
              f"{'Latency':<8} {'Healthy':<8} {'Capacity':<8}")
        print("-" * 85)
        for ep in manager.endpoints:
            print(f"{ep.host:<25} {ep.port:<6} {ep.provider:<12} "
                  f"{ep.country:<6} {ep.latency_ms:>6.0f}ms "
                  f"{str(ep.healthy):<8} {ep.available_capacity:.2f}")
    
    await manager.stop()
    return 0


async def cmd_get(args) -> int:
    """Get best endpoint (for scripting)."""
    manager = VPNRotationManager()
    await manager.initialize()
    
    endpoint = manager.get_endpoint()
    if not endpoint:
        print("No healthy endpoints available", file=sys.stderr)
        await manager.stop()
        return 1
    
    if args.json:
        print(json.dumps(endpoint.to_dict(), indent=2))
    else:
        print(f"{endpoint.host}:{endpoint.port}")
    
    await manager.stop()
    return 0


async def cmd_health(args) -> int:
    """Check health of all endpoints."""
    manager = VPNRotationManager()
    await manager.initialize()
    
    results = await manager.check_health()
    
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"Health check: {results['healthy']}/{results['total']} healthy")
        print()
        for r in results['results']:
            status = "✓" if r['healthy'] else "✗"
            print(f"  {status} {r['host']}:{r['port']} - "
                  f"{r['latency_ms']:.0f}ms - IP: {r['exit_ip']}")
    
    await manager.stop()
    return 0


async def cmd_wireproxy(args) -> int:
    """Manage WireProxy instances."""
    from .wireproxy import WireProxyManager
    
    manager = WireProxyManager(base_port=args.port, max_instances=args.max)
    
    if args.action == "start":
        instance = await manager.spawn_instance()
        if instance:
            print(f"Started: {instance.instance_id} on port {instance.port}")
        else:
            print("Failed to spawn instance")
            return 1
    
    elif args.action == "stop":
        await manager.stop_all()
        print("All instances stopped")
    
    elif args.action == "status":
        stats = manager.get_stats()
        print(json.dumps(stats, indent=2))
    
    elif args.action == "scale":
        instances = await manager.scale_to(args.count)
        print(f"Scaled to {len(instances)} instances")
    
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Unified VPN/IP Rotation CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    # status
    status_parser = subparsers.add_parser("status", help="Show status")
    status_parser.add_argument("--json", action="store_true", help="JSON output")
    
    # endpoints
    endpoints_parser = subparsers.add_parser("endpoints", help="List endpoints")
    endpoints_parser.add_argument("--json", action="store_true", help="JSON output")
    
    # get
    get_parser = subparsers.add_parser("get", help="Get best endpoint")
    get_parser.add_argument("--json", action="store_true", help="JSON output")
    
    # health
    health_parser = subparsers.add_parser("health", help="Check health")
    health_parser.add_argument("--json", action="store_true", help="JSON output")
    
    # wireproxy
    wp_parser = subparsers.add_parser("wireproxy", help="Manage WireProxy")
    wp_parser.add_argument("--port", type=int, default=1080, help="Base port")
    wp_parser.add_argument("--max", type=int, default=32, help="Max instances")
    wp_parser.add_argument("action", choices=["start", "stop", "status", "scale"])
    wp_parser.add_argument("count", type=int, nargs="?", help="Count for scale")
    
    args = parser.parse_args()
    
    if args.command == "status":
        return asyncio.run(cmd_status(args))
    elif args.command == "endpoints":
        return asyncio.run(cmd_endpoints(args))
    elif args.command == "get":
        return asyncio.run(cmd_get(args))
    elif args.command == "health":
        return asyncio.run(cmd_health(args))
    elif args.command == "wireproxy":
        return asyncio.run(cmd_wireproxy(args))
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
