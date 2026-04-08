"""Health monitoring with exit IP detection."""

from __future__ import annotations

import asyncio
import logging
import time
import urllib.request
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from .models import VPNEndpoint

logger = logging.getLogger("vpn_rotation.health")


# Exit IP detection services
IP_DETECTION_URLS = [
    "https://ifconfig.me/ip",
    "https://api.ipify.org",
    "https://icanhazip.com",
    "https://ipinfo.io/ip",
]

# Default timeout for health checks
DEFAULT_TIMEOUT = 5.0

# Try to import aiohttp, fall back to urllib if not available
try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False


@dataclass
class HealthResult:
    """Result of a health check."""
    endpoint: VPNEndpoint
    healthy: bool
    latency_ms: float = 0.0
    exit_ip: str = ""
    error: str = ""
    timestamp: float = 0.0


class IPDetector:
    """Detects exit IP by making requests through endpoints.
    
    Uses multiple detection services for reliability.
    Falls back to urllib if aiohttp not available.
    """
    
    def __init__(
        self,
        detection_urls: List[str] = IP_DETECTION_URLS,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.detection_urls = detection_urls
        self.timeout = timeout
        self._session: Optional["aiohttp.ClientSession"] = None
    
    async def _get_session(self) -> Optional["aiohttp.ClientSession"]:
        """Get or create aiohttp session."""
        if not HAS_AIOHTTP:
            return None
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def detect_via_http(
        self,
        proxy_host: str,
        proxy_port: int,
    ) -> Optional[str]:
        """Detect exit IP using HTTP proxy.
        
        Args:
            proxy_host: Proxy server host.
            proxy_port: Proxy server port.
            
        Returns:
            Detected IP string, or None if failed.
        """
        # Try aiohttp first if available
        if HAS_AIOHTTP:
            session = await self._get_session()
            if session:
                for url in self.detection_urls:
                    try:
                        async with session.get(
                            url,
                            proxy=f"socks5://{proxy_host}:{proxy_port}",
                            timeout=aiohttp.ClientTimeout(total=self.timeout),
                        ) as resp:
                            if resp.status == 200:
                                ip = await resp.text()
                                return ip.strip()
                    except Exception as e:
                        logger.debug(f"IP detection failed via {url}: {e}")
                        continue
        
        # Fallback: use urllib (no SOCKS5 support, but works for HTTP proxies)
        for url in self.detection_urls:
            try:
                req = urllib.request.Request(url)
                req.set_proxy(f"{proxy_host}:{proxy_port}", "http")
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return resp.read().decode().strip()
            except Exception as e:
                logger.debug(f"URllib IP detection failed via {url}: {e}")
                continue
        
        return None
    
    async def detect_via_socks5(
        self,
        socks_host: str,
        socks_port: int,
    ) -> Optional[str]:
        """Detect exit IP using SOCKS5 proxy.
        
        Uses a custom SOCKS5 connection to detect IP.
        """
        # Create SOCKS5 connection to detect IP
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(socks_host, socks_port),
                timeout=self.timeout
            )
            
            # SOCKS5 handshake
            writer.write(b"\x05\x01\x00")  # Version 5, 1 method (no auth)
            await writer.drain()
            resp = await asyncio.wait_for(reader.readexactly(2), timeout=self.timeout)
            if resp != b"\x05\x00":
                writer.close()
                return None
            
            # Connect to ipinfo.io:80
            host = b"ipinfo.io"
            req = b"\x05\x01\x00\x03" + bytes([len(host)]) + host + b"\x00\x50"
            writer.write(req)
            await writer.drain()
            
            reply = await asyncio.wait_for(reader.readexactly(10), timeout=self.timeout)
            if reply[1] != 0:
                writer.close()
                return None
            
            # Send HTTP request for IP
            writer.write(b"GET /ip HTTP/1.1\r\nHost: ipinfo.io\r\n\r\n")
            await writer.drain()
            
            # Read response
            data = b""
            try:
                while True:
                    chunk = await asyncio.wait_for(reader.read(1024), timeout=5.0)
                    if not chunk:
                        break
                    data += chunk
                    if b"\r\n\r\n" in data:
                        break
            except asyncio.TimeoutError:
                pass
            
            writer.close()
            await writer.wait_closed()
            
            # Extract IP from response
            if b"200 OK" in data or b"HTTP/" in data:
                # Parse body
                if b"\r\n\r\n" in data:
                    body = data.split(b"\r\n\r\n", 1)[-1]
                    return body.strip().decode("utf-8", errors="ignore").strip()
            
        except Exception as e:
            logger.debug(f"SOCKS5 IP detection failed: {e}")
        
        return None
    
    async def close(self) -> None:
        """Close the aiohttp session."""
        if HAS_AIOHTTP and self._session and not self._session.closed:
            await self._session.close()


