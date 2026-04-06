"""
Settings Screen Module for N-Xyme MIND Dashboard TUI.

Provides a full-screen settings interface for dashboard configuration.
"""

from dataclasses import dataclass, asdict
from typing import Any, Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Header, Static, Label

from ..widgets.forms import SelectField, CheckboxField, NumberField


# Settings data class
@dataclass
class SettingsData:
    """Settings data for the dashboard."""
    # General
    default_tab: str = "home"
    auto_refresh: bool = True
    refresh_interval: int = 5
    show_notifications: bool = True
    
    # Appearance
    theme: str = "dark"
    font_size: int = 14
    compact_mode: bool = False
    show_borders: bool = True
    
    # Data
    cache_enabled: bool = True
    cache_size_mb: int = 100
    data_retention_days: int = 30
    
    # Advanced
    debug_mode: bool = False
    verbose_logging: bool = False
    experimental_features: bool = False
    
    def to_dict(self) -> dict[str, Any]:
        """Convert settings to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SettingsData":
        """Create settings from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class SettingsScreen(Screen):
    """
    Full-screen settings screen for dashboard configuration.
    
    Sections:
    - General: default_tab, auto_refresh, refresh_interval, show_notifications
    - Appearance: theme, font_size, compact_mode, show_borders
    - Data: cache_enabled, cache_size_mb, data_retention_days
    - Advanced: debug_mode, verbose_logging, experimental_features
    
    Features:
    - Tab-based navigation between sections
    - Save/Reset buttons with confirmation
    - Form validation
    """
    
    CSS = """
    SettingsScreen {
        background: $surface;
    }
    
    #settings_container {
        width: 100%;
        height: 100%;
    }
    
    #header_bar {
        height: auto;
        background: $primary;
        padding: 1 2;
    }
    
    #tab_bar {
        height: 3;
        background: $panel;
        padding: 0 2;
    }
    
    .tab_button {
        width: 16;
        text-align: center;
        padding: 1 2;
    }
    
    .tab_button:hover {
        background: $primary-darken-1;
    }
    
    .tab_button.active {
        background: $accent;
        text-style: bold;
    }
    
    #section_content {
        width: 100%;
        height: auto;
        padding: 2 4;
    }
    
    .section_title {
        text-style: bold;
        color: $accent;
        height: auto;
        margin-bottom: 1;
    }
    
    .form_row {
        height: auto;
        margin-bottom: 1;
        align: left middle;
    }
    
    .form_label {
        width: 24;
        color: $text-muted;
    }
    
    .hidden {
        display: none;
    }
    
    #button_bar {
        height: 3;
        align: center middle;
        background: $panel;
        padding: 1 2;
    }
    
    #button_bar Button {
        margin: 0 2;
    }
    
    #confirm_dialog {
        display: none;
    }
    
    #confirm_dialog.visible {
        display: block;
    }
    
    #confirm_overlay {
        background: black;
        opacity: 0.8;
    }
    
    #confirm_box {
        width: 40;
        height: auto;
        border: solid $error;
        background: $panel;
        padding: 2;
    }
    
    #confirm_title {
        text-style: bold;
        color: $error;
        height: auto;
    }
    
    #confirm_message {
        height: auto;
        margin-top: 1;
    }
    
    #confirm_buttons {
        height: auto;
        margin-top: 2;
        align: center middle;
    }
    """
    
    def __init__(self, settings: Optional[SettingsData] = None) -> None:
        """Initialize the Settings Screen.
        
        Args:
            settings: Optional settings to edit. Creates new if not provided.
        """
        super().__init__()
        self._settings = settings or SettingsData()
        self._original_settings = SettingsData(**self._settings.to_dict())
        self._current_tab: str = "general"
        self._confirm_type: Optional[str] = None
    
    def compose(self) -> ComposeResult:
        """Compose the settings screen widgets."""
        yield Header(show_clock=True)
        
        with Container(id="settings_container"):
            # Header bar
            yield Static("\u26c4 Dashboard Settings", id="header_bar")
            
            # Tab bar
            with Horizontal(id="tab_bar"):
                yield Button("General", id="tab_general", classes="tab_button active")
                yield Button("Appearance", id="tab_appearance", classes="tab_button")
                yield Button("Data", id="tab_data", classes="tab_button")
                yield Button("Advanced", id="tab_advanced", classes="tab_button")
            
            # Section content area - General section
            with ScrollableContainer(id="section_content"):
                # General Section
                with Container(id="general_section"):
                    yield Static("General Settings", classes="section_title")
                    
                    with Horizontal(classes="form_row"):
                        yield Label("Default Tab:", classes="form_label")
                        yield SelectField(
                            id="field_default_tab",
                            options=["home", "agents", "memory", "tools", "settings"],
                            value=self._settings.default_tab,
                        )
                    
                    with Horizontal(classes="form_row"):
                        yield Label("Auto Refresh:", classes="form_label")
                        yield CheckboxField(
                            id="field_auto_refresh",
                            label="Enable auto-refresh",
                            value=self._settings.auto_refresh,
                        )
                    
                    with Horizontal(classes="form_row"):
                        yield Label("Refresh Interval:", classes="form_label")
                        yield NumberField(
                            id="field_refresh_interval",
                            value=float(self._settings.refresh_interval),
                            min_val=1,
                            max_val=300,
                        )
                    
                    with Horizontal(classes="form_row"):
                        yield Label("Notifications:", classes="form_label")
                        yield CheckboxField(
                            id="field_show_notifications",
                            label="Show notifications",
                            value=self._settings.show_notifications,
                        )
                
                # Appearance Section (hidden by default)
                with Container(id="appearance_section", classes="hidden"):
                    yield Static("Appearance Settings", classes="section_title")
                    
                    with Horizontal(classes="form_row"):
                        yield Label("Theme:", classes="form_label")
                        yield SelectField(
                            id="field_theme",
                            options=["dark", "light", "auto"],
                            value=self._settings.theme,
                        )
                    
                    with Horizontal(classes="form_row"):
                        yield Label("Font Size:", classes="form_label")
                        yield NumberField(
                            id="field_font_size",
                            value=float(self._settings.font_size),
                            min_val=10,
                            max_val=24,
                        )
                    
                    with Horizontal(classes="form_row"):
                        yield Label("Compact Mode:", classes="form_label")
                        yield CheckboxField(
                            id="field_compact_mode",
                            label="Enable compact layout",
                            value=self._settings.compact_mode,
                        )
                    
                    with Horizontal(classes="form_row"):
                        yield Label("Show Borders:", classes="form_label")
                        yield CheckboxField(
                            id="field_show_borders",
                            label="Display borders around elements",
                            value=self._settings.show_borders,
                        )
                
                # Data Section (hidden by default)
                with Container(id="data_section", classes="hidden"):
                    yield Static("Data Settings", classes="section_title")
                    
                    with Horizontal(classes="form_row"):
                        yield Label("Cache Enabled:", classes="form_label")
                        yield CheckboxField(
                            id="field_cache_enabled",
                            label="Enable data caching",
                            value=self._settings.cache_enabled,
                        )
                    
                    with Horizontal(classes="form_row"):
                        yield Label("Cache Size (MB):", classes="form_label")
                        yield NumberField(
                            id="field_cache_size_mb",
                            value=float(self._settings.cache_size_mb),
                            min_val=10,
                            max_val=1000,
                        )
                    
                    with Horizontal(classes="form_row"):
                        yield Label("Data Retention:", classes="form_label")
                        yield NumberField(
                            id="field_data_retention_days",
                            value=float(self._settings.data_retention_days),
                            min_val=1,
                            max_val=365,
                        )
                
                # Advanced Section (hidden by default)
                with Container(id="advanced_section", classes="hidden"):
                    yield Static("Advanced Settings", classes="section_title")
                    
                    with Horizontal(classes="form_row"):
                        yield Label("Debug Mode:", classes="form_label")
                        yield CheckboxField(
                            id="field_debug_mode",
                            label="Enable debug mode",
                            value=self._settings.debug_mode,
                        )
                    
                    with Horizontal(classes="form_row"):
                        yield Label("Verbose Logging:", classes="form_label")
                        yield CheckboxField(
                            id="field_verbose_logging",
                            label="Enable verbose logging",
                            value=self._settings.verbose_logging,
                        )
                    
                    with Horizontal(classes="form_row"):
                        yield Label("Experimental:", classes="form_label")
                        yield CheckboxField(
                            id="field_experimental_features",
                            label="Enable experimental features",
                            value=self._settings.experimental_features,
                        )
            
            # Button bar
            with Horizontal(id="button_bar"):
                yield Button("Save", variant="success", id="btn_save")
                yield Button("Reset", variant="error", id="btn_reset")
                yield Button("Cancel", variant="default", id="btn_cancel")
            
            # Confirmation dialog (overlay)
            with Container(id="confirm_dialog"):
                yield Static("", id="confirm_overlay")
                with Container(id="confirm_box"):
                    yield Static("Confirm Action", id="confirm_title")
                    yield Static("", id="confirm_message")
                    with Horizontal(id="confirm_buttons"):
                        yield Button("Confirm", variant="error", id="btn_confirm")
                        yield Button("Cancel", variant="default", id="btn_cancel_confirm")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id
        
        if button_id == "tab_general":
            self._switch_tab("general")
        elif button_id == "tab_appearance":
            self._switch_tab("appearance")
        elif button_id == "tab_data":
            self._switch_tab("data")
        elif button_id == "tab_advanced":
            self._switch_tab("advanced")
        elif button_id == "btn_save":
            self._save_settings()
        elif button_id == "btn_reset":
            self._show_confirm("reset")
        elif button_id == "btn_cancel":
            self._cancel()
        elif button_id == "btn_confirm":
            self._handle_confirm()
        elif button_id == "btn_cancel_confirm":
            self._hide_confirm()
    
    def _switch_tab(self, tab_name: str) -> None:
        """Switch between settings tabs."""
        self._current_tab = tab_name
        
        # Update tab button states
        for tab_id in ["tab_general", "tab_appearance", "tab_data", "tab_advanced"]:
            btn = self.query_one(f"#{tab_id}", Button)
            btn.remove_class("active")
        
        active_btn = self.query_one(f"#tab_{tab_name}", Button)
        active_btn.add_class("active")
        
        # Show/hide sections
        for section_id in ["general_section", "appearance_section", "data_section", "advanced_section"]:
            section = self.query_one(f"#{section_id}", Container)
            if section_id == f"{tab_name}_section":
                section.remove_class("hidden")
            else:
                section.add_class("hidden")
    
    def _get_form_values(self) -> dict[str, Any]:
        """Extract values from form fields."""
        values: dict[str, Any] = {}
        
        # General
        try:
            tab_field = self.query_one("#field_default_tab", SelectField)
            values["default_tab"] = tab_field.get_value()
        except Exception:
            values["default_tab"] = self._settings.default_tab
        
        try:
            auto_refresh_field = self.query_one("#field_auto_refresh", CheckboxField)
            values["auto_refresh"] = auto_refresh_field.get_value()
        except Exception:
            values["auto_refresh"] = self._settings.auto_refresh
        
        try:
            interval_field = self.query_one("#field_refresh_interval", NumberField)
            values["refresh_interval"] = int(interval_field.get_value())
        except Exception:
            values["refresh_interval"] = self._settings.refresh_interval
        
        try:
            notif_field = self.query_one("#field_show_notifications", CheckboxField)
            values["show_notifications"] = notif_field.get_value()
        except Exception:
            values["show_notifications"] = self._settings.show_notifications
        
        # Appearance
        try:
            theme_field = self.query_one("#field_theme", SelectField)
            values["theme"] = theme_field.get_value()
        except Exception:
            values["theme"] = self._settings.theme
        
        try:
            font_field = self.query_one("#field_font_size", NumberField)
            values["font_size"] = int(font_field.get_value())
        except Exception:
            values["font_size"] = self._settings.font_size
        
        try:
            compact_field = self.query_one("#field_compact_mode", CheckboxField)
            values["compact_mode"] = compact_field.get_value()
        except Exception:
            values["compact_mode"] = self._settings.compact_mode
        
        try:
            borders_field = self.query_one("#field_show_borders", CheckboxField)
            values["show_borders"] = borders_field.get_value()
        except Exception:
            values["show_borders"] = self._settings.show_borders
        
        # Data
        try:
            cache_enabled_field = self.query_one("#field_cache_enabled", CheckboxField)
            values["cache_enabled"] = cache_enabled_field.get_value()
        except Exception:
            values["cache_enabled"] = self._settings.cache_enabled
        
        try:
            cache_size_field = self.query_one("#field_cache_size_mb", NumberField)
            values["cache_size_mb"] = int(cache_size_field.get_value())
        except Exception:
            values["cache_size_mb"] = self._settings.cache_size_mb
        
        try:
            retention_field = self.query_one("#field_data_retention_days", NumberField)
            values["data_retention_days"] = int(retention_field.get_value())
        except Exception:
            values["data_retention_days"] = self._settings.data_retention_days
        
        # Advanced
        try:
            debug_field = self.query_one("#field_debug_mode", CheckboxField)
            values["debug_mode"] = debug_field.get_value()
        except Exception:
            values["debug_mode"] = self._settings.debug_mode
        
        try:
            verbose_field = self.query_one("#field_verbose_logging", CheckboxField)
            values["verbose_logging"] = verbose_field.get_value()
        except Exception:
            values["verbose_logging"] = self._settings.verbose_logging
        
        try:
            exp_field = self.query_one("#field_experimental_features", CheckboxField)
            values["experimental_features"] = exp_field.get_value()
        except Exception:
            values["experimental_features"] = self._settings.experimental_features
        
        return values
    
    def _set_form_values(self, settings: SettingsData) -> None:
        """Set form field values from settings."""
        # General
        try:
            tab_field = self.query_one("#field_default_tab", SelectField)
            tab_field.set_value(settings.default_tab)
        except Exception:
            pass
        
        try:
            auto_refresh_field = self.query_one("#field_auto_refresh", CheckboxField)
            auto_refresh_field.set_value(settings.auto_refresh)
        except Exception:
            pass
        
        try:
            interval_field = self.query_one("#field_refresh_interval", NumberField)
            interval_field.set_value(float(settings.refresh_interval))
        except Exception:
            pass
        
        try:
            notif_field = self.query_one("#field_show_notifications", CheckboxField)
            notif_field.set_value(settings.show_notifications)
        except Exception:
            pass
        
        # Appearance
        try:
            theme_field = self.query_one("#field_theme", SelectField)
            theme_field.set_value(settings.theme)
        except Exception:
            pass
        
        try:
            font_field = self.query_one("#field_font_size", NumberField)
            font_field.set_value(float(settings.font_size))
        except Exception:
            pass
        
        try:
            compact_field = self.query_one("#field_compact_mode", CheckboxField)
            compact_field.set_value(settings.compact_mode)
        except Exception:
            pass
        
        try:
            borders_field = self.query_one("#field_show_borders", CheckboxField)
            borders_field.set_value(settings.show_borders)
        except Exception:
            pass
        
        # Data
        try:
            cache_enabled_field = self.query_one("#field_cache_enabled", CheckboxField)
            cache_enabled_field.set_value(settings.cache_enabled)
        except Exception:
            pass
        
        try:
            cache_size_field = self.query_one("#field_cache_size_mb", NumberField)
            cache_size_field.set_value(float(settings.cache_size_mb))
        except Exception:
            pass
        
        try:
            retention_field = self.query_one("#field_data_retention_days", NumberField)
            retention_field.set_value(float(settings.data_retention_days))
        except Exception:
            pass
        
        # Advanced
        try:
            debug_field = self.query_one("#field_debug_mode", CheckboxField)
            debug_field.set_value(settings.debug_mode)
        except Exception:
            pass
        
        try:
            verbose_field = self.query_one("#field_verbose_logging", CheckboxField)
            verbose_field.set_value(settings.verbose_logging)
        except Exception:
            pass
        
        try:
            exp_field = self.query_one("#field_experimental_features", CheckboxField)
            exp_field.set_value(settings.experimental_features)
        except Exception:
            pass
    
    def _save_settings(self) -> None:
        """Save settings."""
        new_settings = SettingsData.from_dict(self._get_form_values())
        self._settings = new_settings
        self._original_settings = SettingsData(**new_settings.to_dict())
        self.notify("Settings saved successfully", severity="information")
        self.app.pop_screen()
    
    def _show_confirm(self, confirm_type: str) -> None:
        """Show confirmation dialog."""
        self._confirm_type = confirm_type
        dialog = self.query_one("#confirm_dialog", Container)
        
        message = self.query_one("#confirm_message", Static)
        
        if confirm_type == "reset":
            message.update("Reset all settings to defaults? This cannot be undone.")
        elif confirm_type == "discard":
            message.update("Discard unsaved changes?")
        
        dialog.add_class("visible")
    
    def _hide_confirm(self) -> None:
        """Hide confirmation dialog."""
        self._confirm_type = None
        dialog = self.query_one("#confirm_dialog", Container)
        dialog.remove_class("visible")
    
    def _handle_confirm(self) -> None:
        """Handle confirmation action."""
        if self._confirm_type == "reset":
            self._reset_to_default()
        elif self._confirm_type == "discard":
            self._cancel()
        
        self._hide_confirm()
    
    def _reset_to_default(self) -> None:
        """Reset settings to defaults."""
        self._settings = SettingsData()
        self._original_settings = SettingsData()
        self._set_form_values(self._settings)
        self.notify("Settings reset to defaults", severity="warning")
    
    def _cancel(self) -> None:
        """Cancel and close settings screen."""
        self.app.pop_screen()


# Module-level default settings instance
_default_settings: Optional[SettingsData] = None


def get_settings() -> SettingsData:
    """Get the global settings instance."""
    global _default_settings
    if _default_settings is None:
        _default_settings = SettingsData()
    return _default_settings