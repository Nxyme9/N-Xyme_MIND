#!/usr/bin/env python3
"""
Model Heartbeat — Fetcher
Fetches model lists from OpenRouter, OpenCode Zen, and Kilo.ai.
Normalizes each to a common schema and saves as JSON snapshots.

Usage:
    python fetch_models.py [--output-dir data]
"""

import json
import os
import sys
import time
import argparse
from datetime import datetime, timezone
from typing import Any
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# ── Provider endpoints ──────────────────────────────────────────────────────

ENDPOINTS = {
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/models",
        "headers": {"Accept": "application/json", "User-Agent": "ModelHeartbeat/1.0"},
    },
    "opencodezen": {
        "url": "https://opencode.ai/zen/v1/models",
        "headers": {"Accept": "application/json", "User-Agent": "ModelHeartbeat/1.0"},
    },
    "kiloai": {
        "url": "https://api.kilo.ai/api/gateway/models",
        "headers": {"Accept": "application/json", "User-Agent": "ModelHeartbeat/1.0"},
    },
}

# ── Normalized schema field mapping ─────────────────────────────────────────

def normalize_openrouter(raw: dict) -> dict:
    """Normalize an OpenRouter model dict to common schema."""
    return {
        "provider": "openrouter",
        "model_id": raw.get("id", ""),
        "name": raw.get("name") or raw.get("id", ""),
        "created": raw.get("created"),
        "is_free": None,  # OpenRouter has per-route pricing, no simple boolean
        "expiration_date": raw.get("expiration_date"),  # null = active, str = deprecated
        "pricing": raw.get("pricing"),
        "architecture": _safe_str(raw.get("architecture", {}), " None"),
        "owner": raw.get("top_provider", {}).get("id") if isinstance(raw.get("top_provider"), dict) else None,
    }


def normalize_opencodezen(raw: dict) -> dict:
    """Normalize an OpenCode Zen model dict to common schema."""
    return {
        "provider": "opencodezen",
        "model_id": raw.get("id", ""),
        "name": raw.get("id", ""),
        "created": raw.get("created"),
        "is_free": None,  # OpenCode Zen doesn't expose pricing in list endpoint
        "expiration_date": None,
        "pricing": None,
        "architecture": None,
        "owner": raw.get("owned_by"),
    }


def normalize_kiloai(raw: dict) -> dict:
    """Normalize a Kilo.ai model dict to common schema."""
    return {
        "provider": "kiloai",
        "model_id": raw.get("id", ""),
        "name": raw.get("name") or raw.get("id", ""),
        "created": None,  # Kilo.ai doesn't expose created timestamp in list
        "is_free": raw.get("isFree", None),
        "expiration_date": None,
        "pricing": raw.get("pricing"),
        "architecture": _safe_str(raw.get("architecture"), None),
        "owner": _safe_str(raw.get("opencode", {}).get("ai_sdk_provider")),
    }


NORMALIZERS = {
    "openrouter": normalize_openrouter,
    "opencodezen": normalize_opencodezen,
    "kiloai": normalize_kiloai,
}


def _safe_str(val: Any, default=None) -> str | None:
    """Convert value to string safely, returning default on failure."""
    if val is None:
        return default
    try:
        s = str(val)
        return s if s and s != "None" else default
    except Exception:
        return default


# ── Fetcher ─────────────────────────────────────────────────────────────────

def fetch_provider(name: str, config: dict) -> list[dict]:
    """Fetch models from a single provider. Returns list of normalized model dicts."""
    url = config["url"]
    headers = config.get("headers", {})

    req = Request(url, headers=headers, method="GET")
    try:
        with urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode())
    except HTTPError as e:
        print(f"  [WARN] HTTP {e.code} fetching {name} ({url}): {e.reason}", file=sys.stderr)
        return []
    except URLError as e:
        print(f"  [WARN] Connection error fetching {name} ({url}): {e.reason}", file=sys.stderr)
        return []
    except json.JSONDecodeError as e:
        print(f"  [WARN] Invalid JSON from {name}: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"  [WARN] Unexpected error fetching {name}: {e}", file=sys.stderr)
        return []

    # Extract the model list — API responses use different wrappers
    raw_models = []
    if isinstance(body, dict):
        # OpenAI-style: {"data": [...]} or {"object": "list", "data": [...]}
        if "data" in body and isinstance(body["data"], list):
            raw_models = body["data"]
        # Some APIs return models directly under a key
        elif "models" in body and isinstance(body["models"], list):
            raw_models = body["models"]
    elif isinstance(body, list):
        raw_models = body

    if not raw_models:
        print(f"  [WARN] No models found in {name} response", file=sys.stderr)
        return []

    # Normalize
    normalizer = NORMALIZERS.get(name)
    if normalizer is None:
        print(f"  [WARN] No normalizer registered for {name}", file=sys.stderr)
        return []

    normalized = [normalizer(m) for m in raw_models]
    # Deduplicate by model_id
    seen: set[str] = set()
    unique: list[dict] = []
    for m in normalized:
        mid = m["model_id"]
        if mid and mid not in seen:
            seen.add(mid)
            unique.append(m)

    print(f"  OK  {name}: {len(unique)} models (from {len(raw_models)} raw entries)")
    return unique


# ── Snapshot helpers ────────────────────────────────────────────────────────

def build_snapshot(models_by_provider: dict[str, list[dict]]) -> dict:
    """Build a snapshot dict from provider model lists."""
    all_models: list[dict] = []
    for provider_name, models in sorted(models_by_provider.items()):
        all_models.extend(models)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {name: len(models) for name, models in sorted(models_by_provider.items())},
        "total_models": len(all_models),
        "models": all_models,
    }


def save_snapshot(snapshot: dict, output_dir: str) -> str:
    """Save snapshot to output_dir. Returns the file path."""
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, "snapshot_latest.json")
    with open(filepath, "w") as f:
        json.dump(snapshot, f, indent=2, default=str)
    print(f"\n  Snapshot saved: {filepath} ({snapshot['total_models']} models)")
    return filepath


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fetch model lists from all providers")
    parser.add_argument("--output-dir", default="data", help="Output directory for snapshots")
    args = parser.parse_args()

    print("── Model Heartbeat: Fetch ──────────────────────────────────────")
    start = time.time()

    models_by_provider: dict[str, list[dict]] = {}
    for name, config in ENDPOINTS.items():
        print(f"\n  Fetching {name} ...")
        models_by_provider[name] = fetch_provider(name, config)

    snapshot = build_snapshot(models_by_provider)
    path = save_snapshot(snapshot, args.output_dir)

    elapsed = time.time() - start
    print(f"\n  Done in {elapsed:.1f}s. Total models: {snapshot['total_models']}")
    return 0 if snapshot["total_models"] > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
