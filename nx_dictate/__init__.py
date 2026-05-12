# N-Xyme Dictate - Main Application
# Uses existing nx_engine whisper integration

__version__ = "1.0.0"


# Lazy imports to avoid circular dependency
def __getattr__(name):
    if name == "DictationApp":
        from .dictate_app import DictationApp

        return DictationApp
    if name == "DictationEngine":
        from .core.engine import DictationEngine

        return DictationEngine
    if name == "DictationConfig":
        from .core.engine import DictationConfig

        return DictationConfig
    if name == "AudioPipeline":
        from .core.audio import AudioPipeline

        return AudioPipeline
    if name == "AudioConfig":
        from .core.audio import AudioConfig

        return AudioConfig
    if name == "DictationState":
        from .core.state import DictationState

        return DictationState
    if name == "StateMachine":
        from .core.state import StateMachine

        return StateMachine
    if name == "main":
        from .__main__ import main

        return main
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def main():
    """Entry point for CLI."""
    from .dictate_app import main as _main

    _main()


if __name__ == "__main__":
    main()
