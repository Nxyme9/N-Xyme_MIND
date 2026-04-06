"""N-Xyme MIND v0.1 — Layer 3: Self-Learning System.

Provides skill lifecycle management, prompt evolution via PromptWizard,
and outcome-driven self-learning with pattern extraction and adaptation.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

from src.tools.learning.skill_lifecycle import SkillLifecycleManager, SkillState
from src.tools.learning.prompt_evolution import PromptWizard, PromptVersion
from src.tools.learning.self_learning import SelfLearner, LearningOutcome

# ---------------------------------------------------------------------------
# Module-level singletons (lazy initialization, thread-safe)
# ---------------------------------------------------------------------------

_learner: Optional[SelfLearner] = None
_wizard: Optional[PromptWizard] = None
_skill_mgr: Optional[SkillLifecycleManager] = None
_lock = threading.Lock()



def get_learner() -> SelfLearner:
    """Get or create the module-level SelfLearner singleton.

    Lazy-initializes with db_path="context/memory/learning.db".
    Thread-safe.
    """
    global _learner
    if _learner is None:
        with _lock:
            if _learner is None:
                Path("context/memory").mkdir(parents=True, exist_ok=True)
                _learner = SelfLearner(db_path="context/memory/learning.db")
    return _learner


def get_wizard() -> PromptWizard:
    """Get or create the module-level PromptWizard singleton.


    Lazy-initializes with db_path="context/memory/prompts.db".
    Thread-safe.
    """
    global _wizard
    if _wizard is None:
        with _lock:
            if _wizard is None:
                Path("context/memory").mkdir(parents=True, exist_ok=True)
                _wizard = PromptWizard(db_path="context/memory/prompts.db")
    return _wizard


def get_skill_mgr() -> SkillLifecycleManager:
    """Get or create the module-level SkillLifecycleManager singleton.


    Lazy-initializes with db_path="context/memory/skills.db".
    Thread-safe.
    """
    global _skill_mgr
    if _skill_mgr is None:
        with _lock:
            if _skill_mgr is None:
                Path("context/memory").mkdir(parents=True, exist_ok=True)
                _skill_mgr = SkillLifecycleManager(db_path="context/memory/skills.db")
    return _skill_mgr


__all__ = [
    "SkillLifecycleManager",
    "SkillState",
    "PromptWizard",
    "PromptVersion",
    "SelfLearner",
    "LearningOutcome",
    "get_learner",
    "get_wizard",
    "get_skill_mgr",
]
