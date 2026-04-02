#!/usr/bin/env python3
"""N-Xyme Resource Monitor - Real-time hardware status for intelligent task routing."""

import json, subprocess, sys, psutil
import logging
from datetime import datetime


def get_gpu_status():
    try:
        r = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,utilization.memory,temperature.gpu,power.draw,power.limit",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0:
            p = r.stdout.strip().split(", ")
            return {
                "name": p[0],
                "vram_total_mb": int(p[1]),
                "vram_used_mb": int(p[2]),
                "vram_free_mb": int(p[3]),
                "gpu_util_pct": int(p[4]),
                "mem_util_pct": int(p[5]),
                "temp_c": int(p[6]),
                "power_w": float(p[7]),
                "power_limit_w": float(p[8]),
            }
    except Exception as e:
        logging.error(f"nvidia-smi failed: {e}")
    return {"error": "nvidia-smi failed"}


def get_ram_status():
    m = psutil.virtual_memory()
    return {
        "total_gb": round(m.total / 1e9, 1),
        "free_gb": round(m.available / 1e9, 1),
        "used_gb": round(m.used / 1e9, 1),
        "used_pct": m.percent,
    }


def get_cpu_status():
    f = psutil.cpu_freq()
    return {
        "cores": psutil.cpu_count(False),
        "threads": psutil.cpu_count(True),
        "load_pct": psutil.cpu_percent(interval=1),
        "freq_mhz": round(f.current) if f else 0,
    }


def get_ollama_status():
    try:
        import requests

        # Import centralized configuration
        try:
            from jarvis.config.graphiti_config import OLLAMA_URL
        except ImportError:
            import os

            OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

        d = requests.get(f"{OLLAMA_URL}/api/ps", timeout=5).json()
        models = [
            {
                "name": m["name"],
                "size_gb": round(m.get("size", 0) / 1e9, 1),
                "vram_gb": round(m.get("size_vram", 0) / 1e9, 1),
            }
            for m in d.get("models", [])
        ]
        return {"loaded": models, "count": len(models)}
    except Exception as e:
        logging.error(f"Ollama status check failed: {e}")
        return {"loaded": [], "count": 0}


def get_recommendations(gpu, ram, cpu):
    recs = []
    vf = gpu.get("vram_free_mb", 0)
    if vf > 8000:
        recs.append(("gpu", "high", f"{vf}MB free VRAM", "Load 2+ models in parallel"))
    elif vf > 4000:
        recs.append(("gpu", "medium", f"{vf}MB free VRAM", "Load qwen2.5-coder:7b for coding"))
    if gpu.get("gpu_util_pct", 100) < 20:
        recs.append(
            (
                "gpu",
                "medium",
                f"GPU at {gpu['gpu_util_pct']}%",
                "Run more parallel tasks",
            )
        )
    if ram.get("used_pct", 0) > 80:
        recs.append(("ram", "high", f"RAM at {ram['used_pct']}%", "Use GPU offloading"))
    if cpu.get("load_pct", 100) < 50:
        recs.append(
            (
                "cpu",
                "medium",
                f"CPU at {cpu['load_pct']}%",
                "Can run more parallel tasks",
            )
        )
    return recs


def main():
    gpu, ram, cpu, ollama = (
        get_gpu_status(),
        get_ram_status(),
        get_cpu_status(),
        get_ollama_status(),
    )
    recs = get_recommendations(gpu, ram, cpu)
    # Normalize VRAM-free to integer to avoid static type issues
    vram_free_mb = 0
    try:
        vram_free_mb = int(gpu.get("vram_free_mb", 0))
    except (ValueError, TypeError):
        vram_free_mb = 0
    report = {
        "timestamp": datetime.now().isoformat(),
        "gpu": gpu,
        "ram": ram,
        "cpu": cpu,
        "ollama": ollama,
        "recommendations": recs,
        "capacity": {
            "parallel_models": f"{(vram_free_mb // 4000) + 1} models",
            "parallel_tasks": f"{cpu.get('threads', 8)} concurrent",
            "bottleneck": "RAM" if ram.get("used_pct", 0) > 75 else "none",
        },
    }
    if "--json" in sys.argv:
        print(json.dumps(report, indent=2))
    else:
        print("=" * 60)
        print("  N-XYME RESOURCE MONITOR")
        print("=" * 60)
        print(f"\n  GPU: {gpu.get('name', '?')}")
        print(
            f"    VRAM: {gpu.get('vram_used_mb', 0)}MB / {gpu.get('vram_total_mb', 0)}MB ({gpu.get('vram_free_mb', 0)}MB free)"
        )
        print(
            f"    Util: {gpu.get('gpu_util_pct', 0)}% GPU | {gpu.get('mem_util_pct', 0)}% Mem | {gpu.get('temp_c', 0)}C"
        )
        print(
            f"\n  RAM: {ram.get('used_gb', 0)}GB / {ram.get('total_gb', 0)}GB ({ram.get('free_gb', 0)}GB free, {ram.get('used_pct', 0)}%)"
        )
        print(
            f"\n  CPU: {cpu.get('cores', 0)} cores / {cpu.get('threads', 0)} threads | Load: {cpu.get('load_pct', 0)}%"
        )
        print(f"\n  Ollama: {ollama.get('count', 0)} model(s) loaded")
        for m in ollama.get("loaded", []):
            print(f"    - {m['name']}: {m['size_gb']}GB ({m['vram_gb']}GB VRAM)")
        if recs:
            print(f"\n  RECOMMENDATIONS:")
            for t, p, msg, action in recs:
                print(f"    [{'!' if p == 'high' else 'i'}] [{t.upper()}] {msg} -> {action}")
        print(
            f"\n  CAPACITY: {report['capacity']['parallel_models']} | {report['capacity']['parallel_tasks']} | Bottleneck: {report['capacity']['bottleneck']}"
        )
        print("=" * 60)


if __name__ == "__main__":
    main()
