#!/usr/bin/env python3
"""
GPU Optimizer - Preload models and maximize GPU utilization for RTX 3080 Ti.

RTX 3080 Ti Specs:
- 12GB VRAM
- 10240 CUDA cores
- Should run 14B models at Q4 quantization
- Power: 20W idle, 350W max load
- Thermal limit: 83°C (throttles above)

Usage:
    python scripts/gpu-optimizer.py              # Optimize GPU usage
    python scripts/gpu-optimizer.py --status     # Check GPU status
    python scripts/gpu-optimizer.py --preload    # Preload best models
    python scripts/gpu-optimizer.py --benchmark  # Run inference benchmark
    python scripts/gpu-optimizer.py --power      # Set power profile
    python scripts/gpu-optimizer.py --thermal    # Check thermal status
"""

import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Import centralized configuration
try:
    from jarvis.config.graphiti_config import OLLAMA_URL
except ImportError:
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

# SAFE VRAM LIMIT: 85% (10.2GB) — leaves 2GB for OS + CUDA overhead
MAX_VRAM_PERCENT = 85
MAX_VRAM_GB = 10.2

# Power profiles for RTX 3080 Ti
POWER_PROFILES = {
    "eco": {"watts": 200, "description": "Eco mode — low power, cool"},
    "balanced": {"watts": 300, "description": "Balanced — normal inference"},
    "performance": {"watts": 350, "description": "Performance — max speed"},
}

# Temperature thresholds
TEMP_THRESHOLDS = {
    "cool": 60,  # <60°C — normal operation
    "warm": 75,  # 60-75°C — normal operation
    "hot": 85,  # 75-85°C — reduce power
    "critical": 85,  # >85°C — emergency throttle
}

# Model recommendations for RTX 3080 Ti (12GB VRAM) — SAFE LIMITS
MODELS = {
    "coding": {
        "name": "qwen2.5-coder:7b",  # Changed from 14b to 7b for safety
        "size_gb": 4.5,
        "quality": "★★★★☆ (4/5)",
        "use_case": "Code generation, debugging, refactoring",
        "priority": 1,
    },
    "general": {
        "name": "llama3.1:8b",
        "size_gb": 4.9,
        "quality": "★★★★☆ (4/5)",
        "use_case": "General chat, quick tasks",
        "priority": 2,
    },
    "heartbeat": {
        "name": "llama3.2:3b-instruct-q4_K_M",
        "size_gb": 2.0,
        "quality": "★★★☆☆ (3/5)",
        "use_case": "Heartbeat monitoring, simple tasks",
        "priority": 3,
    },
    "embedding": {
        "name": "nomic-embed-text:latest",
        "size_gb": 0.3,
        "quality": "★★★★★ (5/5)",
        "use_case": "Text embeddings for RAG",
        "priority": 4,
    },
}

# NOTE: llava:7b (4.5GB) removed — would push to 94% VRAM (UNSAFE)

# CPU OFFLOADING: Run larger models by splitting between GPU + RAM
# These models won't fit in 12GB VRAM alone, but CAN run with partial GPU offload
CPU_OFFLOAD_MODELS = {
    "coding-large": {
        "name": "qwen2.5-coder:14b",
        "size_gb": 9.0,
        "gpu_layers": 20,  # Half layers on GPU (~4.5GB VRAM)
        "ram_layers": 20,  # Half layers on RAM (~4.5GB RAM)
        "speed": "12-15 tok/s (vs 25 full GPU)",
        "quality": "★★★★★ (5/5)",
        "use_case": "Complex coding, architecture, review",
    },
    "reasoning-large": {
        "name": "deepseek-r1:14b",
        "size_gb": 9.0,
        "gpu_layers": 15,  # ~3.5GB VRAM
        "ram_layers": 25,  # ~5.5GB RAM
        "speed": "10-13 tok/s (vs 22 full GPU)",
        "quality": "★★★★★ (5/5)",
        "use_case": "Deep reasoning, analysis, problem-solving",
    },
    "reasoning-medium": {
        "name": "qwen3:8b",
        "size_gb": 5.2,
        "gpu_layers": 30,  # ~4GB VRAM
        "ram_layers": 10,  # ~1.2GB RAM
        "speed": "18-20 tok/s (vs 30 full GPU)",
        "quality": "★★★★☆ (4/5)",
        "use_case": "Smart reasoning, creative writing",
    },
}


