"""
Health Core — Ported from N-Xyme LIVE, enhanced for Catalyst

Central health monitoring system with component registration,
caching, and comprehensive reporting.

Usage:
    monitor = HealthMonitor()
    monitor.register("ollama", check_ollama_health)
    monitor.register("neo4j", check_neo4j_health)
    report = await monitor.get_full_report()
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ComponentHealth(Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthMetric:
    """A single health metric."""

    name: str
    value: Any
    unit: str = ""
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ComponentStatus:
    """Status of a single component."""

    name: str
    health: ComponentHealth
    message: str = ""
    metrics: List[HealthMetric] = field(default_factory=list)
    uptime_seconds: float = 0
    last_check: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None


class HealthMonitor:
    """
    Central health monitoring system.

    Aggregates health from all components and provides
    a unified health endpoint.
    """

    def __init__(self):
        self._components: Dict[str, Callable[[], ComponentStatus]] = {}
        self._status_cache: Dict[str, ComponentStatus] = {}
        self._cache_ttl: float = 5.0  # seconds
        self._last_full_check: Optional[datetime] = None
        self._start_time = time.time()

    def register(self, name: str, health_func: Callable[[], ComponentStatus]) -> None:
        """Register a component for health monitoring."""
        self._components[name] = health_func
        logger.debug(f"HealthMonitor: Registered '{name}'")

    def unregister(self, name: str) -> bool:
        """Unregister a component."""
        if name in self._components:
            del self._components[name]
            self._status_cache.pop(name, None)
            return True
        return False

    def check(self, name: str, force: bool = False) -> Optional[ComponentStatus]:
        """Get status of a specific component."""
        if name not in self._components:
            return None

        # Check cache
        if not force and name in self._status_cache:
            cached = self._status_cache[name]
            age = (datetime.now() - cached.last_check).total_seconds()
            if age < self._cache_ttl:
                return cached

        # Get fresh status
        try:
            status = self._components[name]()
            self._status_cache[name] = status
            return status
        except Exception as e:
            logger.error(f"HealthMonitor: Check failed for '{name}': {e}")
            return ComponentStatus(name=name, health=ComponentHealth.UNHEALTHY, error=str(e))

    def check_all(self, force: bool = False) -> Dict[str, ComponentStatus]:
        """Get status of all registered components."""
        statuses = {}
        for name in self._components:
            status = self.check(name, force)
            if status:
                statuses[name] = status
        self._last_full_check = datetime.now()
        return statuses

    async def check_all_async(self, force: bool = False) -> Dict[str, ComponentStatus]:
        """Get status of all registered components in parallel."""
        import asyncio

        async def _check_one(name: str) -> tuple:
            loop = asyncio.get_event_loop()
            status = await loop.run_in_executor(None, self.check, name, force)
            return (name, status)

        tasks = [_check_one(name) for name in self._components]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        statuses = {}
        for result in results:
            if isinstance(result, tuple) and result[1] is not None:
                statuses[result[0]] = result[1]

        self._last_full_check = datetime.now()
        return statuses

    def get_overall_health(
        self, statuses: Optional[Dict[str, ComponentStatus]] = None
    ) -> ComponentHealth:
        """Get overall system health (worst status wins)."""
        if statuses is None:
            statuses = self.check_all()
        if not statuses:
            return ComponentHealth.UNKNOWN

        if any(s.health == ComponentHealth.UNHEALTHY for s in statuses.values()):
            return ComponentHealth.UNHEALTHY
        elif any(s.health == ComponentHealth.DEGRADED for s in statuses.values()):
            return ComponentHealth.DEGRADED
        else:
            return ComponentHealth.HEALTHY

    def get_system_metrics(self) -> Dict:
        """Get system-level metrics."""
        try:
            import psutil

            return {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "memory_used_gb": round(psutil.virtual_memory().used / (1024**3), 1),
                "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 1),
                "disk_percent": psutil.disk_usage("/").percent,
                "uptime_seconds": time.time() - self._start_time,
                "timestamp": datetime.now().isoformat(),
            }
        except ImportError:
            return {"error": "psutil not installed"}

    def get_full_report(self) -> Dict:
        """Get comprehensive health report."""
        statuses = self.check_all()
        system = self.get_system_metrics()
        overall = self.get_overall_health(statuses)  # Reuse statuses, don't re-check

        return {
            "overall": overall.value,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": system.get("uptime_seconds", 0),
            "system": system,
            "components": {
                name: {
                    "health": status.health.value,
                    "message": status.message,
                    "uptime_seconds": status.uptime_seconds,
                    "error": status.error,
                    "metrics": [
                        {"name": m.name, "value": m.value, "unit": m.unit} for m in status.metrics
                    ],
                }
                for name, status in statuses.items()
            },
        }

    def get_stats(self) -> Dict:
        """Get monitoring statistics."""
        statuses = self.check_all()
        return {
            "total_components": len(self._components),
            "healthy": sum(1 for s in statuses.values() if s.health == ComponentHealth.HEALTHY),
            "degraded": sum(1 for s in statuses.values() if s.health == ComponentHealth.DEGRADED),
            "unhealthy": sum(1 for s in statuses.values() if s.health == ComponentHealth.UNHEALTHY),
            "unknown": sum(1 for s in statuses.values() if s.health == ComponentHealth.UNKNOWN),
        }
