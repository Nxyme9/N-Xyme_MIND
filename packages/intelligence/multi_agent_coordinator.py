"""Multi-Agent Coordinator

Routes complex tasks to multiple agents in parallel and synthesizes results.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger("multi-agent-coordinator")


@dataclass
class AgentTask:
    """A task assigned to a specific agent."""
    agent: str
    prompt: str
    priority: int = 0
    timeout_ms: float = 30000


@dataclass
class AgentResult:
    """Result from an agent task."""
    agent: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    latency_ms: float = 0


@dataclass
class CoordinationPlan:
    """Plan for multi-agent coordination."""
    tasks: List[AgentTask] = field(default_factory=list)
    synthesis_prompt: Optional[str] = None
    max_parallel: int = 3


class MultiAgentCoordinator:
    """Coordinates multiple agents for complex tasks."""
    
    def __init__(self, router=None):
        self._router = router
        self._task_executor: Optional[Callable] = None
    
    def set_task_executor(self, executor: Callable):
        """Set the function to execute agent tasks."""
        self._task_executor = executor
    
    def create_coordination_plan(self, task_description: str, level: int) -> CoordinationPlan:
        """Create a coordination plan based on task complexity."""
        plan = CoordinationPlan()
        
        if level <= 2:
            # Simple tasks: single agent
            plan.tasks = [
                AgentTask(agent="hephaestus", prompt=task_description, priority=1)
            ]
            plan.max_parallel = 1
        
        elif level == 3:
            # Moderate tasks: research + implementation
            plan.tasks = [
                AgentTask(agent="explore", prompt=f"Research and find patterns for: {task_description}", priority=1),
                AgentTask(agent="hephaestus", prompt=f"Implement: {task_description}", priority=2),
            ]
            plan.max_parallel = 2
            plan.synthesis_prompt = f"Synthesize research and implementation for: {task_description}"
        
        elif level == 4:
            # Complex tasks: planning + implementation + review
            plan.tasks = [
                AgentTask(agent="prometheus", prompt=f"Create implementation plan for: {task_description}", priority=1),
                AgentTask(agent="hephaestus", prompt=f"Implement: {task_description}", priority=2),
                AgentTask(agent="oracle", prompt=f"Review architecture for: {task_description}", priority=3),
            ]
            plan.max_parallel = 2  # Plan first, then implement + review in parallel
            plan.synthesis_prompt = f"Synthesize plan, implementation, and review for: {task_description}"
        
        elif level == 5:
            # Architect tasks: full coordination
            plan.tasks = [
                AgentTask(agent="metis", prompt=f"Analyze gaps and requirements for: {task_description}", priority=1),
                AgentTask(agent="prometheus", prompt=f"Create detailed plan for: {task_description}", priority=2),
                AgentTask(agent="hephaestus", prompt=f"Implement: {task_description}", priority=3),
                AgentTask(agent="oracle", prompt=f"Review architecture for: {task_description}", priority=4),
                AgentTask(agent="momus", prompt=f"Red-team analysis for: {task_description}", priority=5),
            ]
            plan.max_parallel = 2
            plan.synthesis_prompt = f"Synthesize full analysis for: {task_description}"
        
        return plan
    
    async def execute_plan(self, plan: CoordinationPlan, task_description: str) -> Dict[str, Any]:
        """Execute a coordination plan."""
        start_time = time.time()
        results: List[AgentResult] = []
        
        # Sort tasks by priority
        sorted_tasks = sorted(plan.tasks, key=lambda t: t.priority)
        
        # Execute tasks in batches based on max_parallel
        for i in range(0, len(sorted_tasks), plan.max_parallel):
            batch = sorted_tasks[i:i + plan.max_parallel]
            
            # Execute batch in parallel
            batch_tasks = [self._execute_agent_task(task) for task in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for task, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    results.append(AgentResult(
                        agent=task.agent,
                        success=False,
                        error=str(result),
                        latency_ms=(time.time() - start_time) * 1000
                    ))
                else:
                    results.append(result)
        
        # Synthesize results if needed
        synthesis = None
        if plan.synthesis_prompt and results:
            synthesis = await self._synthesize_results(plan.synthesis_prompt, results)
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        return {
            "task_description": task_description,
            "plan": {
                "total_tasks": len(plan.tasks),
                "max_parallel": plan.max_parallel,
            },
            "results": [
                {
                    "agent": r.agent,
                    "success": r.success,
                    "error": r.error,
                    "latency_ms": r.latency_ms,
                }
                for r in results
            ],
            "synthesis": synthesis,
            "total_latency_ms": elapsed_ms,
            "success_rate": sum(1 for r in results if r.success) / len(results) if results else 0,
        }
    
    async def _execute_agent_task(self, task: AgentTask) -> AgentResult:
        """Execute a single agent task."""
        start_time = time.time()
        
        try:
            if self._task_executor:
                result = await self._task_executor(task.agent, task.prompt)
                return AgentResult(
                    agent=task.agent,
                    success=True,
                    result=result,
                    latency_ms=(time.time() - start_time) * 1000
                )
            else:
                # No executor set, simulate success
                return AgentResult(
                    agent=task.agent,
                    success=True,
                    result={"status": "simulated", "prompt": task.prompt},
                    latency_ms=(time.time() - start_time) * 1000
                )
        except Exception as e:
            return AgentResult(
                agent=task.agent,
                success=False,
                error=str(e),
                latency_ms=(time.time() - start_time) * 1000
            )
    
    async def _synthesize_results(self, prompt: str, results: List[AgentResult]) -> str:
        """Synthesize results from multiple agents."""
        # In a real implementation, this would call an LLM to synthesize
        # For now, return a summary
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        summary = f"Synthesis: {len(successful)}/{len(results)} agents succeeded.\n"
        if successful:
            summary += f"Successful: {', '.join(r.agent for r in successful)}\n"
        if failed:
            summary += f"Failed: {', '.join(f'{r.agent} ({r.error})' for r in failed)}\n"
        
        return summary


# Global coordinator instance
_coordinator = None

def get_coordinator() -> MultiAgentCoordinator:
    """Get or create the global coordinator."""
    global _coordinator
    if _coordinator is None:
        _coordinator = MultiAgentCoordinator()
    return _coordinator