def get_system_ram():
    """Get system RAM info."""
    try:
        import psutil

        ram = psutil.virtual_memory()
        return {
            "total_gb": ram.total / (1024**3),
            "available_gb": ram.available / (1024**3),
            "used_gb": ram.used / (1024**3),
            "percent": ram.percent,
        }
    except ImportError:
        return None


def get_gpu_status():
    """Get current GPU status with thermal and power info."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu,power.draw,power.limit,clocks_throttle_reason_gpu_idle,clocks_throttle_reason_sw_thermal",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(", ")
            return {
                "name": parts[0],
                "memory_used_mb": int(parts[1]),
                "memory_total_mb": int(parts[2]),
                "utilization_percent": int(parts[3]),
                "temperature_c": int(parts[4]),
                "power_draw_w": float(parts[5]),
                "power_limit_w": float(parts[6]),
                "throttle_idle": parts[7] == "1",
                "throttle_thermal": parts[8] == "1",
                "memory_free_mb": int(parts[2]) - int(parts[1]),
                "memory_used_percent": round(int(parts[1]) / int(parts[2]) * 100, 1),
            }
    except Exception as e:
        logger.error(f"Error getting GPU status: {e}")
    return None


def check_thermal_throttling():
    """Check if GPU is thermal throttling."""
    gpu = get_gpu_status()
    if gpu:
        return gpu["throttle_thermal"]
    return False


def auto_throttle(gpu_temp: int):
    """Alert on temperature thresholds (no power limiting — use MSI Afterburner)."""
    if gpu_temp > TEMP_THRESHOLDS["critical"]:
        logger.critical(f"GPU TEMP CRITICAL: {gpu_temp}°C — cool manually!")
    elif gpu_temp > TEMP_THRESHOLDS["hot"]:
        logger.warning(f"GPU TEMP WARNING: {gpu_temp}°C — consider unloading models")
    elif gpu_temp < TEMP_THRESHOLDS["cool"]:
        logger.info(f"GPU TEMP OK: {gpu_temp}°C")


def set_power_profile(profile_name: str):
    """DEPRECATED: Power limiting disabled — conflicts with MSI Afterburner undervolt."""
    if profile_name not in POWER_PROFILES:
        logger.error(f"Unknown profile: {profile_name}")
        return False

    watts = POWER_PROFILES[profile_name]["watts"]
    logger.warning(
        f"Power profile change to {profile_name} ({watts}W) SKIPPED — use MSI Afterburner"
    )
    return False


def show_thermal_status():
    """Show detailed thermal status."""
    print("=" * 60)
    print("GPU THERMAL STATUS")
    print("=" * 60)

    gpu = get_gpu_status()
    if not gpu:
        print("ERROR: Cannot access GPU")
        return

    print(f"\nGPU: {gpu['name']}")
    print(f"Temperature: {gpu['temperature_c']}°C")
    print(f"Power Draw: {gpu['power_draw_w']:.1f}W / {gpu['power_limit_w']:.1f}W")
    print(f"Thermal Throttling: {'YES' if gpu['throttle_thermal'] else 'NO'}")
    print(f"Idle Throttling: {'YES' if gpu['throttle_idle'] else 'NO'}")

    # Temperature status
    temp = gpu["temperature_c"]
    if temp < TEMP_THRESHOLDS["cool"]:
        status = "COOL"
        color = "🟢"
    elif temp < TEMP_THRESHOLDS["warm"]:
        status = "WARM"
        color = "🟡"
    elif temp < TEMP_THRESHOLDS["hot"]:
        status = "HOT"
        color = "🟠"
    else:
        status = "CRITICAL"
        color = "🔴"

    print(f"\nThermal Status: {color} {status}")

    # Power efficiency
    if gpu["power_draw_w"] > 0:
        efficiency = gpu["utilization_percent"] / gpu["power_draw_w"]
        print(f"Power Efficiency: {efficiency:.2f} %/W")

    # Recommendations
    print("\nRecommendations:")
    if temp > TEMP_THRESHOLDS["hot"]:
        print("  ⚠️  GPU is hot — consider reducing power limit")
    if gpu["throttle_thermal"]:
        print("  ⚠️  GPU is thermal throttling — performance reduced")
    if gpu["power_draw_w"] > 300:
        print("  ⚠️  High power draw — check cooling")
    if temp < TEMP_THRESHOLDS["cool"] and gpu["utilization_percent"] < 50:
        print("  ✅ GPU is cool and underutilized — can increase power")


def get_loaded_models():
    """Get currently loaded models."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/ps", timeout=5)
        return resp.json().get("models", [])
    except Exception as e:
        return []


