"""Dialog components for N-Xyme MIND Dashboard TUI."""

from typing import Any

# Common dialog components exports
__all__ = [
    "Dialog",
    "ConfirmDialog",
    "InputDialog",
    "MessageDialog",
    "ChoiceDialog",
]

# Placeholder imports - to be implemented
# from .dialog import Dialog
# from .confirm_dialog import ConfirmDialog
# from .input_dialog import InputDialog
# from .message_dialog import MessageDialog
# from .choice_dialog import ChoiceDialog


class Dialog:
    """Base dialog class."""
    
    def __init__(self, title: str, **kwargs: Any) -> None:
        self.title = title
        self.width = kwargs.get("width", 60)
        self.height = kwargs.get("height", None)
        self.returns_value = kwargs.get("returns_value", False)


class ConfirmDialog(Dialog):
    """Confirmation dialog with Yes/No options."""
    
    def __init__(self, title: str = "Confirm", message: str = "", **kwargs: Any) -> None:
        super().__init__(title, **kwargs)
        self.message = message


class InputDialog(Dialog):
    """Input dialog for user text entry."""
    
    def __init__(self, title: str = "Input", prompt: str = "", **kwargs: Any) -> None:
        super().__init__(title, returns_value=True, **kwargs)
        self.prompt = prompt
        self.default_value = kwargs.get("default_value", "")


class MessageDialog(Dialog):
    """Message dialog for displaying information."""
    
    def __init__(self, title: str = "Message", message: str = "", **kwargs: Any) -> None:
        super().__init__(title, **kwargs)
        self.message = message


class ChoiceDialog(Dialog):
    """Dialog for selecting from a list of choices."""
    
    def __init__(self, title: str = "Choose", choices: list[str] | None = None, **kwargs: Any) -> None:
        super().__init__(title, returns_value=True, **kwargs)
        self.choices = choices or []
