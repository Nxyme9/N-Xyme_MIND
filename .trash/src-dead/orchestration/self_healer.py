"""
Self-Healer Module — Ported from N-Xyme ECOSYSTEM SPINE

Autonomous healing and self-repair capabilities.
Monitors service health and automatically executes remediation actions.

Usage:
    healer = SelfHealer(config)
    healer.record_health("ollama", True)   # OK
    healer.record_health("ollama", False)  # Triggers healing if degraded
"""

import logging
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class HealingActionType(Enum):
    RESTART = "restart"
    SCALE = "scale"
    FALLBACK = "fallback"
    ROLLBACK = "rollback"
    NOTIFY = "notify"


@dataclass
class HealingPolicy:
    """Defines when and how to heal a service."""

    name: str
    trigger_condition: str  # "degraded", "unhealthy", "critical"
    action_type: HealingActionType
    action_target: str  # Service name or PM2 process name
    cooldown_seconds: float = 60.0
    max_retries: int = 3
    enabled: bool = True


@dataclass
class HealingAction:
    """Record of a healing action taken."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    policy_name: str = ""
    action_type: HealingActionType = HealingActionType.RESTART
    target: str = ""
    timestamp: float = field(default_factory=time.time)
    executed: bool = False
    success: bool = False
    result: str = ""


@dataclass
class HealthStatus:
    """Health status for a service."""

    service_name: str
    status: str = "healthy"  # healthy, degraded, unhealthy
    consecutive_failures: int = 0
    last_success: float = 0.0
    last_failure: float = 0.0


class SelfHealer:
    """
    Autonomous healing system for Catalyst services.

    Monitors service health and executes remediation policies
    when degradation is detected.
    """

    def __init__(
        self,
        services: List[str],
        policies: Optional[List[HealingPolicy]] = None,
        enabled: bool = True,
        cooldown_seconds: float = 60.0,
        max_retries: int = 3,
    ):
        self.services = services
        self.enabled = enabled
        self.default_cooldown = cooldown_seconds
        self.default_max_retries = max_retries

        self.health_status: Dict[str, HealthStatus] = {
            s: HealthStatus(service_name=s) for s in services
        }
        self.execution_history: deque = deque(maxlen=1000)
        self.retry_counters: Dict[str, int] = {}
        self.cooldowns: Dict[str, float] = {}

        self.policies = policies or self._default_policies()
        self._event_bus = None
        logger.info(f"SelfHealer: Initialized for {len(services)} services")

    def wire_event_bus(self, event_bus) -> None:
        """Wire event bus for anomaly subscription and healing notifications."""
        self._event_bus = event_bus
        event_bus.subscribe("anomaly.detected", self._on_anomaly)
        logger.info("SelfHealer: Event bus wired, subscribed to anomaly.detected")

    def _on_anomaly(self, anomaly_data: dict) -> None:
        """React to anomaly events by recording health failure."""
        if anomaly_data and anomaly_data.get("severity") in ("high", "critical"):
            service = anomaly_data.get("service", "")
            if service:
                logger.info(f"SelfHealer: Anomaly received for {service}, recording failure")
                self.record_health(service, is_healthy=False)

    def _default_policies(self) -> List[HealingPolicy]:
        """Default healing policies."""
        return [
            HealingPolicy(
                name="restart_on_degraded",
                trigger_condition="degraded",
                action_type=HealingActionType.RESTART,
                action_target="*",
                cooldown_seconds=60.0,
                max_retries=3,
            ),
            HealingPolicy(
                name="notify_on_unhealthy",
                trigger_condition="unhealthy",
                action_type=HealingActionType.NOTIFY,
                action_target="*",
                cooldown_seconds=300.0,
                max_retries=1,
            ),
        ]

    def record_health(self, service_name: str, is_healthy: bool) -> None:
        """Record a health check result for a service."""
        if service_name not in self.health_status:
            self.health_status[service_name] = HealthStatus(service_name=service_name)

        status = self.health_status[service_name]
        now = time.time()

        if is_healthy:
            status.status = "healthy"
            status.consecutive_failures = 0
            status.last_success = now
            # Reset retry counter on success
            self.retry_counters.pop(service_name, None)
        else:
            status.consecutive_failures += 1
            status.last_failure = now
            status.status = "unhealthy" if status.consecutive_failures >= 3 else "degraded"

        if status.status != "healthy":
            logger.warning(
                f"SelfHealer: {service_name} is {status.status} "
                f"(failures: {status.consecutive_failures})"
            )
            self._evaluate_policies(service_name, status)

    def _evaluate_policies(self, service_name: str, health: HealthStatus) -> None:
        """Evaluate and execute healing policies."""
        if not self.enabled:
            return

        for policy in self.policies:
            if not policy.enabled:
                continue

            if self._should_execute(policy, service_name, health):
                self._execute_policy(policy, service_name)

    def _should_execute(
        self, policy: HealingPolicy, service_name: str, health: HealthStatus
    ) -> bool:
        """Check if a policy should be executed."""
        # Check trigger condition
        if policy.trigger_condition == "degraded" and health.status not in (
            "degraded",
            "unhealthy",
        ):
            return False
        if policy.trigger_condition == "unhealthy" and health.status != "unhealthy":
            return False

        # Check cooldown
        cooldown_key = f"{policy.name}:{service_name}"
        last_execution = self.cooldowns.get(cooldown_key, 0)
        if time.time() - last_execution < policy.cooldown_seconds:
            return False

        # Check retry limit
        retry_key = f"{policy.name}:{service_name}"
        retries = self.retry_counters.get(retry_key, 0)
        if retries >= policy.max_retries:
            logger.info(
                f"SelfHealer: Max retries ({policy.max_retries}) reached for {service_name}"
            )
            return False

        return True

    def _execute_policy(self, policy: HealingPolicy, service_name: str) -> None:
        """Execute a healing policy."""
        cooldown_key = f"{policy.name}:{service_name}"
        retry_key = f"{policy.name}:{service_name}"

        action = HealingAction(
            policy_name=policy.name,
            action_type=policy.action_type,
            target=service_name,
        )

        try:
            if policy.action_type == HealingActionType.RESTART:
                self._restart_service(service_name)
                action.success = True
                action.result = "Service restarted"

            elif policy.action_type == HealingActionType.NOTIFY:
                self._notify_failure(service_name)
                action.success = True
                action.result = "Notification sent"

            elif policy.action_type == HealingActionType.FALLBACK:
                self._switch_fallback(service_name)
                action.success = True
                action.result = "Switched to fallback"

            else:
                action.success = False
                action.result = f"Unknown action type: {policy.action_type}"

            action.executed = True

        except Exception as e:
            action.success = False
            action.result = str(e)
            logger.error(f"SelfHealer: Failed to execute {policy.name} for {service_name}: {e}")

        # Update counters
        self.cooldowns[cooldown_key] = time.time()
        self.retry_counters[retry_key] = self.retry_counters.get(retry_key, 0) + 1

        self.execution_history.append(action)

        # Publish healing event
        if self._event_bus:
            self._event_bus.publish(
                "healer.action",
                {
                    "policy": action.policy_name,
                    "action": action.action_type.value,
                    "target": action.target,
                    "success": action.success,
                    "result": action.result,
                },
            )

        logger.info(
            f"SelfHealer: Executed {policy.action_type.value} for {service_name} "
            f"(success={action.success})"
        )

    def _restart_service(self, service_name: str) -> None:
        """Restart a service via PM2."""
        import subprocess

        try:
            subprocess.run(
                ["pm2", "restart", service_name], capture_output=True, text=True, timeout=30
            )
            logger.info(f"SelfHealer: PM2 restarted {service_name}")
        except FileNotFoundError:
            logger.warning("SelfHealer: PM2 not found, skipping restart")

    def _notify_failure(self, service_name: str) -> None:
        """Send notification about service failure."""
        status = self.health_status.get(service_name)
        if status:
            logger.warning(
                f"SelfHealer: ALERT - {service_name} is {status.status} "
                f"({status.consecutive_failures} failures)"
            )

    def _switch_fallback(self, service_name: str) -> None:
        """Switch to fallback service/model."""
        logger.info(f"SelfHealer: Switching {service_name} to fallback")

    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary for all services."""
        return {
            "services": {
                name: {
                    "status": s.status,
                    "consecutive_failures": s.consecutive_failures,
                    "last_success": s.last_success,
                    "last_failure": s.last_failure,
                }
                for name, s in self.health_status.items()
            },
            "total_actions": len(self.execution_history),
            "successful_actions": sum(1 for a in self.execution_history if a.success),
            "failed_actions": sum(
                1 for a in self.execution_history if not a.success and a.executed
            ),
        }


# ============================================
# CONVENIENCE: Create healer for Catalyst services
# ============================================


def create_catalyst_healer() -> SelfHealer:
    """Create a SelfHealer configured for Catalyst services."""
    services = [
        "ollama",
        "neo4j",
        "graphiti-mcp",
        "playwright-mcp",
        "puppeteer-mcp",
        "fetch-mcp",
        "exa-mcp",
        "ollama-mcp",
        "github-mcp",
        "git-mcp",
        "sqlite-mcp",
        "context7-mcp",
        "grep-app-mcp",
        "obsidian-mcp",
        "shadcn-mcp",
    ]

    policies = [
        HealingPolicy(
            name="restart_mcp_on_degraded",
            trigger_condition="degraded",
            action_type=HealingActionType.RESTART,
            action_target="*",
            cooldown_seconds=30.0,
            max_retries=3,
        ),
        HealingPolicy(
            name="notify_on_critical",
            trigger_condition="unhealthy",
            action_type=HealingActionType.NOTIFY,
            action_target="*",
            cooldown_seconds=300.0,
            max_retries=1,
        ),
    ]

    return SelfHealer(services=services, policies=policies)
