"""Agent health monitoring for N-Xyme MIND Dashboard.

This module provides the AgentHealth dataclass and AgentMonitor class
for monitoring agent health status in the N-Xyme orchestration system.
"""

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AgentHealth:
    """Represents the health status of a single agent.
    
    Attributes:
        agent_name: Name of the agent.
        status: Current health status - "healthy", "degraded", or "down".
        response_time_ms: Last recorded response time in milliseconds.
        success_count: Number of successful operations.
        failure_count: Number of failed operations.
        last_check: Unix timestamp of last check.
    """
    agent_name: str
    status: str = "healthy"
    response_time_ms: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    last_check: float = field(default_factory=time.time)
    
    @property
    def success_rate(self) -> float:
        """Calculate the success rate as a percentage.
        
        Returns:
            Success rate between 0 and 100.
        """
        total = self.success_count + self.failure_count
        if total == 0:
            return 100.0
        return (self.success_count / total) * 100


class AgentMonitor:
    """Monitors health status of agents in the N-Xyme system.
    
    This class tracks the health of various agents, recording success
    and failure counts to determine their operational status.
    
    Attributes:
        _agents: Dictionary mapping agent names to their health status.
    """
    
    DEFAULT_AGENTS = ["sisyphus", "hephaestus", "oracle", "explore", "librarian"]
    
    def __init__(self, agents: Optional[list[str]] = None) -> None:
        """Initialize the agent monitor with default or custom agents.
        
        Args:
            agents: Optional list of agent names to track. Defaults to DEFAULT_AGENTS.
        """
        agent_list = agents if agents is not None else self.DEFAULT_AGENTS
        self._agents: dict[str, AgentHealth] = {
            name: AgentHealth(agent_name=name) for name in agent_list
        }
    
    def _determine_status(self, agent: AgentHealth) -> str:
        """Determine the health status based on success rate.
        
        Args:
            agent: The AgentHealth instance to evaluate.
            
        Returns:
            Status string: "healthy", "degraded", or "down".
        """
        rate = agent.success_rate
        if rate > 90:
            return "healthy"
        elif rate >= 70:
            return "degraded"
        else:
            return "down"
    
    def check_agent(self, agent_name: str) -> AgentHealth:
        """Get the health status for a specific agent.
        
        Args:
            agent_name: Name of the agent to check.
            
        Returns:
            AgentHealth instance for the requested agent.
            
        Raises:
            KeyError: If the agent is not tracked.
        """
        if agent_name not in self._agents:
            raise KeyError(f"Unknown agent: {agent_name}")
        
        agent = self._agents[agent_name]
        agent.last_check = time.time()
        agent.status = self._determine_status(agent)
        return agent
    
    def check_all_agents(self) -> list[AgentHealth]:
        """Get health status for all tracked agents.
        
        Returns:
            List of AgentHealth instances for all tracked agents.
        """
        return [self.check_agent(name) for name in self._agents]
    
    def get_status(self, agent_name: str) -> str:
        """Get the status string for a specific agent.
        
        Args:
            agent_name: Name of the agent.
            
        Returns:
            Status string: "healthy", "degraded", or "down".
            Returns "unknown" for untracked agents.
        """
        if agent_name not in self._agents:
            return "unknown"
        return self.check_agent(agent_name).status
    
    def get_all_statuses(self) -> dict[str, str]:
        """Get status strings for all tracked agents.
        
        Returns:
            Dictionary mapping agent names to their status strings.
        """
        return {name: self.get_status(name) for name in self._agents}
    
    def record_success(self, agent_name: str) -> None:
        """Record a successful operation for an agent.
        
        If the agent is not tracked, it will be added automatically.
        
        Args:
            agent_name: Name of the agent that succeeded.
        """
        if agent_name not in self._agents:
            self._agents[agent_name] = AgentHealth(agent_name=agent_name)
        
        self._agents[agent_name].success_count += 1
        self._agents[agent_name].last_check = time.time()
        self._agents[agent_name].status = self._determine_status(self._agents[agent_name])
    
    def record_failure(self, agent_name: str) -> None:
        """Record a failed operation for an agent.
        
        If the agent is not tracked, it will be added automatically.
        
        Args:
            agent_name: Name of the agent that failed.
        """
        if agent_name not in self._agents:
            self._agents[agent_name] = AgentHealth(agent_name=agent_name)
        
        self._agents[agent_name].failure_count += 1
        self._agents[agent_name].last_check = time.time()
        self._agents[agent_name].status = self._determine_status(self._agents[agent_name])
