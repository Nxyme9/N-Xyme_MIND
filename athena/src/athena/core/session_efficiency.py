"""
athena.core.session_efficiency
===============================

Session Efficiency Scoring — adapted from Zeude's composite
efficiency metric. Measures how effectively each session
leverages Athena's capabilities.

Components (weighted):
    - Skill Utilization (35%): % of work that triggered skills
    - Token Efficiency  (35%): Tokens used vs budget ceiling
    - Context Reuse     (20%): Memory bank cache hits
    - Retry Density     (10%): Lower retries = better

Score: 0-100 (higher = more efficient)

Usage:
    from athena.core.session_efficiency import calculate_session_efficiency

    score = calculate_session_efficiency(
        skill_invocations=8,
        total_prompts=20,
        tokens_used=8207,
        token_budget=20000,
        memory_hits=15,
        total_queries=20,
        retry_count=1,
        total_actions=20,
    )
"""

from dataclasses import dataclass


# --- THRESHOLDS ---

TOKEN_BUDGET_CEILING = 20_000  # Athena boot budget
EFFICIENCY_THRESHOLDS = {
    "excellent": 80,  # Green
    "good": 60,  # Yellow
    "needs_work": 0,  # Red (below 60)
}


@dataclass
class EfficiencyResult:
    """Result of a session efficiency calculation."""

    score: int  # 0-100 composite
    skill_utilization: float  # 0.0-1.0
    token_efficiency: float  # 0.0-1.0
    context_reuse: float  # 0.0-1.0
    retry_density: float  # 0.0-1.0 (inverted: 1.0 = no retries)
    grade: str  # "excellent" | "good" | "needs_work"

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "grade": self.grade,
            "components": {
                "skill_utilization": round(self.skill_utilization, 3),
                "token_efficiency": round(self.token_efficiency, 3),
                "context_reuse": round(self.context_reuse, 3),
                "retry_density": round(self.retry_density, 3),
            },
        }


def calculate_session_efficiency(
    skill_invocations: int = 0,
    total_prompts: int = 1,
    tokens_used: int = 0,
    token_budget: int = TOKEN_BUDGET_CEILING,
    memory_hits: int = 0,
    total_queries: int = 1,
    retry_count: int = 0,
    total_actions: int = 1,
) -> EfficiencyResult:
    """
    Calculate composite efficiency score for a session.

    Args:
        skill_invocations: Number of skill/protocol invocations
        total_prompts: Total number of prompts in the session
        tokens_used: Boot tokens consumed
        token_budget: Token budget ceiling (default: 20K)
        memory_hits: Number of queries that hit cached memory
        total_queries: Total search/recall queries
        retry_count: Number of retries/doom-loops
        total_actions: Total actions taken

    Returns:
        EfficiencyResult with score 0-100 and component breakdown.
    """
    # Prevent division by zero
    total_prompts = max(total_prompts, 1)
    total_queries = max(total_queries, 1)
    total_actions = max(total_actions, 1)
    token_budget = max(token_budget, 1)

    # 1. Skill Utilization (35%): What % of prompts triggered a skill?
    #    Higher = better (means the system is being leveraged)
    skill_utilization = min(1.0, skill_invocations / total_prompts)

    # 2. Token Efficiency (35%): Stay under budget ceiling
    #    Using less of the budget = more headroom = better
    #    But using too little might mean under-utilization, so sweet spot is 30-60%
    usage_ratio = tokens_used / token_budget
    if usage_ratio <= 0.6:
        token_efficiency = 1.0  # Under 60% = excellent
    elif usage_ratio <= 0.8:
        token_efficiency = 1.0 - ((usage_ratio - 0.6) * 2.5)  # Linear decay
    elif usage_ratio <= 1.0:
        token_efficiency = 0.5 - ((usage_ratio - 0.8) * 2.5)  # Steeper decay
    else:
        token_efficiency = 0.0  # Over budget

    token_efficiency = max(0.0, min(1.0, token_efficiency))

    # 3. Context Reuse (20%): How often did we hit cached memory?
    #    Higher = leveraging the exocortex effectively
    context_reuse = min(1.0, memory_hits / total_queries)

    # 4. Retry Density (10%): Lower is better (inverted)
    #    retry_density = 1 - (retries / total_actions), capped at 0
    retry_density = max(0.0, 1.0 - (retry_count / total_actions))

    # Composite Score (0-100)
    score = round(
        (skill_utilization * 35)
        + (token_efficiency * 35)
        + (context_reuse * 20)
        + (retry_density * 10)
    )
    score = max(0, min(100, score))

    # Grade
    if score >= EFFICIENCY_THRESHOLDS["excellent"]:
        grade = "excellent"
    elif score >= EFFICIENCY_THRESHOLDS["good"]:
        grade = "good"
    else:
        grade = "needs_work"

    return EfficiencyResult(
        score=score,
        skill_utilization=skill_utilization,
        token_efficiency=token_efficiency,
        context_reuse=context_reuse,
        retry_density=retry_density,
        grade=grade,
    )


def format_efficiency_report(result: EfficiencyResult) -> str:
    """Format an efficiency result as a human-readable string."""
    grade_emoji = {"excellent": "🟢", "good": "🟡", "needs_work": "🔴"}
    emoji = grade_emoji.get(result.grade, "⚪")

    lines = [
        f"📊 Session Efficiency: {emoji} {result.score}/100 ({result.grade.upper()})",
        f"   ├── Skill Utilization: {result.skill_utilization:.0%} (weight: 35%)",
        f"   ├── Token Efficiency:  {result.token_efficiency:.0%} (weight: 35%)",
        f"   ├── Context Reuse:     {result.context_reuse:.0%} (weight: 20%)",
        f"   └── Retry Density:     {result.retry_density:.0%} (weight: 10%)",
    ]
    return "\n".join(lines)
