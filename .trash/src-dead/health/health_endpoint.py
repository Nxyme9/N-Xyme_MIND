"""
Health Endpoint — HTTP endpoint for health checks

Provides /health, /live, /ready endpoints.

Usage:
    from health_core import HealthMonitor
    from health_endpoint import HealthEndpoint

    monitor = HealthMonitor()
    endpoint = HealthEndpoint(monitor, port=18753)
    await endpoint.start()
"""

import logging
from typing import Optional

from src.health.health_core import ComponentHealth, HealthMonitor

logger = logging.getLogger(__name__)


class HealthEndpoint:
    """HTTP endpoint for health checks."""

    def __init__(self, monitor: HealthMonitor, host: str = "127.0.0.1", port: int = 18753):
        self.monitor = monitor
        self.host = host
        self.port = port
        self._server = None

    async def start(self):
        """Start health endpoint server."""
        try:
            from aiohttp import web

            async def health(request):
                """Full health report."""
                report = self.monitor.get_full_report()
                status = report.get("overall", "unknown")
                return web.json_response(report, status=200 if status == "healthy" else 503)

            async def liveness(request):
                """Liveness probe (always OK if server is running)."""
                return web.Response(text="OK")

            async def readiness(request):
                """Readiness probe (OK only if all components healthy)."""
                overall = self.monitor.get_overall_health()
                if overall == ComponentHealth.HEALTHY:
                    return web.Response(text="OK")
                return web.Response(text="NOT READY", status=503)

            async def metrics(request):
                """Prometheus-style metrics."""
                report = self.monitor.get_full_report()
                lines = []

                for name, component in report.get("components", {}).items():
                    health = component.get("health", "unknown")
                    lines.append(
                        f'component_health{{name="{name}"}} {1 if health == "healthy" else 0}'
                    )

                for metric_name, metric_data in report.get("system", {}).items():
                    if isinstance(metric_data, (int, float)):
                        lines.append(f"system_{metric_name} {metric_data}")

                return web.Response(text="\n".join(lines), content_type="text/plain")

            app = web.Application()
            app.router.add_get("/health", health)
            app.router.add_get("/live", liveness)
            app.router.add_get("/ready", readiness)
            app.router.add_get("/metrics", metrics)

            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, self.host, self.port)
            await site.start()

            logger.info(f"HealthEndpoint: Started at http://{self.host}:{self.port}")
            return True
        except ImportError:
            logger.warning("HealthEndpoint: aiohttp not installed, skipping")
            return False
        except Exception as e:
            logger.error(f"HealthEndpoint: Failed to start: {e}")
            return False

    async def stop(self):
        """Stop health endpoint server."""
        if self._server:
            self._server.close()
            logger.info("HealthEndpoint: Stopped")
