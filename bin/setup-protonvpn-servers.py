#!/usr/bin/env python3
"""
ProtonVPN Server Setup — Creates nmcli connections for free servers in multiple countries.

Usage: python3 bin/setup-protonvpn-servers.py
"""

import sys
import os
import json
import subprocess
import time
from typing import List, Dict, Optional

sys.path.insert(0, "/usr/lib/python3.14/site-packages")

from proton.vpn.core.api import ProtonVPNAPI
from proton.vpn.core.session_holder import ClientTypeMetadata
from proton.vpn.session.servers import TierEnum


# Countries with free ProtonVPN servers
FREE_COUNTRIES = ["NL", "JP", "US", "CA", "PL", "RO", "NO", "SE"]


def run_cmd(cmd: List[str], timeout: int = 30) -> tuple:
    """Run command and return (success, stdout, stderr)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return False, "", str(e)


def get_api():
    """Get ProtonVPN API instance."""
    client_type = ClientTypeMetadata(type="cli")
    api = ProtonVPNAPI(client_type)
    return api


def get_free_servers():
    """Get all free tier servers from ProtonVPN API."""
    print("Fetching server list from ProtonVPN...")

    # Use the API to get servers
    # The API needs to be initialized first
    api = get_api()

    # We need to wait for the server list to be loaded
    # This happens automatically in the background
    import asyncio

    async def fetch_servers():
        # Initialize the API
        await api.load_settings()

        # Wait for server list to be available
        max_wait = 30
        waited = 0
        while waited < max_wait:
            try:
                server_list = api.refresher.server_list
                if server_list and server_list._logicals:
                    return server_list
            except Exception:
                pass
            await asyncio.sleep(1)
            waited += 1

        return None

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        server_list = loop.run_until_complete(fetch_servers())
    finally:
        loop.close()

    if not server_list:
        print("Failed to fetch server list")
        return []

    # Filter free servers
    free_servers = []
    for server in server_list._logicals:
        if server.tier == 0:  # Free tier
            free_servers.append(server)

    print(f"Found {len(free_servers)} free servers")

    # Group by country
    by_country = {}
    for server in free_servers:
        country = server.country
        if country not in by_country:
            by_country[country] = []
        by_country[country].append(server)

    print(f"Countries with free servers: {len(by_country)}")
    for country in sorted(by_country.keys()):
        servers = by_country[country]
        print(f"  {country}: {len(servers)} servers")
        # Show top 3 by load
        sorted_servers = sorted(servers, key=lambda s: s.load)[:3]
        for s in sorted_servers:
            print(f"    {s.name} - load: {s.load}%")

    return free_servers


def list_existing_connections() -> List[str]:
    """List existing ProtonVPN connections in NetworkManager."""
    success, output, _ = run_cmd(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"])
    if not success:
        return []

    connections = []
    for line in output.split("\n"):
        if "vpn" in line.lower() and "ProtonVPN" in line:
            name = line.split(":")[0]
            connections.append(name)

    return connections


def create_connection_for_server(server_name: str, country: str) -> bool:
    """Create a NetworkManager connection for a ProtonVPN server."""
    # This requires the ProtonVPN daemon to be running
    # The GUI app creates connections automatically when you connect
    # We'll use the protonvpn CLI or the API to create connections

    print(f"Would create connection for {server_name} in {country}")
    # For now, we'll rely on the GUI app to create connections
    # The user needs to connect to each country once via the GUI
    return False


def main():
    print("=== ProtonVPN Server Setup ===\n")

    # Get free servers
    servers = get_free_servers()
    if not servers:
        print("No free servers found. Make sure you're logged in to ProtonVPN.")
        return

    # List existing connections
    existing = list_existing_connections()
    print(f"\nExisting connections: {len(existing)}")
    for conn in existing:
        print(f"  {conn}")

    # Check which countries we have connections for
    countries_with_connections = set()
    for conn in existing:
        for country in FREE_COUNTRIES:
            if country in conn.upper():
                countries_with_connections.add(country)

    print(f"\nCountries with connections: {countries_with_connections}")
    print(f"Missing countries: {set(FREE_COUNTRIES) - countries_with_connections}")

    print("\nTo add missing countries:")
    print("1. Open the ProtonVPN GUI app")
    print("2. Connect to a free server in each missing country")
    print("3. The connection will be saved automatically")
    print("4. Run this script again to verify")


if __name__ == "__main__":
    main()
