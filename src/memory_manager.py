"""Memory Manager — Track and optimize memory usage"""

import gc, logging
from typing import Dict

logger = logging.getLogger(__name__)


class MemoryManager:
    def get_usage(self) -> Dict:
        try:
            import psutil

            process = psutil.Process()
            mem = process.memory_info()
            return {
                "rss_mb": round(mem.rss / (1024 * 1024), 1),
                "vms_mb": round(mem.vms / (1024 * 1024), 1),
                "percent": round(process.memory_percent(), 1),
                "system_available_gb": round(psutil.virtual_memory().available / (1024**3), 1),
            }
        except ImportError:
            return {"error": "psutil not installed"}

    def force_gc(self) -> Dict:
        before = self.get_usage()
        gc.collect()
        after = self.get_usage()
        freed = before.get("rss_mb", 0) - after.get("rss_mb", 0)
        return {"before": before, "after": after, "freed_mb": round(freed, 1)}

    def get_object_count(self) -> Dict:
        gc.collect()
        return {"objects": len(gc.get_objects()), "garbage": len(gc.garbage)}
