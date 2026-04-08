"""Main VPN rotation manager - orchestrates all components."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .health import HealthMonitor, IPDetector, get_health_monitor
from .models import ProviderConfig, ProviderType, RotationOutcome, VPNEndpoint
from .provider import ProviderRegistry, SOCKS5Provider, WireProxyProvider
from .router import QLearningRouter, RoutingDecision, get_router
from .wireproxy import WireProxyManager, get_wireproxy_manager

logger = logging.getLogger("vpn_rotation.manager")


@dataclass
class RotationStats:
    """Statistics for the rotation manager."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_rotation_switches: int = 0
    avg_latency_ms: float = 0.0
    start_time: float = field(default_factory=time.time)
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    @property
    def uptime_seconds(self) -> float:
        return time.time() - self.start_time


class VPNRotationManager:
    """Unified VPN/IP rotation manager.
    
    Orchestrates:
    - ProviderRegistry: Plugin-based provider abstraction
    - WireProxyManager: Dynamic instance spawning
    - HealthMonitor: Exit IP detection + health checks
    - QLearningRouter: Self-learning routing
    
    Key features:
    - No hard limit on instances (dynamic spawning)
    - Self-learning via Q-Learning + SQLite
    - Exit IP detection via ifconfig.me/ipify
    - Weighted routing by speed/success
    - Portable single module
    """
    
    def __init__(
        self,
        db_path: str = "data/proxy/vpn_routing.db",
        health_check_interval: float = 300.0,
        wireproxy_base_port: int = 1080,
        wireproxy_max_instances: int = 32,
    ):
        self.db_path = db_path
        self.health_check_interval = health_check_interval
        
        # Core components (lazy init)
        self._wireproxy_manager: Optional[WireProxyManager] = None
        self._health_monitor: Optional[HealthMonitor] = None
        self._router: Optional[QLearningRouter] = None
        
        # Configuration
        self.wireproxy_base_port = wireproxy_base_port
        self.wireproxy_max_instances = wireproxy_max_instances
        
        # State
        self._endpoints: List[VPNEndpoint] = []
        self._stats = RotationStats()
        self._running = False
        self._init_task: Optional[asyncio.Task] = None
        
        # Provider configurations
        self._provider_configs: List[ProviderConfig] = []
    
    # ==================== Properties ====================
    
    @property
    def wireproxy_manager(self) -> WireProxyManager:
        if self._wireproxy_manager is None:
            self._wireproxy_manager = WireProxyManager(
                base_port=self.wireproxy_base_port,
                max_instances=self.wireproxy_max_instances,
            )
        return self._wireproxy_manager
    
    @property
    def health_monitor(self) -> HealthMonitor:
        if self._health_monitor is None:
            self._health_monitor = HealthMonitor(
                check_interval=self.health_check_interval,
            )
        return self._health_monitor
    
    @property
    def router(self) -> QLearningRouter:
        if self._router is None:
            self._router = QLearningRouter(db_path=self.db_path)
        return self._router
    
    @property
    def endpoints(self) -> List[VPNEndpoint]:
        return self._endpoints
    
    @property
    def stats(self) -> RotationStats:
        return self._stats
    
    # ==================== Configuration ====================
    
    def add_provider(self, config: ProviderConfig) -> None:
        """Add a VPN provider configuration.
        
        Args:
            config: Provider configuration.
        """
        self._provider_configs.append(config)
        
        # Register with ProviderRegistry
        ProviderRegistry.add_provider(config.name, config)
        logger.info(f"Added provider: {config.name} ({config.provider_type.value})")
    
    def add_socks5_proxy(
        self,
        name: str,
        host: str,
        port: int,
        max_instances: int = 1,
    ) -> None:
        """Add a SOCKS5 proxy provider.
        
        Args:
            name: Provider name.
            host: Proxy host.
            port: Proxy port.
            max_instances: Max instances (usually 1 for static proxy).
        """
        config = ProviderConfig(
            name=name,
            provider_type=ProviderType.SOCKS5,
            host=host,
            port=port,
            max_instances=max_instances,
        )
        self.add_provider(config)
    
    def add_wireproxy_instances(self, count: int = 8) -> None:
        """Configure WireProxy instances.
        
        Args:
            count: Number of instances to spawn.
        """
        # WireProxy is handled by WireProxyManager directly
        # This just sets the target count
        self._wireproxy_target_count = count
        logger.info(f"Configured WireProxy: {count} instances")
    
    # ==================== Lifecycle ====================
    
    async def initialize(self) -> None:
        """Initialize all components and load endpoints."""
        logger.info("Initializing VPN rotation manager...")
        
        # Setup default providers if none configured
        if not self._provider_configs:
            # Add local SOCKS5 as default
            self.add_socks5_proxy(
                name="local",
                host="127.0.0.1",
                port=1080,
            )
        
        # Collect endpoints from all providers
        await self._refresh_endpoints()
        
        # Add endpoints to health monitor
        self.health_monitor.add_endpoints(self._endpoints)
        
        # Initial health check
        await self.health_monitor.check_all(detect_ip=True)
        
        logger.info(f"Initialized with {len(self._endpoints)} endpoints")
    
    async def _refresh_endpoints(self) -> None:
        """Refresh endpoints from all providers."""
        endpoints = []
        
        # Get from ProviderRegistry
        try:
            registry_endpoints = await ProviderRegistry.list_all_endpoints()
            endpoints.extend(registry_endpoints)
        except Exception as e:
            logger.warning(f"Failed to get registry endpoints: {e}")
        
        # Get from WireProxyManager
        if self._wireproxy_manager:
            try:
                wireproxy_endpoints = await self._wireproxy_manager.get_endpoints()
                endpoints.extend(wireproxy_endpoints)
            except Exception as e:
                logger.warning(f"Failed to get WireProxy endpoints: {e}")
        
        # Deduplicate by host:port
        seen = set()
        unique_endpoints = []
        for ep in endpoints:
            key = f"{ep.host}:{ep.port}"
            if key not in seen:
                seen.add(key)
                unique_endpoints.append(ep)
        
        self._endpoints = unique_endpoints
    
    async def start(self) -> None:
        """Start the rotation manager."""
        if self._running:
            return
        
        await self.initialize()
        
        # Start WireProxy monitoring
        if self._wireproxy_manager:
            await self._wireproxy_manager.start_monitoring()
        
        # Start health monitoring
        await self.health_monitor.start_monitoring()
        
        self._running = True
        logger.info("VPN rotation manager started")
    
    async def stop(self) -> None:
        """Stop the rotation manager."""
        if not self._running:
            return
        
        # Stop health monitoring
        await self.health_monitor.stop_monitoring()
        
        # Stop WireProxy monitoring
        if self._wireproxy_manager:
            await self._wireproxy_manager.stop_all()
        
        self._running = False
        logger.info("VPN rotation manager stopped")
    
    # ==================== Core API ====================
    
    def get_endpoint(self) -> Optional[VPNEndpoint]:
        """Get the best endpoint using Q-Learning router.
        
        Returns:
            Selected VPNEndpoint, or None if no healthy endpoints.
        """
        if not self._endpoints:
            return None
        
        # Use router to select
        decision = self.router.select_endpoint(self._endpoints)
        
        if decision.endpoint:
            self._stats.total_requests += 1
            logger.debug(
                f"Selected endpoint: {decision.endpoint.host}:{decision.endpoint.port} "
                f"({decision.strategy}, q={decision.q_value:.2f})"
            )
        
        return decision.endpoint
    
    async def get_endpoint_with_ip(self) -> Optional[tuple[VPNEndpoint, str]]:
        """Get endpoint along with its exit IP.
        
        Returns:
            Tuple of (endpoint, exit_ip), or None.
        """
        endpoint = self.get_endpoint()
        if not endpoint:
            return None
        
        # Detect exit IP
        exit_ip = await self.health_monitor.get_exit_ip(endpoint)
        
        return (endpoint, exit_ip or "unknown")
    
    def record_outcome(
        self,
        endpoint: VPNEndpoint,
        latency_ms: float,
        success: bool,
        exit_ip: str = "",
        error_type: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        """Record outcome for learning.
        
        Args:
            endpoint: The endpoint that was used.
            latency_ms: Request latency.
            success: Whether the request succeeded.
            exit_ip: Detected exit IP.
            error_type: Type of error if failed.
            input_tokens: Input token count.
            output_tokens: Output token count.
        """
        outcome = RotationOutcome(
            endpoint=endpoint,
            latency_ms=latency_ms,
            success=success,
            exit_ip=exit_ip,
            error_type=error_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        
        # Update stats
        if success:
            self._stats.successful_requests += 1
        else:
            self._stats.failed_requests += 1
        
        # Update router with outcome
        self.router.update_from_outcome(outcome)
        
        # Update endpoint metrics
        endpoint.latency_ms = latency_ms
        
        # Handle failure
        if not success and error_type == "rate_limited":
            endpoint.rate_limited_until = time.time() + 60.0
        
        logger.debug(
            f"Recorded outcome: {endpoint.host}:{endpoint.port} "
            f"latency={latency_ms:.0f}ms success={success}"
        )
    
    async def rotate(self) -> Optional[VPNEndpoint]:
        """Force rotation to a new endpoint.
        
        Used when current endpoint is rate-limited or unhealthy.
        
        Returns:
            New endpoint, or None.
        """
        # Filter out current unhealthy endpoints
        candidates = [
            ep for ep in self._endpoints
            if ep.healthy and not ep.is_rate_limited
        ]
        
        if not candidates:
            return None
        
        # Select a different endpoint (prefer different country)
        decision = self.router.select_endpoint(candidates)
        
        self._stats.total_rotation_switches += 1
        logger.info(
            f"Rotated to: {decision.endpoint.host}:{decision.endpoint.port} "
            f"(switch #{self._stats.total_rotation_switches})"
        )
        
        return decision.endpoint
    
    # ==================== Monitoring ====================
    
    async def check_health(self) -> dict:
        """Check health of all endpoints.
        
        Returns:
            Health check results.
        """
        results = await self.health_monitor.check_all(detect_ip=True)
        return {
            "total": len(results),
            "healthy": sum(1 for r in results if r.healthy),
            "results": [
                {
                    "host": r.endpoint.host,
                    "port": r.endpoint.port,
                    "healthy": r.healthy,
                    "latency_ms": round(r.latency_ms, 1),
                    "exit_ip": r.exit_ip,
                }
                for r in results
            ],
        }
    
    def get_status(self) -> dict:
        """Get comprehensive status.
        
        Returns:
            Status dict with all metrics.
        """
        return {
            "running": self._running,
            "stats": {
                "total_requests": self._stats.total_requests,
                "successful": self._stats.successful_requests,
                "failed": self._stats.failed_requests,
                "success_rate": round(self._stats.success_rate, 3),
                "avg_latency_ms": round(self._stats.avg_latency_ms, 1),
                "rotation_switches": self._stats.total_rotation_switches,
                "uptime_seconds": round(self._stats.uptime_seconds, 1),
            },
            "endpoints": {
                "total": len(self._endpoints),
                "healthy": sum(1 for ep in self._endpoints if ep.healthy),
                "rate_limited": sum(1 for ep in self._endpoints if ep.is_rate_limited),
            },
            "router": self.router.get_stats(),
            "wireproxy": (
                self._wireproxy_manager.get_stats()
                if self._wireproxy_manager
                else {}
            ),
        }
    
    def get_endpoints_json(self) -> str:
        """Get endpoints as JSON for debugging."""
        import json
        return json.dumps(
            [ep.to_dict() for ep in self._endpoints],
            indent=2,
        )


# Convenience function for quick access
_manager: Optional[VPNRotationManager] = None


def get_vpn_manager() -> VPNRotationManager:
    """Get or create the default VPNRotationManager instance."""
    global _manager
    if _manager is None:
        _manager = VPNRotationManager()
    return _manager
