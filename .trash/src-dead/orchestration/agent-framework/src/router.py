from typing import Dict, List, Any, Optional
from .agent_config import AgentConfig
from .tool_registry import (
    ToolRegistry,
    RoundCapEnforcer,
    ToolNotRegisteredError,
    RoundCapExceededError,
)


class Router:
    """BMAD hybrid workflow router for task delegation.

    Supports tool allowlist enforcement via ToolRegistry and
    reasoning round caps via RoundCapEnforcer.
    """

    def __init__(
        self,
        agent_configs_dir: str = "configs/opencode/agents",
        max_rounds: int = 6,
    ):
        self.agent_configs_dir = agent_configs_dir
        self.agents = self._load_agents()
        self.bmad_threshold = 0.2

        # Tool registry for allowlist enforcement
        self.tool_registry = ToolRegistry()

        # Round cap enforcer (per-task state)
        self._round_enforcer = RoundCapEnforcer(max_rounds=max_rounds)
        self._task_rounds: Dict[str, RoundCapEnforcer] = {}

    def _load_agents(self) -> Dict[str, AgentConfig]:
        """Load all agent configurations from the agents directory."""
        import os

        agents = {}
        for filename in os.listdir(self.agent_configs_dir):
            if filename.endswith(".yaml"):
                filepath = os.path.join(self.agent_configs_dir, filename)
                try:
                    config = AgentConfig.load(filepath)
                    agents[config.get_name()] = config
                except Exception as e:
                    print(f"Warning: Could not load agent config {filename}: {e}")
        return agents

    def route_task(
        self, task_description: str, context: Dict[str, Any] = None
    ) -> AgentConfig:
        """Route a task to the most appropriate agent using BMAD matching."""
        if context is None:
            context = {}

        # Extract keywords from task
        task_keywords = self._extract_keywords(task_description)

        # Score each agent based on capabilities and skills
        best_agent = None
        best_score = 0

        for agent_name, agent_config in self.agents.items():
            score = self._score_agent(agent_config, task_keywords, context)
            if score > best_score:
                best_score = score
                best_agent = agent_config

        if best_agent and best_score >= self.bmad_threshold:
            return best_agent
        else:
            # Default to planner agent if no good match
            return self.agents.get("planner")

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from task description."""
        # Simple keyword extraction - can be improved with NLP
        words = text.lower().split()
        # Remove common stop words
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
        }
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        return keywords

    def _score_agent(
        self, agent: AgentConfig, keywords: List[str], context: Dict[str, Any]
    ) -> float:
        """Score an agent based on capability match with task keywords."""
        score = 0.0

        # Score based on capabilities
        capabilities = agent.get_capabilities()
        for keyword in keywords:
            for capability in capabilities:
                if keyword in capability:
                    score += 0.1

        # Score based on skills
        skills = agent.get_skills()
        for keyword in keywords:
            for skill in skills:
                if keyword in skill["name"] or keyword in skill["description"]:
                    score += 0.15

        # Adjust based on agent type
        agent_type = agent.get_type()
        task_type = context.get("task_type", "")

        # Type matching bonuses
        type_bonuses = {
            ("memory", "recall"): 0.3,
            ("memory", "store"): 0.3,
            ("security", "analyze"): 0.3,
            ("capture", "record"): 0.3,
            ("mcp", "search"): 0.2,
        }

        for (t1, t2), bonus in type_bonuses.items():
            if agent_type == t1 and t2 in task_type:
                score += bonus

        return min(score, 1.0)

    def get_all_agents(self) -> List[AgentConfig]:
        """Get all loaded agent configurations."""
        return list(self.agents.values())

    def get_agent_by_name(self, name: str) -> AgentConfig:
        """Get a specific agent by name."""
        return self.agents.get(name)

    # --- Tool execution via registry ---

    def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Execute a tool through the registry (allowlist enforced).

        Args:
            tool_name: Name of the registered tool.
            params: Parameters for the tool handler.

        Returns:
            Validated tool output.

        Raises:
            ToolNotRegisteredError: If tool is not in the allowlist.
        """
        return self.tool_registry.execute_tool(tool_name, params)

    def register_tool(
        self,
        name: str,
        description: str,
        schema: Dict[str, Any],
        handler,
    ) -> None:
        """Register a tool in the router's registry.

        Args:
            name: Unique tool identifier.
            description: Human-readable description.
            schema: JSON Schema for output validation.
            handler: Callable that executes the tool.
        """
        self.tool_registry.register_tool(name, description, schema, handler)

    # --- Round cap enforcement ---

    def start_task_round(self, task_id: str) -> int:
        """Start a reasoning round for a specific task.

        Creates a per-task round enforcer if one doesn't exist.

        Args:
            task_id: Unique task identifier.

        Returns:
            Current round number (1-indexed).

        Raises:
            RoundCapExceededError: If the task has hit its round cap.
        """
        if task_id not in self._task_rounds:
            self._task_rounds[task_id] = RoundCapEnforcer(
                max_rounds=self._round_enforcer.max_rounds
            )
        return self._task_rounds[task_id].start_round()

    def should_synthesize(self, task_id: str) -> bool:
        """Check if a task should synthesize its final response.

        Args:
            task_id: Unique task identifier.

        Returns:
            True if the task has reached its round cap.
        """
        enforcer = self._task_rounds.get(task_id)
        if enforcer is None:
            return False
        return enforcer.should_synthesize()

    def get_remaining_rounds(self, task_id: str) -> int:
        """Get remaining rounds for a task.

        Args:
            task_id: Unique task identifier.

        Returns:
            Number of rounds remaining (0 if task unknown or exhausted).
        """
        enforcer = self._task_rounds.get(task_id)
        if enforcer is None:
            return self._round_enforcer.max_rounds
        return enforcer.get_remaining_rounds()

    def reset_task_rounds(self, task_id: str) -> None:
        """Reset round tracking for a task.

        Args:
            task_id: Unique task identifier.
        """
        if task_id in self._task_rounds:
            self._task_rounds[task_id].reset()
        else:
            self._task_rounds[task_id] = RoundCapEnforcer(
                max_rounds=self._round_enforcer.max_rounds
            )

    def clear_task(self, task_id: str) -> None:
        """Remove all state for a completed task.

        Args:
            task_id: Unique task identifier.
        """
        self._task_rounds.pop(task_id, None)

    def __repr__(self):
        return f"<Router agents={len(self.agents)} tools={len(self.tool_registry.list_tools())}>"
