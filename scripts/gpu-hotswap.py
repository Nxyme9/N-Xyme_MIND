#!/usr/bin/env python3
"""
GPU Hot-Swap -- Model hot-swap manager for RTX 3080 Ti.

Manages model loading/unloading to stay within VRAM budget.
Evicts low-priority models when high-priority models need space.

Usage:
    python scripts/gpu-hotswap.py load <model>        # Load model (evict if needed)
    python scripts/gpu-hotswap.py unload <model>      # Unload model
    python scripts/gpu-hotswap.py swap <from> <to>     # Atomic swap
    python scripts/gpu-hotswap.py evict <model>        # Force eviction
    python scripts/gpu-hotswap.py plan <model>         # Show eviction plan (dry run)
    python scripts/gpu-hotswap.py status               # Show loaded models
"""

import argparse
import logging
import os
import subprocess
import sys
import time
from typing import Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# -- Configuration -----------------------------------------------------

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

# VRAM budget
VRAM_TOTAL_GB = 12.0
VRAM_RESERVED_GB = 2.0
VRAM_MAX_GB = VRAM_TOTAL_GB - VRAM_RESERVED_GB  # 10.2GB

# Model registry with priorities (lower number = higher priority, harder to evict)
MODEL_REGISTRY = {
    # Resident models (never evict)
    "llama3.2:latest": {"size_gb": 2.0, "priority": 0, "type": "resident", "purpose": "Fast tasks"},
    "llama3.2:3b": {"size_gb": 2.0, "priority": 0, "type": "resident", "purpose": "Fast tasks"},
    "llama3.2:3b-instruct-q4_K_M": {
        "size_gb": 2.0,
        "priority": 0,
        "type": "resident",
        "purpose": "Fast tasks",
    },
    "qwen2.5-coder:7b": {
        "size_gb": 4.7,
        "priority": 0,
        "type": "resident",
        "purpose": "Code tasks",
    },
    "nomic-embed-text:latest": {
        "size_gb": 0.2,
        "priority": 0,
        "type": "resident",
        "purpose": "Embeddings",
    },
    # Hot-swap models (evictable)
    "llava:7b": {"size_gb": 4.7, "priority": 5, "type": "hotswap", "purpose": "Vision"},
    "qwen3:8b": {"size_gb": 5.2, "priority": 5, "type": "hotswap", "purpose": "Advanced reasoning"},
    "llama3.1:8b": {"size_gb": 4.9, "priority": 4, "type": "hotswap", "purpose": "General chat"},
    "qwen2.5:7b": {"size_gb": 4.7, "priority": 4, "type": "hotswap", "purpose": "General chat"},
}

# Thermal limit
TEMP_CRITICAL = 85


# -- GPU Status --------------------------------------------------------


def get_gpu_status() -> Optional[Dict]:
    """Get current GPU VRAM usage."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        used_mb, total_mb, temp = result.stdout.strip().split(", ")
        used_gb = int(used_mb) / 1000
        total_gb = int(total_mb) / 1000
        return {
            "used_gb": used_gb,
            "total_gb": total_gb,
            "free_gb": total_gb - used_gb,
            "headroom_gb": VRAM_MAX_GB - used_gb,
            "temperature_c": int(temp),
        }
    except Exception as e:
        logger.error(f"GPU query failed: {e}")
        return None


def get_loaded_models() -> List[Dict]:
    """Get currently loaded Ollama models."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/ps", timeout=5)
        resp.raise_for_status()
        return resp.json().get("models", [])
    except Exception as e:
        logger.error(f"Failed to get loaded models: {e}")
        return []


# -- Model Operations --------------------------------------------------


def load_model(model_name: str, keep_alive: str = "-1") -> bool:
    """Load model into VRAM."""
    try:
        logger.info(f"Loading {model_name}...")
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model_name,
                "prompt": "ready",
                "stream": False,
                "keep_alive": keep_alive,
                "options": {"num_predict": 1},
            },
            timeout=300,
        )
        resp.raise_for_status()
        logger.info(f"  OK {model_name} loaded")
        return True
    except Exception as e:
        logger.error(f"  FAIL {model_name} load failed: {e}")
        return False


