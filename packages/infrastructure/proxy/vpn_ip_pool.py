"""
VPN IP Health Tracker — Monitor SOCKS5 proxy health, skip blocked IPs.
"""

import threading
import time
from typing import List, Optional


class VPNIP:
    """Represents a single VPN exit IP (SOCKS5 proxy)."""

    def __init__(self, host: str, port: int, name: str = ""):
        self.host = host
        self.port = port
        self.name = name or f"{host}:{port}"
        self.health_score = 1.0
        self.consecutive_failures = 0
        self.cooldown_until = 0.0
        self.total_requests = 0
        self.total_failures = 0
        self.total_successes = 0
        self.avg_latency_ms = 0.0
        self.last_used = 0.0
        self.is_banned = False
        self.ban_until = 0.0

    def is_available(self) -> bool:
        now = time.time()
        if self.is_banned and now < self.ban_until:
            return False
        if now < self.cooldown_until:
            return False
        return True

    def record_success(self, latency_ms: float) -> None:
        self.total_successes += 1
        self.total_requests += 1
        self.last_used = time.time()
        self.consecutive_failures = 0
        if self.avg_latency_ms == 0:
            self.avg_latency_ms = latency_ms
        else:
            self.avg_latency_ms = 0.9 * self.avg_latency_ms + 0.1 * latency_ms
        self.health_score = min(1.0, self.health_score + 0.05)
        self.is_banned = False

    def record_failure(self, error_type: str = "unknown") -> None:
        now = time.time()
        self.total_failures += 1
        self.total_requests += 1
        self.consecutive_failures += 1
        self.health_score = max(0.0, self.health_score - 0.15)
        if error_type in ("403", "ban", "captcha"):
            self.is_banned = True
            self.ban_until = now + 300
            self.cooldown_until = now + 300
        elif error_type == "429" or self.consecutive_failures >= 3:
            cooldown = min(10 * (2 ** (self.consecutive_failures - 1)), 120)
            self.cooldown_until = now + cooldown

    def to_dict(self) -> dict:
        now = time.time()
        return {
            "name": self.name, "host": self.host, "port": self.port,
            "health_score": round(self.health_score, 2),
            "is_available": self.is_available(),
            "is_banned": self.is_banned and now < self.ban_until,
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "consecutive_failures": self.consecutive_failures,
            "total_requests": self.total_requests,
            "total_successes": self.total_successes,
            "total_failures": self.total_failures,
            "cooldown_remaining": max(0, round(self.cooldown_until - now, 1)),
        }


class VPNIPPool:
    """Manages pool of VPN exit IPs with health tracking."""

    def __init__(self):
        self._ips: List[VPNIP] = []
        self._lock = threading.Lock()

    def add_ip(self, host: str, port: int, name: str = "") -> None:
        with self._lock:
            self._ips.append(VPNIP(host, port, name))

    def get_best_ip(self) -> Optional[VPNIP]:
        with self._lock:
            available = [ip for ip in self._ips if ip.is_available()]
            if not available:
                self._ips.sort(key=lambda ip: ip.cooldown_until)
                return self._ips[0] if self._ips else None
            available.sort(key=lambda ip: (ip.health_score, -ip.avg_latency_ms), reverse=True)
            return available[0]

    def record_success(self, ip: VPNIP, latency_ms: float) -> None:
        with self._lock:
            ip.record_success(latency_ms)

    def record_failure(self, ip: VPNIP, error_type: str) -> None:
        with self._lock:
            ip.record_failure(error_type)

    def get_pool_status(self) -> dict:
        with self._lock:
            return {
                "total_ips": len(self._ips),
                "available_ips": sum(1 for ip in self._ips if ip.is_available()),
                "banned_ips": sum(1 for ip in self._ips if ip.is_banned),
                "ips": [ip.to_dict() for ip in self._ips],
            }


# Global instance with 8 SOCKS5 proxies
vpn_ip_pool = VPNIPPool()
for port in range(1080, 1088):
    vpn_ip_pool.add_ip("127.0.0.1", port, f"socks5-{port}")
