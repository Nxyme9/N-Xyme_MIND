#!/usr/bin/env python3
"""Verify exit IPs for all configured proxies."""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def verify_exit_ips():
    """Check exit IP through each proxy."""
    from packages.infrastructure.vpn_rotation import VPNRotationManager
    import packages.infrastructure.vpn_rotation.health as health_mod

    # Create manager
    manager = VPNRotationManager()

    # Add SOCKS5 proxies from backends.json
    import json

    backends_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "configs/vpn/backends.json",
    )

    with open(backends_path) as f:
        config = json.load(f)

    print("=" * 60)
    print("SOCKS5 PROXY EXIT IP VERIFICATION")
    print("=" * 60)

    results = []

    for backend in config["backends"]:
        host = backend["socks_host"]
        port = backend["socks_port"]
        name = backend["name"]
        country = backend.get("country", "unknown")

        print(f"\n[{name}] {host}:{port} ({country})")

        try:
            # Use IPDetector to check exit IP through this proxy
            detector = health_mod.IPDetector()
            exit_ip = await detector.detect_via_socks5(host, port)

            if exit_ip:
                print(f"  → Exit IP: {exit_ip}")
                results.append((name, f"{host}:{port}", exit_ip, country))
            else:
                print(f"  → FAILED to detect IP")
                results.append((name, f"{host}:{port}", "FAILED", country))

            await detector.close()
        except Exception as e:
            print(f"  → Error: {e}")
            results.append((name, f"{host}:{port}", f"ERROR: {e}", country))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    # Group by exit IP
    ip_groups = {}
    for name, proxy, exit_ip, country in results:
        if exit_ip not in ip_groups:
            ip_groups[exit_ip] = []
        ip_groups[exit_ip].append((name, proxy, country))

    print(f"\nTotal proxies: {len(results)}")
    print(f"Unique exit IPs: {len(ip_groups)}")

    for ip, proxies in ip_groups.items():
        print(f"\n  IP: {ip}")
        for name, proxy, country in proxies:
            print(f"    - {name} ({proxy}) [{country}]")

    # Now check ProtonVPN
    print("\n" + "=" * 60)
    print("PROTONVPN SERVER EXIT IP VERIFICATION")
    print("=" * 60)

    # Add ProtonVPN provider
    from packages.infrastructure.vpn_rotation.provider import (
        ProviderRegistry,
        ProviderConfig,
    )
    from packages.infrastructure.vpn_rotation.models import ProviderType

    config = ProviderConfig(name="protonvpn", provider_type=ProviderType.PROTONVPN)
    ProviderRegistry.add_provider("protonvpn", config)

    proton_provider = ProviderRegistry.get_provider("protonvpn")
    endpoints = await proton_provider.list_endpoints()

    proton_results = []
    detector = health_mod.IPDetector()

    for ep in endpoints:
        print(f"\n[{ep.country}] {ep.host}:{ep.port}")
        print(f"  → Note: ProtonVPN requires WireGuard setup")
        print(
            f"  → Without active WireGuard, IP detection returns server IP (not rotated)"
        )
        proton_results.append((ep.country, ep.host, ep.port))

    await detector.close()

    print("\n" + "=" * 60)
    print("CONCLUSION")
    print("=" * 60)

    if len(ip_groups) == 1:
        print("⚠️  ALL SOCKS5 proxies give the SAME exit IP!")
        print("    They are likely tunnels to the same upstream server.")
    elif len(ip_groups) > 1:
        print(f"✅ SOCKS5 proxies give {len(ip_groups)} DIFFERENT exit IPs!")
    else:
        print("❌ Could not detect any exit IPs from SOCKS5 proxies")


if __name__ == "__main__":
    asyncio.run(verify_exit_ips())
