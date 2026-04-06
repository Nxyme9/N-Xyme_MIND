#!/usr/bin/env python3
"""
GPU Preload - Pre-load Ollama models to maximize RTX 3080 Ti utilization.

Loads resident models into VRAM on startup with keep_alive pinning.
Target: 85% VRAM (10.2GB) for instant inference readiness.

Usage:
    python scripts/gpu-preload.py              # Full preload
    python scripts/gpu-preload.py --status     # Show status only
    python scripts/gpu-preload.py --unload     # Unload all models
    python scripts/gpu-preload.py --fill       # Fill to 85% VRAM target
"""

import argparse
import logging
import subprocess
import sys
import time
import os
from typing import Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# -- Configuration -----------------------------------------------------

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

# VRAM budget (85% of 12GB = 10.2GB)
VRAM_TOTAL_GB = 12.0
VRAM_RESERVED_GB = 2.0  # OS + CUDA overhead
VRAM_MAX_PERCENT = 85.0
VRAM_MAX_GB = VRAM_TOTAL_GB - VRAM_RESERVED_GB  # 10.2GB

# Resident models (always loaded, pinned with keep_alive=-1)
RESIDENT_MODELS = [
    {"name": "llama3.2:latest", "size_gb": 2.0, "priority": "HIGH", "purpose": "Fast tasks"},
    {"name": "qwen2.5-coder:7b", "size_gb": 4.7, "priority": "HIGH", "purpose": "Code tasks"},
    {
        "name": "nomic-embed-text:latest",
        "size_gb": 0.2,
        "priority": "HIGH",
        "purpose": "Embeddings",
    },
]

# Hot-swap models (load if VRAM available, TTL-based keep_alive)
HOT_SWAP_MODELS = [
    {"name": "llava:7b", "size_gb": 4.7, "priority": "MEDIUM", "purpose": "Vision"},
    {"name": "qwen3:8b", "size_gb": 5.2, "priority": "MEDIUM", "purpose": "Advanced reasoning"},
]

# Thermal thresholds
TEMP_WARNING = 75
TEMP_CRITICAL = 85

# Power limits (watts)
POWER_ECO = 200
POWER_BALANCED = 300
POWER_PERFORMANCE = 350


# -- GPU Status --------------------------------------------------------


def get_gpu_status() -> Dict:
    """Get current GPU status via nvidia-smi."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.used,memory.total,temperature.gpu,utilization.gpu,"
                "power.draw,power.limit",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        parts = result.stdout.strip().split(", ")
        used_mb, total_mb = int(parts[0]), int(parts[1])
        temp_c = int(parts[2])
        util_percent = int(parts[3])
        power_draw = float(parts[4])
        power_limit = float(parts[5])

        used_gb = used_mb / 1000
        total_gb = total_mb / 1000

        return {
            "used_gb": used_gb,
            "total_gb": total_gb,
            "free_gb": total_gb - used_gb,
            "used_percent": (used_gb / total_gb) * 100,
            "temperature_c": temp_c,
            "utilization_percent": util_percent,
            "power_draw_w": power_draw,
            "power_limit_w": power_limit,
            "throttle_thermal": temp_c > TEMP_CRITICAL,
            "is_safe": (used_gb / total_gb) * 100 < VRAM_MAX_PERCENT and temp_c < TEMP_CRITICAL,
            "headroom_gb": VRAM_MAX_GB - used_gb,
        }
    except Exception as e:
        logger.error(f"Failed to get GPU status: {e}")
        return {
            "used_gb": 0.0,
            "total_gb": VRAM_TOTAL_GB,
            "free_gb": VRAM_TOTAL_GB,
            "used_percent": 0.0,
            "temperature_c": 0,
            "utilization_percent": 0,
            "power_draw_w": 0,
            "power_limit_w": 350,
            "throttle_thermal": False,
            "is_safe": True,
            "headroom_gb": VRAM_MAX_GB,
        }


def get_loaded_models() -> List[Dict]:
    """Get list of currently loaded Ollama models with VRAM usage."""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/ps", timeout=5)
        response.raise_for_status()
        data = response.json()
        return data.get("models", [])
    except Exception as e:
        logger.error(f"Failed to get loaded models: {e}")
        return []


def get_available_models() -> List[str]:
    """Get list of available (installed) Ollama models."""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        response.raise_for_status()
        data = response.json()
        return [m["name"] for m in data.get("models", [])]
    except Exception as e:
        logger.error(f"Failed to get available models: {e}")
        return []


# -- Power Management --------------------------------------------------


def set_power_limit(watts: int) -> bool:
    """Set GPU power limit via nvidia-smi."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "-pl", str(watts)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            logger.info(f"Power limit set to {watts}W")
            return True
        else:
            logger.warning(f"Failed to set power limit: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Power limit error: {e}")
        return False


