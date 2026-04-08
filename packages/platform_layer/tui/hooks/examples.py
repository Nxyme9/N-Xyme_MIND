"""Integration examples for TUI hooks.

This module provides examples showing how to use the ported hooks
in the N-Xyme_MIND TUI.

Usage:
    # Example 1: Using use_input for keyboard handling
    from tui.hooks.examples import keyboard_demo
    
    # Example 2: Using wrap_text for terminal formatting  
    from tui.hooks.examples import format_text_demo
    
    # Example 3: Using FocusManager for widget focus
    from tui.hooks.examples import focus_demo
"""

import sys
import threading
import time
from typing import Optional


# Try to import Textual - required for full examples
try:
    from textual.app import App, ComposeResult
    from textual.widgets import Button, Static, Label
    from textual.containers import Vertical, Horizontal
    from textual.binding import Binding
    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False
    App = None  # type: ignore


# Example 1: Input handling demo
def keyboard_input_example():
    """Example: Using use_input hook for terminal keyboard handling.
    
    This demonstrates how to capture keyboard input in a terminal application.
    
    Expected behavior:
    - Arrow keys move selection
    - Enter key activates selection
    - Escape key exits
    - q quits the demo
    """
    from .use_input import use_input, InputKey, InputKey
    
    print("=" * 50)
    print("Keyboard Input Demo")
    print("=" * 50)
    print("Controls:")
    print("  Arrow keys - Move selection")
    print("  Enter       - Activate")
    print("  Escape     - Exit")
    print("  q          - Quit")
    print("=" * 50)
    print()
    
    # Selection state
    options = ["Option 1", "Option 2", "Option 3"]
    selected = 0
    
    def print_menu():
        print("\n" + "=" * 30)
        for i, opt in enumerate(options):
            marker = ">" if i == selected else " "
            print(f"  {marker} {opt}")
        print("=" * 30 + "\n")
    
    def handle_key(input_str: str, key: InputKey, event):
        nonlocal selected
        
        if key.escape:
            print("Exiting...")
            return True  # Signal to exit
        
        if input_str == 'q':
            print("Quit!")
            return True
        
        if key.upArrow and selected > 0:
            selected -= 1
        elif key.downArrow and selected < len(options) - 1:
            selected += 1
        elif key.enter_key:
            print(f"Selected: {options[selected]}")
        
        print_menu()
        return False
    
    print_menu()
    
    # Note: Full interactive input would need proper TUI loop
    print("Install Textual to run full interactive demo")
    print("Run: pip install textual")


# Example 2: Text wrapping demo
def text_wrap_example():
    """Example: Using wrap_text hook for terminal text formatting.
    
    This demonstrates different text wrapping and truncation modes.
    """
    from .wrap_text import wrap_text, truncate_text, measure_text
    
    test_text = "This is a very long piece of text that needs to be wrapped or truncated."
    test_text_ansi = "\x1b[32mThis is green text\x1b[0m that continues here."
    
    print("=" * 50)
    print("Text Wrap Demo")
    print("=" * 50)
    
    # Test different wrap types
    print("\n1. Normal text (original):")
    print(f"   '{test_text}'")
    
    print("\n2. Wrapped at 20 columns:")
    wrapped = wrap_text(test_text, 20, "wrap")
    for line in wrapped.split('\n'):
        print(f"   '{line}'")
    
    print("\n3. Truncated (end) at 15 columns:")
    truncated = wrap_text(test_text, 15, "truncate")
    print(f"   '{truncated}'")
    
    print("\n4. Truncated (middle) at 15 columns:")
    trunc_mid = wrap_text(test_text, 15, "truncate-middle")
    print(f"   '{trunc_mid}'")
    
    print("\n5. Truncated (start) at 15 columns:")
    trunc_start = wrap_text(test_text, 15, "truncate-start")
    print(f"   '{trunc_start}'")
    
    print("\n6. With ANSI codes:")
    print(f"   Original: '{test_text_ansi}' ({measure_text(test_text_ansi)} chars)")
    print(f"   Truncated: '{wrap_text(test_text_ansi, 20, 'truncate')}'")
    
    print("\n" + "=" * 50)


