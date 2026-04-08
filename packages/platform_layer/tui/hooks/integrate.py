"""TUI Hook Integration Module.

This module shows how to integrate the ported Ink hooks with the existing N-Xyme_MIND TUI.
Import these hooks into any TUI component to use them.

Usage:
    from tui.hooks.integrate import InputHandler, WrapHelper, FocusHelper
    
    # In your TUI component:
    class MyComponent:
        def __init__(self):
            self.input_handler = InputHandler(self.on_key)
            self.wrap_helper = WrapHelper()
            self.focus_helper = FocusHelper()
"""

import sys
from typing import Callable, Optional, Any, List
from dataclasses import dataclass


# Import our hooks
from .use_input import (
    InputHandler as _InputHandler,
    InputKey,
    InputEvent,
    get_input_state,
    set_raw_mode,
)
from .wrap_text import (
    wrap_text as _wrap_text,
    truncate_text as _truncate_text,
    measure_text,
    pad_text,
    wrap_text_ansi,
    ansi_length,
)
from .focus import (
    FocusManager as _FocusManager,
    FocusEvent,
    FocusableElement,
    get_focus_manager,
    FocusableMixin,
)


# Re-export with friendly names
class InputHandler:
    """Wrapper for terminal input handling.
    
    Usage:
        handler = InputHandler(my_callback)
        handler.start()  # Begin capturing input
        handler.stop() # Stop capturing
    """
    
    def __init__(
        self,
        callback: Callable[[str, InputKey, InputEvent], bool],
        active: bool = True,
    ):
        """Initialize input handler.
        
        Args:
            callback: Function to call on input
            active: Whether to start active
        """
        self._callback = callback
        self._active = active
        self._running = False
    
    def start(self) -> None:
        """Start capturing input."""
        self._running = True
        set_raw_mode(True)
    
    def stop(self) -> None:
        """Stop capturing input."""
        self._running = False
        set_raw_mode(False)
    
    @property
    def is_active(self) -> bool:
        """Check if handler is active."""
        return self._running


class WrapHelper:
    """Helper for text wrapping and formatting.
    
    Usage:
        helper = WrapHelper()
        wrapped = helper.wrap("long text...", 40)
        truncated = helper.truncate("long text...", 20)
    """
    
    def __init__(self, default_width: int = 80):
        """Initialize wrap helper.
        
        Args:
            default_width: Default terminal width
        """
        self._width = default_width
    
    @property
    def width(self) -> int:
        """Get current width."""
        return self._width
    
    @width.setter
    def width(self, w: int) -> None:
        """Set width."""
        self._width = w
    
    def wrap(
        self,
        text: str,
        width: Optional[int] = None,
        trim: bool = False,
    ) -> str:
        """Wrap text to width.
        
        Args:
            text: Text to wrap
            width: Width (uses default if None)
            trim: Whether to trim whitespace
            
        Returns:
            Wrapped text
        """
        w = width or self._width
        lines = wrap_text_ansi(text, w, trim=trim, hard=True)
        return '\n'.join(lines)
    
    def truncate(
        self,
        text: str,
        width: int,
        position: str = "end",
    ) -> str:
        """Truncate text to width.
        
        Args:
            text: Text to truncate
            width: Maximum width
            position: Position of ellipsis (start/middle/end)
            
        Returns:
            Truncated text
        """
        return _truncate_text(text, width, position)
    
    def measure(self, text: str) -> int:
        """Measure text width.
        
        Args:
            text: Text to measure
            
        Returns:
            Visual width
        """
        return measure_text(text)
    
    def pad(
        self,
        text: str,
        width: int,
        align: str = "left",
    ) -> str:
        """Pad text to width.
        
        Args:
            text: Text to pad
            width: Target width
            align: Alignment (left/right/center)
            
        Returns:
            Padded text
        """
        return pad_text(text, width, align)
    
    def format_table(
        self,
        rows: List[List[str]],
        widths: List[int],
        padding: int = 1,
    ) -> str:
        """Format rows as a table.
        
        Args:
            rows: List of rows (each row is list of cell strings)
            widths: Column widths
            padding: Padding between columns
            
        Returns:
            Formatted table string
        """
        lines = []
        pad = " " * padding
        
        for row in rows:
            cells = []
            for i, cell in enumerate(row):
                if i < len(widths):
                    cells.append(self.pad(cell, widths[i]))
                else:
                    cells.append(cell)
            lines.append(pad.join(cells))
        
        return '\n'.join(lines)


class FocusHelper:
    """Helper for focus management in TUI widgets.
    
    Usage:
        helper = FocusHelper(self.on_focus)
        helper.focus(widget)
        helper.next(elements)
    """
    
    def __init__(
        self,
        on_focus_event: Callable[[Any, FocusEvent], None] = None,
    ):
        """Initialize focus helper.
        
        Args:
            on_focus_event: Callback for focus events
        """
        self._manager = _FocusManager(on_focus_event) if on_focus_event else None
    
    @property
    def manager(self) -> Optional[_FocusManager]:
        """Get the focus manager."""
        return self._manager
    
    def focus(self, element: FocusableElement) -> None:
        """Focus an element.
        
        Args:
            element: Element to focus
        """
        if self._manager:
            self._manager.focus(element)
    
    def blur(self) -> None:
        """Blur current element."""
        if self._manager:
            self._manager.blur()
    
    def next(self, elements: list[FocusableElement]) -> None:
        """Focus next element.
        
        Args:
            elements: List of all focusable elements
        """
        if self._manager:
            self._manager.focus_next(elements)
    
    def previous(self, elements: list[FocusableElement]) -> None:
        """Focus previous element.
        
        Args:
            elements: List of all focusable elements
        """
        if self._manager:
            self._manager.focus_previous(elements)
    
    def enable(self) -> None:
        """Enable focus."""
        if self._manager:
            self._manager.enable()
    
    def disable(self) -> None:
        """Disable focus."""
        if self._manager:
            self._manager.disable()


# Default exports
__all__ = [
    "InputHandler",
    "WrapHelper", 
    "FocusHelper",
    "InputKey",
    "InputEvent",
    "FocusEvent",
    "FocusableElement",
    "get_input_state",
    "set_raw_mode",
    "wrap_text",
    "truncate_text",
    "measure_text",
    "pad_text",
    "ansi_length",
]