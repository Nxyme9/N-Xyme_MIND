"""Agent Coordinator — Coordinate multiple agents"""

import logging, time
from typing import Dict, List

logger = logging.getLogger(__name__)


class AgentCoordinator:
    def __init__(self):
        self._agents: Dict[str, dict] = {}
        self._tasks: List[dict] = []

    def register_agent(self, name: str, capabilities: List[str]):
        self._agents[name] = {"capabilities": capabilities, "status": "idle", "current_task": None}

    def assign_task(self, task_type: str, task_data: dict) -> str:
        for name, agent in self._agents.items():
            if task_type in agent["capabilities"] and agent["status"] == "idle":
                agent["status"] = "busy"
                agent["current_task"] = task_data
                task_id = f"task_{len(self._tasks)}"
                self._tasks.append(
                    {
                        "id": task_id,
                        "agent": name,
                        "type": task_type,
                        "data": task_data,
                        "status": "assigned",
                    }
                )
                logger.info(f"AgentCoordinator: Assigned {task_type} to {name}")
                return task_id
        logger.warning(f"AgentCoordinator: No available agent for {task_type}")
        return ""

    def complete_task(self, agent_name: str):
        if agent_name in self._agents:
            self._agents[agent_name]["status"] = "idle"
            self._agents[agent_name]["current_task"] = None

    def get_status(self) -> Dict:
        return {
            name: {"status": a["status"], "task": a["current_task"]}
            for name, a in self._agents.items()
        }
