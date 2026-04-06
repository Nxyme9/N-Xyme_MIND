"""Task Router - LLM-based intelligent routing with cost/latency scoring."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TaskRouter:
    """Intelligent task router with capability matching and load balancing."""
    
    def __init__(self, agent_registry=None):
        self.agent_registry = agent_registry
        self.load_balancer = "round_robin"  # round_robin, least_loaded, cost_aware
        self.agent_loads: Dict[str, int] = {}
        self.agent_costs: Dict[str, float] = {}
    
    def route_task(self, task: Dict[str, Any]) -> Optional[str]:
        """Route task to optimal agent based on capabilities and load."""
        if not self.agent_registry:
            return None
        
        # Get available agents
        agents = self.agent_registry.get_all_agents()
        if not agents:
            return None
        
        # Get task requirements
        task_capabilities = task.get("capabilities", [])
        task_priority = task.get("priority", 1)
        
        # Filter agents by capability
        matching_agents = []
        for name, card in agents.items():
            agent_caps = card.get("capabilities", [])
            if any(cap in agent_caps for cap in task_capabilities):
                matching_agents.append(name)
        
        if not matching_agents:
            # Fallback to first available agent
            return list(agents.keys())[0] if agents else None
        
        # Select based on load balancing strategy
        if self.load_balancer == "round_robin":
            return self._round_robin_select(matching_agents)
        elif self.load_balancer == "least_loaded":
            return self._least_loaded_select(matching_agents)
        elif self.load_balancer == "cost_aware":
            return self._cost_aware_select(matching_agents)
        else:
            return matching_agents[0]
    
    def _round_robin_select(self, agents: List[str]) -> str:
        """Select agent using round-robin."""
        if not agents:
            return None
        
        # Simple round-robin based on current loads
        min_load = min(self.agent_loads.get(a, 0) for a in agents)
        for agent in agents:
            if self.agent_loads.get(agent, 0) == min_load:
                return agent
        return agents[0]
    
    def _least_loaded_select(self, agents: List[str]) -> str:
        """Select agent with least current load."""
        if not agents:
            return None
        
        min_load = min(self.agent_loads.get(a, 0) for a in agents)
        for agent in agents:
            if self.agent_loads.get(agent, 0) == min_load:
                return agent
        return agents[0]
    
    def _cost_aware_select(self, agents: List[str]) -> str:
        """Select agent based on cost and load."""
        if not agents:
            return None
        
        # Simple cost-aware selection (lower cost + lower load = better)
        best_score = float('inf')
        best_agent = agents[0]
        
        for agent in agents:
            cost = self.agent_costs.get(agent, 1.0)
            load = self.agent_loads.get(agent, 0)
            score = cost + (load * 0.1)  # Weight load lightly
            if score < best_score:
                best_score = score
                best_agent = agent
        
        return best_agent
    
    def record_task_start(self, agent: str):
        """Record that a task started on an agent."""
        self.agent_loads[agent] = self.agent_loads.get(agent, 0) + 1
    
    def record_task_end(self, agent: str, cost: float = 0.0):
        """Record that a task ended on an agent."""
        self.agent_loads[agent] = max(0, self.agent_loads.get(agent, 0) - 1)
        if cost > 0:
            self.agent_costs[agent] = cost
    
    def get_status(self) -> Dict[str, Any]:
        """Get router status."""
        return {
            "load_balancer": self.load_balancer,
            "agent_loads": self.agent_loads.copy(),
            "agent_costs": self.agent_costs.copy(),
        }


# Global router instance
_router = None


def get_task_router(agent_registry=None) -> TaskRouter:
    """Get or create the global task router."""
    global _router
    if _router is None:
        _router = TaskRouter(agent_registry)
    return _router