def unload_model(model_name: str) -> bool:
    """Unload model from VRAM."""
    try:
        logger.info(f"Unloading {model_name}...")
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model_name,
                "prompt": "ready",
                "stream": False,
                "keep_alive": "0",
                "options": {"num_predict": 1},
            },
            timeout=60,
        )
        resp.raise_for_status()
        logger.info(f"  OK {model_name} unloaded")
        return True
    except Exception as e:
        logger.error(f"  FAIL {model_name} unload failed: {e}")
        return False


# -- Eviction Logic ----------------------------------------------------


def get_model_info(model_name: str) -> Dict:
    """Get model info from registry or estimate."""
    if model_name in MODEL_REGISTRY:
        return MODEL_REGISTRY[model_name]
    # Unknown model -- estimate 5GB, medium priority
    return {"size_gb": 5.0, "priority": 3, "type": "unknown", "purpose": "Unknown"}


def plan_eviction(target_model: str) -> Tuple[bool, List[str], float]:
    """Plan eviction to make room for target model.

    Returns:
        (possible, models_to_evict, vram_freed_gb)
    """
    gpu = get_gpu_status()
    if not gpu:
        return False, [], 0

    target_info = get_model_info(target_model)
    target_size = target_info["size_gb"] * 1.2  # 20% buffer

    # Check if model fits at all
    if target_size > VRAM_MAX_GB:
        logger.error(f"{target_model} ({target_size:.1f}GB) exceeds VRAM budget ({VRAM_MAX_GB}GB)")
        return False, [], 0

    # Check if we have room already
    if gpu["headroom_gb"] >= target_size:
        return True, [], 0

    # Need to evict -- find evictable models sorted by priority (highest priority number first)
    loaded = get_loaded_models()
    loaded_names = [m["name"] for m in loaded]

    evictable = []
    for name in loaded_names:
        info = get_model_info(name)
        if info["type"] != "resident" and info["priority"] > 0:
            vram_mb = next((m.get("size_vram", 0) for m in loaded if m["name"] == name), 0)
            evictable.append(
                {
                    "name": name,
                    "priority": info["priority"],
                    "size_gb": vram_mb / 1e9 if vram_mb > 0 else info["size_gb"],
                }
            )

    # Sort by priority (evict lowest priority first)
    evictable.sort(key=lambda x: -x["priority"])

    # Check if target is evictable (can't evict what we're trying to load)
    evictable = [e for e in evictable if e["name"] != target_model]

    # Find minimum eviction set
    needed = target_size - gpu["headroom_gb"]
    freed = 0
    to_evict = []

    for model in evictable:
        if freed >= needed:
            break
        to_evict.append(model["name"])
        freed += model["size_gb"]

    if freed < needed:
        logger.warning(f"Cannot free enough VRAM: need {needed:.1f}GB, can free {freed:.1f}GB")
        return False, to_evict, freed

    return True, to_evict, freed


def load_with_eviction(target_model: str, keep_alive: str = "-1", dry_run: bool = False) -> bool:
    """Load model, evicting others if necessary."""
    possible, to_evict, freed = plan_eviction(target_model)

    if not possible:
        logger.error(f"Cannot load {target_model} -- insufficient VRAM")
        return False

    if to_evict:
        logger.info(f"Eviction plan for {target_model}:")
        for model in to_evict:
            info = get_model_info(model)
            logger.info(f"  - {model} ({info['size_gb']:.1f}GB, priority {info['priority']})")
        logger.info(f"  Will free ~{freed:.1f}GB")

        if dry_run:
            return True

        # Execute eviction
        for model in to_evict:
            unload_model(model)
            time.sleep(1)  # Let VRAM settle

    if dry_run:
        logger.info(f"Dry run: would load {target_model}")
        return True

    # Load target
    return load_model(target_model, keep_alive)


def swap_models(from_model: str, to_model: str) -> bool:
    """Atomic model swap: unload one, load another."""
    logger.info(f"Swapping: {from_model} -> {to_model}")

    # Check if from_model is actually loaded
    loaded = get_loaded_models()
    loaded_names = [m["name"] for m in loaded]

    if from_model not in loaded_names:
        logger.info(f"{from_model} not loaded -- skipping unload")
    else:
        if not unload_model(from_model):
            return False
        time.sleep(1)

    return load_model(to_model)


