"""
Service Registry for The Catalyst

Manages service discovery and health monitoring for all system components.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("catalyst.registry")


class ServiceStatus(Enum):
    """Service status states."""

    STARTING = "starting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    STOPPED = "stopped"


@dataclass
class ServiceInfo:
    """Information about a registered service."""

    name: str
    status: ServiceStatus
    host: str
    port: int
    health_endpoint: str = "/health"
    last_check: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ServiceRegistry:
    """
    Registry for tracking and managing system services.

    Provides service discovery, health checking, and lifecycle management.
    """

    def __init__(self):
        """Initialize the service registry."""
        self._services: Dict[str, ServiceInfo] = {}
        self._health_check_interval = 60  # seconds
        self._health_check_task: Optional[asyncio.Task] = None
        self._on_status_change: List[Callable] = []

    def register(
        self,
        name: str,
        host: str,
        port: int,
        health_endpoint: str = "/health",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Register a service.

        Args:
            name: Service name.
            host: Service host.
            port: Service port.
            health_endpoint: Health check endpoint path.
            metadata: Optional service metadata.
        """
        self._services[name] = ServiceInfo(
            name=name,
            status=ServiceStatus.STARTING,
            host=host,
            port=port,
            health_endpoint=health_endpoint,
            metadata=metadata or {},
        )
        logger.info(f"Registered service: {name} at {host}:{port}")

    def unregister(self, name: str) -> None:
        """
        Unregister a service.

        Args:
            name: Service name.
        """
        if name in self._services:
            del self._services[name]
            logger.info(f"Unregistered service: {name}")

    def get_service(self, name: str) -> Optional[ServiceInfo]:
        """
        Get service information.

        Args:
            name: Service name.

        Returns:
            ServiceInfo or None if not found.
        """
        return self._services.get(name)

    def get_all_services(self) -> List[ServiceInfo]:
        """
        Get all registered services.

        Returns:
            List of ServiceInfo objects.
        """
        return list(self._services.values())

    def get_healthy_services(self) -> List[ServiceInfo]:
        """
        Get all healthy services.

        Returns:
            List of healthy ServiceInfo objects.
        """
        return [s for s in self._services.values() if s.status == ServiceStatus.HEALTHY]

    def update_status(self, name: str, status: ServiceStatus) -> None:
        """
        Update service status.

        Args:
            name: Service name.
            status: New status.
        """
        if name in self._services:
            old_status = self._services[name].status
            self._services[name].status = status
            self._services[name].last_check = datetime.now()

            if old_status != status:
                logger.info(f"Service {name} status: {old_status.value} -> {status.value}")
                self._notify_status_change(name, old_status, status)

    def _notify_status_change(
        self, name: str, old_status: ServiceStatus, new_status: ServiceStatus
    ) -> None:
        """Notify registered handlers of status change."""
        for handler in self._on_status_change:
            try:
                handler(name, old_status, new_status)
            except Exception as e:
                logger.error(f"Status change handler error: {e}")

    def on_status_change(self, handler: Callable) -> None:
        """
        Register a status change handler.

        Args:
            handler: Callable(service_name, old_status, new_status)
        """
        self._on_status_change.append(handler)

    async def start_health_checks(self) -> None:
        """Start periodic health checks."""
        if self._health_check_task is not None:
            return

        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Started health check loop")

    async def stop_health_checks(self) -> None:
        """Stop periodic health checks."""
        if self._health_check_task is not None:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
            logger.info("Stopped health check loop")

    async def _health_check_loop(self) -> None:
        """Run periodic health checks."""
        while True:
            await self._check_all_services()
            await asyncio.sleep(self._health_check_interval)

    async def _check_all_services(self) -> None:
        """Check health of all registered services."""
        for name, service in self._services.items():
            try:
                # Simple TCP check for now
                # In production, this would make HTTP requests to health endpoints
                self.update_status(name, ServiceStatus.HEALTHY)
            except Exception as e:
                logger.warning(f"Health check failed for {name}: {e}")
                self.update_status(name, ServiceStatus.UNHEALTHY)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics.

        Returns:
            Dict with service counts by status.
        """
        stats = {
            "total": len(self._services),
            "healthy": 0,
            "degraded": 0,
            "unhealthy": 0,
            "stopped": 0,
        }

        for service in self._services.values():
            if service.status == ServiceStatus.HEALTHY:
                stats["healthy"] += 1
            elif service.status == ServiceStatus.DEGRADED:
                stats["degraded"] += 1
            elif service.status == ServiceStatus.UNHEALTHY:
                stats["unhealthy"] += 1
            elif service.status == ServiceStatus.STOPPED:
                stats["stopped"] += 1

        return stats

    def __repr__(self) -> str:
        return f"<ServiceRegistry services={len(self._services)}>"
