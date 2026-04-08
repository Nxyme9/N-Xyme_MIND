"""Input handling hook - Ported from ant-source-code Ink.

This module provides terminal input handling capabilities equivalent to Ink's useInput hook,
adapted for use with the Textual framework.

Usage:
    from tui.hooks import use_input, InputKey
    
    def handle_input(input_str: str, key: InputKey):
        if key.escape:
            # Handle escape key
        elif input_str == 'q':
            # Handle quit

    use_input(handle_input)
"""

import sys
import tty
import termios
import select
from typing import Callable, Optional
from dataclasses import dataclass
from enum import Enum, auto


class KeyCode(Enum):
    """Special key codes that can be detected."""
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    ENTER = auto()
    TAB = auto()
    ESCAPE = auto()
    BACKSPACE = auto()
    DELETE = auto()
    HOME = auto()
    END = auto()
    PAGE_UP = auto()
    PAGE_DOWN = auto()
    F1 = auto()
    F2 = auto()
    F3 = auto()
    F4 = auto()
    F5 = auto()
    F6 = auto()
    F7 = auto()
    F8 = auto()
    F9 = auto()
    F10 = auto()
    F11 = auto()
    F12 = auto()
    CTRL_C = auto()
    CTRL_D = auto()
    CTRL_Z = auto()
    UNKNOWN = auto()


@dataclass
class InputKey:
    """Represents special key modifiers and states.
    
    Attributes:
        ctrl: True if Ctrl key is held
        shift: True if Shift key is held  
        alt: True if Alt key is held
        meta: True if Meta (Cmd/Windows) key is held
        leftArrow: True if left arrow was pressed
        rightArrow: True if right arrow was pressed
        upArrow: True if up arrow was pressed
        downArrow: True if down arrow was pressed
        return: True if Enter/Return was pressed
        tab: True if Tab was pressed
        escape: True if Escape was pressed
        backspace: True if Backspace was pressed
        delete: True if Delete was pressed
        home: True if Home was pressed
        end: True if End was pressed
        pageUp: True if Page Up was pressed
        pageDown: True if Page Down was pressed
        f1-f12: Function key flags
    """
    # Modifier flags
    ctrl: bool = False
    shift: bool = False
    alt: bool = False
    meta: bool = False
    
    # Arrow keys
    leftArrow: bool = False
    rightArrow: bool = False
    upArrow: bool = False
    downArrow: bool = False
    
    # Special keys
    enter_key: bool = False  # Enter/Return key
    tab: bool = False
    escape: bool = False
    backspace: bool = False
    delete: bool = False
    home: bool = False
    end: bool = False
    pageUp: bool = False
    pageDown: bool = False
    
    # Function keys
    f1: bool = False
    f2: bool = False
    f3: bool = False
    f4: bool = False
    f5: bool = False
    f6: bool = False
    f7: bool = False
    f8: bool = False
    f9: bool = False
    f10: bool = False
    f11: bool = False
    f12: bool = False


@dataclass 
class InputEvent:
    """Full input event containing character and key state.
    
    Attributes:
        input: The character(s) typed
        key: The key state/modifiers
    """
    input: str
    key: InputKey


InputHandler = Callable[[str, InputKey, InputEvent], None]
"""Type alias for input handler callbacks."""