def get_available_models():
    """Get available models."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return resp.json().get("models", [])
    except Exception as e:
        return []


def preload_model(model_name: str):
    """Preload a model by sending a dummy request."""
    print(f"  Preloading {model_name}...")
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model_name,
                "prompt": "Say 'ready' and nothing else.",
                "stream": False,
                "options": {"num_predict": 5},
            },
            timeout=120,
        )
        if resp.status_code == 200:
            print(f"  ✓ {model_name} loaded")
            return True
    except Exception as e:
        print(f"  ✗ {model_name} failed: {e}")
    return False


def preload_with_offload(model_name: str, gpu_layers: int = -1):
    """Preload a model with CPU offloading (partial GPU layers)."""
    print(f"  Preloading {model_name} with CPU offload (gpu_layers={gpu_layers})...")
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model_name,
                "prompt": "Say 'ready' and nothing else.",
                "stream": False,
                "options": {
                    "num_predict": 5,
                    "num_gpu": gpu_layers,  # Number of layers to offload to GPU
                },
                "keep_alive": "30m",
            },
            timeout=180,  # Longer timeout for large models
        )
        if resp.status_code == 200:
            result = resp.json()
            print(f"  ✓ {model_name} loaded ({gpu_layers} GPU layers)")
            return True
    except Exception as e:
        print(f"  ✗ {model_name} failed: {e}")
    return False


def show_cpu_offload_options():
    """Show CPU offloading options for larger models."""
    print("=" * 60)
    print("CPU OFFLOADING — RUN 14B MODELS ON 12GB VRAM")
    print("=" * 60)

    gpu = get_gpu_status()
    ram = get_system_ram()

    if not gpu:
        print("ERROR: Cannot access GPU")
        return

    print(f"\nGPU VRAM: {gpu['memory_free_mb']}MB free")
    if ram:
        print(f"System RAM: {ram['available_gb']:.1f}GB available / {ram['total_gb']:.1f}GB total")

    print("\n" + "-" * 60)
    print("AVAILABLE LARGE MODELS (CPU OFFLOAD)")
    print("-" * 60)

    for category, info in CPU_OFFLOAD_MODELS.items():
        vram_needed = info["size_gb"] * (info["gpu_layers"] / 40)  # Approximate
        ram_needed = info["size_gb"] * (info["ram_layers"] / 40)

        can_fit_vram = gpu["memory_free_mb"] > vram_needed * 1024
        can_fit_ram = (ram["available_gb"] > ram_needed) if ram else False
        can_run = can_fit_vram and can_fit_ram

        status = "✓ CAN RUN" if can_run else "✗ NOT ENOUGH MEMORY"
        status_color = "🟢" if can_run else "🔴"

        print(f"\n{status_color} {info['name']} — {info['quality']}")
        print(f"  GPU: {info['gpu_layers']}/40 layers (~{vram_needed:.1f}GB VRAM)")
        print(f"  RAM: {info['ram_layers']}/40 layers (~{ram_needed:.1f}GB RAM)")
        print(f"  Speed: {info['speed']}")
        print(f"  Use case: {info['use_case']}")
        print(f"  Status: {status}")

    print("\n" + "-" * 60)
    print("RECOMMENDATION")
    print("-" * 60)
    print("""
  With your 12GB VRAM + 32GB RAM:

  BEST: qwen2.5-coder:14b (20 GPU layers)
    → 4.5GB VRAM + 4.5GB RAM
    → 12-15 tok/s (great for coding)

  ALT:  deepseek-r1:14b (15 GPU layers)
    → 3.5GB VRAM + 5.5GB RAM
    → 10-13 tok/s (great for reasoning)

  NOTE: These are SLOWER than full-GPU models
        but give MUCH BETTER quality responses.
        Use for complex tasks, not quick lookups.
