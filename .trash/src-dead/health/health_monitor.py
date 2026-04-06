"""Health Monitor — Track service health over time"""

import logging, time
from typing import Dict, List

logger = logging.getLogger(__name__)


class HealthMonitor:
    def __init__(self):
        self._checks: Dict[str, List[dict]] = {}

    def check(self, service: str, url: str) -> bool:
        import httpx

        try:
            r = httpx.get(url, timeout=3)
            ok = r.status_code == 200
        except Exception:
            ok = False
        if service not in self._checks:
            self._checks[service] = []
        self._checks[service].append({"ok": ok, "time": time.time()})
        return ok

    def get_stats(self, service: str) -> Dict:
        checks = self._checks.get(service, [])
        if not checks:
            return {"service": service, "total": 0}
        ok = sum(1 for c in checks if c["ok"])
        return {
            "service": service,
            "total": len(checks),
            "healthy": ok,
            "rate": round(ok / len(checks) * 100, 1),
        }