# ANSI escape code mappings
_ESCAPE_SEQUENCES = {
    # Arrow keys (standard)
    '\x1b[A': KeyCode.UP,
    '\x1b[B': KeyCode.DOWN,
    '\x1b[C': KeyCode.RIGHT,
    '\x1b[D': KeyCode.LEFT,
    # Arrow keys (Application mode)
    '\x1bOA': KeyCode.UP,
    '\x1bOB': KeyCode.DOWN,
    '\x1bOC': KeyCode.RIGHT,
    '\x1bOD': KeyCode.LEFT,
    # Home/End
    '\x1b[H': KeyCode.HOME,
    '\x1b[F': KeyCode.END,
    '\x1b[1~': KeyCode.HOME,
    '\x1b[4~': KeyCode.END,
    # Page Up/Down
    '\x1b[5~': KeyCode.PAGE_UP,
    '\x1b[6~': KeyCode.PAGE_DOWN,
    # Delete
    '\x1b[3~': KeyCode.DELETE,
    # Function keys (standard)
    '\x1bOP': KeyCode.F1,
    '\x1bOQ': KeyCode.F2,
    '\x1bOR': KeyCode.F3,
    '\x1bOS': KeyCode.F4,
    # Function keys (extended)
    '\x1b[15~': KeyCode.F5,
    '\x1b[17~': KeyCode.F6,
    '\x1b[18~': KeyCode.F7,
    '\x1b[19~': KeyCode.F8,
    '\x1b[20~': KeyCode.F9,
    '\x1b[21~': KeyCode.F10,
    '\x1b[23~': KeyCode.F11,
    '\x1b[24~': KeyCode.F12,
}


def _parse_escape_sequence(data: str) -> tuple[Optional[KeyCode], bool, bool, bool]:
    """Parse ANSI escape sequence to determine key code and modifiers.
    
    Returns:
        Tuple of (key_code, alt Modifier, ctrl Modifier, meta Modifier)
    """
    # Check for escape sequence
    if not data.startswith('\x1b'):
        return None, False, False, False
    
    # Get the full escape sequence
    seq = data[1:]  # Remove the ESC character
    
    # Check for modifier prefixes (3 for alt, 5 for ctrl, 7 for meta)
    alt_mod = seq.startswith('[')
    ctrl_mod = seq.startswith('^')
    meta_mod = seq.startswith('*')
    
    # Look up the key code
    key_code = _ESCAPE_SEQUENCES.get(data, KeyCode.UNKNOWN)
    
    return key_code, alt_mod, ctrl_mod, meta_mod


def _parse_key(input_data: str) -> tuple[str, InputKey]:
    """Parse raw input into character and key state.
    
    Args:
        input_data: Raw input from terminal
        
    Returns:
        Tuple of (character, key_state)
    """
    key = InputKey()
    char = input_data
    
    # Handle escape sequences
    if input_data.startswith('\x1b'):
        code, alt, ctrl, meta = _parse_escape_sequence(input_data)
        
        if code == KeyCode.UP:
            key.upArrow = True
            char = ''
        elif code == KeyCode.DOWN:
            key.downArrow = True
            char = ''
        elif code == KeyCode.LEFT:
            key.leftArrow = True
            char = ''
        elif code == KeyCode.RIGHT:
            key.rightArrow = True
            char = ''
        elif code == KeyCode.ENTER:
            key.enter_key = True
            char = ''
        elif code == KeyCode.TAB:
            key.tab = True
            char = ''
        elif code == KeyCode.ESCAPE:
            key.escape = True
            char = ''
        elif code == KeyCode.BACKSPACE:
            key.backspace = True
            char = ''
        elif code == KeyCode.DELETE:
            key.delete = True
            char = ''
        elif code == KeyCode.HOME:
            key.home = True
            char = ''
        elif code == KeyCode.END:
            key.end = True
            char = ''
        elif code == KeyCode.PAGE_UP:
            key.pageUp = True
            char = ''
        elif code == KeyCode.PAGE_DOWN:
            key.pageDown = True
            char = ''
        elif code == KeyCode.F1:
            key.f1 = True
            char = ''
        elif code == KeyCode.F2:
            key.f2 = True
            char = ''
        elif code == KeyCode.F3:
            key.f3 = True
            char = ''
        elif code == KeyCode.F4:
            key.f4 = True
            char = ''
        elif code == KeyCode.F5:
            key.f5 = True
            char = ''
        elif code == KeyCode.F6:
            key.f6 = True
            char = ''
        elif code == KeyCode.F7:
            key.f7 = True
            char = ''
        elif code == KeyCode.F8:
            key.f8 = True
            char = ''
        elif code == KeyCode.F9:
            key.f9 = True
            char = ''
        elif code == KeyCode.F10:
            key.f10 = True
            char = ''
        elif code == KeyCode.F11:
            key.f11 = True
            char = ''
        elif code == KeyCode.F12:
            key.f12 = True
            char = ''
        else:
            key.escape = True
            char = input_data[1:] if len(input_data) > 1 else ''
        
        key.alt = alt
        key.ctrl = ctrl
        key.meta = meta
        
        return char, key
    
    # Handle regular characters
    if len(input_data) == 1:
        char = input_data
        
        # Check for control characters
        if ord(char) < 32:
            if char == '\r':
                key.enter_key = True
                char = ''
            elif char == '\t':
                key.tab = True
                char = ''
            elif char == '\x7f':
                key.backspace = True
                char = ''
            else:
                key.ctrl = True
                char = chr(ord(char) + 96)  # Ctrl+a = 1, etc.
        
        return char, key
    
    return input_data, key


