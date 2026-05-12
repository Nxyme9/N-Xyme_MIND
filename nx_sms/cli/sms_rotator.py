#!/usr/bin/env python3
"""
SMS Rotator CLI - Self-Learning SMS API Key Rotator
=====================================================

A command-line interface for the NxSMS Rotator system.

Usage:
    python3 sms_rotator.py send +15551234567 "Hello world!"
    python3 sms_rotator.py add-key textbelt YOUR_KEY_HERE
    python3 sms_rotator.py list
    python3 sms_rotator.py stats

Features:
    - Multi-key SMS API rotation (TextBelt, SeaSMS, WiFiText, SMSMode)
    - SQLite learning from outcomes
    - Auto-failover on quota limits
    - Per-key health tracking with circuit breakers
    - Colored output for better UX
"""

import sys
import os
import argparse
import json
from pathlib import Path
from datetime import datetime

_project_root = Path(__file__).parent
sys.path.insert(0, str(_project_root))

class Colors:
    """ANSI color codes for terminal output."""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'


def colorize(text: str, color: str, bold: bool = False) -> str:
    """Wrap text with ANSI color codes."""
    prefix = color
    if bold:
        prefix = Colors.BOLD + color
    return f"{prefix}{text}{Colors.RESET}"


def success_msg(text: str) -> str:
    return colorize(f"✓ {text}", Colors.GREEN, bold=True)


def error_msg(text: str) -> str:
    return colorize(f"✗ {text}", Colors.RED, bold=True)


def warning_msg(text: str) -> str:
    return colorize(f"⚠ {text}", Colors.YELLOW, bold=True)


def info_msg(text: str) -> str:
    return colorize(f"ℹ {text}", Colors.CYAN)


def header(text: str) -> str:
    return colorize(f"\n{'='*60}\n  {text}\n{'='*60}", Colors.BLUE, bold=True)


