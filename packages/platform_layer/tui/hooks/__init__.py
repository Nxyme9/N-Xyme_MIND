"""TUI hooks module - Ported from ant-source-code Ink hooks.

This module provides Python equivalents of the core Ink hooks,
adapted for use with the Textual framework in N-Xyme_MIND.

Hooks:
    - use_input: Terminal input handling with key detection
    - wrap_text: Text wrapping and truncation utilities
    - FocusManager: DOM-like focus management for TUI components
"""

from .use_input import use_input, InputHandler, InputKey, InputEvent
from .wrap_text import wrap_text, truncate_text, wrap_text_ansi
from .focus import FocusManager, FocusEvent, get_focus_manager

__all__ = [
    "use_input",
    "InputHandler", 
    "InputKey",
    "InputEvent",
    "wrap_text",
    "truncate_text",
    "wrap_text_ansi",
    "FocusManager",
    "FocusEvent",
    "get_focus_manager",
]