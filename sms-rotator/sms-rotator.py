#!/usr/bin/env python3
"""
SMS Rotator - Send SMS using multiple free API keys with automatic rotation
2026 - Free SMS App for CachyOS/Arch Linux
"""

import argparse
import json
import os
import sys
import time
from typing import Optional
import requests

CONFIG_FILE = os.path.expanduser("~/.sms-rotator.json")

# Free SMS services configuration
SERVICES = {
    "textbelt": {
        "url": "https://textbelt.com/text",
        "param_key": "key",
        "param_number": "number",
        "param_message": "message",
        "quota_field": "quotaRemaining",
        "error_field": "error",
        "free_key": "textbelt",  # Default free key
    },
    "seasms": {
        "url": "https://api.seasms.com/send",
        "param_key": "apikey",
        "param_number": "to",
        "param_message": "message",
        "quota_field": "credits",
        "error_field": "error",
    },
    "wifitext": {
        "url": "https://api.wifitext.com/api/send",
        "param_key": "api_key",
        "param_number": "number",
        "param_message": "message",
        "quota_field": "credits",
        "error_field": "error",
    },
    "smsmode": {
        "url": "https://api.smsmode.com/sms/send",
        "param_key": "apiKey",
        "param_number": "to",
        "param_message": "message",
        "quota_field": "credits",
        "error_field": "error",
    },
}

# Default config
DEFAULT_CONFIG = {
    "keys": {},
    "stats": {},
}


def load_config() -> dict:
    """Load configuration from file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    """Save configuration to file."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def add_key(service: str, key: str, config: dict) -> dict:
    """Add or update an API key for a service."""
    if service not in SERVICES:
        print(f"Unknown service: {service}")
        print(f"Available: {', '.join(SERVICES.keys())}")
        return config

    if "keys" not in config:
        config["keys"] = {}
    if "stats" not in config:
        config["stats"] = {}

    config["keys"][service] = key
    config["stats"][service] = config["stats"].get(service, {"used": 0, "success": 0, "failed": 0})
    save_config(config)
    print(f"Added key for {service}")
    return config


def list_keys(config: dict) -> None:
    """List all configured keys."""
    keys = config.get("keys", {})
    if not keys:
        print("No keys configured. Use: sms-rotator.py add-key <service> <key>")
        return

    print("Configured Keys:")
    for service, key in keys.items():
        # Show masked key
        masked = key[:4] + "*" * (len(key) - 8) + key[-4:] if len(key) > 8 else "****"
        stats = config.get("stats", {}).get(service, {})
        print(f"  {service}: {masked}")
        print(f"    Used: {stats.get('used', 0)}, Success: {stats.get('success', 0)}, Failed: {stats.get('failed', 0)}")


def get_working_key(service: str, config: dict) -> Optional[str]:
    """Get API key for service, or use default textbelt if no key configured."""
    keys = config.get("keys", {})
    if service in keys:
        return keys[service]
    # Use default free key for textbelt
    if service == "textbelt":
        return SERVICES["textbelt"]["free_key"]
    return None


def send_sms(phone: str, message: str, service: str = "textbelt", config: dict = None) -> bool:
    """Send SMS using the specified service with key rotation."""
    if config is None:
        config = load_config()

    svc = SERVICES.get(service)
    if not svc:
        print(f"Unknown service: {service}")
        return False

    # Get API key
    api_key = get_working_key(service, config)
    if not api_key and service != "textbelt":
        print(f"No API key for {service}. Add one first: add-key {service} <key>")
        return False

    # Prepare request
    data = {
        svc["param_key"]: api_key,
        svc["param_number"]: phone,
        svc["param_message"]: message,
    }

    try:
        response = requests.post(svc["url"], data=data, timeout=30)
        result = response.json()

        # Check for errors
        if svc["error_field"] in result and result[svc["error_field"]]:
            error = result[svc["error_field"]]
            print(f"Error: {error}")

            # Update stats
            config["stats"][service] = config["stats"].get(service, {})
            config["stats"][service]["failed"] = config["stats"][service].get("failed", 0) + 1
            save_config(config)
            return False

        # Check quota
        if svc["quota_field"] in result:
            quota = result[svc["quota_field"]]
            print(f"Quota remaining: {quota}")

        # Update stats
        config["stats"][service] = config["stats"].get(service, {})
        config["stats"][service]["used"] = config["stats"][service].get("used", 0) + 1
        config["stats"][service]["success"] = config["stats"][service].get("success", 0) + 1
        save_config(config)
        print(f"SMS sent successfully via {service}")
        return True

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        config["stats"][service] = config["stats"].get(service, {})
        config["stats"][service]["failed"] = config["stats"][service].get("failed", 0) + 1
        save_config(config)
        return False


def send_with_rotation(phone: str, message: str, config: dict = None) -> bool:
    """Send SMS with automatic key rotation - tries each service until one works."""
    if config is None:
        config = load_config()

    for service in SERVICES.keys():
        print(f"Trying {service}...")
        if send_sms(phone, message, service, config):
            return True
        print(f"Failed, trying next...")
        time.sleep(1)  # Rate limit

    print("All services failed!")
    return False


def show_status(config: dict) -> None:
    """Show overall status."""
    stats = config.get("stats", {})
    if not stats:
        print("No stats yet. Send some messages!")
        return

    print("Usage Statistics:")
    for service, s in stats.items():
        print(f"  {service}:")
        print(f"    Used: {s.get('used', 0)}")
        print(f"    Success: {s.get('success', 0)}")
        print(f"    Failed: {s.get('failed', 0)}")


def main():
    parser = argparse.ArgumentParser(
        description="SMS Rotator - Send SMS using multiple free API keys",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sms-rotator.py send +15551234567 "Hello from SMS Rotator"
  sms-rotator.py add-key textbelt YOUR_API_KEY
  sms-rotator.py add-key seasms YOUR_API_KEY
  sms-rotator.py list-keys
  sms-rotator.py status
  sms-rotator.py try +15551234567 "Test"  # Try all services
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # send command
    send_parser = subparsers.add_parser("send", help="Send SMS")
    send_parser.add_argument("phone", help="Phone number (with country code)")
    send_parser.add_argument("message", help="Message to send")
    send_parser.add_argument("-s", "--service", default="textbelt", help="Service to use")

    # try command (auto-rotate)
    try_parser = subparsers.add_parser("try", help="Try all services until one works")
    try_parser.add_argument("phone", help="Phone number (with country code)")
    try_parser.add_argument("message", help="Message to send")

    # add-key command
    add_parser = subparsers.add_parser("add-key", help="Add API key")
    add_parser.add_argument("service", help="Service name")
    add_parser.add_argument("key", help="API key")

    # list-keys command
    subparsers.add_parser("list-keys", help="List configured keys")

    # status command
    subparsers.add_parser("status", help="Show usage statistics")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    config = load_config()

    if args.command == "send":
        send_sms(args.phone, args.message, args.service, config)
    elif args.command == "try":
        send_with_rotation(args.phone, args.message, config)
    elif args.command == "add-key":
        add_key(args.service, args.key, config)
    elif args.command == "list-keys":
        list_keys(config)
    elif args.command == "status":
        show_status(config)


if __name__ == "__main__":
    main()