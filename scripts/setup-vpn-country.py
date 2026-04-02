#!/usr/bin/env python3
"""
Setup ProtonVPN connections for all free tier countries.
Uses NetworkManager to create VPN connections.
"""
import os
import sys
import subprocess
import json
import shutil

PROTONVPN_FREE_SERVERS = {
    "nl": {
        "name": "Netherlands",
        "servers": ["nl-115.protonvpn.com", "nl-245.protonvpn.com"],
        "ports": [80, 443, 4569, 1194, 5060]
    },
    "jp": {
        "name": "Japan",
        "servers": ["jp-105.protonvpn.com", "jp-179.protonvpn.com"],
        "ports": [80, 443, 4569, 1194, 5060]
    },
    "us": {
        "name": "United States",
        "servers": ["us-109.protonvpn.com", "us-169.protonvpn.com"],
        "ports": [80, 443, 4569, 1194, 5060]
    },
    "ca": {
        "name": "Canada", 
        "servers": ["ca-103.protonvpn.com", "ca-131.protonvpn.com"],
        "ports": [80, 443, 4569, 1194, 5060]
    },
    "pl": {
        "name": "Poland",
        "servers": ["pl-107.protonvpn.com", "pl-113.protonvpn.com"],
        "ports": [80, 443, 4569, 1194, 5060]
    },
    "ro": {
        "name": "Romania",
        "servers": ["ro-105.protonvpn.com", "ro-108.protonvpn.com"],
        "ports": [80, 443, 4569, 1194, 5060]
    },
    "no": {
        "name": "Norway",
        "servers": ["no-108.protonvpn.com", "no-111.protonvpn.com"],
        "ports": [80, 443, 4569, 1194, 5060]
    },
    "se": {
        "name": "Sweden",
        "servers": ["se-106.protonvpn.com", "se-124.protonvpn.com"],
        "ports": [80, 443, 4569, 1194, 5060]
    }
}


def get_cert_dir():
    """Get the certificates directory"""
    return os.path.expanduser("~/.local/share/networkmanagement/certificates/nm-openvpn")


def list_existing_certs():
    """List existing certificate files"""
    cert_dir = get_cert_dir()
    if not os.path.exists(cert_dir):
        return []
    return [f for f in os.listdir(cert_dir) if f.endswith('.pem')]


def run_nmcli(*args):
    """Run nmcli command"""
    cmd = ["nmcli"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result


def create_vpn_connection(country_code: str, server: str, use_tcp: bool = True):
    """Create a VPN connection using nmcli"""
    connection_name = f"ProtonVPN {country_code.upper()}-FREE"
    
    existing = run_nmcli("-t", "-f", "NAME", "connection", "show")
    for line in existing.stdout.strip().split('\n'):
        if connection_name in line:
            print(f"Connection '{connection_name}' already exists")
            return True
    
    cert_files = list_existing_certs()
    if not cert_files:
        print("No certificates found. Please connect to ProtonVPN first using the GUI or CLI.")
        return False
    
    ca_cert = os.path.join(get_cert_dir(), cert_files[0].rsplit('-', 1)[0] + '-ca.pem')
    
    result = run_nmcli(
        "connection", "add", "type", "vpn",
        "con-name", connection_name,
        "vpn-type", "openvpn",
        "vpn.service-type", "org.freedesktop.NetworkManager.openvpn",
        "vpn.data", f"ca = {ca_cert}, dev = tun, proto-tcp = {use_tcp}, remote = {server}, connection-type = tls"
    )
    
    if result.returncode == 0:
        print(f"Created connection: {connection_name}")
        return True
    else:
        print(f"Failed to create connection: {result.stderr}")
        return False


def main():
    print("ProtonVPN Free Tier Connection Setup")
    print("=" * 40)
    
    existing_conns = run_nmcli("-t", "-f", "NAME,TYPE", "connection", "show")
    proton_conns = [line.split(':')[0] for line in existing_conns.stdout.strip().split('\n') 
                   if 'protonvpn' in line.lower() and 'vpn' in line.lower()]
    
    print(f"Existing ProtonVPN connections: {len(proton_conns)}")
    for conn in proton_conns:
        print(f"  - {conn}")
    
    print("\nAvailable countries:")
    for code, info in PROTONVPN_FREE_SERVERS.items():
        print(f"  {code.upper()}: {info['name']}")
    
    print("\nDone - use nmcli connection up/down to switch countries")
    print("Or use vpn-rotator.py rotate command")


if __name__ == "__main__":
    main()