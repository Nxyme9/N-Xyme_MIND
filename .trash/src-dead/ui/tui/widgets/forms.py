"""
Form field widgets for Textual TUI.

This module provides form input widgets for the N-Xyme MIND Dashboard TUI:
- TextField: Text input with validation
- SelectField: Dropdown selection
- CheckboxField: Boolean checkbox
- NumberField: Numeric input with range validation
"""

from typing import Optional
from textual.widgets import Input, Static
from textual.message import Message
from textual.events import Click
from textual import on


class TextField(Input):
    """Text input field widget with value management.

    Inherits from Textual's Input widget and provides additional methods
    for value manipulation and placeholder text.

    Attributes:
        value (str): Current text value.
        placeholder (str): Placeholder text when empty.
    """

    def __init__(self, placeholder: str = "", value: str = "", **kwargs) -> None:
        """Initialize the TextField.

        Args:
            placeholder: Placeholder text to show when field is empty.
            value: Initial text value.
            **kwargs: Additional arguments passed to Input.
        """
        super().__init__(value=value, placeholder=placeholder, **kwargs)

    def get_value(self) -> str:
        """Get the current text value.

        Returns:
            Current text content of the field.
        """
        return self.value

    def set_value(self, value: str) -> None:
        """Set the text value.

        Args:
            value: New text value to set.
        """
        self.value = value

    def set_placeholder(self, text: str) -> None:
        """Set the placeholder text.

        Args:
            text: Placeholder text to display when empty.
        """
        self.placeholder = text


class SelectFieldOptionSelected(Message):
    """Message emitted when an option is selected."""

    def __init__(self, value: str, label: str) -> None:
        """Initialize the option selected message.

        Args:
            value: The selected option value.
            label: The display label of the selected option.
        """
        super().__init__()
        self.value = value
        self.label = label


class SelectField(Static):
    """Dropdown selection field with options management.

    A static-based widget that displays a selectable dropdown of options.
    Provides methods for getting/setting value and updating options.

    Attributes:
        options: List of available option strings.
        value: Currently selected option value.
    """

    def __init__(
        self, options: Optional[list[str]] = None, value: str = "", **kwargs
    ) -> None:
        """Initialize the SelectField.

        Args:
            options: List of available options.
            value: Initial selected value.
            **kwargs: Additional arguments passed to Static.
        """
        self._options: list[str] = options or []
        self._value: str = value
        self._selected_index: int = -1

        # Find initial selected index
        if value in self._options:
            self._selected_index = self._options.index(value)

        super().__init__(**kwargs)
        self._update_display()

    def _update_display(self) -> None:
        """Update the display content based on current state."""
        if self._selected_index >= 0:
            self.update(f"[b]{self._options[self._selected_index]}[/b]")
        else:
            self.update("[dim]Select...[/dim]")

    def get_value(self) -> str:
        """Get the current selected value.

        Returns:
            Currently selected option, or empty string if none.
        """
        return self._value

    def set_value(self, value: str) -> None:
        """Set the selected value.

        Args:
            value: Option value to select.

        Note:
            If value is not in options, selection is cleared.
        """
        if value in self._options:
            self._value = value
            self._selected_index = self._options.index(value)
        else:
            self._value = ""
            self._selected_index = -1
        self._update_display()

    def set_options(self, options: list[str]) -> None:
        """Set the available options.

        Args:
            options: New list of option strings.

        Note:
            If current value is not in new options, selection is cleared.
        """
        self._options = list(options)
        if self._value not in self._options:
            self._value = ""
            self._selected_index = -1
        self._update_display()

    @on(Click)
    def _handle_click(self) -> None:
        """Handle click to cycle through options."""
        if self._options:
            self._selected_index = (self._selected_index + 1) % len(self._options)
            self._value = self._options[self._selected_index]
            self._update_display()
            self.post_message(SelectFieldOptionSelected(self._value, self._value))