def auto_power_profile(gpu: Dict) -> int:
    """Determine optimal power profile based on GPU status."""
    temp = gpu["temperature_c"]

    if temp > TEMP_CRITICAL:
        return POWER_ECO
    elif temp > TEMP_WARNING:
        return POWER_BALANCED
    else:
        return POWER_BALANCED  # 300W is safe default


# -- Model Loading -----------------------------------------------------


def load_model(model_name: str, keep_alive: str = "-1") -> bool:
    """Load model into Ollama with keep_alive control.

    keep_alive values:
        -1      = Pin forever (resident models)
        "30m"   = Keep for 30 minutes (hot-swap)
        0       = Unload immediately after response
    """
    try:
        logger.info(f"Loading {model_name} (keep_alive={keep_alive})...")

        # Convert string "-1" to numeric -1, keep duration strings as-is
        if keep_alive == "-1":
            keep_alive_value = -1
        elif keep_alive == "0":
            keep_alive_value = 0
        else:
            keep_alive_value = keep_alive

        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model_name,
                "prompt": "ready",
                "stream": False,
                "keep_alive": keep_alive_value,
                "options": {"num_predict": 1},
            },
            timeout=300,  # 5 minutes max for large models
        )
        response.raise_for_status()

        logger.info(f"  OK {model_name} loaded")
        return True

    except requests.exceptions.Timeout:
        logger.error(f"  FAIL {model_name} timed out (5 min)")
        return False
    except Exception as e:
        logger.error(f"  FAIL {model_name} failed: {e}")
        return False
    except Exception as e:
        logger.error(f"  FAIL {model_name} failed: {e}")
        return False


def unload_model(model_name: str) -> bool:
    """Unload model from Ollama to free VRAM."""
    try:
        logger.info(f"Unloading {model_name}...")

        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model_name,
                "prompt": "ready",
                "stream": False,
                "keep_alive": "0",  # Immediate unload
                "options": {"num_predict": 1},
            },
            timeout=60,
        )
        response.raise_for_status()

        logger.info(f"  OK {model_name} unloaded")
        return True

    except Exception as e:
        logger.error(f"  FAIL {model_name} unload failed: {e}")
        return False


# -- Preload Sequences -------------------------------------------------


def preload_resident() -> Tuple[int, float]:
    """Pre-load resident models (always in VRAM). Returns (count, vram_used_gb)."""
    loaded = 0
    vram_used = 0.0
    gpu = get_gpu_status()

    for model in RESIDENT_MODELS:
        # Check VRAM budget with 20% buffer for actual size vs estimate
        estimated_actual = model["size_gb"] * 1.2
        if gpu["headroom_gb"] < estimated_actual:
            logger.warning(
                f"Insufficient VRAM for {model['name']} "
                f"({estimated_actual:.1f}GB estimated, {gpu['headroom_gb']:.1f}GB headroom)"
            )
            continue

        # Check thermal safety
        if gpu["temperature_c"] > TEMP_CRITICAL:
            logger.warning(f"GPU too hot ({gpu['temperature_c']}degC) -- pausing preload")
            time.sleep(30)
            gpu = get_gpu_status()
            continue

        # Load model with permanent pin
        success = load_model(model["name"], keep_alive="-1")
        if success:
            loaded += 1
            vram_used += model["size_gb"]

        # Update GPU status
        gpu = get_gpu_status()

    return loaded, vram_used


