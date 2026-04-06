"""Meta-learning module for learning-engine.

Exports:
- maml: Meta-learning engine
- ewc: Elastic weight consolidation
- active: Active learning engine
"""

from .maml import MetaLearningEngine
from .ewc import EWCEngine
from .active import ActiveLearningEngine

__all__ = [
    "MetaLearningEngine",
    "EWCEngine",
    "ActiveLearningEngine",
]