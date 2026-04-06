"""
Health Recovery — Auto-healing system

Automatically fixes common health issues.

Usage:
    from health_recovery import HealthRecovery
    from health_core import HealthMonitor

    monitor = HealthMonitor()
    recovery = HealthRecovery(monitor)
    results = recovery.heal_all()
"""

import logging
import subprocess
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.health.health_core import ComponentHealth, ComponentStatus, HealthMonitor

logger = logging.getLogger(__name__)


@dataclass
class RecoveryAction:
    """A recovery action taken."""

    component: str
    action: str
    success: bool
    message: str
    timestamp: float = field(default_factory=time.time)


class HealthRecovery:
    """Auto-healing system."""

    def __init__(self, monitor: HealthMonitor):
        self.monitor = monitor
        self._history: List[RecoveryAction] = []
        self._ai_diagnostics = None
        logger.info("HealthRecovery: Initialized")

    def set_ai_diagnostics(self, ai_diagnostics) -> None:
        """Set AI diagnostics for intelligent recovery decisions."""
        self._ai_diagnostics = ai_diagnostics

    def heal(self, component_name: str) -> RecoveryAction:
        """Attempt to heal a specific component."""
        status = self.monitor.check(component_name)
        if not status:
            return RecoveryAction(
                component=component_name,
                action="check",
                success=False,
                message="Component not found",
            )

        if status.health == ComponentHealth.HEALTHY:
            return RecoveryAction(
                component=component_name, action="none", success=True, message="Already healthy"
            )

        # Determine recovery action
        action = self._determine_action(status)
        result = self._execute_action(component_name, action, status)

        self._history.append(result)
        return result

    def heal_all(self) -> Dict[str, RecoveryAction]:
        """Attempt to heal all unhealthy components."""
        results = {}
        statuses = self.monitor.check_all()

        for name, status in statuses.items():
            if status.health != ComponentHealth.HEALTHY:
                result = self.heal(name)
                results[name] = result

        return results

    def _determine_action(self, status: ComponentStatus) -> str:
        """Determine what recovery action to take."""
        message = (status.message or "").lower()

        if "not found" in message or "not running" in message:
            return "restart"
        elif "closed" in message:
            return "restart"
        elif "timeout" in message:
            return "restart"
        elif "high" in message:
            return "clear_cache"
        elif "locked" in message:
            return "wait"
        else:
            return "restart"

    def _execute_action(
        self, component_name: str, action: str, status: ComponentStatus
    ) -> RecoveryAction:
        """Execute the recovery action."""
        try:
            if action == "restart":
                return self._restart_component(component_name, status)
            elif action == "clear_cache":
                return self._clear_cache(component_name)
            elif action == "wait":
                return self._wait_and_retry(component_name)
            else:
                return RecoveryAction(
                    component=component_name,
                    action=action,
                    success=False,
                    message=f"Unknown action: {action}",
                )
        except Exception as e:
            return RecoveryAction(
                component=component_name, action=action, success=False, message=str(e)
            )

    def _restart_component(self, component_name: str, status: ComponentStatus) -> RecoveryAction:
        """Restart a component via PM2."""
        try:
            result = subprocess.run(
                ["pm2", "restart", component_name], capture_output=True, text=True, timeout=30
            )

            if result.returncode == 0:
                return RecoveryAction(
                    component=component_name,
                    action="restart",
                    success=True,
                    message=f"Restarted {component_name}",
                )
            else:
                return RecoveryAction(
                    component=component_name,
                    action="restart",
                    success=False,
                    message=f"PM2 restart failed: {result.stderr}",
                )
        except FileNotFoundError:
            return RecoveryAction(
                component=component_name, action="restart", success=False, message="PM2 not found"
            )

    def _clear_cache(self, component_name: str) -> RecoveryAction:
        """Clear cache for a component."""
        try:
            # Clear Ollama cache
            import httpx

            client = httpx.Client(timeout=5)
            client.post(
                "http://localhost:11434/api/generate",
                json={"model": "llama3.2:3b-instruct-q4_K_M", "prompt": "", "keep_alive": 0},
            )
            client.close()

            return RecoveryAction(
                component=component_name,
                action="clear_cache",
                success=True,
                message="Cache cleared",
            )
        except Exception as e:
            return RecoveryAction(
                component=component_name, action="clear_cache", success=False, message=str(e)
            )

    def _wait_and_retry(self, component_name: str) -> RecoveryAction:
        """Wait and retry a component."""
        time.sleep(5)  # Wait 5 seconds
        status = self.monitor.check(component_name, force=True)

        if status and status.health == ComponentHealth.HEALTHY:
            return RecoveryAction(
                component=component_name, action="wait", success=True, message="Component recovered"
            )
        else:
            return RecoveryAction(
                component=component_name,
                action="wait",
                success=False,
                message="Component still unhealthy",
            )

    def get_history(self, limit: int = 50) -> List[Dict]:
        """Get recovery history."""
        return [
            {
                "component": r.component,
                "action": r.action,
                "success": r.success,
                "message": r.message,
                "timestamp": r.timestamp,
            }
            for r in self._history[-limit:]
        ]

    def get_stats(self) -> Dict:
        """Get recovery statistics."""
        total = len(self._history)
        successful = len([r for r in self._history if r.success])

        return {
            "total_actions": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": round(successful / total * 100, 1) if total > 0 else 0,
        }