# -- Status Display ----------------------------------------------------


def show_status() -> None:
    """Show loaded models and VRAM usage."""
    gpu = get_gpu_status()
    loaded = get_loaded_models()

    print()
    print("=" * 60)
    print("GPU HOT-SWAP STATUS")
    print("=" * 60)
    print()

    if gpu:
        print(f"VRAM: {gpu['used_gb']:.1f}GB / {gpu['total_gb']:.1f}GB")
        print(f"Headroom: {gpu['headroom_gb']:.1f}GB (to 85% target)")
        print(f"Temperature: {gpu['temperature_c']}degC")
        print()

    print(f"Loaded Models ({len(loaded)}):")
    for m in loaded:
        vram_mb = m.get("size_vram", 0) / 1e6
        info = get_model_info(m["name"])
        model_type = info.get("type", "unknown")
        priority = info.get("priority", "?")

        expires = m.get("expires_at", "")
        if "0001-01-01" in expires:
            keep = "PINNED"
        elif expires:
            keep = f"TTL:{expires[:19]}"
        else:
            keep = "?"

        evictable = "EVICTABLE" if info.get("priority", 0) > 0 else "RESIDENT"
        print(f"  * {m['name']:30s} {vram_mb:6.0f}MB  [{keep}]  {evictable}")

    print()
    print("Model Registry:")
    for name, info in sorted(MODEL_REGISTRY.items(), key=lambda x: x[1]["priority"]):
        print(
            f"  [{info['type']:8s}] P{info['priority']} {name:30s} {info['size_gb']:.1f}GB  {info['purpose']}"
        )

    print("=" * 60)


# -- Main --------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="GPU Hot-Swap Manager")
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # load
    load_parser = subparsers.add_parser("load", help="Load model (evict if needed)")
    load_parser.add_argument("model", help="Model name")
    load_parser.add_argument("--keep-alive", default="-1", help="Keep alive duration (default: -1)")
    load_parser.add_argument("--dry-run", action="store_true", help="Show plan without executing")

    # unload
    unload_parser = subparsers.add_parser("unload", help="Unload model")
    unload_parser.add_argument("model", help="Model name")

    # swap
    swap_parser = subparsers.add_parser("swap", help="Atomic model swap")
    swap_parser.add_argument("from_model", help="Model to unload")
    swap_parser.add_argument("to_model", help="Model to load")

    # evict
    evict_parser = subparsers.add_parser("evict", help="Force eviction of model")
    evict_parser.add_argument("model", help="Model name")

    # plan
    plan_parser = subparsers.add_parser("plan", help="Show eviction plan (dry run)")
    plan_parser.add_argument("model", help="Target model")

    # status
    subparsers.add_parser("status", help="Show loaded models")

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if args.command == "load":
        success = load_with_eviction(args.model, args.keep_alive, args.dry_run)
        sys.exit(0 if success else 1)

    elif args.command == "unload":
        success = unload_model(args.model)
        sys.exit(0 if success else 1)

    elif args.command == "swap":
        success = swap_models(args.from_model, args.to_model)
        sys.exit(0 if success else 1)

    elif args.command == "evict":
        success = unload_model(args.model)
        sys.exit(0 if success else 1)

    elif args.command == "plan":
        possible, to_evict, freed = plan_eviction(args.model)
        print(f"\nEviction plan for {args.model}:")
        print(f"  Possible: {'YES' if possible else 'NO'}")
        if to_evict:
            print(f"  Models to evict:")
            for m in to_evict:
                info = get_model_info(m)
                print(f"    - {m} ({info['size_gb']:.1f}GB)")
            print(f"  VRAM freed: ~{freed:.1f}GB")
        elif possible:
            print(f"  No eviction needed -- sufficient headroom")
        else:
            print(f"  Cannot free enough VRAM -- no evictable models loaded")

    elif args.command == "status":
        show_status()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