def preload_hot_swap() -> Tuple[int, float]:
    """Pre-load hot-swap models (if VRAM available). Returns (count, vram_used_gb)."""
    loaded = 0
    vram_used = 0.0
    gpu = get_gpu_status()

    for model in HOT_SWAP_MODELS:
        # Check VRAM budget with 20% buffer
        estimated_actual = model["size_gb"] * 1.2
        if gpu["headroom_gb"] < estimated_actual:
            logger.info(
                f"Skipping {model['name']} -- "
                f"insufficient headroom ({gpu['headroom_gb']:.1f}GB, need {estimated_actual:.1f}GB)"
            )
            continue

        # Check thermal safety
        if gpu["temperature_c"] > TEMP_WARNING:
            logger.info(
                f"GPU warm ({gpu['temperature_c']}degC) -- skipping hot-swap {model['name']}"
            )
            continue

        # Load model with 30 min keep-alive
        success = load_model(model["name"], keep_alive="30m")
        if success:
            loaded += 1
            vram_used += model["size_gb"]

        # Update GPU status
        gpu = get_gpu_status()

    return loaded, vram_used


def fill_to_target() -> None:
    """Fill VRAM to 85% target by loading models in priority order."""
    gpu = get_gpu_status()
    target_gb = VRAM_MAX_GB

    print(f"\nTarget: {target_gb:.1f}GB ({VRAM_MAX_PERCENT}% of {VRAM_TOTAL_GB}GB)")
    print(f"Current: {gpu['used_gb']:.1f}GB ({gpu['used_percent']:.0f}%)")
    print(f"Headroom: {gpu['headroom_gb']:.1f}GB\n")

    if gpu["headroom_gb"] <= 0:
        print("Already at or above target VRAM usage.")
        return

    # Get all available models sorted by size (smallest first for max packing)
    available = get_available_models()
    loaded_names = {m["name"] for m in get_loaded_models()}

    # Combine resident + hotswap, skip already loaded
    all_models = []
    for m in RESIDENT_MODELS + HOT_SWAP_MODELS:
        if m["name"] not in loaded_names and m["name"] in available:
            all_models.append(m)

    # Sort by size (load smallest first to maximize model count)
    all_models.sort(key=lambda x: x["size_gb"])

    for model in all_models:
        gpu = get_gpu_status()
        estimated_actual = model["size_gb"] * 1.2

        if gpu["headroom_gb"] < estimated_actual:
            logger.info(f"Skipping {model['name']} -- would exceed target")
            continue

        if gpu["temperature_c"] > TEMP_CRITICAL:
            logger.warning("GPU too hot -- stopping fill")
            break

        keep_alive = "-1" if model["priority"] == "HIGH" else "30m"
        success = load_model(model["name"], keep_alive=keep_alive)
        if success:
            print(f"  OK Loaded {model['name']} ({model['size_gb']}GB)")

    # Final status
    gpu = get_gpu_status()
    print(
        f"\nFinal VRAM: {gpu['used_gb']:.1f}GB / {gpu['total_gb']:.1f}GB ({gpu['used_percent']:.0f}%)"
    )


def unload_all() -> int:
    """Unload all models to free VRAM."""
    unloaded = 0
    loaded = get_loaded_models()

    for model in loaded:
        success = unload_model(model["name"])
        if success:
            unloaded += 1

    return unloaded


# -- Status Display ----------------------------------------------------