class InputState:
    """Maintains terminal input state."""
    
    def __init__(self) -> None:
        self._original_settings: Optional[termios.tcflaglist] = None
        self._fd: int = sys.stdin.fileno()
        self._is_raw: bool = False
    
    def enable_raw_mode(self) -> None:
        """Enable raw mode for character-by-character input."""
        if self._is_raw:
            return
        
        self._original_settings = termios.tcgetattr(self._fd)
        tty.setraw(self._fd)
        self._is_raw = True
    
    def disable_raw_mode(self) -> None:
        """Restore original terminal settings."""
        if not self._is_raw or self._original_settings is None:
            return
        
        termios.tcsetattr(self._fd, termios.TCSADRAIN, self._original_settings)
        self._is_raw = False
    
    def read_input(self, timeout: float = 0.1) -> Optional[str]:
        """Read available input with timeout.
        
        Args:
            timeout: Maximum time to wait for input (seconds)
            
        Returns:
            Input string if available, None otherwise
        """
        if select.select([sys.stdin], [], [], timeout)[0]:
            return sys.stdin.read(1)
        return None
    
    def read_line(self) -> str:
        """Read a complete line of input."""
        return sys.stdin.readline()
    
    @property
    def is_raw_mode(self) -> bool:
        """Check if raw mode is enabled."""
        return self._is_raw


# Global input state
_input_state = InputState()


def use_input(
    handler: InputHandler,
    is_active: bool = True,
    exit_on_ctrl_c: bool = True,
) -> InputState:
    """Hook for handling terminal user input.
    
    This is a more convenient alternative to using stdin directly.
    The handler callback is called for each character when user enters input.
    However, if user pastes text and it's more than one character, 
    the callback will be called only once and the whole string will be passed.
    
    Args:
        handler: Callback function(input: str, key: InputKey, event: InputEvent)
        is_active: Enable or disable capturing of user input
        exit_on_ctrl_c: Whether to exit program on Ctrl+C
        
    Returns:
        InputState instance for advanced control
        
    Example:
        >>> def handle_input(input_str, key, event):
        ...     if input_str == 'q':
        ...         print("Quit!")
        ...     if key.leftArrow:
        ...         print("Left!")
        >>> use_input(handle_input)
    """
    if not is_active:
        return _input_state
    
    # Enable raw mode
    _input_state.enable_raw_mode()
    
    try:
        # Read input non-blocking
        while True:
            char = _input_state.read_input(timeout=0.05)
            if char is None:
                break
            
            # Parse the input
            input_str, key = _parse_key(char)
            
            # Handle Ctrl+C specially
            if exit_on_ctrl_c and input_str == 'c' and key.ctrl:
                _input_state.disable_raw_mode()
                raise KeyboardInterrupt
            
            # Call the handler
            event = InputEvent(input=input_str, key=key)
            handler(input_str, key, event)
            
    except KeyboardInterrupt:
        _input_state.disable_raw_mode()
        raise
    
    return _input_state


def get_input_state() -> InputState:
    """Get the global input state instance.
    
    Returns:
        The global InputState instance
    """
    return _input_state


def set_raw_mode(enabled: bool) -> None:
    """Enable or disable raw terminal mode.
    
    Args:
        enabled: True to enable raw mode, False to disable
    """
    if enabled:
        _input_state.enable_raw_mode()
    else:
        _input_state.disable_raw_mode()