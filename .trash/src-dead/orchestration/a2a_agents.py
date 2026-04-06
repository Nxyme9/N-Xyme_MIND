"""
A2A (Agent-to-Agent) Protocol Implementation
Enables agent discovery and task delegation.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class AgentSkill:
    """A skill that an agent can perform."""

    id: str
    name: str
    description: str
    tags: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    input_modes: List[str] = field(default_factory=lambda: ["text"])
    output_modes: List[str] = field(default_factory=lambda: ["text"])


@dataclass
class AgentCard:
    """Agent capability discovery card (A2A standard)."""

    name: str
    description: str
    url: str
    version: str = "1.0.0"
    skills: List[AgentSkill] = field(default_factory=list)
    capabilities: Dict[str, bool] = field(default_factory=dict)
    default_input_modes: List[str] = field(default_factory=lambda: ["text"])
    default_output_modes: List[str] = field(default_factory=lambda: ["text"])

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class AgentTask:
    """A task to delegate between agents."""

    id: str
    status: str  # pending, running, completed, failed
    skill_id: str
    input: Dict[str, Any]
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class A2AAgentRegistry:
    """Registry of available agents and their capabilities."""

    def __init__(self):
        self.agents: Dict[str, AgentCard] = {}
        self.tasks: Dict[str, AgentTask] = {}

    def register(self, card: AgentCard):
        """Register an agent."""
        self.agents[card.name] = card
        logger.info(f"A2A: Registered agent '{card.name}' with {len(card.skills)} skills")

    def unregister(self, name: str):
        """Unregister an agent."""
        if name in self.agents:
            del self.agents[name]
            logger.info(f"A2A: Unregistered agent '{name}'")

    def discover(self, skill_filter: Optional[str] = None) -> List[AgentCard]:
        """Discover agents, optionally filtered by skill."""
        if not skill_filter:
            return list(self.agents.values())

        matching = []
        for agent in self.agents.values():
            for skill in agent.skills:
                if (
                    skill_filter.lower() in skill.name.lower()
                    or skill_filter.lower() in skill.description.lower()
                    or skill_filter in skill.tags
                ):
                    matching.append(agent)
                    break
        return matching

    def find_agent_for_task(self, task_description: str) -> Optional[AgentCard]:
        """Find best agent for a task description."""
        task_lower = task_description.lower()

        for agent in self.agents.values():
            for skill in agent.skills:
                if skill.name.lower() in task_lower or any(tag in task_lower for tag in skill.tags):
                    return agent

        return None

    def get_agent(self, name: str) -> Optional[AgentCard]:
        """Get agent by name."""
        return self.agents.get(name)

    def list_agents(self) -> List[str]:
        """List all registered agent names."""
        return list(self.agents.keys())


# CATALYST Agent Cards
CATALYST_AGENTS = {
    "sisyphus": AgentCard(
        name="sisyphus",
        description="Orchestration agent - delegates work, verifies results",
        url="local://sisyphus",
        skills=[
            AgentSkill(
                id="orchestrate",
                name="orchestrate",
                description="Delegate tasks to specialists",
                tags=["orchestration", "delegate"],
            ),
            AgentSkill(
                id="verify",
                name="verify",
                description="Verify work quality",
                tags=["quality", "verify"],
            ),
        ],
        capabilities={"streaming": True, "pushNotifications": False},
    ),
    "prometheus": AgentCard(
        name="prometheus",
        description="Planning agent - creates detailed plans",
        url="local://prometheus",
        skills=[
            AgentSkill(
                id="plan",
                name="plan",
                description="Create implementation plans",
                tags=["planning", "architecture"],
            ),
        ],
        capabilities={"streaming": True, "pushNotifications": False},
    ),
    "hephaestus": AgentCard(
        name="hephaestus",
        description="Implementation agent - writes code",
        url="local://hephaestus",
        skills=[
            AgentSkill(
                id="implement",
                name="implement",
                description="Write code implementations",
                tags=["coding", "implementation"],
            ),
        ],
        capabilities={"streaming": True, "pushNotifications": False},
    ),
    "oracle": AgentCard(
        name="oracle",
        description="Consultation agent - architecture and debugging advice",
        url="local://oracle",
        skills=[
            AgentSkill(
                id="consult",
                name="consult",
                description="Provide expert consultation",
                tags=["consulting", "architecture", "debugging"],
            ),
        ],
        capabilities={"streaming": True, "pushNotifications": False},
    ),
    "explore": AgentCard(
        name="explore",
        description="Code exploration agent - find patterns and implementations",
        url="local://explore",
        skills=[
            AgentSkill(
                id="search",
                name="search",
                description="Search codebase for patterns",
                tags=["search", "explore", "grep"],
            ),
        ],
        capabilities={"streaming": True, "pushNotifications": False},
    ),
    "librarian": AgentCard(
        name="librarian",
        description="Research agent - find external documentation and examples",
        url="local://librarian",
        skills=[
            AgentSkill(
                id="research",
                name="research",
                description="Research external resources",
                tags=["research", "docs", "external"],
            ),
        ],
        capabilities={"streaming": True, "pushNotifications": False},
    ),
}


def get_registry() -> A2AAgentRegistry:
    """Get global agent registry with CATALYST agents pre-registered."""
    registry = A2AAgentRegistry()
    for card in CATALYST_AGENTS.values():
        registry.register(card)
    return registry


# Global instance
REGISTRY = get_registry()
