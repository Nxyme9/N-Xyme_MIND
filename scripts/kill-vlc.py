#!/usr/bin/env python3
"""Kills VLC immediately when it starts. Run as background process."""

import time
import logging
import subprocess
import tempfile
from pathlib import Path

# Use system temp directory instead of hardcoded path
TEMP_DIR = Path(tempfile.gettempdir())

print("VLC Blocker running... (Ctrl+C to stop)")
while True:
    try:
        result = subprocess.run(
            ["taskkill", "/F", "/IM", "vlc.exe"], capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            print(f"[{time.strftime('%H:%M:%S')}] Killed VLC")
    except Exception as e:
        logging.error(f"Error killing VLC: {e}")

    # Also clean up temp .mp3 files
    try:
        subprocess.run(
            ["cmd", "/c", "del", "/q", str(TEMP_DIR / "*.mp3")], capture_output=True, timeout=2
        )
    except Exception as e:
        logging.error(f"Error cleaning temp mp3 files: {e}")

    time.sleep(1)  # Check every second