class CheckboxField(Static):
    """Checkbox field with boolean state.

    A static-based widget representing a checkbox that can be toggled.
    Provides methods for getting/setting boolean state and labels.

    Attributes:
        value: Current checkbox state (True = checked, False = unchecked).
    """

    def __init__(self, label: str = "", value: bool = False, **kwargs) -> None:
        """Initialize the CheckboxField.

        Args:
            label: Label text to display next to checkbox.
            value: Initial boolean state.
        **kwargs: Additional arguments passed to Static.
        """
        self._label: str = label
        self._value: bool = value
        super().__init__(**kwargs)
        self._update_display()

    def _update_display(self) -> None:
        """Update the display content based on current state."""
        checkbox = "[×]" if self._value else "[ ]"
        self.update(f"{checkbox} {self._label}")

    def get_value(self) -> bool:
        """Get the current checkbox state.

        Returns:
            True if checked, False if unchecked.
        """
        return self._value

    def set_value(self, value: bool) -> None:
        """Set the checkbox state.

        Args:
            value: New boolean state.
        """
        self._value = bool(value)
        self._update_display()

    def set_label(self, label: str) -> None:
        """Set the checkbox label.

        Args:
            label: New label text.
        """
        self._label = label
        self._update_display()

    @on(Click)
    def _handle_click(self) -> None:
        """Handle click to toggle checkbox state."""
        self._value = not self._value
        self._update_display()


class NumberField(Input):
    """Numeric input field with validation and range constraints.

    Inherits from Textual's Input widget with number validation.
    Provides methods for numeric value management and min/max constraints.

    Attributes:
        min_val: Minimum allowed value.
        max_val: Maximum allowed value.
    """

    def __init__(
        self,
        value: float = 0.0,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        **kwargs,
    ) -> None:
        """Initialize the NumberField.

        Args:
            value: Initial numeric value.
            min_val: Minimum allowed value.
            max_val: Maximum allowed value.
            **kwargs: Additional arguments passed to Input.
        """
        self._min_val: Optional[float] = min_val
        self._max_val: Optional[float] = max_val
        self._current_value: float = value

        super().__init__(value=str(value), **kwargs)

    def validate(self, value: str) -> bool:
        """Validate the input value.

        Args:
            value: String value to validate.

        Returns:
            True if valid, False otherwise.
        """
        try:
            num = float(value)

            if self._min_val is not None and num < self._min_val:
                return False

            if self._max_val is not None and num > self._max_val:
                return False

            self._current_value = num
            return True

        except ValueError:
            return False

    def _validate_value(self, value: str) -> Optional[str]:
        """Legacy validation method for compatibility.

        Args:
            value: String value to validate.

        Returns:
            Error message if invalid, None if valid.
        """
        if self.validate(value):
            return None
        return "Invalid number or out of range"

    def get_value(self) -> float:
        """Get the current numeric value.

        Returns:
            Current numeric value.
        """
        return self._current_value

    def set_value(self, value: float) -> None:
        """Set the numeric value.

        Args:
            value: New numeric value to set.

        Note:
            Value is clamped to min/max range if constraints are set.
        """
        if self._min_val is not None and value < self._min_val:
            value = self._min_val
        if self._max_val is not None and value > self._max_val:
            value = self._max_val

        self._current_value = float(value)
        self.value = str(self._current_value)

    def set_min_max(self, min_val: Optional[float], max_val: Optional[float]) -> None:
        """Set the minimum and maximum value constraints.

        Args:
            min_val: Minimum allowed value (None to remove constraint).
            max_val: Maximum allowed value (None to remove constraint).
        """
        self._min_val = min_val
        self._max_val = max_val

        # Clamp current value to new range
        if self._current_value < min_val if min_val is not None else False:
            self._current_value = min_val
        if self._max_val is not None and self._current_value > self._max_val:
            self._current_value = self._max_val

        self.value = str(self._current_value)
