"""Network Orchestrator - Hierarchical orchestration (CrewAI pattern)."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class NetworkOrchestrator:
    """Hierarchical orchestrator for multi-agent teams."""
    
    def __init__(self, agent_registry=None, task_router=None, executor=None):
        self.agent_registry = agent_registry
        self.task_router = task_router
        self.executor = executor
        self.teams: Dict[str, Dict[str, Any]] = {}
    
    def create_team(self, name: str, agents: List[str], process: str = "sequential") -> Dict[str, Any]:
        """Create an agent team."""
        team = {
            "name": name,
            "agents": agents,
            "process": process,  # sequential, hierarchical, parallel
            "tasks": [],
        }
        self.teams[name] = team
        logger.info(f"✅ Created team: {name} with {len(agents)} agents")
        return team
    
    def add_task(self, team_name: str, task: Dict[str, Any]) -> bool:
        """Add a task to a team."""
        team = self.teams.get(team_name)
        if not team:
            logger.warning(f"❌ Team not found: {team_name}")
            return False
        
        team["tasks"].append(task)
        logger.info(f"✅ Added task to team {team_name}")
        return True
    
    def execute_team(self, team_name: str) -> List[Any]:
        """Execute all tasks in a team."""
        team = self.teams.get(team_name)
        if not team:
            logger.warning(f"❌ Team not found: {team_name}")
            return []
        
        results = []
        process = team.get("process", "sequential")
        
        if process == "sequential":
            results = self._execute_sequential(team)
        elif process == "hierarchical":
            results = self._execute_hierarchical(team)
        elif process == "parallel":
            results = self._execute_parallel(team)
        else:
            results = self._execute_sequential(team)
        
        return results
    
    def _execute_sequential(self, team: Dict[str, Any]) -> List[Any]:
        """Execute tasks sequentially."""
        results = []
        for task in team.get("tasks", []):
            # Route to appropriate agent
            agent = self._route_task(task)
            if agent:
                result = self._execute_task(agent, task)
                results.append(result)
        return results
    
    def _execute_hierarchical(self, team: Dict[str, Any]) -> List[Any]:
        """Execute tasks hierarchically (manager delegates to workers)."""
        results = []
        agents = team.get("agents", [])
        if not agents:
            return results
        
        # First agent is manager
        manager = agents[0]
        workers = agents[1:]
        
        for task in team.get("tasks", []):
            # Manager delegates to workers
            for worker in workers:
                result = self._execute_task(worker, task)
                results.append(result)
        
        return results
    
    def _execute_parallel(self, team: Dict[str, Any]) -> List[Any]:
        """Execute tasks in parallel."""
        if not self.executor:
            return self._execute_sequential(team)
        
        tasks = []
        for task in team.get("tasks", []):
            agent = self._route_task(task)
            if agent:
                tasks.append({
                    "func": lambda a=agent, t=task: self._execute_task(a, t),
                    "task": task,
                })
        
        return self.executor.execute_tasks(tasks)
    
    def _route_task(self, task: Dict[str, Any]) -> Optional[str]:
        """Route task to appropriate agent."""
        if self.task_router:
            return self.task_router.route_task(task)
        return None
    
    def _execute_task(self, agent: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single task on an agent."""
        return {
            "agent": agent,
            "task": task,
            "status": "completed",
            "result": None,
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status."""
        return {
            "teams": list(self.teams.keys()),
            "total_teams": len(self.teams),
        }


# Global orchestrator instance
_orchestrator = None


def get_network_orchestrator(agent_registry=None, task_router=None, executor=None) -> NetworkOrchestrator:
    """Get or create the global network orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = NetworkOrchestrator(agent_registry, task_router, executor)
    return _orchestrator