def show_status() -> None:
    """Show current GPU and model status."""
    gpu = get_gpu_status()
    loaded = get_loaded_models()

    # GPU bar
    bar_len = 30
    filled = int(gpu["used_percent"] / 100 * bar_len)
    bar = "#" * filled + "." * (bar_len - filled)

    print()
    print("=" * 60)
    print("GPU STATUS -- RTX 3080 Ti (12GB VRAM)")
    print("=" * 60)
    print()
    print(f"VRAM: {bar} {gpu['used_percent']:.1f}%")
    print(f"      {gpu['used_gb']:.1f}GB / {gpu['total_gb']:.1f}GB ({gpu['free_gb']:.1f}GB free)")
    print(f"      Headroom to 85%: {gpu['headroom_gb']:.1f}GB")
    print()
    print(f"Temperature:  {gpu['temperature_c']}degC", end="")
    if gpu["temperature_c"] > TEMP_CRITICAL:
        print(" WARN CRITICAL")
    elif gpu["temperature_c"] > TEMP_WARNING:
        print(" WARN HOT")
    else:
        print(" OK Normal")

    print(f"Utilization:  {gpu['utilization_percent']}%")
    print(f"Power:        {gpu['power_draw_w']:.0f}W / {gpu['power_limit_w']:.0f}W")
    print(f"Throttling:   {'YES' if gpu['throttle_thermal'] else 'No'}")
    print(f"Safe:         {'OK Yes' if gpu['is_safe'] else 'WARN NO'}")
    print()
    print(f"Loaded Models ({len(loaded)}):")
    total_vram = 0
    for m in loaded:
        vram_mb = m.get("size_vram", 0) / 1e6
        total_vram += vram_mb / 1000
        expires = m.get("expires_at", "pinned")
        if expires == "0001-01-01T00:00:00Z":
            keep = "pinned"
        else:
            keep = f"ttl:{expires[:19]}"
        print(f"  * {m['name']:30s} {vram_mb:6.0f}MB  [{keep}]")
    print(f"  {'Total VRAM:':30s} {total_vram:6.1f}GB")
    print()
    print(
        f"VRAM Budget: {VRAM_MAX_PERCENT}% = {VRAM_MAX_GB:.1f}GB max (reserved: {VRAM_RESERVED_GB}GB)"
    )
    print("=" * 60)


# -- Main --------------------------------------------------------------


def main():
    """Main preload sequence."""
    parser = argparse.ArgumentParser(description="GPU Preload for RTX 3080 Ti")
    parser.add_argument("--status", action="store_true", help="Show status only")
    parser.add_argument("--unload", action="store_true", help="Unload all models")
    parser.add_argument("--fill", action="store_true", help="Fill VRAM to 85% target")
    parser.add_argument("--quiet", action="store_true", help="Minimal output")
    args = parser.parse_args()

    # Configure logging
    level = logging.WARNING if args.quiet else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # Status only
    if args.status:
        show_status()
        return

    # Unload all
    if args.unload:
        print("Unloading all models...")
        count = unload_all()
        print(f"Unloaded {count} models")
        show_status()
        return

    # Fill to target
    if args.fill:
        fill_to_target()
        return

    # Full preload
    print()
    print("=" * 60)
    print("GPU PRELOAD -- RTX 3080 Ti Maximization")
    print("=" * 60)
    print()

    # Check Ollama connectivity
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        response.raise_for_status()
        logger.info("OK Ollama connected")
    except Exception as e:
        logger.error(f"FAIL Ollama not reachable: {e}")
        logger.error("  Start Ollama first: ollama serve")
        sys.exit(1)

    # Initial GPU status
    gpu = get_gpu_status()
    logger.info(
        f"GPU: {gpu['used_gb']:.1f}GB used, {gpu['headroom_gb']:.1f}GB headroom, {gpu['temperature_c']}degC"
    )

    # Set power profile
    power = auto_power_profile(gpu)
    set_power_limit(power)

    # Phase 1: Resident models (always loaded)
    print()
    logger.info("[Phase 1] Loading RESIDENT models (pinned)...")
    resident_count, resident_vram = preload_resident()

    # Phase 2: Hot-swap models (if VRAM available)
    print()
    logger.info("[Phase 2] Loading HOT-SWAP models (30min TTL)...")
    hotswap_count, hotswap_vram = preload_hot_swap()

    # Final status
    print()
    gpu = get_gpu_status()
    print("=" * 60)
    print("PRELOAD COMPLETE")
    print(f"  Resident:  {resident_count}/{len(RESIDENT_MODELS)} loaded ({resident_vram:.1f}GB)")
    print(f"  Hot-swap:  {hotswap_count}/{len(HOT_SWAP_MODELS)} loaded ({hotswap_vram:.1f}GB)")
    print(
        f"  VRAM:      {gpu['used_gb']:.1f}GB / {gpu['total_gb']:.1f}GB ({gpu['used_percent']:.0f}%)"
    )
    print(f"  Headroom:  {gpu['headroom_gb']:.1f}GB to 85% target")
    print(f"  Temp:      {gpu['temperature_c']}degC")
    print(f"  Power:     {power}W")
    print("=" * 60)


if __name__ == "__main__":
    main()
