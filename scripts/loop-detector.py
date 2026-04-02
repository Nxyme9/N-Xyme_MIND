#!/usr/bin/env python3
import sys
import json
import logging
from collections import deque
from pathlib import Path
from datetime import datetime

"""
Loop detector for AI model outputs.
Features:
- Accept input from stdin (one response per line) or a file path.
- Track last N responses (default 5).
- Detect loops:
  * exact repeat of the same response for threshold times in a row
  * degeneration: decreasing length for 3 consecutive responses
  * same tool call repeated 3+ times in last 3 responses
- Print human-readable warning and log to a JSONL file.
- Optional machine-readable JSON output with --json.
- Options: --threshold N, --window N, --json, and an optional path.
"""

logger = logging.getLogger(__name__)

DEFAULT_WINDOW = 5
DEFAULT_THRESHOLD = 3
CATALYST_DIR = Path(os.environ.get("CATALYST_DIR", Path(__file__).resolve().parent.parent))
LOG_DIR = CATALYST_DIR / "data"
LOG_FILE = LOG_DIR / "loop-detections.jsonl"

# Cleanup counter
_cleanup_counter = 0
CLEANUP_INTERVAL = 50  # Run cleanup every 50 detections


def ensure_log_file():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.touch(exist_ok=True)


def extract_calls(text):
    # Heuristic to detect tool invocation mentions in plain text without using regex module.
    found = []
    if not text:
        return found
    markers = [
        "Tool:",
        "Tool-",
        "tool:",
        "tool-",
        "Call:",
        "Call-",
        "call:",
        "call-",
        "invoke:",
        "invoke-",
    ]
    for marker in markers:
        start = 0
        while True:
            pos = text.find(marker, start)
            if pos == -1:
                break
            end = pos + len(marker)
            # skip whitespace
            j = end
            while j < len(text) and text[j].isspace():
                j += 1
            # read word characters as the tool name
            k = j
            while k < len(text) and (text[k].isalnum() or text[k] == "_"):
                k += 1
            if k > j:
                found.append(text[j:k].lower())
            start = pos + len(marker)
    return found


def truncate_preview(text, max_len=200):
    if text is None:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def parse_args(argv):
    path = None
    json_output = False
    threshold = DEFAULT_THRESHOLD
    window = DEFAULT_WINDOW
    i = 1
    while i < len(argv):
        a = argv[i]
        if a in ("--json", "-j"):
            json_output = True
            i += 1
        elif a == "--threshold":
            i += 1
            if i < len(argv):
                try:
                    threshold = int(argv[i])
                except ValueError:
                    threshold = DEFAULT_THRESHOLD
            i += 1
        elif a == "--window":
            i += 1
            if i < len(argv):
                try:
                    window = int(argv[i])
                except ValueError:
                    window = DEFAULT_WINDOW
            i += 1
        else:
            path = a
            i += 1
    return path, json_output, threshold, window


def main():
    path, json_output, threshold, window = parse_args(sys.argv)
    ensure_log_file()

    window_size = max(1, window)
    threshold_val = max(1, threshold)

    recent = deque(maxlen=window_size)  # stores last N responses

    if path:
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.rstrip("\n")
                    if line:
                        process_line(line, recent, threshold_val, window_size, json_output)
        except FileNotFoundError:
            print(f"Error: file not found: {path}", file=sys.stderr)
            sys.exit(2)
    else:
        for line in sys.stdin:
            line = line.rstrip("\n")
            if line:
                process_line(line, recent, threshold_val, window_size, json_output)


def process_line(line, recent, threshold, window_size, json_output):
    recent.append(line)
    detected = None

    # 1) exact-repeat: last 'threshold' items identical
    if len(recent) >= threshold:
        tail = list(recent)[-threshold:]
        if all(x == tail[0] for x in tail):
            detected = ("exact_repeat", threshold, tail[0])

    # 2) degeneration: 3 consecutive lengths strictly decreasing
    if detected is None and len(recent) >= 3:
        a, b, c = list(recent)[-3], list(recent)[-2], list(recent)[-1]
        if len(a) > len(b) > len(c):
            detected = ("degeneration", None, None)

    # 3) same tool call repeated 3+ times across last 3 responses
    if detected is None:
        last_three = list(recent)[-3:]
        calls = []
        for t in last_three:
            calls.extend(extract_calls(t))
        if calls:
            names = {}
            for nm in calls:
                names[nm] = names.get(nm, 0) + 1
            for nm, cnt in names.items():
                if cnt >= 3:
                    detected = ("tool_call_repeat", nm, cnt)
                    break

    if detected:
        typ = detected[0]
        if typ == "exact_repeat":
            count = detected[1]
            resp = detected[2]
            print("[!!] LOOP DETECTED")
            print(f"  Pattern: Same response repeated {count} times consecutively")
            print(f'  Response: "{truncate_preview(resp, 2000)}"')
            print("  Action: Stop this model. Try different model or approach.")
            log = {
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "type": "exact_repeat",
                "count": count,
                "response_preview": truncate_preview(resp, 400),
            }
        else:
            if typ == "degeneration":
                desc = "Response length decreased over last 3 outputs"
            else:
                if typ == "tool_call_repeat":
                    desc = f"Same tool call '{detected[1]}' repeated across last 3 responses"
                else:
                    desc = "Unknown loop detected"
            resp = line
            print("[!!] LOOP DETECTED")
            print(f"  Pattern: {desc}")
            print(f'  Response: "{truncate_preview(resp, 2000)}"')
            print("  Action: Stop this model. Try different model or approach.")
            log = {
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "type": typ,
                "detail": desc,
                "response_preview": truncate_preview(resp, 400),
            }

        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            with open(LOG_FILE, "a", encoding="utf-8") as lf:
                lf.write(json.dumps(log, ensure_ascii=False) + "\n")

            # Periodic cleanup
            global _cleanup_counter
            _cleanup_counter += 1
            if _cleanup_counter >= CLEANUP_INTERVAL:
                _cleanup_counter = 0
                try:
                    import sys as _sys

                    _sys.path.insert(0, str(CATALYST_DIR))
                    from packages.auto_capture.src.data_retention import cleanup_jsonl_file

                    cleanup_jsonl_file(LOG_FILE)
                except (ImportError, Exception) as e:
                    logger.debug(f"data_retention not available or cleanup failed: {e}")
        except Exception as e:
            logger.error(f"Failed to write loop detection log: {e}")
            print(f"Warning: failed to write log: {e}", file=sys.stderr)

        if json_output:
            if detected[0] == "exact_repeat":
                payload = {
                    "detected": True,
                    "type": "exact_repeat",
                    "count": detected[1],
                    "response_preview": truncate_preview(detected[2], 200),
                    "action": "stop_model",
                }
            else:
                payload = {
                    "detected": True,
                    "type": detected[0],
                    "details": str(detected[1]),
                    "response_preview": truncate_preview(line, 200),
                    "action": "stop_model",
                }
            print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