class HealthMonitor:
    """Monitors VPN endpoint health with periodic checks.
    
    Key features:
    - Periodic health checks (configurable interval)
    - Exit IP detection via ifconfig.me/ipify
    - Latency measurement
    - Rate limit detection
    - Background monitoring task
    """
    
    def __init__(
        self,
        check_interval: float = 300.0,
        timeout: float = DEFAULT_TIMEOUT,
        ip_detector: Optional[IPDetector] = None,
    ):
        self.check_interval = check_interval
        self.timeout = timeout
        self.ip_detector = ip_detector or IPDetector()
        
        self._endpoints: Dict[str, VPNEndpoint] = {}
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        # Health check statistics
        self._check_count: int = 0
        self._healthy_count: int = 0
    
    def add_endpoint(self, endpoint: VPNEndpoint) -> None:
        """Add an endpoint to monitor."""
        key = self._endpoint_key(endpoint)
        self._endpoints[key] = endpoint
        logger.debug(f"Added endpoint to monitor: {endpoint.host}:{endpoint.port}")
    
    def add_endpoints(self, endpoints: List[VPNEndpoint]) -> None:
        """Add multiple endpoints to monitor."""
        for ep in endpoints:
            self.add_endpoint(ep)
    
    def _endpoint_key(self, endpoint: VPNEndpoint) -> str:
        return f"{endpoint.host}:{endpoint.port}"
    
    async def check_endpoint(
        self,
        endpoint: VPNEndpoint,
        detect_ip: bool = True,
    ) -> HealthResult:
        """Check health of a single endpoint.
        
        Args:
            endpoint: Endpoint to check.
            detect_ip: Whether to detect exit IP.
            
        Returns:
            HealthResult with health status and metrics.
        """
        result = HealthResult(
            endpoint=endpoint,
            healthy=False,
            timestamp=time.time(),
        )
        
        start = time.time()
        
        try:
            # Determine check method based on provider type
            if endpoint.provider_type.value in ("socks5", "wireproxy"):
                # SOCKS5 health check
                result.exit_ip = await self.ip_detector.detect_via_socks5(
                    endpoint.host, endpoint.port
                )
                # If IP detection works, endpoint is healthy
                result.healthy = result.exit_ip is not None
            else:
                # HTTP-based check
                result.exit_ip = await self.ip_detector.detect_via_http(
                    endpoint.host, endpoint.port
                )
                result.healthy = result.exit_ip is not None
            
            result.latency_ms = (time.time() - start) * 1000
            
        except asyncio.TimeoutError:
            result.error = "timeout"
            result.latency_ms = self.timeout * 1000
        except Exception as e:
            result.error = str(e)
            result.latency_ms = (time.time() - start) * 1000
        
        return result
    
    async def check_all(
        self,
        endpoints: Optional[List[VPNEndpoint]] = None,
        detect_ip: bool = False,
    ) -> List[HealthResult]:
        """Check health of all endpoints (or a specific list).
        
        Args:
            endpoints: Optional specific endpoints to check.
            detect_ip: Whether to detect exit IPs.
            
        Returns:
            List of HealthResult objects.
        """
        if endpoints is None:
            endpoints = list(self._endpoints.values())
        
        # Check all concurrently
        tasks = [self.check_endpoint(ep, detect_ip=detect_ip) for ep in endpoints]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Update endpoint states
        for r in results:
            if isinstance(r, HealthResult):
                ep = r.endpoint
                ep.healthy = r.healthy
                ep.latency_ms = r.latency_ms
                ep.last_check = r.timestamp
                
                key = self._endpoint_key(ep)
                self._endpoints[key] = ep
                
                self._check_count += 1
                if r.healthy:
                    self._healthy_count += 1
        
        return [r for r in results if isinstance(r, HealthResult)]
    
    async def get_exit_ip(self, endpoint: VPNEndpoint) -> Optional[str]:
        """Get exit IP for a specific endpoint.
        
        Args:
            endpoint: The endpoint to test.
            
        Returns:
            Exit IP string, or None if failed.
        """
        return await self.ip_detector.detect_via_socks5(
            endpoint.host, endpoint.port
        ) if endpoint.provider_type.value in ("socks5", "wireproxy") \
            else await self.ip_detector.detect_via_http(
                endpoint.host, endpoint.port
            )
    
    def get_endpoint(self, host: str, port: int) -> Optional[VPNEndpoint]:
        """Get a monitored endpoint by host:port."""
        key = f"{host}:{port}"
        return self._endpoints.get(key)
    
    def get_healthy_endpoints(self) -> List[VPNEndpoint]:
        """Get all healthy endpoints."""
        return [ep for ep in self._endpoints.values() if ep.healthy]
    
    async def start_monitoring(self) -> None:
        """Start background health monitoring."""
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Health monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop background health monitoring."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        await self.ip_detector.close()
        logger.info("Health monitoring stopped")
    
    async def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self._running:
            try:
                await self.check_all()
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
            
            await asyncio.sleep(self.check_interval)
    
    def get_stats(self) -> dict:
        """Get health monitoring statistics."""
        return {
            "total_endpoints": len(self._endpoints),
            "healthy_endpoints": len(self.get_healthy_endpoints()),
            "total_checks": self._check_count,
            "successful_checks": self._healthy_count,
            "success_rate": round(self._healthy_count / max(1, self._check_count), 3),
        }


# Default singleton
_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """Get or create the default HealthMonitor instance."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor
