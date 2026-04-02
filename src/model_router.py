"""
Model Router — Intelligent task classification and model routing.

Routes agent requests to optimal model based on:
- Agent type (explore, oracle, hephaestus, etc.)
- Task complexity (simple, medium, complex, deep)
- Resource availability (VRAM, rate limits)
- Latency requirements (fast vs quality)

Architecture:
    Task → Classify → Route → Execute
    ├── Simple (explore, quick) → Local llama3.2:latest
    ├── Code (sisyphus-jr) → Local qwen2.5-coder:7b
    ├── Vision (multimodal) → Local llava:7b
    ├── Complex (oracle, plan) → Cloud mimo-v2-pro-free
    └── Deep (hephaestus) → Cloud deepseek-r1:free
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class TaskComplexity(Enum):
    """Task complexity levels."""

    SIMPLE = "simple"  # Local 3B — fast, unlimited
    MEDIUM = "medium"  # Local 7B — code, moderate
    COMPLEX = "complex"  # Cloud — architecture, planning
    DEEP = "deep"  # Cloud premium — deep reasoning


class ModelProvider(Enum):
    """Model provider types."""

    OLLAMA = "ollama"  # Local GPU inference
    OPENCODE = "opencode"  # Cloud (rate-limited)
    OPENROUTER = "openrouter"  # Cloud premium (rate-limited)


@dataclass
class ModelRoute:
    """Route specification for a task."""

    model_name: str
    provider: ModelProvider
    priority: int  # 1=CRITICAL, 2=HIGH, 3=MEDIUM, 4=LOW
    fallback_model: Optional[str] = None
    fallback_provider: Optional[ModelProvider] = None
    keep_alive: str = "-1"  # Ollama keep-alive duration

    @property
    def is_local(self) -> bool:
        return self.provider == ModelProvider.OLLAMA

    @property
    def is_cloud(self) -> bool:
        return self.provider in (ModelProvider.OPENCODE, ModelProvider.OPENROUTER)


# ── Agent Type → Task Signature Mapping ───────────────────────────────

AGENT_SIGNATURES: Dict[str, dict] = {
    # Simple tasks → Local 3B (unlimited, fast)
    "explore": {
        "complexity": TaskComplexity.SIMPLE,
        "task_type": "search",
        "description": "Quick code scanning and file search",
    },
    "librarian": {
        "complexity": TaskComplexity.SIMPLE,
        "task_type": "lookup",
        "description": "Fast research queries and documentation",
    },
    "quick": {
        "complexity": TaskComplexity.SIMPLE,
        "task_type": "fix",
        "description": "Trivial fixes and simple edits",
    },
    "momus": {
        "complexity": TaskComplexity.SIMPLE,
        "task_type": "review",
        "description": "Plan review and critique",
    },
    # Medium tasks → Local 7B (code, reasoning)
    "sisyphus-jr": {
        "complexity": TaskComplexity.MEDIUM,
        "task_type": "code",
        "description": "Category tasks and code generation",
    },
    "metis": {
        "complexity": TaskComplexity.MEDIUM,
        "task_type": "evaluation",
        "description": "Evaluation and quality assessment",
    },
    "multimodal": {
        "complexity": TaskComplexity.MEDIUM,
        "task_type": "vision",
        "description": "Vision and image analysis",
    },
    # Complex tasks → Cloud (architecture, orchestration)
    "sisyphus": {
        "complexity": TaskComplexity.COMPLEX,
        "task_type": "orchestration",
        "description": "Complex orchestration and execution",
    },
    "prometheus": {
        "complexity": TaskComplexity.COMPLEX,
        "task_type": "planning",
        "description": "Strategic planning and design",
    },
    "oracle": {
        "complexity": TaskComplexity.COMPLEX,
        "task_type": "architecture",
        "description": "Architecture review and analysis",
    },
    "atlas": {
        "complexity": TaskComplexity.COMPLEX,
        "task_type": "orchestration",
        "description": "Master orchestration and coordination",
    },
    # Deep tasks → Cloud premium (deep reasoning)
    "hephaestus": {
        "complexity": TaskComplexity.DEEP,
        "task_type": "implementation",
        "description": "Long complex implementations",
    },
}


# ── Model Routing Table ───────────────────────────────────────────────

MODEL_ROUTES: Dict[TaskComplexity, ModelRoute] = {
    TaskComplexity.SIMPLE: ModelRoute(
        model_name="llama3.2:latest",
        provider=ModelProvider.OLLAMA,
        priority=4,  # LOW
        fallback_model="minimax-m2.5-free",
        fallback_provider=ModelProvider.OPENCODE,
        keep_alive="-1",  # Always loaded
    ),
    TaskComplexity.MEDIUM: ModelRoute(
        model_name="qwen2.5-coder:7b",
        provider=ModelProvider.OLLAMA,
        priority=3,  # MEDIUM
        fallback_model="qwen3-coder:free",
        fallback_provider=ModelProvider.OPENROUTER,
        keep_alive="-1",  # Always loaded
    ),
    TaskComplexity.COMPLEX: ModelRoute(
        model_name="mimo-v2-pro-free",
        provider=ModelProvider.OPENCODE,
        priority=2,  # HIGH
        fallback_model="sherlock-think-alpha",
        fallback_provider=ModelProvider.OPENROUTER,
    ),
    TaskComplexity.DEEP: ModelRoute(
        model_name="mimo-v2-pro-free",
        provider=ModelProvider.OPENCODE,
        priority=1,  # CRITICAL
        fallback_model="deepseek-r1:free",
        fallback_provider=ModelProvider.OPENROUTER,
    ),
}

# ── Special-case overrides ────────────────────────────────────────────

SPECIAL_ROUTES: Dict[str, ModelRoute] = {
    "multimodal": ModelRoute(
        model_name="llava:7b",
        provider=ModelProvider.OLLAMA,
        priority=3,  # MEDIUM
        fallback_model="openrouter/vision",
        fallback_provider=ModelProvider.OPENROUTER,
        keep_alive="30m",  # Hot-swap (30 min keep-alive)
    ),
    "metis": ModelRoute(
        model_name="qwen3:8b",
        provider=ModelProvider.OLLAMA,
        priority=3,  # MEDIUM
        fallback_model="mimo-v2-pro-free",
        fallback_provider=ModelProvider.OPENCODE,
        keep_alive="30m",  # Hot-swap
    ),
}


class TaskClassifier:
    """
    Classify agent tasks and route to optimal model.

    Usage:
        classifier = TaskClassifier()
        route = classifier.classify("explore")  # → llama3.2:latest (local)
        route = classifier.classify("oracle")   # → mimo-v2-pro-free (cloud)
    """

    def classify(self, agent_type: str, task_content: str = "") -> ModelRoute:
        """
        Route task to optimal model based on agent type.

        Args:
            agent_type: Agent type (explore, oracle, hephaestus, etc.)
            task_content: Optional task content for dynamic routing

        Returns:
            ModelRoute with model, provider, and priority
        """
        # Check for special-case overrides
        if agent_type in SPECIAL_ROUTES:
            route = SPECIAL_ROUTES[agent_type]
            logger.debug(f"Router: {agent_type} → {route.model_name} (special)")
            return route

        # Get agent signature
        signature = AGENT_SIGNATURES.get(agent_type)
        if not signature:
            logger.warning(f"Router: Unknown agent type '{agent_type}' — defaulting to simple")
            signature = AGENT_SIGNATURES["quick"]

        # Get route for complexity level
        complexity = signature["complexity"]
        route = MODEL_ROUTES[complexity]

        # Dynamic override: simple code tasks can use local 7B
        if self._is_simple_code(task_content) and complexity == TaskComplexity.SIMPLE:
            route = ModelRoute(
                model_name="qwen2.5-coder:7b",
                provider=ModelProvider.OLLAMA,
                priority=3,
                fallback_model="minimax-m2.5-free",
                fallback_provider=ModelProvider.OPENCODE,
                keep_alive="-1",
            )
            logger.debug(f"Router: {agent_type} → qwen2.5-coder:7b (code override)")
        else:
            logger.debug(f"Router: {agent_type} → {route.model_name} ({complexity.value})")

        return route

    def _is_simple_code(self, content: str) -> bool:
        """Detect if content is simple code (can use local 7B)."""
        if not content:
            return False

        code_indicators = [
            "def ",
            "class ",
            "import ",
            "from ",
            "function ",
            "const ",
            "let ",
            "var ",
            "```",
            "async ",
            "await ",
        ]

        content_lower = content.lower()
        return any(indicator in content_lower for indicator in code_indicators)

    def get_route_info(self, agent_type: str) -> dict:
        """Get human-readable route info for an agent type."""
        route = self.classify(agent_type)
        signature = AGENT_SIGNATURES.get(agent_type, {})

        return {
            "agent_type": agent_type,
            "description": signature.get("description", "Unknown"),
            "complexity": signature.get("complexity", TaskComplexity.SIMPLE).value,
            "task_type": signature.get("task_type", "unknown"),
            "primary_model": route.model_name,
            "primary_provider": route.provider.value,
            "priority": route.priority,
            "fallback_model": route.fallback_model,
            "fallback_provider": route.fallback_provider.value if route.fallback_provider else None,
            "is_local": route.is_local,
        }


# ── Global Instance ──────────────────────────────────────────────────

CLASSIFIER = TaskClassifier()
