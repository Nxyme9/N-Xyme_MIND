"""System API endpoints for health and status."""
from fastapi import APIRouter
import subprocess
import json

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health")
async def health():
    return {"status": "ok", "api": "running"}


@router.get("/pm2")
async def pm2_status():
    try:
        result = subprocess.run(["pm2", "jlist"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            processes = json.loads(result.stdout)
            return {"status": "ok", "count": len(processes), "processes": processes}
        return {"status": "error", "error": result.stderr}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/gpu")
async def gpu_status():
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.free,memory.used,utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(", ")
            return {
                "status": "ok",
                "name": parts[0],
                "memory_total_mb": int(parts[1]),
                "memory_free_mb": int(parts[2]),
                "memory_used_mb": int(parts[3]),
                "utilization_pct": int(parts[4]),
                "temperature_c": int(parts[5]),
            }
        return {"status": "error", "error": result.stderr}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/graphiti")
async def graphiti_health():
    try:
        import requests
        resp = requests.get("http://localhost:8001/health", timeout=5)
        return resp.json()
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.post("/pm2/restart/{service}")
async def pm2_restart(service: str):
    try:
        result = subprocess.run(["pm2", "restart", service], capture_output=True, text=True, timeout=30)
        return {"status": "ok" if result.returncode == 0 else "error", "output": result.stdout}
    except Exception as e:
        return {"status": "error", "error": str(e)}
