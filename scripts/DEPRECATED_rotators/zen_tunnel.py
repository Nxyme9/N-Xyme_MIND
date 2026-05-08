#!/usr/bin/env python3
"""
OPENCODE ZEN IP TUNNEL - FREE MAXIMUM THROUGHPUT

OpenCode Zen is FREE but IP-based - route through proxies to bypass IP rate limits!
- Rotates SOCKS5 proxies for IP diversity
- No API key needed - just IP access
- Combines with OpenRouter aggregator for maximum power

Usage:
    python scripts/zen_tunnel.py status      # Show status
    python scripts/zen_tunnel.py test        # Test connection
    python scripts/zen_tunnel.py dashboard   # Full metrics
    python scripts/zen_tunnel.py add-proxy   # Add a proxy
    python scripts/zen_tunnel.py daemon      # Run with auto-rotation
"""

import json
import os
import sys
import time
import threading
import socket
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from collections import deque, defaultdict
import signal
import atexit
import requests

# Config paths
CONFIG_DIR = Path(__file__).parent.parent / "configs" / "api-keys"
PROXY_FILE = CONFIG_DIR / "proxies.json"
STATE_FILE = CONFIG_DIR / "zen_state.json"
METRICS_FILE = CONFIG_DIR / "zen_metrics.json"
LOG_FILE = CONFIG_DIR / "zen_tunnel.log"

# Thread safety
_lock = threading.Lock()

# Zen uses no API key - just IP-based access!
ZEN_BASE_URL = "https://api.opencode.ai/v1"

# Metrics
_metrics = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "total_rotations": 0,
    "by_proxy": {},
    "request_history": [],
    "error_history": [],
    "uptime_start": datetime.now().isoformat(),
}

_state = {
    "current_proxy_idx": 0,
    "proxies_in_rotation": [],
    "daemon_mode": False,
}


@dataclass
class ProxyInfo:
    """Proxy for IP rotation - supports SOCKS5, HTTP, or direct connection."""

    proxy_id: str
    host: str
    port: int
    proxy_type: str = "socks5"  # socks5, http, or "none" for direct
    username: Optional[str] = None
    password: Optional[str] = None
    is_active: bool = True
    error_count: int = 0
    consecutive_errors: int = 0
    last_used: Optional[datetime] = None
    last_error: Optional[str] = None

    def get_proxy_dict(self) -> Optional[Dict[str, str]]:
        """Get proxy dict for requests. Returns None for direct connection."""
        # Direct connection mode - no proxy!
        if self.proxy_type == "none" or not self.host:
            return None

        # Build proxy URL based on type
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        else:
            auth = ""

        proxy_url = f"{self.proxy_type}://{auth}{self.host}:{self.port}"

        return {
            "http": proxy_url,
            "https": proxy_url,
        }


