"""
Configuration Editor Module for N-Xyme MIND Dashboard TUI.

Provides a modal dialog for editing dashboard and system configuration.
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Header, Static, Label

from ..widgets.forms import TextField, SelectField, CheckboxField, NumberField


# Configuration directory and file paths
CONFIG_DIR = Path.home() / ".config" / "n-xyme"
CONFIG_FILE = CONFIG_DIR / "preferences.json"

# JSON Schema for configuration validation
CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "theme": {
            "type": "string",
            "enum": ["dark", "light", "auto"],
            "default": "dark",
        },
        "auto_refresh_interval": {
            "type": "number",
            "minimum": 1,
            "maximum": 300,
            "default": 5,
        },
        "show_animations": {
            "type": "boolean",
            "default": True,
        },
        "default_tab": {
            "type": "string",
            "enum": ["home", "agents", "memory", "tools", "settings"],
            "default": "home",
        },
        "log_level": {
            "type": "string",
            "enum": ["debug", "info", "warning", "error"],
            "default": "info",
        },
    },
    "additionalProperties": False,
}


@dataclass
class DashboardConfig:
    """
    Configuration data for the dashboard.

    Attributes:
        theme: UI theme (dark, light, auto).
        auto_refresh_interval: Interval in seconds for auto-refresh.
        show_animations: Whether to show UI animations.
        default_tab: Default tab to show on startup.
        log_level: Logging verbosity level.
    """

    theme: str = "dark"
    auto_refresh_interval: int = 5
    show_animations: bool = True
    default_tab: str = "home"
    log_level: str = "info"

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DashboardConfig":
        """Create config from dictionary with validation."""
        validated = cls._validate_with_schema(data)
        return cls(**validated)

    @staticmethod
    def _validate_with_schema(data: dict[str, Any]) -> dict[str, Any]:
        """Validate data against CONFIG_SCHEMA with defaults."""
        result = {}
        props = CONFIG_SCHEMA.get("properties", {})

        for key, schema in props.items():
            if key in data:
                value = data[key]
                # Type validation
                expected_type = schema.get("type")
                if expected_type == "string" and not isinstance(value, str):
                    value = schema.get("default", "")
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    value = schema.get("default", 0)
                elif expected_type == "boolean" and not isinstance(value, bool):
                    value = schema.get("default", False)

                # Enum validation
                if "enum" in schema and value not in schema["enum"]:
                    value = schema.get("default", "")

                # Range validation for numbers
                if expected_type == "number":
                    min_val = schema.get("minimum")
                    max_val = schema.get("maximum")
                    if min_val is not None and value < min_val:
                        value = min_val
                    if max_val is not None and value > max_val:
                        value = max_val

                result[key] = value
            else:
                # Use default if not present
                result[key] = schema.get("default")

        return result

    def save(self) -> bool:
        """
        Write configuration to JSON file.

        Returns:
            True if save succeeded, False otherwise.
        """
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2)
            return True
        except (IOError, OSError):
            return False

    @classmethod
    def load(cls) -> "DashboardConfig":
        """
        Load configuration from JSON file.

        Returns:
            DashboardConfig: The loaded config, or default config if file not found.
        """
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return cls.from_dict(data)
        except (IOError, json.JSONDecodeError):
            pass
        return cls()

    @staticmethod
    def get_default() -> "DashboardConfig":
        """Create a default configuration instance."""
        return DashboardConfig()


class ConfigEditorDialog(ModalScreen):
    """
    Modal dialog for editing dashboard configuration.

    Features:
    - Form fields for all configurable options
    - Save/Cancel buttons
    - JSON schema validation on save
    - Load from and save to JSON file
    """

    CSS = """
    ConfigEditorDialog {
        background: $surface;
    }

    #dialog_container {
        width: 60;
        height: auto;
        border: solid $primary;
        background: $panel;
        padding: 1 2;
    }

    #header {
        height: auto;
        padding: 1;
        background: $primary;
        text-align: center;
    }

    #title {
        text-style: bold;
        color: $text;
    }

    .form_row {
        height: auto;
        margin-bottom: 1;
        align: center middle;
    }

    .form_label {
        width: 22;
        color: $text-muted;
    }

    .form_field {
        width: 36;
    }

    #button_row {
        height: auto;
        margin-top: 2;
        align: center middle;
    }

    Button {
        margin: 0 2;
    }

    #error_message {
        color: $error;
        text-style: bold;
        height: auto;
        padding: 1;
    }
    """

    def __init__(self, config: Optional[DashboardConfig] = None) -> None:
        """
        Initialize the Config Editor Dialog.

        Args:
            config: Optional configuration to edit. Loads from file if not provided.
        """
        super().__init__()
        self._config = config or DashboardConfig.load()
        self._error_message: str = ""

    def compose(self) -> ComposeResult:
        """Compose the dialog widgets."""
        with Vertical(id="dialog_container"):
            # Header
            yield Static("Configuration Editor", id="header")

            with Horizontal(classes="form_row"):
                yield Label("Theme:", classes="form_label")
                yield SelectField(
                    id="field_theme",
                    options=["dark", "light", "auto"],
                    value=self._config.theme,
                )

            # Auto-refresh interval
            with Horizontal(classes="form_row"):
                yield Label("Auto-refresh (s):", classes="form_label")
                yield NumberField(
                    id="field_interval",
                    value=float(self._config.auto_refresh_interval),
                    min_val=1,
                    max_val=300,
                )

            # Show animations
            with Horizontal(classes="form_row"):
                yield Label("Show Animations:", classes="form_label")
                yield CheckboxField(
                    id="field_animations",
                    label="Enable animations",
                    value=self._config.show_animations,
                )

            # Default tab
            with Horizontal(classes="form_row"):
                yield Label("Default Tab:", classes="form_label")
                yield SelectField(
                    id="field_tab",
                    options=["home", "agents", "memory", "tools", "settings"],
                    value=self._config.default_tab,
                )

            # Log level
            with Horizontal(classes="form_row"):
                yield Label("Log Level:", classes="form_label")
                yield SelectField(
                    id="field_log_level",
                    options=["debug", "info", "warning", "error"],
                    value=self._config.log_level,
                )

            # Error message display
            yield Static("", id="error_message")

            # Buttons
            with Horizontal(id="button_row"):
                yield Button("Save", variant="success", id="btn_save")
                yield Button("Cancel", variant="default", id="btn_cancel")
                yield Button("Reset", variant="error", id="btn_reset")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id

        if button_id == "btn_save":
            self._save_config()
        elif button_id == "btn_cancel":
            self._cancel()
        elif button_id == "btn_reset":
            self._reset_to_default()

    def _get_form_values(self) -> dict[str, Any]:
        """Extract values from form fields."""
        values: dict[str, Any] = {}

        # Theme
        theme_field = self.query_one("#field_theme", SelectField)
        values["theme"] = theme_field.get_value()

        # Auto-refresh interval
        interval_field = self.query_one("#field_interval", NumberField)
        values["auto_refresh_interval"] = int(interval_field.get_value())

        # Show animations
        animations_field = self.query_one("#field_animations", CheckboxField)
        values["show_animations"] = animations_field.get_value()

        # Default tab
        tab_field = self.query_one("#field_tab", SelectField)
        values["default_tab"] = tab_field.get_value()

        # Log level
        log_field = self.query_one("#field_log_level", SelectField)
        values["log_level"] = log_field.get_value()

        return values

    def _set_form_values(self, config: DashboardConfig) -> None:
        """Set form field values from config."""
        # Theme
        theme_field = self.query_one("#field_theme", SelectField)
        theme_field.set_value(config.theme)

        # Auto-refresh interval
        interval_field = self.query_one("#field_interval", NumberField)
        interval_field.set_value(float(config.auto_refresh_interval))

        # Show animations
        animations_field = self.query_one("#field_animations", CheckboxField)
        animations_field.set_value(config.show_animations)

        # Default tab
        tab_field = self.query_one("#field_tab", SelectField)
        tab_field.set_value(config.default_tab)

        # Log level
        log_field = self.query_one("#field_log_level", SelectField)
        log_field.set_value(config.log_level)

    def _show_error(self, message: str) -> None:
        """Display error message."""
        error_widget = self.query_one("#error_message", Static)
        error_widget.update(message)

    def _clear_error(self) -> None:
        """Clear error message."""
        self._show_error("")

    def _validate_config(self, values: dict[str, Any]) -> bool:
        """
        Validate configuration values against schema.

        Args:
            values: Dictionary of configuration values.

        Returns:
            True if valid, False otherwise.
        """
        props = CONFIG_SCHEMA.get("properties", {})

        for key, value in values.items():
            schema = props.get(key, {})

            # Type check
            expected = schema.get("type")
            if expected == "string" and not isinstance(value, str):
                self._show_error(f"Invalid type for {key}: expected string")
                return False
            if expected == "number" and not isinstance(value, (int, float)):
                self._show_error(f"Invalid type for {key}: expected number")
                return False
            if expected == "boolean" and not isinstance(value, bool):
                self._show_error(f"Invalid type for {key}: expected boolean")
                return False

            # Enum check
            if "enum" in schema and value not in schema["enum"]:
                self._show_error(
                    f"Invalid value for {key}: must be one of {schema['enum']}"
                )
                return False

            # Range check
            if expected == "number":
                min_val = schema.get("minimum")
                max_val = schema.get("maximum")
                if min_val is not None and value < min_val:
                    self._show_error(f"{key} must be at least {min_val}")
                    return False
                if max_val is not None and value > max_val:
                    self._show_error(f"{key} must be at most {max_val}")
                    return False

        self._clear_error()
        return True

    def _save_config(self) -> None:
        """Save configuration to file."""
        values = self._get_form_values()

        if not self._validate_config(values):
            return

        # Create config object and save
        new_config = DashboardConfig.from_dict(values)
        success = new_config.save()

        if success:
            self.notify("Configuration saved successfully", severity="information")
            self.app.pop_screen()
        else:
            self._show_error("Failed to save configuration")

    def _cancel(self) -> None:
        """Cancel and close dialog."""
        self.app.pop_screen()

    def _reset_to_default(self) -> None:
        """Reset form to default values."""
        default_config = DashboardConfig.get_default()
        self._set_form_values(default_config)
        self._clear_error()
        self.notify("Configuration reset to defaults", severity="information")


# Module-level default config instance
_default_config: Optional[DashboardConfig] = None


def get_config() -> DashboardConfig:
    """
    Get the global configuration instance.

    Returns:
        The global DashboardConfig instance.
    """
    global _default_config
    if _default_config is None:
        _default_config = DashboardConfig.load()
    return _default_config


def reload_config() -> DashboardConfig:
    """
    Reload configuration from file.

    Returns:
        The reloaded DashboardConfig instance.
    """
    global _default_config
    _default_config = DashboardConfig.load()
    return _default_config
