"""System Utils — CPU, RAM, disk info"""

import logging, os, platform
from typing import Dict

logger = logging.getLogger(__name__)


class SystemUtils:
    @staticmethod
    def get_info() -> Dict:
        try:
            import psutil

            cpu = psutil.cpu_percent(interval=0.1)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            return {
                "platform": platform.system(),
                "cpu_percent": cpu,
                "ram_total_gb": round(ram.total / (1024**3), 1),
                "ram_used_gb": round(ram.used / (1024**3), 1),
                "ram_percent": ram.percent,
                "disk_total_gb": round(disk.total / (1024**3), 1),
                "disk_used_gb": round(disk.used / (1024**3), 1),
                "disk_percent": round(disk.used / disk.total * 100, 1),
            }
        except ImportError:
            return {"platform": platform.system(), "error": "psutil not installed"}
