#!/usr/bin/env python3
"""
VPN Rotator for ProtonVPN Free Tier
Uses nmcli for reliable VPN management (protonvpn CLI times out on free tier)
Based on acastellana/vpn-rotate-skill, adapted for nmcli
"""

import json
import os
import subprocess
import time
from pathlib import Path

CONFIG_DIR = Path(__file__).parent.parent.parent / "configs" / "vpn"
COUNTRY_MAPPINGS = CONFIG_DIR / "country_mappings.json"


class VPNRotator:
    def __init__(self):
        self.config = self._load_config()
        self.rotation_count = 0

    def _load_config(self) -> dict:
        with open(COUNTRY_MAPPINGS) as f:
            return json.load(f)

    def _run_cmd(self, cmd: list[str], timeout: int = 30) -> tuple[bool, str]:
        """Run command, return (success, output)"""
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
            return result.returncode == 0, result.stdout.strip()
        except subprocess.TimeoutExpired:
            return False, "timeout"
        except Exception as e:
            return False, str(e)

    def status(self) -> dict:
        """Get current VPN status"""
        success, output = self._run_cmd(["nmcli", "-t", "-f", "NAME,DEVICE,STATE", "con", "show", "--active"])
        if not success:
            return {"connected": False, "error": output}

        for line in output.split("\n"):
            if "tun" in line.lower() or "vpn" in line.lower():
                parts = line.split(":")
                if len(parts) >= 3:
                    return {
                        "connected": True,
                        "connection": parts[0],
                        "device": parts[1],
                        "state": parts[2],
                    }
        return {"connected": False}

    def check_ip(self) -> str:
        """Get current external IP"""
        success, ip = self._run_cmd(["curl", "-s", "--max-time", "5", "ifconfig.me"])
        return ip if success else "unknown"

    def _get_connections(self) -> list[dict]:
        """List all nmcli VPN connections"""
        success, output = self._run_cmd(["nmcli", "-t", "-f", "NAME,UUID,TYPE", "con", "show"])
        if not success:
            return []
        connections = []
        for line in output.split("\n"):
            parts = line.split(":")
            if len(parts) >= 3 and parts[2] == "vpn":
                connections.append({"name": parts[0], "uuid": parts[1]})
        return connections

    def disconnect(self) -> bool:
        """Disconnect all VPN connections"""
        status = self.status()
        if not status["connected"]:
            return True

        connection = status["connection"]
        success, _ = self._run_cmd(["nmcli", "con", "down", connection])
        if success:
            time.sleep(2)
        return success

    def connect(self, country: str = None) -> dict:
        """
        Connect to VPN. If country specified, try that country.
        Otherwise rotate through available connections.
        """
        self.disconnect()
        time.sleep(1)

        connections = self._get_connections()
        if not connections:
            return {"success": False, "error": "No VPN connections configured"}

        # Pick connection
        if country:
            country = country.upper()
            matching = [c for c in connections if country in c["name"].upper()]
            if matching:
                conn = matching[0]
            else:
                # Try existing connection
                conn = connections[0] if connections else None
                if not conn:
                    return {"success": False, "error": f"No connection for {country}"}
        else:
            # Rotate
            idx = self.rotation_count % len(connections)
            conn = connections[idx]
            self.rotation_count += 1

        # Connect
        old_ip = self.check_ip()
        success, output = self._run_cmd(["nmcli", "con", "up", conn["name"]], timeout=30)

        if not success:
            return {"success": False, "error": output, "connection": conn["name"]}

        time.sleep(3)
        new_ip = self.check_ip()

        return {
            "success": True,
            "connection": conn["name"],
            "old_ip": old_ip,
            "new_ip": new_ip,
            "ip_changed": old_ip != new_ip,
        }

    def rotate(self) -> dict:
        """Rotate to next VPN connection"""
        return self.connect()


if __name__ == "__main__":
    import sys

    rotator = VPNRotator()
    print(f"Current IP: {rotator.check_ip()}")
    print(f"Status: {rotator.status()}")

    if len(sys.argv) > 1:
        country = sys.argv[1]
        print(f"\nConnecting to {country}...")
        result = rotator.connect(country)
        print(f"Result: {result}")
    else:
        print("\nRotating...")
        result = rotator.rotate()
        print(f"Result: {result}")
