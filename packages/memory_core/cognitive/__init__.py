"""Cognitive package — Advanced memory cognition and meta-cognition.

Provides:
- Adaptive forgetting (FadeMem-style decay)
- Sleep-based memory consolidation
- Memory reconsolidation
- Priority-based retention
- Trust-aware retrieval
"""

from .forgetting import AdaptiveDecay, DecayScore, compute_decay_score, record_access, apply_decay_actions
from .sleep_engine import SleepEngine, consolidate_memories
from .reconsolidation import MemoryReconsolidation, reconsolidate_memory
from .priority import PriorityEngine, compute_priority
from .retention import RetentionPolicy, should_retain
from .trust import TrustAwareRetrieval, trust_weighted_search

__all__ = [
    # Forgetting
    "AdaptiveDecay",
    "DecayScore",
    "compute_decay_score",
    "record_access",
    "apply_decay_actions",
    # Sleep
    "SleepEngine",
    "consolidate_memories",
    # Reconsolidation
    "MemoryReconsolidation",
    "reconsolidate_memory",
    # Priority
    "PriorityEngine",
    "compute_priority",
    # Retention
    "RetentionPolicy",
    "should_retain",
    # Trust
    "TrustAwareRetrieval",
    "trust_weighted_search",
]