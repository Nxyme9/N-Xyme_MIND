#!/usr/bin/env python3
"""N-Xyme Rate Limit Monitor - Detect API rate limits and service health."""

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

CATALYST_DIR = Path(os.environ.get("CATALYST_DIR", Path(__file__).resolve().parent.parent))
RATE_LIMIT_LOG = CATALYST_DIR / "data" / "rate-limit-log.jsonl"

# Ensure data dir exists
(CATALYST_DIR / "data").mkdir(parents=True, exist_ok=True)

# API Configuration
ZEN_API_URL = "https://opencode.ai/zen/v1"
ZEN_API_KEY = os.getenv("ZEN_API_KEY", "")

# Import centralized configuration
try:
    from jarvis.config.graphiti_config import OLLAMA_URL, TOOLBRIDGE_URL
except ImportError:
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
    TOOLBRIDGE_URL = os.getenv("TOOLBRIDGE_URL", "http://localhost:3100")

# Deduplication: track last logged status
_last_logged_status = None
_cleanup_counter = 0
CLEANUP_INTERVAL = 60  # Run cleanup every 60 checks


def check_zen_api():
    """Test OpenCode Zen API with minimal request."""
    try:
        headers = {
            "Authorization": f"Bearer {ZEN_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "mimo-v2-flash-free",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 5,
        }
        r = requests.post(
            f"{ZEN_API_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=10,
        )

        if r.status_code == 200:
            return {"status": "ok", "code": 200}
        elif r.status_code == 429:
            return {"status": "rate_limited", "code": 429, "detail": r.text[:200]}
        elif "FreeUsageLimitError" in r.text:
            return {
                "status": "rate_limited",
                "code": r.status_code,
                "detail": "FreeUsageLimitError",
            }
        else:
            return {"status": "error", "code": r.status_code, "detail": r.text[:200]}
    except requests.exceptions.ConnectionError:
        return {"status": "unreachable", "detail": "Connection refused"}
    except requests.exceptions.Timeout:
        return {"status": "timeout", "detail": "Request timed out"}
    except Exception as e:
        return {"status": "error", "detail": str(e)[:200]}


def check_ollama():
    """Check Ollama health endpoint."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if r.status_code == 200:
            models = r.json().get("models", [])
            return {
                "status": "ok",
                "model_count": len(models),
                "models": [m["name"] for m in models],
            }
        return {"status": "error", "code": r.status_code}
    except requests.exceptions.ConnectionError:
        return {"status": "unreachable", "detail": "Connection refused"}
    except requests.exceptions.Timeout:
        return {"status": "timeout", "detail": "Request timed out"}
    except Exception as e:
        return {"status": "error", "detail": str(e)[:200]}


def check_toolbridge():
    """Check ToolBridge health endpoint."""
    try:
        r = requests.get(f"{TOOLBRIDGE_URL}/v1/models", timeout=5)
        if r.status_code == 200:
            models = r.json().get("data", [])
            return {"status": "ok", "model_count": len(models)}
        return {"status": "error", "code": r.status_code}
    except requests.exceptions.ConnectionError:
        return {"status": "unreachable", "detail": "Connection refused"}
    except requests.exceptions.Timeout:
        return {"status": "timeout", "detail": "Request timed out"}
    except Exception as e:
        return {"status": "error", "detail": str(e)[:200]}


def _status_key(result):
    """Extract status key for deduplication (ignores timestamp)."""
    return (
        result.get("zen_api", {}).get("status"),
        result.get("ollama", {}).get("status"),
        result.get("toolbridge", {}).get("status"),
    )


def log_check(result):
    """Log check result to JSONL file with deduplication."""
    global _last_logged_status, _cleanup_counter

    try:
        current_status = _status_key(result)

        # Dedup: only log if status changed or if all services are down
        if current_status == _last_logged_status:
            # Skip logging duplicate status
            return

        _last_logged_status = current_status

        RATE_LIMIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(RATE_LIMIT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(result) + "\n")

        # Periodic cleanup
        _cleanup_counter += 1
        if _cleanup_counter >= CLEANUP_INTERVAL:
            _cleanup_counter = 0
            try:
                import sys as _sys

                _sys.path.insert(0, str(CATALYST_DIR))
                from packages.auto_capture.src.data_retention import cleanup_jsonl_file

                cleanup_jsonl_file(RATE_LIMIT_LOG)
            except (ImportError, Exception) as e:
                logger.debug(f"data_retention not available or cleanup failed: {e}")
    except Exception as e:
        logger.error(f"Failed to log check result: {e}")


def run_check():
    """Run all health checks."""
    timestamp = datetime.now().isoformat()
    zen = check_zen_api()
    ollama = check_ollama()
    toolbridge = check_toolbridge()

    result = {
        "timestamp": timestamp,
        "zen_api": zen,
        "ollama": ollama,
        "toolbridge": toolbridge,
    }

    log_check(result)
    return result


def print_notification(result):
    """Print clear notification for rate limits and issues."""
    zen = result["zen_api"]
    ollama = result["ollama"]
    toolbridge = result["toolbridge"]

    print("=" * 60)
    print("  N-XYME RATE LIMIT MONITOR")
    print(f"  {result['timestamp']}")
    print("=" * 60)

    # Zen API status
    if zen["status"] == "ok":
        print(f"\n  [OK] Zen API: OK")
    elif zen["status"] == "rate_limited":
        print(f"\n  [!!] Zen API: RATE LIMITED")
        print(f"       Detail: {zen.get('detail', 'Unknown')}")
        print(f"       ACTION: Cycle VPN connection and retry")
        print(f"       TIP: Use a different VPN server location")
    elif zen["status"] == "unreachable":
        print(f"\n  [!] Zen API: UNREACHABLE")
        print(f"       Check network connection")
    else:
        print(f"\n  [!] Zen API: ERROR ({zen.get('code', '?')})")
        print(f"       {zen.get('detail', 'Unknown error')}")

    # Ollama status
    if ollama["status"] == "ok":
        print(f"\n  [OK] Ollama: OK ({ollama.get('model_count', 0)} models)")
    elif ollama["status"] == "unreachable":
        print(f"\n  [!] Ollama: UNREACHABLE")
        print(f"       ACTION: Run 'ollama serve' or check service")
    else:
        print(f"\n  [!] Ollama: ERROR")
        print(f"       {ollama.get('detail', 'Unknown error')}")

    # ToolBridge status
    if toolbridge["status"] == "ok":
        print(f"\n  [OK] ToolBridge: OK")
    elif toolbridge["status"] == "unreachable":
        print(f"\n  [i] ToolBridge: UNREACHABLE (optional)")
    else:
        print(f"\n  [!] ToolBridge: ERROR")
        print(f"       {toolbridge.get('detail', 'Unknown error')}")

    print("\n" + "=" * 60)


def main():
    once = "once" in sys.argv
    json_output = "--json" in sys.argv

    if once:
        result = run_check()
        if json_output:
            print(json.dumps(result, indent=2))
        else:
            print_notification(result)
        return

    # Continuous monitoring loop
    print("[Rate Limit Monitor] Starting continuous monitoring (60s interval)")
    print("[Rate Limit Monitor] Press Ctrl+C to stop\n")

    try:
        while True:
            result = run_check()
            if json_output:
                print(json.dumps(result, indent=2))
            else:
                print_notification(result)
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n[Rate Limit Monitor] Stopped")


if __name__ == "__main__":
    main()
