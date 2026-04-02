"""
Notification Monitor
Shows popup notifications instead of cluttering chat.
Run as background process to show task completions.
"""

import json
import time
from pathlib import Path

NOTIFICATION_DIR = Path(".notifications")
QUEUE_FILE = NOTIFICATION_DIR / "queue.json"


def show_popup(title: str, message: str, timeout: int = 5):
    """Show system tray notification."""
    try:
        from plyer import notification

        notification.notify(title=title, message=message, timeout=timeout)
    except ImportError:
        # Fallback: print to console
        print(f"[NOTIFICATION] {title}: {message}")


def process_queue():
    """Process notification queue."""
    if not QUEUE_FILE.exists():
        return

    try:
        with open(QUEUE_FILE) as f:
            queue = json.load(f)

        for item in queue:
            show_popup(
                title=item.get("title", "Task Complete"),
                message=item.get("message", ""),
                timeout=item.get("timeout", 5),
            )

        # Clear queue
        with open(QUEUE_FILE, "w") as f:
            json.dump([], f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Warning: Failed to clear notification queue: {e}")


if __name__ == "__main__":
    print("Notification monitor running...")
    while True:
        process_queue()
        time.sleep(2)
