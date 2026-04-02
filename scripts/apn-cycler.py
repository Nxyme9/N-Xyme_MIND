#!/usr/bin/env python3
"""
APN Cycling for Xiaomi/Android Phones - ADB-based solution.

Changes mobile APN to get fresh IP from carrier.
This is different from VPN rotation - it changes your actual mobile data connection.

Usage:
    python scripts/apn-cycler.py --list              # List available APNs
    python scripts/apn-cycler.py --current           # Show current APN
    python scripts/apn-cycler.py --cycle             # Cycle to next APN
    python scripts/apn-cycler.py --auto              # Auto-cycle every N seconds
    python scripts/apn-cycler.py --test              # Test APN cycling
"""

import subprocess
import time
import json
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ADB path (adjust if needed)
ADB_PATH = "adb"


class APNCycler:
    """Cycle through mobile APNs to get fresh IPs."""

    def __init__(self):
        self.device_connected = False
        self.check_adb()

    def check_adb(self):
        """Check if ADB is available and device is connected."""
        try:
            result = subprocess.run(
                [ADB_PATH, "devices"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                if len(lines) > 1:  # First line is header
                    self.device_connected = True
                    print(f"[ADB] Device connected: {lines[1].split()[0]}")
                    return True
            print(
                "[ADB] No device connected. Connect your phone via USB with USB debugging enabled."
            )
            return False
        except FileNotFoundError:
            print("[ADB] ADB not found. Install Android SDK or add to PATH.")
            return False
        except Exception as e:
            print(f"[ADB] Error: {e}")
            return False

    def run_adb(self, command):
        """Run ADB command."""
        try:
            cmd = [ADB_PATH] + command.split()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return result.stdout.strip()
        except Exception as e:
            return f"Error: {e}"

    def get_current_apn(self):
        """Get current APN settings."""
        # Method 1: Try to get APN via settings
        output = self.run_adb("shell settings get global apn")
        if output and output != "null":
            return {"apn": output}

        # Method 2: Get from telephony database
        output = self.run_adb("shell content query --uri content://telephony/carriers/preferapn")
        if output:
            return {"raw": output}

        return None

    def list_apns(self):
        """List all available APNs on device."""
        print("\n[APN] Listing available APNs...")

        # Get APNs from telephony database
        output = self.run_adb("shell content query --uri content://telephony/carriers")

        if not output or "No result found" in output:
            print("[APN] Could not retrieve APNs. Trying alternative method...")
            # Alternative: dumpsys telephony
            output = self.run_adb("shell dumpsys telephony.registry | grep -i apn")

        print(f"[APN] Raw output:\n{output[:500]}...")
        return output

    def set_apn_by_index(self, index):
        """Set APN by index in the list."""
        print(f"[APN] Setting APN to index {index}...")

        # This requires root access on most devices
        # Alternative: Use settings intent to open APN settings
        self.run_adb("shell am start -a android.settings.APN_SETTINGS")
        print("[APN] Opened APN settings. Manual selection required.")
        print("[APN] TIP: Use Tasker for automated APN cycling (see README)")
        return False

    def cycle_apn_airplane_mode(self):
        """
        Cycle APN using airplane mode toggle.
        This forces reconnection and often gets a new IP from carrier.
        """
        print("\n[APN] Cycling via airplane mode...")

        # Get current IP
        old_ip = self.get_ip_via_adb()
        print(f"[APN] Current IP: {old_ip}")

        # Enable airplane mode
        print("[APN] Enabling airplane mode...")
        self.run_adb("shell settings put global airplane_mode_on 1")
        self.run_adb("shell am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true")
        time.sleep(5)

        # Disable airplane mode
        print("[APN] Disabling airplane mode...")
        self.run_adb("shell settings put global airplane_mode_on 0")
        self.run_adb("shell am broadcast -a android.intent.action.AIRPLANE_MODE --ez state false")
        time.sleep(10)  # Wait for reconnection

        # Get new IP
        new_ip = self.get_ip_via_adb()
        print(f"[APN] New IP: {new_ip}")

        if new_ip and new_ip != old_ip:
            print(f"[SUCCESS] IP changed! {old_ip} -> {new_ip}")
            return True
        else:
            print(f"[WARNING] IP didn't change: {old_ip}")
            return False

    def cycle_apn_data_toggle(self):
        """
        Cycle APN by toggling mobile data.
        Less aggressive than airplane mode.
        """
        print("\n[APN] Cycling via mobile data toggle...")

        old_ip = self.get_ip_via_adb()
        print(f"[APN] Current IP: {old_ip}")

        # Disable mobile data
        print("[APN] Disabling mobile data...")
        self.run_adb("shell svc data disable")
        time.sleep(3)

        # Enable mobile data
        print("[APN] Enabling mobile data...")
        self.run_adb("shell svc data enable")
        time.sleep(10)

        new_ip = self.get_ip_via_adb()
        print(f"[APN] New IP: {new_ip}")

        if new_ip and new_ip != old_ip:
            print(f"[SUCCESS] IP changed! {old_ip} -> {new_ip}")
            return True
        else:
            print(f"[WARNING] IP didn't change: {old_ip}")
            return False

    def get_ip_via_adb(self):
        """Get phone's public IP via ADB."""
        try:
            # Use phone's browser to check IP
            output = self.run_adb("shell curl -s https://api.ipify.org")
            if output and len(output) < 20:  # Valid IP
                return output
        except Exception as e:
            logger.debug(f"Failed to get public IP: {e}")

        # Alternative: check via ip addr
        output = self.run_adb("shell ip addr show rmnet0 2>/dev/null | grep 'inet '")
        if output:
            return output.split()[1].split("/")[0]

        return None

    def auto_cycle(self, interval=300):
        """Auto-cycle APN every N seconds."""
        print(f"\n[APN] Starting auto-cycle every {interval} seconds...")
        print("[APN] Press Ctrl+C to stop\n")

        cycle_count = 0
        try:
            while True:
                cycle_count += 1
                print(f"\n{'=' * 60}")
                print(f"CYCLE #{cycle_count}")
                print(f"{'=' * 60}")

                # Try data toggle first (less aggressive)
                success = self.cycle_apn_data_toggle()

                if not success:
                    # If data toggle didn't work, try airplane mode
                    print("[APN] Data toggle didn't change IP, trying airplane mode...")
                    success = self.cycle_apn_airplane_mode()

                print(f"\n[APN] Waiting {interval} seconds until next cycle...")
                time.sleep(interval)

        except KeyboardInterrupt:
            print(f"\n[APN] Stopped after {cycle_count} cycles")

    def test(self):
        """Test APN cycling functionality."""
        print("\n" + "=" * 60)
        print("APN CYCLING TEST")
        print("=" * 60)

        if not self.device_connected:
            print("\n[FAIL] No device connected!")
            print("\nTo connect your Xiaomi phone:")
            print("1. Enable Developer Options (tap Build Number 7 times)")
            print("2. Enable USB Debugging")
            print("3. Connect via USB")
            print("4. Accept USB debugging prompt on phone")
            print("5. Run: adb devices")
            return False

        print("\n[TEST 1] Getting current IP...")
        old_ip = self.get_ip_via_adb()
        print(f"  Current IP: {old_ip}")

        print("\n[TEST 2] Testing data toggle method...")
        success = self.cycle_apn_data_toggle()

        if success:
            print("\n[RESULT] APN cycling WORKS!")
        else:
            print("\n[RESULT] IP didn't change. Trying airplane mode...")
            success = self.cycle_apn_airplane_mode()

            if success:
                print("\n[RESULT] Airplane mode method WORKS!")
            else:
                print("\n[RESULT] Neither method changed IP.")
                print("Possible reasons:")
                print("  1. Carrier doesn't assign new IPs on reconnect")
                print("  2. Carrier uses CGNAT (shared IPs)")
                print("  3. Need to switch between actual APNs (requires root)")

        return success


def main():
    cycler = APNCycler()

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--list":
            cycler.list_apns()
        elif arg == "--current":
            current = cycler.get_current_apn()
            print(f"Current APN: {current}")
        elif arg == "--cycle":
            cycler.cycle_apn_data_toggle()
        elif arg == "--auto":
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 300
            cycler.auto_cycle(interval)
        elif arg == "--test":
            cycler.test()
        else:
            print(f"Unknown option: {arg}")
            print("Usage: apn-cycler.py [--list|--current|--cycle|--auto [interval]|--test]")
    else:
        cycler.test()


if __name__ == "__main__":
    main()