# Example 3: Focus manager demo (requires Textual)
if TEXTUAL_AVAILABLE:
    class FocusDemoApp(App):
        """Demo application showing FocusManager integration."""
        
        BINDINGS = [
            Binding("q", "quit", "Quit"),
            Binding("tab", "focus_next", "Next"),
            Binding("shift+tab", "focus_previous", "Previous"),
            Binding("escape", "blur", "Blur"),
        ]
        
        CSS = """
        FocusDemoApp { background: $background; }
        #container { width: 100%; height: 100%; }
        Button { margin: 1; }
        .focused { background: $primary; }
        """
        
        def compose(self) -> ComposeResult:
            yield Label("Focus Manager Demo - Tab to navigate", id="title")
            with Horizontal(id="buttons"):
                yield Button("Button 1", id="btn1", variant="primary")
                yield Button("Button 2", id="btn2")
                yield Button("Button 3", id="btn3")
                yield Button("Disabled", id="btn4", variant="error", disabled=True)
            yield Label("Status: ", id="status")
        
        def on_mount(self) -> None:
            self._focus_manager = self._create_focus_manager()
            self._update_status("Use Tab to navigate, Escape to blur")
        
        def _create_focus_manager(self):
            from .focus import FocusManager, FocusEvent
            
            def dispatch(element, event: FocusEvent):
                self._update_status(f"Focus event: {event.type.value}")
            
            return FocusManager(dispatch)
        
        def action_focus_next(self) -> None:
            # Get all focusable buttons
            buttons = list(self.query(Button))
            if not buttons:
                return
            
            # Find current focus
            current = self.screen.focused
            if current in buttons:
                idx = buttons.index(current)
                next_idx = (idx + 1) % len(buttons)
            else:
                next_idx = 0
            
            # Focus next (skip disabled)
            for i in range(len(buttons)):
                btn = buttons[(next_idx + i) % len(buttons)]
                if not btn.disabled:
                    btn.focus()
                    break
        
        def action_focus_previous(self) -> None:
            buttons = list(self.query(Button))
            if not buttons:
                return
            
            current = self.screen.focused
            if current in buttons:
                idx = buttons.index(current)
                prev_idx = (idx - 1) % len(buttons)
            else:
                prev_idx = len(buttons) - 1
            
            for i in range(len(buttons)):
                btn = buttons[(prev_idx - i) % len(buttons)]
                if not btn.disabled:
                    btn.focus()
                    break
        
        def action_blur(self) -> None:
            self.app.focused = None
            self._update_status("Blurred")
        
        def _update_status(self, message: str) -> None:
            status = self.query_one("#status", Label)
            status.update(f"Status: {message}")
else:
    FocusDemoApp = None


def focus_demo():
    """Run the focus manager demo application."""
    if not TEXTUAL_AVAILABLE:
        print("Textual not installed. Install with: pip install textual")
        print("Running text wrap example instead...")
        text_wrap_example()
        return
    
    app = FocusDemoApp()
    app.run()


# Example 4: Combined example with all hooks
def combined_example():
    """Example combining all three hooks.
    
    This creates a simple interactive program using all hooks.
    """
    from .use_input import use_input, InputKey
    from .wrap_text import wrap_text, measure_text, pad_text
    from .focus import FocusManager, FocusableElement, FocusEvent
    
    print("=" * 50)
    print("Combined Hooks Demo")
    print("=" * 50)
    
    # Create focus manager
    elements = [
        FocusableElement("btn1", tab_index=0),
        FocusableElement("btn2", tab_index=1),
        FocusableElement("btn3", tab_index=2),
    ]
    
    def on_focus(element, event: FocusEvent):
        print(f"  Focus event: {event.type.value} on {element.id}")
    
    fm = FocusManager(on_focus)
    focused_idx = 0
    
    def handle_input(input_str: str, key: InputKey, event):
        nonlocal focused_idx
        
        if key.escape or input_str == 'q':
            print("\nExiting...")
            return True
        
        # Tab handling via focus manager
        if key.tab:
            if key.shift:
                # Previous
                focused_idx = (focused_idx - 1) % len(elements)
            else:
                # Next
                focused_idx = (focused_idx + 1) % len(elements)
            fm.focus(elements[focused_idx])
        
        return False
    
    # Show initial menu
    print("\nMenu:")
    for i, el in enumerate(elements):
        marker = ">" if i == focused_idx else " "
        print(f"  {marker} [{el.tab_index}] {el.id}")
    
    print("\nControls:")
    print("  Tab/Shift+Tab - Navigate")
    print("  Enter - Activate")
    print("  Escape/q - Exit")
    
    print("\nInstall Textual and run focus_demo() for full TUI experience")


# Main function to run all demos
def main():
    """Run all demonstration examples."""
    import argparse
    
    parser = argparse.ArgumentParser(description="TUI Hooks Examples")
    parser.add_argument(
        "--example",
        choices=["keyboard", "wrap", "focus", "combined", "all"],
        default="all",
        help="Which example to run"
    )
    
    args = parser.parse_args()
    
    if args.example == "keyboard" or args.example == "all":
        keyboard_input_example()
    
    if args.example == "wrap" or args.example == "all":
        print()
        text_wrap_example()
    
    if args.example == "focus" or args.example == "all":
        print()
        print("Run focus_demo() to launch the Textual app")
        if TEXTUAL_AVAILABLE:
            focus_demo()
    
    if args.example == "combined" or args.example == "all":
        print()
        combined_example()


if __name__ == "__main__":
    main()