class SMSRotatorCLI:
    """CLI interface for NxSMS Rotator."""

    def __init__(self):
        try:
            from nx_sms.core import NxSMS
            self.sms = NxSMS()
        except ImportError as e:
            print(error_msg(f"Failed to import NxSMS core: {e}"))
            print(info_msg("Make sure you're running from the project root directory"))
            sys.exit(1)
        except Exception as e:
            print(error_msg(f"Failed to initialize NxSMS: {e}"))
            sys.exit(1)

    def send_sms(self, phone: str, message: str) -> int:
        """
        Send an SMS with automatic key rotation.

        Args:
            phone: Phone number with country code (e.g., +15551234567)
            message: Message to send

        Returns:
            Exit code (0 for success, 1 for failure)
        """
        print(header("SMS ROTATOR - SEND MESSAGE"))
        print(info_msg(f"To: {phone}"))
        print(info_msg(f"Message: {message}"))
        print(info_msg(f"Length: {len(message)} characters\n"))

        if not phone or not phone.startswith('+'):
            print(error_msg("Phone number must start with '+' and include country code"))
            print(info_msg("Example: +15551234567"))
            return 1

        if not message:
            print(error_msg("Message cannot be empty"))
            return 1

        if len(message) > 1600:
            print(warning_msg(f"Message length ({len(message)}) exceeds typical SMS limit (1600 chars)"))

        available = self.sms.get_available_keys()
        if not available:
            print(error_msg("No SMS services available!"))
            print(info_msg("Add a key first with: python3 sms_rotator.py add-key <service> <key>"))
            print(info_msg("Available services: textbelt, seasms, wifitext, smsmode"))
            return 1

        print(info_msg(f"Available services: {', '.join(available)}"))
        print(info_msg("Attempting to send...\n"))

        try:
            result = self.sms.send(phone, message)

            if result.success:
                print(success_msg("SMS sent successfully!"))
                print(f"\n  {Colors.BOLD}Service:{Colors.RESET} {result.service}")
                print(f"  {Colors.BOLD}Key Used:{Colors.RESET} {result.key_used}")
                print(f"  {Colors.BOLD}Latency:{Colors.RESET} {result.latency_ms}ms")
                if result.quota_remaining >= 0:
                    print(f"  {Colors.BOLD}Quota Remaining:{Colors.RESET} {result.quota_remaining}")
                return 0
            else:
                print(error_msg(f"Failed to send SMS"))
                print(f"\n  {Colors.BOLD}Error:{Colors.RESET} {result.error}")
                print(f"  {Colors.BOLD}Service:{Colors.RESET} {result.service}")

                error_lower = result.error.lower()
                if 'quota' in error_lower or 'limit' in error_lower or 'exceed' in error_lower:
                    print(warning_msg("Quota/rate limit detected - keys may need rotation"))
                elif 'auth' in error_lower or 'key' in error_lower or 'invalid' in error_lower:
                    print(warning_msg("Authentication error - check your API keys"))

                print(f"\n{info_msg('All available services failed')}")
                return 1

        except Exception as e:
            print(error_msg(f"Unexpected error: {e}"))
            return 1

    def add_key(self, service: str, api_key: str) -> int:
        """
        Add or update an API key for a service.

        Args:
            service: Service name (textbelt, seasms, wifitext, smsmode, email2sms)
            api_key: The API key to add (or JSON config for email2sms)

        Returns:
            Exit code (0 for success, 1 for failure)
        """
        print(header("SMS ROTATOR - ADD API KEY"))

        valid_services = ['textbelt', 'seasms', 'wifitext', 'smsmode', 'smsto', 'textlocal', 'email2sms']
        service = service.lower().strip()

        if service not in valid_services:
            print(error_msg(f"Unknown service: {service}"))
            print(info_msg(f"Valid services: {', '.join(valid_services)}"))
            return 1

        # Handle email2sms specially - requires JSON config
        if service == "email2sms":
            import json
            try:
                config = json.loads(api_key)
                sms = NxSMS()
                if "email2sms" not in sms.config:
                    sms.config["email2sms"] = {}
                sms.config["email2sms"].update(config)
                KEYS_FILE = Path(__file__).parent.parent / "configs" / "nx_sms" / "keys.json"
                KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
                with open(KEYS_FILE, "w") as f:
                    json.dump(sms.config, f, indent=2)
                print(success_msg(f"Email2SMS configured successfully!"))
                print(f"  SMTP: {config.get('smtp_host', 'smtp.gmail.com')}")
                print(f"  Email: {config.get('email', 'N/A')}")
                print(f"  Gateway: {config.get('carrier_gateway', 'vtext.com')}")
                return 0
            except json.JSONDecodeError:
                print(error_msg("email2sms requires JSON config"))
                print(info_msg("Example: add-key email2sms '{\"email\":\"you@gmail.com\",\"password\":\"apppassword\",\"carrier_gateway\":\"@vtext.com\"}'"))
                return 1

        if not api_key or api_key.strip() == "":
            print(error_msg("API key cannot be empty"))
            return 1

        api_key = api_key.strip()
        masked_key = api_key[:8] + "***" if len(api_key) > 8 else "***"

        print(info_msg(f"Service: {service}"))
        print(info_msg(f"API Key: {masked_key}"))
        print(info_msg("Adding key...\n"))

        try:
            success = self.sms.add_key(service, api_key)

            if success:
                print(success_msg(f"API key added for {service}!"))
                print(info_msg(f"Masked key: {masked_key}"))
                print(info_msg("You can now send SMS using this service."))
                return 0
            else:
                print(error_msg("Failed to add API key"))
                return 1

        except Exception as e:
            print(error_msg(f"Error adding key: {e}"))
            return 1

    def list_keys(self) -> int:
        """
        List all configured keys and their status.

        Returns:
            Exit code (0 for success)
        """
        print(header("SMS ROTATOR - KEY STATUS"))

        try:
            from nx_sms.core import DEFAULT_SERVICES, KEYS_FILE

            if not KEYS_FILE.exists():
                print(warning_msg("No keys file found!"))
                print(info_msg("Add a key with: python3 sms_rotator.py add-key <service> <key>"))
                return 0

            with open(KEYS_FILE) as f:
                keys_data = json.load(f)

            if not keys_data:
                print(warning_msg("No API keys configured!"))
                print(info_msg("Add a key with: python3 sms_rotator.py add-key <service> <key>"))
                return 0

            available = self.sms.get_available_keys()

            print(f"\n{Colors.BOLD}{'Service':<15} {'Status':<15} {'Key':<20} {'Quota':<10} {'Success Rate':<12}{Colors.RESET}")
            print("-" * 72)

            for service, key_data in keys_data.items():
                if isinstance(key_data, dict):
                    api_key = key_data.get("api_key", "")
                else:
                    api_key = str(key_data)

                if api_key:
                    masked_key = api_key[:8] + "***" if len(api_key) > 8 else "***"
                else:
                    masked_key = "Not set"

                is_available = service in available
                if is_available:
                    status = colorize("● Available", Colors.GREEN, bold=True)
                else:
                    status = colorize("● Unavailable", Colors.RED)

                stats = self.sms.stats.get(service, {})
                success_rate = stats.get("success_rate", 0.0)
                quota = stats.get("quota_remaining", "N/A")

                if success_rate >= 0.7:
                    rate_color = Colors.GREEN
                elif success_rate >= 0.3:
                    rate_color = Colors.YELLOW
                else:
                    rate_color = Colors.RED

                success_rate_str = colorize(f"{success_rate*100:.1f}%", rate_color)

                print(f"{service:<15} {status:<15} {masked_key:<20} {str(quota):<10} {success_rate_str:<12}")

            print(f"\n{info_msg('Legend: ● Available = Ready to use')}")
            print(info_msg(f"Total services configured: {len(keys_data)}"))

            return 0

        except json.JSONDecodeError:
            print(error_msg("Keys file is corrupted (invalid JSON)"))
            return 1
        except Exception as e:
            print(error_msg(f"Error listing keys: {e}"))
            return 1

    def show_stats(self) -> int:
        """
        Show statistics for all services.

        Returns:
            Exit code (0 for success)
        """
        print(header("SMS ROTATOR - STATISTICS"))

        try:
            from nx_sms.core import DB_FILE
            import sqlite3

            if not DB_FILE.exists():
                print(warning_msg("No statistics database found!"))
                print(info_msg("Statistics will appear after sending some SMS messages."))
                return 0

            all_stats = self.sms.get_all_stats()

            if not all_stats:
                print(warning_msg("No statistics available yet!"))
                print(info_msg("Statistics will appear after sending some SMS messages."))
                return 0

            print(f"\n{Colors.BOLD}PER-SERVICE STATISTICS{Colors.RESET}")
            print("=" * 60)

            total_requests = 0
            total_successful = 0
            total_failed = 0

            for service, stats in all_stats.items():
                print(f"\n{Colors.BOLD}Service: {service.upper()}{Colors.RESET}")
                total = stats.get('total_requests', 0)
                successful = stats.get('successful_requests', 0)
                failed = stats.get('failed_requests', 0)
                avg_latency = stats.get('avg_latency_ms', 0)

                print(f"  Total Requests:     {total}")
                success_display = colorize(str(successful), Colors.GREEN)
                print(f"  Successful:          {success_display}")
                fail_display = colorize(str(failed), Colors.RED)
                print(f"  Failed:              {fail_display}")
                print(f"  Avg Latency:         {avg_latency:.0f} ms")

                success_rate = stats.get('success_rate', 0.0)

                if success_rate >= 0.7:
                    rate_display = colorize(f"{success_rate*100:.1f}%", Colors.GREEN, bold=True)
                elif success_rate >= 0.3:
                    rate_display = colorize(f"{success_rate*100:.1f}%", Colors.YELLOW, bold=True)
                else:
                    rate_display = colorize(f"{success_rate*100:.1f}%", Colors.RED, bold=True)

                print(f"  Success Rate:        {rate_display}")

                total_requests += total
                total_successful += successful
                total_failed += failed

            print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
            print(f"{Colors.BOLD}SUMMARY{Colors.RESET}")
            print(f"  Total Requests:     {total_requests}")
            success_total = colorize(str(total_successful), Colors.GREEN)
            print(f"  Total Successful:   {success_total}")
            fail_total = colorize(str(total_failed), Colors.RED)
            print(f"  Total Failed:       {fail_total}")

            if total_requests > 0:
                overall_rate = (total_successful / total_requests) * 100
                if overall_rate >= 70:
                    rate_display = colorize(f"{overall_rate:.1f}%", Colors.GREEN, bold=True)
                elif overall_rate >= 30:
                    rate_display = colorize(f"{overall_rate:.1f}%", Colors.YELLOW, bold=True)
                else:
                    rate_display = colorize(f"{overall_rate:.1f}%", Colors.RED, bold=True)
                print(f"  Overall Success Rate: {rate_display}")

            print(f"\n{Colors.BOLD}RECENT ACTIVITY{Colors.RESET}")
            print("-" * 60)

            try:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT service, success, error, latency_ms, timestamp
                    FROM outcomes
                    ORDER BY timestamp DESC
                    LIMIT 10
                """)

                rows = cursor.fetchall()
                conn.close()

                if rows:
                    for row in rows:
                        service, success, error, latency_ms, timestamp = row
                        dt = datetime.fromtimestamp(timestamp)
                        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")

                        if success:
                            status = colorize("✓ SUCCESS", Colors.GREEN)
                        else:
                            status = colorize("✗ FAILED", Colors.RED)

                        print(f"  [{time_str}] {status} via {service} ({latency_ms}ms)")
                        if error and not success:
                            truncated = error[:60] + ('...' if len(error) > 60 else '')
                            print(f"    └─ Error: {truncated}")
                else:
                    print(f"  {Colors.DIM}No recent activity{Colors.RESET}")

            except Exception as e:
                print(f"  {Colors.DIM}Could not fetch recent activity: {e}{Colors.RESET}")

            return 0

        except Exception as e:
            print(error_msg(f"Error showing stats: {e}"))
            return 1

    def check_health(self) -> int:
        """
        Check health of all services.

        Returns:
            Exit code (0 if all healthy, 1 if issues found)
        """
        print(header("SMS ROTATOR - HEALTH CHECK"))

        available = self.sms.get_available_keys()

        if not available:
            print(error_msg("No services available!"))
            print(info_msg("Add keys with: python3 sms_rotator.py add-key <service> <key>"))
            return 1

        print(info_msg(f"Available services: {len(available)}"))

        all_healthy = True

        for service in available:
            stats = self.sms.stats.get(service, {})
            success_rate = stats.get("success_rate", 0.0)

            if success_rate >= 0.7:
                status = colorize("HEALTHY", Colors.GREEN, bold=True)
            elif success_rate >= 0.3:
                status = colorize("DEGRADED", Colors.YELLOW, bold=True)
                all_healthy = False
            else:
                status = colorize("UNHEALTHY", Colors.RED, bold=True)
                all_healthy = False

            print(f"  {service:<15} {status} (Success Rate: {success_rate*100:.1f}%)")

        if all_healthy and len(available) > 0:
            print(success_msg("All services are healthy!"))
            return 0
        else:
            print(warning_msg("Some services need attention"))
            return 1


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="SMS Rotator CLI - Self-Learning SMS API Key Rotator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 sms_rotator.py send +15551234567 "Hello world!"
  python3 sms_rotator.py add-key textbelt YOUR_KEY_HERE
  python3 sms_rotator.py list
  python3 sms_rotator.py stats

Available services: textbelt, seasms, wifitext, smsmode
"""
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    send_parser = subparsers.add_parser("send", help="Send an SMS (auto-rotates keys)")
    send_parser.add_argument("phone", help="Phone number with country code (e.g., +15551234567)")
    send_parser.add_argument("message", help="Message to send")

    add_key_parser = subparsers.add_parser("add-key", help="Add/update an API key for a service")
    add_key_parser.add_argument("service", help="Service name (textbelt, seasms, wifitext, smsmode)")
    add_key_parser.add_argument("api_key", help="The API key to add")

    subparsers.add_parser("list", help="List all keys and their status")

    subparsers.add_parser("stats", help="Show statistics for all services")

    subparsers.add_parser("health", help="Check health of all services")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    cli = SMSRotatorCLI()

    if args.command == "send":
        exit_code = cli.send_sms(args.phone, args.message)
    elif args.command == "add-key":
        exit_code = cli.add_key(args.service, args.api_key)
    elif args.command == "list":
        exit_code = cli.list_keys()
    elif args.command == "stats":
        exit_code = cli.show_stats()
    elif args.command == "health":
        exit_code = cli.check_health()
    else:
        parser.print_help()
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
