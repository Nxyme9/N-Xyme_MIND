"""
Dynamic Thinking Effort System

Evaluates task complexity and selects appropriate thinking effort level.
Never goes below medium - always applies meaningful reasoning.

THINKING LEVELS:
- medium: Standard reasoning (default minimum)
- high: Deep analysis for complex tasks
- ultra: Maximum reasoning for critical decisions

Usage:
    from thinking_effort import ThinkingEffort

    effort = ThinkingEffort()
    level = effort.evaluate(task)
    # Returns: "medium", "high", or "ultra"
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


class ThinkingLevel(Enum):
    """Thinking effort levels."""

    MEDIUM = "medium"  # Standard reasoning (minimum)
    HIGH = "high"  # Deep analysis
    ULTRA = "ultra"  # Maximum reasoning


@dataclass
class ComplexityFactors:
    """Factors that contribute to task complexity."""

    # Keyword indicators
    high_keywords: Set[str] = field(
        default_factory=lambda: {
            "research",
            "analyze",
            "investigate",
            "evaluate",
            "assess",
            "architecture",
            "design",
            "system",
            "infrastructure",
            "scalab",
            "debug",
            "diagnose",
            "troubleshoot",
            "root cause",
            "failure",
            "security",
            "vulnerability",
            "authentication",
            "authorization",
            "performance",
            "optimization",
            "bottleneck",
            "profiling",
            "refactor",
            "migration",
            "breaking change",
            "deprecat",
            "integration",
            "api",
            "protocol",
            "interface design",
        }
    )

    ultra_keywords: Set[str] = field(
        default_factory=lambda: {
            "critical",
            "production",
            "emergency",
            "outage",
            "incident",
            "database",
            "schema",
            "migration",
            "rollback",
            "security breach",
            "exploit",
            "zero-day",
            "vulnerability",
            "system-wide",
            "cross-cutting",
            "architectural",
            "compliance",
            "audit",
            "regulatory",
            "gdpr",
            "hipaa",
            "data loss",
            "corruption",
            "recovery",
            "backup",
        }
    )

    # Scope indicators
    multi_file_keywords: Set[str] = field(
        default_factory=lambda: {
            "multi-file",
            "cross-module",
            "across",
            "multiple",
            "all",
            "project-wide",
            "repository",
            "codebase",
        }
    )


class ThinkingEffort:
    """Dynamic thinking effort selector based on task complexity."""

    def __init__(self):
        self.factors = ComplexityFactors()

    def evaluate(
        self,
        task_description: str,
        file_count: int = 1,
        agent: Optional[str] = None,
        category: Optional[str] = None,
    ) -> str:
        """
        Evaluate task complexity and return thinking effort level.

        Args:
            task_description: The task description/prompt
            file_count: Number of files involved in the task
            agent: The agent that will execute (optional)
            category: The task category (optional)

        Returns:
            Thinking level string: "medium", "high", or "ultra"
        """
        score = 0.0

        # Base score from keywords
        score += self._analyze_keywords(task_description)

        # File count impact
        score += self._analyze_file_count(file_count)

        # Agent-specific adjustments
        score += self._analyze_agent(agent)

        # Category adjustments
        score += self._analyze_category(category)

        # Convert score to level
        return self._score_to_level(score)

    def _analyze_keywords(self, description: str) -> float:
        """Analyze keywords in task description."""
        score = 0.0
        desc_lower = description.lower()

        # Check for ultra-level keywords (higher weight)
        ultra_count = sum(1 for kw in self.factors.ultra_keywords if kw in desc_lower)
        score += ultra_count * 4.0  # Each ultra keyword adds significant weight

        # Check for high-level keywords
        high_count = sum(1 for kw in self.factors.high_keywords if kw in desc_lower)
        score += min(high_count * 1.5, 4.5)  # Cap at 3 matches

        # Check for multi-file indicators
        for keyword in self.factors.multi_file_keywords:
            if keyword in desc_lower:
                score += 2.0
                break

        # Question marks indicate analysis needed
        if "?" in description:
            score += 0.5

        # Length indicates complexity
        word_count = len(description.split())
        if word_count > 100:
            score += 2.0
        elif word_count > 50:
            score += 1.0

        return score

    def _analyze_file_count(self, file_count: int) -> float:
        """Analyze impact based on file count."""
        if file_count >= 10:
            return 4.0
        elif file_count >= 5:
            return 2.0
        elif file_count >= 3:
            return 1.0
        return 0.0

    def _analyze_agent(self, agent: Optional[str]) -> float:
        """Adjust score based on agent type."""
        if not agent:
            return 0.0

        # Oracle is for deep reasoning - bump up
        if agent == "oracle":
            return 1.0

        # Hephaestus handles complex implementation
        if agent == "hephaestus":
            return 0.5

        # Prometheus handles planning
        if agent == "prometheus":
            return 0.5

        return 0.0

    def _analyze_category(self, category: Optional[str]) -> float:
        """Adjust score based on task category."""
        if not category:
            return 0.0

        # Category alias mapping for backwards compatibility
        # 9→5 consolidation: ultrabrain→deep, artistry→deep, unspecified-low→quick, unspecified-high→deep
        category_aliases = {
            "ultrabrain": "deep",
            "artistry": "deep",
            "unspecified-low": "quick",
            "unspecified-high": "deep",
        }
        category = category_aliases.get(category, category)

        category_scores = {
            "deep": 2.5,  # Updated: consolidated from ultrabrain (3.0) + artistry + unspecified-high
            "writing": 0.5,
            "visual-engineering": 1.0,
            "quick": -0.5,  # Quick tasks can go lower
            "routing": 0.0,  # Meta category, no complexity adjustment
        }

        return category_scores.get(category, 0.0)

    def _score_to_level(self, score: float) -> str:
        """
        Convert complexity score to thinking level.

        Thresholds:
        - < 3.0: MEDIUM (default minimum)
        - 3.0-6.0: HIGH
        - > 6.0: ULTRA
        """
        if score >= 6.0:
            return ThinkingLevel.ULTRA.value
        elif score >= 3.0:
            return ThinkingLevel.HIGH.value
        else:
            return ThinkingLevel.MEDIUM.value

    def evaluate_task(self, task: Dict) -> str:
        """
        Evaluate a task dict (from athena_bridge.Task).

        Args:
            task: Dict with keys: description, agent, category, etc.

        Returns:
            Thinking level string
        """
        return self.evaluate(
            task_description=task.get("description", ""),
            file_count=task.get("file_count", 1),
            agent=task.get("agent"),
            category=task.get("category"),
        )

    def get_effort_config(self, level: str) -> Dict:
        """
        Get configuration for a thinking level.

        Returns config dict that can be passed to agents.
        """
        configs = {
            "medium": {
                "thinking_effort": "medium",
                "max_tokens": 2000,
                "temperature": 0.7,
                "description": "Standard reasoning for straightforward tasks",
            },
            "high": {
                "thinking_effort": "high",
                "max_tokens": 4000,
                "temperature": 0.5,
                "description": "Deep analysis for complex tasks",
            },
            "ultra": {
                "thinking_effort": "ultra",
                "max_tokens": 8000,
                "temperature": 0.3,
                "description": "Maximum reasoning for critical decisions",
            },
        }
        return configs.get(level, configs["medium"])


# Convenience function for direct use
def select_thinking_level(
    task_description: str,
    file_count: int = 1,
    agent: Optional[str] = None,
    category: Optional[str] = None,
) -> str:
    """Quick function to select thinking level for a task."""
    effort = ThinkingEffort()
    return effort.evaluate(task_description, file_count, agent, category)
