# N-Xyme Dictate - Core Module

# Import directly from local modules to avoid circular import
from nx_engine.dictate.dictate_app import DictationApp
from nx_engine.dictate.__main__ import main
from nx_engine.dictate.core.engine import (
    DictationEngine,
    DictationConfig,
    get_engine,
    auto_select_model,
)
from nx_engine.dictate.core.audio import AudioPipeline, AudioConfig
from nx_engine.dictate.core.state import DictationState, StateMachine

__all__ = [
    "DictationApp",
    "DictationEngine",
    "DictationConfig",
    "DictationState",
    "StateMachine",
    "AudioPipeline",
    "AudioConfig",
    "get_engine",
    "auto_select_model",
    "main",
]
