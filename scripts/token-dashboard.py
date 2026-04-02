#!/usr/bin/env python3
"""N-Xyme Token Usage Dashboard - Monitor API token usage across providers."""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

CATALYST_DIR = Path(os.environ.get("CATALYST_DIR", Path(__file__).resolve().parent.parent))
USAGE_FILE = CATALYST_DIR / "configs" / "api-keys" / "usage.json"

# Alert thresholds (percentage of quota used)
WARN_THRESHOLD = 75
CRITICAL_THRESHOLD = 90

# Provider display names
PROVIDER_NAMES = {
    "opencode": "OpenCode",
    "openrouter": "OpenRouter",
    "groq": "Groq",
}


def get_usage_stats():
    """Read usage data from usage.json file.

    Returns:
        dict: Usage data per provider, or empty dict if file missing.
    """
    if not USAGE_FILE.exists():
        return {}

    try:
        with open(USAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"[!] Error reading usage file: {e}")
        return {}


def check_alerts(usage_data):
    """Check if any provider is approaching its quota limit.

    Args:
        usage_data: Dict of provider usage stats.

    Returns:
        list: Alert dicts with provider, level, message.
    """
    alerts = []

    for provider, stats in usage_data.items():
        quota = stats.get("quota")
        used = stats.get("used", 0)

        if quota is None or quota == 0:
            continue

        pct_used = (used / quota) * 100
        name = PROVIDER_NAMES.get(provider, provider)

        if pct_used >= CRITICAL_THRESHOLD:
            alerts.append(
                {
                    "provider": provider,
                    "level": "CRITICAL",
                    "message": f"{name}: {pct_used:.1f}% used ({quota - used:,} tokens remaining)",
                }
            )
        elif pct_used >= WARN_THRESHOLD:
            alerts.append(
                {
                    "provider": provider,
                    "level": "WARNING",
                    "message": f"{name}: {pct_used:.1f}% used ({quota - used:,} tokens remaining)",
                }
            )

    return alerts


def _format_bar(pct, width=20):
    """Create a text-based progress bar."""
    filled = int(width * pct / 100)
    empty = width - filled
    if pct >= CRITICAL_THRESHOLD:
        char = "!"
    elif pct >= WARN_THRESHOLD:
        char = "~"
    else:
        char = "#"
    return f"[{char * filled}{'.' * empty}]"


def _format_reset(reset_time):
    """Format reset time as relative or absolute."""
    if not reset_time:
        return "unknown"

    try:
        reset_dt = datetime.fromisoformat(reset_time)
        now = datetime.now(reset_dt.tzinfo) if reset_dt.tzinfo else datetime.now()
        delta = reset_dt - now

        if delta.total_seconds() < 0:
            return "overdue"
        elif delta.total_seconds() < 3600:
            mins = int(delta.total_seconds() / 60)
            return f"{mins}m"
        elif delta.total_seconds() < 86400:
            hrs = int(delta.total_seconds() / 3600)
            return f"{hrs}h {int((delta.total_seconds() % 3600) / 60)}m"
        else:
            days = delta.days
            return f"{days}d {int((delta.total_seconds() % 86400) / 3600)}h"
    except (ValueError, TypeError):
        return str(reset_time)


def format_dashboard(usage_data, alerts):
    """Format the token usage dashboard for display.

    Args:
        usage_data: Dict of provider usage stats.
        alerts: List of alert dicts from check_alerts().

    Returns:
        str: Formatted dashboard string.
    """
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines.append("=" * 60)
    lines.append("  N-XYME TOKEN USAGE DASHBOARD")
    lines.append(f"  {now}")
    lines.append("=" * 60)

    if not usage_data:
        lines.append("")
        lines.append("  [i] No usage data found.")
        lines.append(f"  [i] Expected: {USAGE_FILE}")
        lines.append("")
        lines.append("  Create usage.json with structure:")
        lines.append("  {")
        lines.append('    "opencode": {')
        lines.append('      "used": 150000,')
        lines.append('      "quota": 500000,')
        lines.append('      "reset_time": "2026-03-21T00:00:00",')
        lines.append('      "requests_today": 42')
        lines.append("    }")
        lines.append("  }")
        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)

    # Provider sections
    for provider in ["opencode", "openrouter", "groq"]:
        stats = usage_data.get(provider)
        name = PROVIDER_NAMES.get(provider, provider)

        lines.append("")
        lines.append(f"  {name}")
        lines.append(f"  {'-' * 40}")

        if not stats:
            lines.append("  Status: No data")
            continue

        quota = stats.get("quota")
        used = stats.get("used", 0)
        reset_time = stats.get("reset_time")
        requests = stats.get("requests_today", stats.get("requests", "?"))

        if quota and quota > 0:
            remaining = quota - used
            pct_used = (used / quota) * 100
            bar = _format_bar(pct_used)

            lines.append(f"  Used:      {used:>12,} / {quota:>12,} tokens")
            lines.append(f"  Remaining: {remaining:>12,} tokens")
            lines.append(f"  {bar} {pct_used:.1f}%")
        else:
            lines.append(f"  Used:      {used:>12,} tokens")
            lines.append(f"  Quota:     Unlimited or not set")

        lines.append(f"  Requests:  {requests}")
        lines.append(f"  Resets in: {_format_reset(reset_time)}")

    # Alerts section
    lines.append("")
    lines.append(f"  {'-' * 40}")

    if alerts:
        lines.append("  ALERTS")
        for alert in alerts:
            prefix = "[!!]" if alert["level"] == "CRITICAL" else "[!]"
            lines.append(f"  {prefix} {alert['message']}")
    else:
        lines.append("  [OK] All providers within limits")

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


def main():
    json_output = "--json" in sys.argv
    watch_mode = "--watch" in sys.argv or "-w" in sys.argv

    if watch_mode:
        import time

        print("[Token Dashboard] Watch mode - refreshing every 30s (Ctrl+C to stop)\n")
        try:
            while True:
                usage_data = get_usage_stats()
                alerts = check_alerts(usage_data)
                if json_output:
                    print(json.dumps({"usage": usage_data, "alerts": alerts}, indent=2))
                else:
                    # Clear screen
                    print("\033[2J\033[H", end="")
                    print(format_dashboard(usage_data, alerts))
                time.sleep(30)
        except KeyboardInterrupt:
            print("\n[Token Dashboard] Stopped")
            return

    usage_data = get_usage_stats()
    alerts = check_alerts(usage_data)

    if json_output:
        print(json.dumps({"usage": usage_data, "alerts": alerts}, indent=2))
    else:
        print(format_dashboard(usage_data, alerts))

    # Exit code reflects alert level
    if any(a["level"] == "CRITICAL" for a in alerts):
        sys.exit(2)
    elif alerts:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
