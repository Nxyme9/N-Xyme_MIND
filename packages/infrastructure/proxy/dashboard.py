"""
Router Dashboard — Real-time monitoring and control.
"""

import json
import time
import threading
from typing import Dict, List


class Dashboard:
    def __init__(self):
        self._data = {
            "requests_total": 0,
            "requests_success": 0,
            "requests_failed": 0,
            "avg_latency_ms": 0.0,
            "current_rpm": 0.0,
            "active_sessions": {},
            "agent_stats": {},
            "provider_health": {},
            "vpn_ip_status": {},
            "recent_requests": [],
            "alerts": [],
            "uptime_seconds": time.time(),
        }
        self._lock = threading.Lock()
        self._request_times: List[float] = []

    def record_request(self, agent: str, session: str, model: str, provider: str,
                       vpn_ip: str, latency_ms: float, success: bool, error: str = "") -> None:
        with self._lock:
            self._data["requests_total"] += 1
            if success:
                self._data["requests_success"] += 1
            else:
                self._data["requests_failed"] += 1
                if error:
                    self._data["alerts"].append({
                        "time": time.time(),
                        "severity": "ERROR",
                        "message": f"{agent} failed: {error[:100]}",
                    })

            # Update latency
            n = self._data["requests_total"]
            self._data["avg_latency_ms"] = (self._data["avg_latency_ms"] * (n-1) + latency_ms) / n

            # Track RPM
            now = time.time()
            self._request_times.append(now)
            self._request_times = [t for t in self._request_times if now - t < 60]
            self._data["current_rpm"] = len(self._request_times)

            # Track per-agent stats
            if agent not in self._data["agent_stats"]:
                self._data["agent_stats"][agent] = {"total": 0, "success": 0, "failed": 0, "models_used": {}}
            self._data["agent_stats"][agent]["total"] += 1
            if success:
                self._data["agent_stats"][agent]["success"] += 1
            else:
                self._data["agent_stats"][agent]["failed"] += 1
            self._data["agent_stats"][agent]["models_used"][model] = self._data["agent_stats"][agent]["models_used"].get(model, 0) + 1

            # Track per-session
            if session not in self._data["active_sessions"]:
                self._data["active_sessions"][session] = {"requests": 0, "last_active": now}
            self._data["active_sessions"][session]["requests"] += 1
            self._data["active_sessions"][session]["last_active"] = now

            # Track recent requests (last 50)
            self._data["recent_requests"].append({
                "time": now,
                "agent": agent,
                "session": session,
                "model": model,
                "provider": provider,
                "vpn_ip": vpn_ip,
                "latency_ms": round(latency_ms, 1),
                "success": success,
            })
            if len(self._data["recent_requests"]) > 50:
                self._data["recent_requests"] = self._data["recent_requests"][-50:]

    def update_provider_health(self, health: Dict) -> None:
        with self._lock:
            self._data["provider_health"] = health

    def update_vpn_status(self, status: Dict) -> None:
        with self._lock:
            self._data["vpn_ip_status"] = status

    def get_status(self) -> dict:
        with self._lock:
            data = dict(self._data)
            data["uptime_seconds"] = round(time.time() - data["uptime_seconds"], 1)
            data["success_rate"] = round(data["requests_success"] / max(1, data["requests_total"]), 3)
            return data


# Global instance
dashboard = Dashboard()
