#!/usr/bin/env python3
"""
archive-sessions.py — Move session files older than 7 days to archive.

Usage: python3 scripts/archive-sessions.py
Add to crontab for daily runs:
    @daily cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND && python3 scripts/archive-sessions.py
"""

import os
import shutil
import time
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "data", "sessions")
DST = os.path.join(BASE, "data", "archive", "sessions")
LOG = os.path.join(BASE, "data", "audit", "session-archival.log")

CUTOFF = time.time() - 7 * 86400

def log(msg: str):
    ts = datetime.now(timezone.utc).isoformat()
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"[{ts}] {msg}\n")
    print(msg)

def main():
    if not os.path.isdir(SRC):
        log(f"Source dir missing: {SRC}")
        return

    os.makedirs(DST, exist_ok=True)

    for entry in os.scandir(SRC):
        if not entry.name.endswith(".jsonl") or not entry.is_file():
            continue
        mtime = entry.stat().st_mtime
        if mtime >= CUTOFF:
            continue
        dest = os.path.join(DST, entry.name)
        shutil.move(entry.path, dest)
        age_h = (time.time() - mtime) / 3600
        log(f"ARCHIVED {entry.name}  (age={age_h:.1f}h  size={entry.stat().st_size})")

if __name__ == "__main__":
    main()
