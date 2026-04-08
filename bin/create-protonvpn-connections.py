#!/usr/bin/env python3
"""
ProtonVPN Connection Creator — Creates nmcli connections for all free countries.

This script uses the ProtonVPN API to get the best server per country,
then creates NetworkManager connections for each one.

Usage: python3 bin/create-protonvpn-connections.py
"""

import sys
import os
import json
import subprocess
import time
import asyncio
from typing import List, Dict, Optional, Tuple

sys.path.insert(0, "/usr/lib/python3.14/site-packages")

from proton.vpn.core.api import ProtonVPNAPI
from proton.vpn.core.session_holder import ClientTypeMetadata
from proton.vpn.core.connection import VPNConnector
from proton.vpn.session.servers import TierEnum


def run_cmd(cmd: List[str], timeout: int = 30) -> Tuple[bool, str, str]:
    """Run command and return (success, stdout, stderr)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return False, "", str(e)


async def get_api_and_servers():
    """Get ProtonVPN API and server list."""
    client_type = ClientTypeMetadata(type="cli")
    api = ProtonVPNAPI(client_type)

    # Load settings
    await api.load_settings()

    # Wait for server list
    for i in range(30):
        try:
            server_list = api.refresher.server_list
            if server_list and hasattr(server_list, "_logicals") and server_list._logicals:
                return api, server_list
        except Exception:
            pass
        await asyncio.sleep(1)

    return None, None


def get_best_server_per_country(server_list) -> Dict[str, dict]:
    """Get the best (lowest load) free server for each country."""
    free_servers = [s for s in server_list._logicals if s.tier == 0]

    by_country = {}
    for server in free_servers:
        country = server.exit_country
        if country not in by_country:
            by_country[country] = []
        by_country[country].append(server)

    best = {}
    for country, servers in by_country.items():
        sorted_servers = sorted(servers, key=lambda s: s.load)
        best[country] = {
            "name": sorted_servers[0].name,
            "load": sorted_servers[0].load,
            "total_servers": len(servers),
            "server": sorted_servers[0],
        }

    return best


def list_existing_connections() -> List[str]:
    """List existing ProtonVPN connections."""
    success, output, _ = run_cmd(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"])
    if not success:
        return []

    connections = []
    for line in output.split("\n"):
        if "vpn" in line.lower() and "ProtonVPN" in line:
            name = line.split(":")[0]
            connections.append(name)

    return connections


def get_active_connection() -> Optional[str]:
    """Get currently active VPN connection."""
    success, output, _ = run_cmd(
        ["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show", "--active"]
    )
    if not success:
        return None

    for line in output.split("\n"):
        if "vpn" in line.lower() and "ProtonVPN" in line:
            return line.split(":")[0]
    return None


def connect_via_protonvpn_cli(server_name: str) -> bool:
    """Connect to a server using protonvpn CLI (creates nmcli connection)."""
    # The protonvpn CLI creates nmcli connections automatically
    cmd = ["protonvpn", "connect", server_name, "-f"]
    print(f"  Running: {' '.join(cmd)}")

    success, output, error = run_cmd(cmd, timeout=60)
    if success:
        print(f"  ✓ Connected to {server_name}")
        return True
    else:
        print(f"  ✗ Failed: {error[:100]}")
        return False


def disconnect_current() -> bool:
    """Disconnect current VPN connection."""
    active = get_active_connection()
    if active:
        print(f"  Disconnecting from {active}...")
        success, _, _ = run_cmd(["nmcli", "connection", "down", active], timeout=15)
        time.sleep(2)
        return success
    return True


def main():
    print("=== ProtonVPN Connection Creator ===\n")

    # Get API and servers
    print("Fetching server list from ProtonVPN...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        api, server_list = loop.run_until_complete(get_api_and_servers())
    finally:
        loop.close()

    if not api or not server_list:
        print("✗ Failed to fetch server list. Make sure you're logged in to ProtonVPN.")
        return

    # Get best server per country
    best_servers = get_best_server_per_country(server_list)
    print(f"Found {len(best_servers)} countries with free servers:\n")

    for country, info in sorted(best_servers.items()):
        print(
            f"  {country}: {info['name']} (load: {info['load']}%, {info['total_servers']} servers)"
        )

    # Check existing connections
    existing = list_existing_connections()
    print(f"\nExisting connections: {len(existing)}")
    for conn in existing:
        print(f"  {conn}")

    # Determine which countries need connections
    countries_with_connections = set()
    for conn in existing:
        for country in best_servers.keys():
            if country in conn.upper():
                countries_with_connections.add(country)

    missing_countries = set(best_servers.keys()) - countries_with_connections
    print(f"\nCountries with connections: {countries_with_connections}")
    print(f"Missing countries: {missing_countries}")

    if not missing_countries:
        print("\n✓ All countries have connections! No action needed.")
        return

    # Create connections for missing countries
    print(f"\nCreating connections for {len(missing_countries)} countries...")

    for country in sorted(missing_countries):
        server_name = best_servers[country]["name"]
        print(f"\nConnecting to {country} ({server_name})...")

        # Disconnect current
        disconnect_current()

        # Connect to server (this creates the nmcli connection)
        success = connect_via_protonvpn_cli(server_name)

        if success:
            # Wait a moment for connection to stabilize
            time.sleep(3)

            # Verify connection was created
            new_connections = list_existing_connections()
            if any(country in conn.upper() for conn in new_connections):
                print(f"  ✓ Connection created for {country}")
            else:
                print(f"  ⚠ Connection may not have been created")
        else:
            print(f"  ✗ Failed to connect to {country}")

    # Final status
    print("\n=== Final Status ===")
    final_connections = list_existing_connections()
    print(f"Total connections: {len(final_connections)}")
    for conn in final_connections:
        active_marker = " <-- ACTIVE" if conn == get_active_connection() else ""
        print(f"  {conn}{active_marker}")

    print("\nTo use VPN rotation:")
    print("  python3 packages/infrastructure/proxy/vpn_manager.py rotate")
    print("  python3 packages/infrastructure/proxy/vpn_manager.py status")


if __name__ == "__main__":
    main()
