#!/usr/bin/env python3
"""
Bot Manager - Robust kill/restart for Telegram bot
No more hanging. Uses PID file + signal handling.
"""

import os
import sys
import signal
import subprocess
import time
import argparse
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
BOT_SCRIPT = SCRIPT_DIR / "main.py"
MIND_DIR = SCRIPT_DIR.parents[2]  # Go up to N-Xyme_MIND root
PID_FILE = SCRIPT_DIR / ".bot.pid"
LOG_FILE = SCRIPT_DIR / "bot.log"

# Use venv Python if available
VENV_PYTHON = MIND_DIR / ".venv/bin/python3"
PYTHON = str(VENV_PYTHON) if VENV_PYTHON.exists() else "python3"


def get_pid():
    if PID_FILE.exists():
        try:
            return int(PID_FILE.read_text().strip())
        except:
            return None
    return None


def is_running(pid):
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def kill_bot(force=False):
    pid = get_pid()
    if not pid:
        # Try to find by process name
        try:
            result = subprocess.run(
                ["pgrep", "-f", "bot/main.py"], capture_output=True, text=True
            )
            pids = result.stdout.strip().split("\n")
            for p in pids:
                if p:
                    try:
                        pid = int(p)
                    except:
                        pass
        except:
            pass

    if pid and is_running(pid):
        print(f"Killing bot (PID {pid})...")
        try:
            os.kill(pid, signal.SIGTERM)
            # Wait up to 5 seconds for graceful shutdown
            for _ in range(50):
                if not is_running(pid):
                    break
                time.sleep(0.1)

            if is_running(pid):
                print("Force killing...")
                os.kill(pid, signal.SIGKILL)
                time.sleep(0.5)
        except OSError as e:
            print(f"Error killing: {e}")

        # Clean up PID file
        if PID_FILE.exists():
            PID_FILE.unlink()
        print("✓ Bot killed")
        return True
    else:
        print("Bot not running")
        return False


def start_bot():
    pid = get_pid()
    if pid and is_running(pid):
        print(f"Bot already running (PID {pid})")
        return False

    print("Starting bot...")

    # Open log file
    log_fd = open(LOG_FILE, "a")

    # Start process using venv python
    proc = subprocess.Popen(
        [PYTHON, str(BOT_SCRIPT)],
        stdout=log_fd,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

    # Write PID
    PID_FILE.write_text(str(proc.pid))

    print(f"✓ Bot started (PID {proc.pid})")
    print(f"  Log: {LOG_FILE}")
    return True


def restart_bot():
    kill_bot()
    time.sleep(1)
    return start_bot()


def status_bot():
    pid = get_pid()
    if pid and is_running(pid):
        print(f"🟢 Bot running (PID {pid})")
        return True
    else:
        print("🔴 Bot not running")
        return False


def main():
    parser = argparse.ArgumentParser(description="Bot Manager")
    parser.add_argument(
        "action",
        choices=["start", "stop", "restart", "status"],
        help="Action to perform",
    )
    args = parser.parse_args()

    if args.action == "start":
        start_bot()
    elif args.action == "stop":
        kill_bot()
    elif args.action == "restart":
        restart_bot()
    elif args.action == "status":
        status_bot()


if __name__ == "__main__":
    main()
