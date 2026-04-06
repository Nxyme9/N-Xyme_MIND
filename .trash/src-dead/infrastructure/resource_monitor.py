"""Resource Monitor — Monitor system resources"""

import logging, time
from typing import Dict, List

logger = logging.getLogger(__name__)


class ResourceMonitor:
    def __init__(self):
        self._history: List[Dict] = []

    def snapshot(self) -> Dict:
        try:
            import psutil

            data = {
                "time": time.time(),
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "ram_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage("/").percent,
            }
            try:
                import GPUtil

                gpus = GPUtil.getGPUs()
                if gpus:
                    data["gpu_percent"] = gpus[0].load * 100
                    data["gpu_memory_percent"] = gpus[0].memoryUtil * 100
            except Exception:
                pass
            self._history.append(data)
            if len(self._history) > 1000:
                self._history = self._history[-1000:]
            return data
        except ImportError:
            return {"error": "psutil not installed"}

    def get_history(self, limit: int = 100) -> List[Dict]:
        return self._history[-limit:]

    def get_averages(self) -> Dict:
        if not self._history:
            return {}
        recent = self._history[-100:]
        return {
            "avg_cpu": sum(h.get("cpu_percent", 0) for h in recent) / len(recent),
            "avg_ram": sum(h.get("ram_percent", 0) for h in recent) / len(recent),
            "avg_gpu": sum(h.get("gpu_percent", 0) for h in recent) / len(recent),
        }
