"""Delegation optimizer module - defines optimization targets for delegation."""

from dataclasses import dataclass
from enum import Enum


class OptimizationTarget(Enum):
    """Optimization targets for delegation decisions."""

    SPEED = "speed"
    SUCCESS = "success"
    COST = "cost"


@dataclass
class DelegationScore:
    """Score for a delegation decision."""

    agent: str
    speed_score: float  # 0-1
    success_score: float  # 0-1
    cost_score: float  # 0-1
    overall_score: float


# Agent capability registry
AGENT_CAPABILITIES: dict = {
    "sisyphus": {"speed": 0.9, "reliability": 0.85, "cost": 0.7},
    "oracle": {"speed": 0.7, "reliability": 0.95, "cost": 0.4},
    "hephaestus": {"speed": 0.95, "reliability": 0.9, "cost": 0.8},
    "explore": {"speed": 0.9, "reliability": 0.8, "cost": 0.9},
    "librarian": {"speed": 0.85, "reliability": 0.8, "cost": 0.85},
    "metis": {"speed": 0.6, "reliability": 0.9, "cost": 0.3},
    "momus": {"speed": 0.7, "reliability": 0.85, "cost": 0.5},
    "prometheus": {"speed": 0.8, "reliability": 0.85, "cost": 0.6},
    "atlas": {"speed": 0.9, "reliability": 0.85, "cost": 0.75},
    "sisyphus-junior": {"speed": 1.0, "reliability": 0.7, "cost": 0.95},
    "multimodal-looker": {"speed": 0.85, "reliability": 0.8, "cost": 0.7},
}


# Complexity keywords for L1-L5 detection
COMPLEXITY_KEYWORDS: dict = {
    "L1": ["typo", "fix", "bump", "simple"],
    "L2": ["bug", "single", "file", "change"],
    "L3": ["feature", "add", "implement", "multi"],
    "L4": ["build", "system", "design", "complex"],
    "L5": ["architecture", "redesign", "refactor", "expert"],
}

# Agent tier mapping
AGENT_TIER_MAP: dict = {
    "L1": "sisyphus-junior",
    "L2": "hephaestus",
    "L3": "hephaestus",
    "L4": "prometheus",
    "L5": "metis",
}


class DelegationOptimizer:
    """Optimizer for delegation decisions."""

    def __init__(self):
        self.capabilities = AGENT_CAPABILITIES.copy()
        self.complexity_history: dict = {}

    def detect_complexity(self, task: str) -> str:
        """Detect task complexity (L1-L5) using keyword detection."""
        task_lower = task.lower()

        # Check complexity keywords
        for level, keywords in COMPLEXITY_KEYWORDS.items():
            for kw in keywords:
                if kw in task_lower:
                    return level

        # Default fallback
        return "L3"

    def get_agent_for_complexity(self, complexity: str) -> str:
        """Map complexity to appropriate agent tier."""
        return AGENT_TIER_MAP.get(complexity, "hephaestus")

    def optimize(
        self, task: str, target: OptimizationTarget = OptimizationTarget.SUCCESS
    ) -> DelegationScore:
        """Optimize delegation for a task."""
        # Detect complexity
        complexity = self.detect_complexity(task)

        # Get appropriate agent
        agent = self.get_agent_for_complexity(complexity)

        # Get agent capabilities
        caps = self.capabilities.get(
            agent, {"speed": 0.8, "reliability": 0.8, "cost": 0.8}
        )

        # Calculate scores based on target
        speed = caps["speed"]
        reliability = caps["reliability"]
        cost = caps["cost"]

        # Overall score weighted by target
        if target == OptimizationTarget.SPEED:
            overall = speed * 0.7 + reliability * 0.2 + cost * 0.1
        elif target == OptimizationTarget.SUCCESS:
            overall = reliability * 0.7 + speed * 0.2 + cost * 0.1
        else:  # COST
            overall = cost * 0.7 + speed * 0.2 + reliability * 0.1

        return DelegationScore(
            agent=agent,
            speed_score=speed,
            success_score=reliability,
            cost_score=cost,
            overall_score=overall,
        )


# Default optimizer instance
default_optimizer = DelegationOptimizer()
