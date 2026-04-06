"""Agent Health Monitoring

Monitors agent health, detects failures, and provides auto-recovery.
"""

import time
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("health-monitor")


class AgentHealthStatus(Enum):
    """Health status of an agent."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class AgentHealth:
    """Health information for an agent."""
    agent: str
    status: AgentHealthStatus = AgentHealthStatus.UNKNOWN
    last_check: float = 0.0
    last_success: float = 0.0
    last_failure: float = 0.0
    consecutive_failures: int = 0
    total_checks: int = 0
    total_successes: int = 0
    total_failures: int = 0
    avg_response_time_ms: float = 0.0
    last_error: Optional[str] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.total_successes + self.total_failures
        return self.total_successes / total if total > 0 else 0.0
    
    def update_status(self):
        """Update health status based on metrics."""
        if self.total_checks == 0:
            self.status = AgentHealthStatus.UNKNOWN
        elif self.consecutive_failures >= 5:
            self.status = AgentHealthStatus.UNHEALTHY
        elif self.consecutive_failures >= 2:
            self.status = AgentHealthStatus.DEGRADED
        elif self.success_rate >= 0.9:
            self.status = AgentHealthStatus.HEALTHY
        elif self.success_rate >= 0.7:
            self.status = AgentHealthStatus.DEGRADED
        else:
            self.status = AgentHealthStatus.UNHEALTHY


class HealthMonitor:
    """Monitors agent health and provides auto-recovery."""
    
    def __init__(self, health_file: str = ".sisyphus/agent_health.json"):
        self.health_file = Path(health_file)
        self.health_file.parent.mkdir(parents=True, exist_ok=True)
        self._agents: Dict[str, AgentHealth] = {}
        self._load_health()
    
    def _load_health(self):
        """Load health data from file."""
        if self.health_file.exists():
            try:
                with open(self.health_file) as f:
                    data = json.load(f)
                
                for agent_name, agent_data in data.items():
                    self._agents[agent_name] = AgentHealth(
                        agent=agent_name,
                        status=AgentHealthStatus(agent_data.get('status', 'unknown')),
                        last_check=agent_data.get('last_check', 0.0),
                        last_success=agent_data.get('last_success', 0.0),
                        last_failure=agent_data.get('last_failure', 0.0),
                        consecutive_failures=agent_data.get('consecutive_failures', 0),
                        total_checks=agent_data.get('total_checks', 0),
                        total_successes=agent_data.get('total_successes', 0),
                        total_failures=agent_data.get('total_failures', 0),
                        avg_response_time_ms=agent_data.get('avg_response_time_ms', 0.0),
                        last_error=agent_data.get('last_error')
                    )
            except Exception as e:
                logger.error(f"Error loading health data: {e}")
    
    def _save_health(self):
        """Save health data to file."""
        data = {}
        for agent_name, health in self._agents.items():
            data[agent_name] = {
                'agent': health.agent,
                'status': health.status.value,
                'last_check': health.last_check,
                'last_success': health.last_success,
                'last_failure': health.last_failure,
                'consecutive_failures': health.consecutive_failures,
                'total_checks': health.total_checks,
                'total_successes': health.total_successes,
                'total_failures': health.total_failures,
                'avg_response_time_ms': health.avg_response_time_ms,
                'last_error': health.last_error
            }
        
        with open(self.health_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def record_check(self, agent: str, success: bool, response_time_ms: float, error: str = None):
        """Record a health check result."""
        if agent not in self._agents:
            self._agents[agent] = AgentHealth(agent=agent)
        
        health = self._agents[agent]
        health.last_check = time.time()
        health.total_checks += 1
        
        # Update response time (EMA)
        alpha = 0.1
        health.avg_response_time_ms = alpha * response_time_ms + (1 - alpha) * health.avg_response_time_ms
        
        if success:
            health.last_success = time.time()
            health.total_successes += 1
            health.consecutive_failures = 0
            health.last_error = None
        else:
            health.last_failure = time.time()
            health.total_failures += 1
            health.consecutive_failures += 1
            health.last_error = error
        
        health.update_status()
        self._save_health()
        
        if not success:
            logger.warning(f"Agent '{agent}' health check failed: {error} (consecutive: {health.consecutive_failures})")
    
    def is_healthy(self, agent: str) -> bool:
        """Check if an agent is healthy."""
        health = self._agents.get(agent)
        if not health:
            return True  # Unknown agents are considered healthy
        
        return health.status in (AgentHealthStatus.HEALTHY, AgentHealthStatus.DEGRADED)
    
    def get_healthy_agents(self) -> List[str]:
        """Get list of healthy agents."""
        return [
            agent for agent, health in self._agents.items()
            if health.status in (AgentHealthStatus.HEALTHY, AgentHealthStatus.DEGRADED)
        ]
    
    def get_unhealthy_agents(self) -> List[str]:
        """Get list of unhealthy agents."""
        return [
            agent for agent, health in self._agents.items()
            if health.status == AgentHealthStatus.UNHEALTHY
        ]
    
    def get_agent_health(self, agent: str) -> Optional[Dict[str, Any]]:
        """Get health information for an agent."""
        health = self._agents.get(agent)
        if not health:
            return None
        
        return {
            'agent': health.agent,
            'status': health.status.value,
            'success_rate': health.success_rate,
            'consecutive_failures': health.consecutive_failures,
            'avg_response_time_ms': health.avg_response_time_ms,
            'last_check': health.last_check,
            'last_error': health.last_error
        }
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health."""
        if not self._agents:
            return {'status': 'unknown', 'agents': {}}
        
        healthy = sum(1 for h in self._agents.values() if h.status == AgentHealthStatus.HEALTHY)
        degraded = sum(1 for h in self._agents.values() if h.status == AgentHealthStatus.DEGRADED)
        unhealthy = sum(1 for h in self._agents.values() if h.status == AgentHealthStatus.UNHEALTHY)
        total = len(self._agents)
        
        if unhealthy > 0:
            status = 'degraded'
        elif degraded > total * 0.3:
            status = 'degraded'
        else:
            status = 'healthy'
        
        return {
            'status': status,
            'total_agents': total,
            'healthy': healthy,
            'degraded': degraded,
            'unhealthy': unhealthy,
            'agents': {
                name: self.get_agent_health(name)
                for name in self._agents
            }
        }
    
    def reset_agent_health(self, agent: str):
        """Reset health for an agent (after recovery)."""
        if agent in self._agents:
            health = self._agents[agent]
            health.consecutive_failures = 0
            health.status = AgentHealthStatus.HEALTHY
            health.last_error = None
            self._save_health()
            logger.info(f"Agent '{agent}' health reset to healthy")


# Global health monitor instance
_health_monitor = None

def get_health_monitor() -> HealthMonitor:
    """Get or create the global health monitor."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor
