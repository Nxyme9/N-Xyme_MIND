#!/usr/bin/env python3
"""N-Xyme Switch Notifier - Log and display model switch events."""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

CATALYST_DIR = Path(os.environ.get("CATALYST_DIR", Path(__file__).resolve().parent.parent))
SWITCH_LOG = CATALYST_DIR / "data" / "model-switches.jsonl"

# Ensure data dir exists
(CATALYST_DIR / "data").mkdir(parents=True, exist_ok=True)

# Cleanup counter
_cleanup_counter = 0
CLEANUP_INTERVAL = 30  # Run cleanup every 30 switches


def log_switch(event):
    """Log switch event to JSONL file with periodic cleanup."""
    global _cleanup_counter

    try:
        SWITCH_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(SWITCH_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")

        # Periodic cleanup
        _cleanup_counter += 1
        if _cleanup_counter >= CLEANUP_INTERVAL:
            _cleanup_counter = 0
            try:
                import sys as _sys

                _sys.path.insert(0, str(CATALYST_DIR))
                from packages.auto_capture.src.data_retention import cleanup_jsonl_file

                cleanup_jsonl_file(SWITCH_LOG)
            except (ImportError, Exception) as e:
                logger.debug(f"data_retention not available or cleanup failed: {e}")
    except Exception as e:
        logger.error(f"Failed to log switch event: {e}")


def print_notification(event):
    """Print clear notification based on risk level."""
    risk = event.get("risk_level", "info")
    from_model = event.get("from_model", "?")
    to_model = event.get("to_model", "?")
    reason = event.get("reason", "Unknown")
    action = event.get("action", "None")

    prefix = {
        "critical": "[!!]",
        "warning": "[!]",
        "info": "[i]",
    }.get(risk, "[i]")

    print("=" * 60)
    print(f"  {prefix} MODEL SWITCH: {risk.upper()}")
    print("=" * 60)
    print(f"  From:   {from_model}")
    print(f"  To:     {to_model}")
    print(f"  Reason: {reason}")
    print(f"  Action: {action}")
    print("=" * 60)


def create_event(from_model, to_model, reason, risk_level="info", action="None"):
    """Create a switch event."""
    return {
        "timestamp": datetime.now().isoformat(),
        "from_model": from_model,
        "to_model": to_model,
        "reason": reason,
        "risk_level": risk_level,
        "action": action,
    }


def main():
    json_output = "--json" in sys.argv

    # Check for command line arguments
    if len(sys.argv) > 1 and sys.argv[1] not in ("--json",):
        # Command line mode: switch-notifier.py <from> <to> <reason> [risk] [action]
        if len(sys.argv) < 4:
            print(
                "Usage: switch-notifier.py <from_model> <to_model> <reason> [risk_level] [action]"
            )
            print("  risk_level: info (default), warning, critical")
            return

        from_model = sys.argv[1]
        to_model = sys.argv[2]
        reason = sys.argv[3]
        risk_level = sys.argv[4] if len(sys.argv) > 4 else "info"
        action = sys.argv[5] if len(sys.argv) > 5 else "None"

        event = create_event(from_model, to_model, reason, risk_level, action)
        log_switch(event)

        if json_output:
            print(json.dumps(event, indent=2))
        else:
            print_notification(event)
        return

    # Stdin mode: read JSON events from stdin
    print("[Switch Notifier] Reading events from stdin (JSON per line)")
    print("[Switch Notifier] Press Ctrl+D (Unix) or Ctrl+Z (Windows) to stop\n")

    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                # Ensure required fields
                event.setdefault("timestamp", datetime.now().isoformat())
                event.setdefault("from_model", "?")
                event.setdefault("to_model", "?")
                event.setdefault("reason", "Unknown")
                event.setdefault("risk_level", "info")
                event.setdefault("action", "None")

                log_switch(event)

                if json_output:
                    print(json.dumps(event, indent=2))
                else:
                    print_notification(event)
            except json.JSONDecodeError:
                print(f"[!] Invalid JSON: {line[:100]}")
    except KeyboardInterrupt:
        print("\n[Switch Notifier] Stopped")
    except EOFError:
        print("\n[Switch Notifier] Done")


if __name__ == "__main__":
    main()
