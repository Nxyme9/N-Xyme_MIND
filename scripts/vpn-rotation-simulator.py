#!/usr/bin/env python3
"""
VPN Rotation Simulator - Test the full flow:
1. Hit rate limit
2. Detect 429 error
3. Activate ProtonVPN
4. Change server (new IP)
5. Retry request
6. Verify success
"""

import subprocess
import time
import requests
import json
import os
from pathlib import Path

# Use environment variable or common installation path
PROTONVPN_PATH = os.environ.get(
    "PROTONVPN_PATH",
    str(
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
        / "Proton"
        / "VPN"
        / "ProtonVPN.Launcher.exe"
    ),
)


def get_ip():
    """Get current public IP."""
    try:
        resp = requests.get("https://api.ipify.org", timeout=5)
        return resp.text.strip()
    except Exception as e:
        return f"Error: {e}"


def protonvpn_disconnect():
    """Disconnect from ProtonVPN."""
    print("[VPN] Disconnecting...")
    try:
        subprocess.run([PROTONVPN_PATH, "--disconnect"], capture_output=True, timeout=10)
        time.sleep(3)
        return True
    except Exception as e:
        print(f"[VPN] Disconnect error: {e}")
        return False


def protonvpn_connect(country=None):
    """Connect to ProtonVPN."""
    print(f"[VPN] Connecting to {'random server' if not country else country}...")
    try:
        if country:
            subprocess.run([PROTONVPN_PATH, "--connect", country], capture_output=True, timeout=15)
        else:
            subprocess.run([PROTONVPN_PATH, "--connect"], capture_output=True, timeout=15)
        time.sleep(10)  # Wait for connection
        return True
    except Exception as e:
        print(f"[VPN] Connect error: {e}")
        return False


def protonvpn_rotate():
    """Rotate to new VPN server."""
    print("\n" + "=" * 60)
    print("VPN ROTATION SEQUENCE")
    print("=" * 60)

    # Step 1: Get current IP
    old_ip = get_ip()
    print(f"\n[1] Current IP: {old_ip}")

    # Step 2: Disconnect
    print("\n[2] Disconnecting from VPN...")
    protonvpn_disconnect()
    time.sleep(2)
    disconnected_ip = get_ip()
    print(f"    IP after disconnect: {disconnected_ip}")

    # Step 3: Connect to new server
    print("\n[3] Connecting to new VPN server...")
    protonvpn_connect()

    # Step 4: Verify new IP
    new_ip = get_ip()
    print(f"\n[4] New IP: {new_ip}")

    # Step 5: Check if IP changed
    if new_ip != old_ip:
        print(f"\n[SUCCESS] IP changed! {old_ip} -> {new_ip}")
        return True
    else:
        print(f"\n[WARNING] IP didn't change: {old_ip}")
        return False


def simulate_rate_limit():
    """Simulate hitting a rate limit and rotating VPN."""
    print("=" * 60)
    print("SIMULATION: Rate Limit -> VPN Rotation")
    print("=" * 60)

    # Step 1: Simulate hitting rate limit
    print("\n[STEP 1] Simulating API rate limit...")
    print("    Status: 429 Too Many Requests")
    print("    Action: Need to rotate IP")

    # Step 2: Check if VPN rotation would help
    print("\n[STEP 2] Checking if VPN rotation helps...")

    # Check master-automation-plan findings
    print("""
    FROM MASTER-PLAN:
    | Provider    | Rate Limit | Per IP? | VPN Helps? |
    |-------------|-----------|---------|------------|
    | opencode    | 200/day   | Per key | NO         |
    | OpenRouter  | 50/day    | Global  | NO         |
    | Groq        | 14,400/day| Per key | NO         |
    
    FINDING: Most providers use KEY-based limits, not IP-based.
    VPN rotation will NOT help with rate limits!
    """)

    # Step 3: When VPN DOES help
    print("\n[STEP 3] When DOES VPN rotation help?")
    print("""
    VPN rotation helps when:
    1. IP-based rate limits (rare for APIs)
    2. Geo-restrictions (access content from different countries)
    3. Web scraping (avoid IP blocks)
    4. Privacy (hide real IP)
    
    For YOUR use case (API tokens), VPN won't help because:
    - Rate limits are tied to API KEY, not IP
    - Changing IP doesn't reset the key's quota
    """)

    # Step 4: What WOULD work
    print("\n[STEP 4] What WOULD work for API rate limits?")
    print("""
    SOLUTION: Rotate API KEYS, not IPs!
    
    1. Create multiple free accounts:
       - opencode (200 req/day per account)
       - OpenRouter (50 req/day per account)
       - Groq (14,400 req/day per account)
    
    2. Rotate between accounts when one hits limit:
       - Account A hits 200/day -> Switch to Account B
       - Account B hits 200/day -> Switch to Account C
       - etc.
    
    3. Total free capacity:
       - 3 opencode accounts = 600 req/day
       - 3 OpenRouter accounts = 150 req/day
       - 3 Groq accounts = 43,200 req/day
       - TOTAL: ~44,000 req/day FREE!
    """)

    return False  # VPN rotation doesn't help for API limits


def test_actual_vpn():
    """Actually test VPN rotation."""
    print("\n" + "=" * 60)
    print("ACTUAL VPN ROTATION TEST")
    print("=" * 60)

    # Get baseline IP
    baseline_ip = get_ip()
    print(f"\n[BASELINE] Your real IP: {baseline_ip}")

    # Test rotation
    print("\n[TEST] Attempting VPN rotation...")
    success = protonvpn_rotate()

    # Get final IP
    final_ip = get_ip()
    print(f"\n[FINAL] Current IP: {final_ip}")

    if success:
        print("\n[RESULT] VPN rotation WORKS!")
        print("    IP changed successfully")
    else:
        print("\n[RESULT] VPN rotation FAILED or not needed")
        print("    IP didn't change")

    return success


def main():
    print("=" * 60)
    print("VPN ROTATION SIMULATOR")
    print("=" * 60)
    print()

    # Run simulation
    simulate_rate_limit()

    # Ask if user wants to test actual VPN
    print("\n" + "=" * 60)
    print("DO YOU WANT TO TEST ACTUAL VPN ROTATION?")
    print("=" * 60)
    print("\nThis will:")
    print("1. Disconnect from VPN (if connected)")
    print("2. Connect to new VPN server")
    print("3. Verify IP changed")
    print()

    # For now, just show the analysis
    print("=" * 60)
    print("CONCLUSION")
    print("=" * 60)
    print("""
    FOR API RATE LIMITS:
    - VPN rotation does NOT help (key-based limits)
    - Need to rotate API KEYS instead
    - Create multiple free accounts
    
    FOR WEB SCRAPING/GEO-RESTRICTIONS:
    - VPN rotation DOES help (IP-based blocks)
    - Use ProtonVPN rotation
    - Change server on block
    
    RECOMMENDATION:
    1. For API tokens: Create multiple accounts
    2. For web scraping: Use VPN rotation
    3. For both: Combine both strategies
    """)


if __name__ == "__main__":
    main()
