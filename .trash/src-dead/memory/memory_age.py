"""Memory age and decay system — adapted from Claude Code's memoryAge.ts.

Memories decay over time based on their type:
- user: Slow decay (user profile stays relevant)
- feedback: Medium decay (feedback may become outdated)
- project: Fast decay (project context changes quickly)
- reference: Slow decay (external references stay valid)
"""

import time
from typing import Dict

from src.memory.memory_types import MemoryType

# Half-life in days for each memory type
MEMORY_HALF_LIFE_DAYS: Dict[MemoryType, float] = {
    MemoryType.USER: 90.0,  # User profile stays relevant for months
    MemoryType.FEEDBACK: 60.0,  # Feedback decays over 2 months
    MemoryType.PROJECT: 14.0,  # Project context changes every 2 weeks
    MemoryType.REFERENCE: 180.0,  # External references stay valid for 6 months
}

# Default half-life for memories without a type
DEFAULT_HALF_LIFE_DAYS = 30.0

# Minimum relevance score (below this, memory is considered stale)
MIN_RELEVANCE_SCORE = 0.1

# Maximum age in days (beyond this, memory is archived)
MAX_AGE_DAYS = 365.0


def compute_decay_score(
    age_days: float,
    memory_type: MemoryType = MemoryType.PROJECT,
) -> float:
    """Compute decay score based on age and memory type.

    Uses exponential decay: score = 2^(-age / half_life)

    Args:
        age_days: Age of the memory in days
        memory_type: Type of memory (determines half-life)

    Returns:
        Decay score between 0.0 (fully decayed) and 1.0 (fresh)
    """
    half_life = MEMORY_HALF_LIFE_DAYS.get(memory_type, DEFAULT_HALF_LIFE_DAYS)
    if age_days <= 0:
        return 1.0
    return 2.0 ** (-age_days / half_life)


def compute_relevance_score(
    age_days: float,
    memory_type: MemoryType = MemoryType.PROJECT,
    access_count: int = 0,
    access_recency_days: float = 0.0,
) -> float:
    """Compute overall relevance score combining decay and access patterns.

    Relevance = decay_score * (1 + access_boost)

    Access boost: memories that are frequently accessed get a relevance boost.
    Recent access also boosts relevance.

    Args:
        age_days: Age of the memory in days
        memory_type: Type of memory
        access_count: Number of times the memory has been accessed
        access_recency_days: Days since last access (0 = never accessed)

    Returns:
        Relevance score between 0.0 and 2.0
    """
    decay = compute_decay_score(age_days, memory_type)

    # Access boost: up to 0.5x boost for frequently accessed memories
    access_boost = min(0.5, access_count * 0.05)

    # Recency boost: up to 0.5x boost for recently accessed memories
    recency_boost = 0.0
    if access_recency_days > 0:
        recency_boost = max(0.0, 0.5 * (1.0 - access_recency_days / 30.0))

    return decay * (1.0 + access_boost + recency_boost)


def is_memory_stale(
    age_days: float,
    memory_type: MemoryType = MemoryType.PROJECT,
    access_count: int = 0,
) -> bool:
    """Check if a memory is stale and should be archived.

    Args:
        age_days: Age of the memory in days
        memory_type: Type of memory
        access_count: Number of times accessed

    Returns:
        True if memory should be archived
    """
    # Never archive frequently accessed memories
    if access_count > 10:
        return False

    # Archive if beyond max age
    if age_days > MAX_AGE_DAYS:
        return True

    # Archive if relevance is below threshold
    score = compute_relevance_score(age_days, memory_type, access_count)
    return score < MIN_RELEVANCE_SCORE


def get_decay_info(
    age_days: float, memory_type: MemoryType = MemoryType.PROJECT
) -> dict:
    """Get detailed decay information for a memory.

    Args:
        age_days: Age of the memory in days
        memory_type: Type of memory

    Returns:
        Dict with decay_score, half_life, is_stale, days_until_stale
    """
    half_life = MEMORY_HALF_LIFE_DAYS.get(memory_type, DEFAULT_HALF_LIFE_DAYS)
    decay = compute_decay_score(age_days, memory_type)

    # Calculate days until stale
    if decay > MIN_RELEVANCE_SCORE:
        # Solve: 2^(-x/half_life) = MIN_RELEVANCE_SCORE
        # x = -half_life * log2(MIN_RELEVANCE_SCORE)
        import math

        days_until_stale = -half_life * math.log2(MIN_RELEVANCE_SCORE) - age_days
        days_until_stale = max(0, days_until_stale)
    else:
        days_until_stale = 0

    return {
        "decay_score": round(decay, 4),
        "half_life_days": half_life,
        "age_days": round(age_days, 1),
        "is_stale": decay < MIN_RELEVANCE_SCORE,
        "days_until_stale": round(days_until_stale, 1),
    }