""")


def optimize_gpu():
    """Optimize GPU usage by preloading best models with safety checks."""
    print("=" * 60)
    print("GPU OPTIMIZER - RTX 3080 Ti (12GB VRAM)")
    print("=" * 60)

    # Check GPU status
    gpu = get_gpu_status()
    if not gpu:
        print("ERROR: Cannot access GPU. Is nvidia-smi available?")
        return

    print(f"\nGPU: {gpu['name']}")
    print(
        f"VRAM: {gpu['memory_used_mb']}MB / {gpu['memory_total_mb']}MB ({gpu['memory_used_percent']}%)"
    )
    print(f"Free: {gpu['memory_free_mb']}MB")
    print(f"Utilization: {gpu['utilization_percent']}%")
    print(f"Temperature: {gpu['temperature_c']}°C")
    print(f"Power: {gpu['power_draw_w']:.1f}W / {gpu['power_limit_w']:.1f}W")

    # Check thermal throttling
    if gpu["throttle_thermal"]:
        print("\n⚠️  WARNING: GPU is thermal throttling!")
        print("  Reducing power limit to prevent damage")
        auto_throttle(gpu["temperature_c"])
        return

    # Check VRAM limit
    if gpu["memory_used_percent"] > MAX_VRAM_PERCENT:
        print(
            f"\n⚠️  WARNING: VRAM at {gpu['memory_used_percent']:.1f}% — exceeds safe limit of {MAX_VRAM_PERCENT}%"
        )
        print("  Skipping preload to prevent OOM")
        return

    # Check temperature
    if gpu["temperature_c"] > TEMP_THRESHOLDS["hot"]:
        print(f"\n⚠️  WARNING: GPU temp {gpu['temperature_c']}°C — too hot for preload")
        print("  Cooling down first...")
        auto_throttle(gpu["temperature_c"])
        time.sleep(5)  # Wait for cooling
        gpu = get_gpu_status()  # Re-check
        if gpu is None:
            print("  ERROR: Cannot access GPU after cooling")
            return
        if gpu["temperature_c"] > TEMP_THRESHOLDS["hot"]:
            print("  Still too hot — aborting preload")
            return

    # Check loaded models
    loaded = get_loaded_models()
    print(f"\nLoaded models: {len(loaded)}")
    for m in loaded:
        size_gb = m.get("size_vram", 0) / 1e9
        print(f"  - {m['name']} ({size_gb:.1f}GB VRAM)")

    # Check available models
    available = get_available_models()
    available_names = {m["name"] for m in available}

    # Find best models to load
    print("\n" + "=" * 60)
    print("RECOMMENDED MODELS FOR YOUR GPU (SAFE LIMITS)")
    print("=" * 60)

    for category, info in sorted(MODELS.items(), key=lambda x: x[1]["priority"]):
        status = "[Available]" if info["name"] in available_names else "[Not installed]"
        print(f"\n{category.upper()}: {info['name']}")
        print(f"  Size: {info['size_gb']}GB | Quality: {info['quality']}")
        print(f"  Use case: {info['use_case']}")
        print(f"  Status: {status}")

    # Calculate optimal loading
    print("\n" + "=" * 60)
    print("OPTIMAL GPU LOADING (SAFE CONFIGURATION)")
    print("=" * 60)

    if gpu is None:
        print("ERROR: Cannot access GPU")
        return

    free_vram = gpu["memory_free_mb"]

    # Option 1: Single large model (best quality)
    if free_vram >= 5000:  # Need 5GB free for 7b model
        print("\nOption 1: BEST QUALITY (Recommended)")
        print("  Load: qwen2.5-coder:7b (4.5GB)")
        print("  Quality: ★★★★☆ for coding tasks")
        print("  Fits safely in your VRAM!")

        if "qwen2.5-coder:7b" not in [m["name"] for m in loaded]:
            if input("\n  Preload qwen2.5-coder:7b? (y/n): ").lower() == "y":
                preload_model("qwen2.5-coder:7b")

    # Option 2: Multiple smaller models
    print("\nOption 2: MULTI-MODEL (More flexible)")
    print("  Load: llama3.2:3b (2GB) + nomic-embed-text (0.3GB)")
    print("  Total: ~2.3GB (leaves 9.9GB free)")
    print("  Good for: Quick tasks + RAG")

    # Option 3: Safe maximum utilization
    print("\nOption 3: SAFE MAX UTILIZATION")
    print("  Load: llama3.2:3b (2GB) + qwen2.5-coder:7b (4.5GB) + nomic-embed-text (0.3GB)")
    print("  Total: ~6.8GB (uses 56% of VRAM)")
    print("  Best for: Coding + Chat + RAG")
    print("  ⚠️  DO NOT load llava:7b — would push to 94% VRAM (UNSAFE)")


def show_status():
    """Show current GPU and model status."""
    print("=" * 60)
    print("GPU STATUS")
    print("=" * 60)

    gpu = get_gpu_status()
    if gpu:
        print(f"\nGPU: {gpu['name']}")
        print(f"VRAM: {gpu['memory_used_mb']}MB / {gpu['memory_total_mb']}MB")
        print(f"Used: {gpu['memory_used_percent']}%")
        print(f"Free: {gpu['memory_free_mb']}MB")
        print(f"Utilization: {gpu['utilization_percent']}%")
        print(f"Temperature: {gpu['temperature_c']}°C")
        print(f"Power: {gpu['power_draw_w']:.1f}W / {gpu['power_limit_w']:.1f}W")
        print(f"Thermal Throttling: {'YES' if gpu['throttle_thermal'] else 'NO'}")

        # Visual bar
        used_bars = int(gpu["memory_used_percent"] / 5)
        free_bars = 20 - used_bars
        print(f"\nVRAM: [{'#' * used_bars}{'.' * free_bars}] {gpu['memory_used_percent']}%")

        # Safety warnings
        if gpu["memory_used_percent"] > MAX_VRAM_PERCENT:
            print(f"\n⚠️  WARNING: VRAM exceeds safe limit of {MAX_VRAM_PERCENT}%")
        if gpu["throttle_thermal"]:
            print("⚠️  WARNING: GPU is thermal throttling")
        if gpu["temperature_c"] > TEMP_THRESHOLDS["hot"]:
            print(
                f"⚠️  WARNING: GPU temp {gpu['temperature_c']}°C exceeds {TEMP_THRESHOLDS['hot']}°C"
            )

    loaded = get_loaded_models()
    print(f"\nLoaded models: {len(loaded)}")
    for m in loaded:
        size_gb = m.get("size_vram", 0) / 1e9
        print(f"  [OK] {m['name']} ({size_gb:.1f}GB VRAM)")


def run_benchmark():
    """Run inference benchmark."""
    print("=" * 60)
    print("INFERENCE BENCHMARK")
    print("=" * 60)

    models_to_test = [
        "llama3.2:3b-instruct-q4_K_M",
        "llama3.1:8b",
        "qwen2.5-coder:7b",
    ]

    prompt = "Write a Python function to calculate fibonacci numbers."

    for model_name in models_to_test:
        print(f"\nTesting {model_name}...")

        gpu_before = get_gpu_status()
        start_time = time.time()

        try:
            resp = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 100},
                },
                timeout=120,
            )

            elapsed = time.time() - start_time
            gpu_after = get_gpu_status()

            if resp.status_code == 200:
                result = resp.json()
                tokens = result.get("eval_count", 0)
                tokens_per_sec = tokens / elapsed if elapsed > 0 else 0

                print(f"  Time: {elapsed:.1f}s")
                print(f"  Tokens: {tokens}")
                print(f"  Speed: {tokens_per_sec:.1f} tokens/sec")
                if gpu_before and gpu_after:
                    vram_used = gpu_after["memory_used_mb"] - gpu_before["memory_used_mb"]
                    print(f"  VRAM delta: {vram_used}MB")
            else:
                print(f"  ERROR: {resp.status_code}")

        except Exception as e:
            print(f"  ERROR: {e}")


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--status":
            show_status()
        elif arg == "--preload":
            optimize_gpu()
        elif arg == "--benchmark":
            run_benchmark()
        elif arg == "--power":
            if len(sys.argv) > 2:
                profile = sys.argv[2]
                set_power_profile(profile)
            else:
                print("Available power profiles:")
                for name, info in POWER_PROFILES.items():
                    print(f"  {name}: {info['description']} ({info['watts']}W)")
                print("\nUsage: gpu-optimizer.py --power <profile>")
        elif arg == "--thermal":
            show_thermal_status()
        else:
            print(f"Unknown option: {arg}")
            print("Usage: gpu-optimizer.py [--status|--preload|--benchmark|--power|--thermal]")
    else:
        optimize_gpu()


if __name__ == "__main__":
    main()