class ZenTunnel:
    """
    OpenCode Zen IP Tunnel - FREE maximum throughput via proxy rotation

    Zen is free but IP-based. Each IP gets rate limited.
    By rotating proxies, we get multiple IPs = 6x+ throughput!
    """

    def __init__(self):
        self.proxies: List[ProxyInfo] = []
        self._load_proxies()
        self._load_metrics()
        self._running = False
        self._daemon_thread = None

    def _load_proxies(self):
        """Load proxy configuration."""
        data = {}
        if PROXY_FILE.exists():
            with open(PROXY_FILE, "r") as f:
                data = json.load(f)

        for p in data.get("proxies", []):
            self.proxies.append(
                ProxyInfo(
                    proxy_id=p.get("id", "unknown"),
                    host=p.get("host", ""),
                    port=p.get("port", 1080),
                    proxy_type=p.get("type", "socks5"),
                    username=p.get("username"),
                    password=p.get("password"),
                )
            )

        print(f"[ZEN] Loaded {len(self.proxies)} proxies")

    def _load_metrics(self):
        """Load persisted metrics."""
        if METRICS_FILE.exists():
            try:
                with open(METRICS_FILE, "r") as f:
                    saved = json.load(f)
                    # Fix: ensure lists are lists, not strings
                    _metrics["request_history"] = saved.get("request_history", [])
                    _metrics["error_history"] = saved.get("error_history", [])
                    _metrics["by_proxy"] = saved.get("by_proxy", {})
                    _metrics["total_requests"] = saved.get("total_requests", 0)
                    _metrics["successful_requests"] = saved.get(
                        "successful_requests", 0
                    )
                    _metrics["failed_requests"] = saved.get("failed_requests", 0)
                    _metrics["total_rotations"] = saved.get("total_rotations", 0)
            except Exception as e:
                print(f"[ZEN] Metrics load warning: {e}")

    def _save_metrics(self):
        """Persist metrics."""
        with _lock:
            with open(METRICS_FILE, "w") as f:
                json.dump(dict(_metrics), f, indent=2, default=str)

    def _save_state(self):
        """Save state."""
        with _lock:
            with open(STATE_FILE, "w") as f:
                json.dump(_state, f, indent=2)

    def get_next_proxy(self) -> Optional[ProxyInfo]:
        """Get next available proxy (round-robin). Returns None for direct mode."""
        if not self.proxies:
            return None

        # Find active proxy
        for i in range(len(self.proxies)):
            idx = (_state["current_proxy_idx"] + i) % len(self.proxies)
            proxy = self.proxies[idx]
            if proxy.is_active:
                _state["current_proxy_idx"] = idx
                return proxy

        # All failed - reset
        print("[ZEN] All proxies exhausted, resetting...")
        for p in self.proxies:
            p.is_active = True
            p.consecutive_errors = 0
            p.error_count = 0

        _state["current_proxy_idx"] = 0
        return self.proxies[0]

    def get_current_mode(self) -> str:
        """Get current connection mode."""
        if not self.proxies:
            return "direct"

        # Check first active proxy
        for p in self.proxies:
            if p.is_active:
                if p.proxy_type == "none" or not p.host:
                    return "direct"
                return p.proxy_type

        return "direct"

    def test_proxy(self, proxy: ProxyInfo) -> bool:
        """Test if proxy works."""
        try:
            kwargs = {
                "url": "https://opencode.ai/api/v1/models",
                "timeout": 15,
            }
            # Only add proxies if not in direct mode
            proxy_dict = proxy.get_proxy_dict()
            if proxy_dict is not None:
                kwargs["proxies"] = proxy_dict

            resp = requests.get(**kwargs)
            return resp.status_code == 200
        except Exception as e:
            print(f"[ZEN] Test failed: {e}")
            return False

    def make_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Dict = None,
        max_retries: int = 3,
    ) -> Dict:
        """
        Make request through proxy rotation.
        Auto-rotates on failure.
        Supports: SOCKS5, HTTP proxy, or direct connection (no proxy).
        """
        proxy = self.get_next_proxy()

        for attempt in range(max_retries):
            if not proxy:
                return {"success": False, "error": "No proxies available"}

            try:
                url = f"{ZEN_BASE_URL}/{endpoint.lstrip('/')}"

                # Build request - handle direct connection (no proxy)
                proxy_dict = proxy.get_proxy_dict()

                kwargs = {
                    "timeout": 60,
                    "headers": {
                        "User-Agent": "N-Xyme-MIND/1.0",
                    },
                }

                # Only add proxies if we're not in direct mode
                if proxy_dict is not None:
                    kwargs["proxies"] = proxy_dict

                if method == "GET":
                    resp = requests.get(url, **kwargs)
                elif method == "POST":
                    kwargs["json"] = data
                    resp = requests.post(url, **kwargs)
                else:
                    return {"success": False, "error": f"Unknown method: {method}"}

                # Track metrics
                with _lock:
                    _metrics["total_requests"] += 1
                    proxy.last_used = datetime.now()

                    # Initialize proxy stats if not exists
                    if proxy.proxy_id not in _metrics["by_proxy"]:
                        _metrics["by_proxy"][proxy.proxy_id] = {
                            "requests": 0,
                            "errors": 0,
                            "last_used": None,
                        }

                    _metrics["by_proxy"][proxy.proxy_id]["requests"] += 1
                    _metrics["by_proxy"][proxy.proxy_id]["last_used"] = (
                        datetime.now().isoformat()
                    )
                    _metrics["request_history"].append(
                        {
                            "timestamp": datetime.now().isoformat(),
                            "proxy": proxy.proxy_id,
                            "status": resp.status_code,
                        }
                    )

                self._save_metrics()

                # Check success
                if resp.status_code == 200:
                    proxy.consecutive_errors = 0
                    with _lock:
                        _metrics["successful_requests"] += 1
                    return {
                        "success": True,
                        "response": resp.json() if resp.text else {},
                        "proxy_used": proxy.proxy_id,
                    }

                # Rate limit or error
                proxy.consecutive_errors += 1
                proxy.error_count += 1
                proxy.last_error = f"HTTP {resp.status_code}: {resp.text[:100]}"

                with _lock:
                    _metrics["failed_requests"] += 1

                    # Initialize proxy stats if not exists
                    if proxy.proxy_id not in _metrics["by_proxy"]:
                        _metrics["by_proxy"][proxy.proxy_id] = {
                            "requests": 0,
                            "errors": 0,
                            "last_used": None,
                        }

                    _metrics["by_proxy"][proxy.proxy_id]["errors"] += 1
                    _metrics["error_history"].append(
                        {
                            "timestamp": datetime.now().isoformat(),
                            "proxy": proxy.proxy_id,
                            "error": proxy.last_error,
                        }
                    )

                # Mark exhausted if too many errors
                if proxy.consecutive_errors >= 3:
                    proxy.is_active = False
                    print(f"[ZEN] Proxy {proxy.proxy_id} marked exhausted")

                # Rotate and retry
                _metrics["total_rotations"] += 1
                _state["current_proxy_idx"] = (_state["current_proxy_idx"] + 1) % len(
                    self.proxies
                )
                proxy = self.get_next_proxy()

            except Exception as e:
                error_str = str(e)
                proxy.consecutive_errors += 1
                proxy.error_count += 1
                proxy.last_error = error_str[:200]

                with _lock:
                    _metrics["failed_requests"] += 1
                    _metrics["error_history"].append(
                        {
                            "timestamp": datetime.now().isoformat(),
                            "proxy": proxy.proxy_id,
                            "error": error_str[:200],
                        }
                    )

                # Timeout = proxy likely bad
                if "timeout" in error_str.lower():
                    proxy.is_active = False

                _metrics["total_rotations"] += 1
                proxy = self.get_next_proxy()

        return {"success": False, "error": "Max retries exceeded"}

    def get_metrics(self) -> Dict:
        """Get tunnel metrics."""
        with _lock:
            active_proxies = sum(1 for p in self.proxies if p.is_active)

            uptime = datetime.now() - datetime.fromisoformat(_metrics["uptime_start"])

            # Determine connection mode
            mode = self.get_current_mode()

            return {
                "status": "operational" if active_proxies > 0 else "degraded",
                "connection_mode": mode,
                "active_proxies": active_proxies,
                "total_proxies": len(self.proxies),
                # Aggregated throughput (each IP gets ~50 req/day)
                "aggregated_daily": active_proxies * 50
                if mode != "direct"
                else "unlimited",
                # Metrics
                "total_requests": _metrics["total_requests"],
                "successful_requests": _metrics["successful_requests"],
                "failed_requests": _metrics["failed_requests"],
                "success_rate": _metrics["successful_requests"]
                / max(_metrics["total_requests"], 1)
                * 100,
                "total_rotations": _metrics["total_rotations"],
                # Per-proxy stats
                "by_proxy": dict(_metrics["by_proxy"]),
                # Uptime
                "uptime_hours": uptime.total_seconds() / 3600,
            }

    def show_dashboard(self):
        """Display dashboard."""
        metrics = self.get_metrics()

        print("\n" + "=" * 70)
        print("🟢 OPENCODE ZEN IP TUNNEL - FREE MAXIMUM THROUGHPUT")
        print("=" * 70)

        print(f"\n🔗 CONNECTION MODE: {metrics['connection_mode'].upper()}")

        if metrics["connection_mode"] == "direct":
            print(f"   Direct connection - NO PROXY (max throughput)")
        else:
            print(f"   Aggregated: {metrics['aggregated_daily']} req/day")
            print(f"   (was 50/day per IP × {metrics['total_proxies']} proxies)")

        print(
            f"\n🌐 PROXIES: {metrics['active_proxies']}/{metrics['total_proxies']} active"
        )
        for p in self.proxies:
            status = "❌" if not p.is_active else "✅"
            mode = p.proxy_type if p.proxy_type != "none" else "DIRECT"
            last = p.last_used.strftime("%H:%M") if p.last_used else "never"
            print(
                f"   {status} {p.proxy_id}: {p.host}:{p.port} [{mode}] ({p.error_count} err, last: {last})"
            )

        print(f"\n📈 METRICS:")
        print(f"   Total Requests: {metrics['total_requests']}")
        print(f"   Successful: {metrics['successful_requests']}")
        print(f"   Failed: {metrics['failed_requests']}")
        print(f"   Success Rate: {metrics['success_rate']:.1f}%")
        print(f"   Rotations: {metrics['total_rotations']}")
        print(f"   Uptime: {metrics['uptime_hours']:.1f} hours")

        print("\n" + "=" * 70)

    def add_proxy(
        self,
        host: str,
        port: int,
        username: str = None,
        password: str = None,
        proxy_type: str = "socks5",
    ):
        """Add a new proxy."""
        proxy_id = f"proxy-{len(self.proxies) + 1:03d}"

        proxy = ProxyInfo(
            proxy_id=proxy_id,
            host=host,
            port=port,
            proxy_type=proxy_type,
            username=username,
            password=password,
        )

        # Test first (skip test for direct mode)
        if proxy_type == "none":
            self.proxies.append(proxy)
            self._save_proxies()
            print(f"✅ Added {proxy_id}: DIRECT CONNECTION (no proxy)")
            return

        print(f"[ZEN] Testing {proxy_id}...")
        if self.test_proxy(proxy):
            self.proxies.append(proxy)

            # Save
            self._save_proxies()
            print(f"✅ Added {proxy_id}: {host}:{port} [{proxy_type}]")
        else:
            print(f"❌ Proxy {proxy_id} failed test")

    def enable_direct_mode(self):
        """Enable direct connection mode (no proxy)."""
        # Clear existing proxies and add direct mode
        direct_proxy = ProxyInfo(
            proxy_id="direct-001",
            host="",
            port=0,
            proxy_type="none",
        )
        self.proxies = [direct_proxy]
        self._save_proxies()
        print("[ZEN] ✅ Direct mode enabled - NO PROXY")

    def enable_proxy_mode(self):
        """Enable proxy mode - requires proxies to be configured."""
        if not self.proxies or self.proxies[0].proxy_type == "none":
            # Try to load from config
            self._load_proxies()
            if not self.proxies:
                print("[ZEN] ❌ No proxies configured. Add proxies first.")
                return False
        print("[ZEN] ✅ Proxy mode enabled")
        return True

    def _save_proxies(self):
        """Save proxy config."""
        data = {
            "proxies": [
                {
                    "id": p.proxy_id,
                    "host": p.host,
                    "port": p.port,
                    "type": p.proxy_type,
                    "username": p.username,
                    "password": p.password,
                }
                for p in self.proxies
            ]
        }
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(PROXY_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def run_daemon(self):
        """Run as daemon with monitoring."""
        self._running = True
        print("[ZEN] Starting Zen tunnel daemon...")

        while self._running:
            try:
                metrics = self.get_metrics()
                print(
                    f"[ZEN] Health: {metrics['status']}, "
                    f"Proxies: {metrics['active_proxies']}/{metrics['total_proxies']}, "
                    f"Req: {metrics['total_requests']}"
                )

                # Revive proxies if they're being retried
                for p in self.proxies:
                    if not p.is_active and p.consecutive_errors < 3:
                        p.is_active = True
                        print(f"[ZEN] Revived proxy {p.proxy_id}")

            except Exception as e:
                print(f"[ZEN] Daemon error: {e}")

            time.sleep(30)

    def health_check(self) -> Dict:
        """Quick health check."""
        return self.get_metrics()


def main():
    """Main entry point."""
    tunnel = ZenTunnel()

    if len(sys.argv) < 2:
        tunnel.show_dashboard()
        return

    cmd = sys.argv[1]

    if cmd == "dashboard" or cmd == "status":
        tunnel.show_dashboard()

    elif cmd == "metrics":
        print(json.dumps(tunnel.get_metrics(), indent=2))

    elif cmd == "health":
        print(json.dumps(tunnel.health_check(), indent=2))

    elif cmd == "mode":
        # Show current mode
        mode = tunnel.get_current_mode()
        print(f"Current mode: {mode}")
        metrics = tunnel.get_metrics()
        print(f"Status: {metrics['status']}")
        print(f"Active proxies: {metrics['active_proxies']}/{metrics['total_proxies']}")

    elif cmd == "direct":
        # Enable direct mode
        tunnel.enable_direct_mode()
        tunnel.show_dashboard()

    elif cmd == "proxy":
        # Enable proxy mode
        tunnel.enable_proxy_mode()
        tunnel.show_dashboard()

    elif cmd == "test":
        proxy = tunnel.get_next_proxy()
        if proxy:
            print(f"[ZEN] Testing {proxy.proxy_id}...")
            if tunnel.test_proxy(proxy):
                print(f"✅ Proxy {proxy.proxy_id} works!")
            else:
                print(f"❌ Proxy {proxy.proxy_id} failed")
        else:
            print("[ZEN] No proxies available")

    elif cmd == "add-proxy":
        if len(sys.argv) < 4:
            print("Usage: zen_tunnel.py add-proxy <host> <port> [username] [password]")
            sys.exit(1)
        host = sys.argv[2]
        port = int(sys.argv[3])
        user = sys.argv[4] if len(sys.argv) > 4 else None
        pw = sys.argv[5] if len(sys.argv) > 5 else None
        tunnel.add_proxy(host, port, user, pw)

    elif cmd == "daemon":
        tunnel.run_daemon()

    elif cmd == "models":
        # Test getting models
        result = tunnel.make_request("models", "GET")
        if result["success"]:
            print(f"✅ Got {len(result['response'].get('data', []))} models")
        else:
            print(f"❌ Error: {result.get('error')}")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
