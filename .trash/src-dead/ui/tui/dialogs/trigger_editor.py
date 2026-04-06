"""
Trigger Editor Dialog for N-Xyme MIND Dashboard TUI.

Provides a modal dialog for managing routing triggers including:
- Adding/editing/removing trigger phrases
- Setting pattern types (exact/prefix/regex)
- Configuring handler types (callback/skill/function/workflow)
- Testing triggers with input strings
- Priority ordering
"""

from dataclasses import dataclass
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Header, Static, Label, Input, Select


# Trigger data model
@dataclass
class Trigger:
    """Represents a routing trigger configuration."""

    phrase: str
    pattern_type: str  # "exact", "prefix", "regex"
    handler: str  # handler identifier
    handler_type: str  # "callback", "skill", "function", "workflow"
    description: str = ""
    priority: int = 0
    enabled: bool = True

    def matches(self, test_string: str) -> bool:
        """Check if the trigger matches a test string.

        Args:
            test_string: String to test against the trigger.

        Returns:
            True if the trigger matches the test string.
        """
        if not self.enabled:
            return False

        if self.pattern_type == "exact":
            return self.phrase == test_string
        elif self.pattern_type == "prefix":
            return test_string.startswith(self.phrase)
        elif self.pattern_type == "regex":
            import re

            try:
                return bool(re.match(self.phrase, test_string))
            except re.error:
                return False
        return False


# Mock trigger data for demonstration
MOCK_TRIGGERS: list[Trigger] = [
    Trigger(
        phrase="/playwright",
        pattern_type="prefix",
        handler="playwright_skill",
        handler_type="skill",
        description="Browser automation via Playwright",
        priority=10,
        enabled=True,
    ),
    Trigger(
        phrase="/git-master",
        pattern_type="exact",
        handler="git_master_skill",
        handler_type="skill",
        description="Git operations - rebase, bisect, blame",
        priority=20,
        enabled=True,
    ),
    Trigger(
        phrase="/frontend",
        pattern_type="prefix",
        handler="frontend_ui_skill",
        handler_type="skill",
        description="UI/UX design and styling",
        priority=30,
        enabled=True,
    ),
    Trigger(
        phrase="/review",
        pattern_type="exact",
        handler="review_work_skill",
        handler_type="skill",
        description="Post-implementation review and QA",
        priority=40,
        enabled=True,
    ),
    Trigger(
        phrase="add feature.*",
        pattern_type="regex",
        handler="feature_handler",
        handler_type="function",
        description="Handle feature addition requests",
        priority=50,
        enabled=True,
    ),
]


class TriggerEditorDialog(ModalScreen):
    """
    Modal dialog for managing routing triggers.

    Features:
    - DataTable listing all triggers with key fields
    - Add/Edit/Remove/Duplicate trigger buttons
    - Test trigger functionality with input strings
    - Priority field for trigger ordering
    - Handler type selection (callback/skill/function/workflow)
    """

    CSS = """
    TriggerEditorDialog {
        background: $surface;
    }
    
    #dialog_container {
        width: 90%;
        height: 90%;
        border: solid $primary;
        background: $panel;
        padding: 1;
    }
    
    #header {
        height: auto;
        padding: 1;
        background: $primary;
    }
    
    #title {
        text-align: center;
        text-style: bold;
        color: $text;
    }
    
    #subtitle {
        text-align: center;
        color: $text-muted;
    }
    
    #main_content {
        height: 1fr;
        margin: 1 0;
    }
    
    #triggers_table {
        height: 40%;
        border: solid $primary;
        margin-bottom: 1;
    }
    
    #button_row {
        height: auto;
        align: center middle;
        margin-bottom: 1;
    }
    
    #editor_section {
        height: auto;
        border: solid $accent;
        padding: 1;
        background: $surface;
    }
    
    #editor_title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    
    .form_row {
        height: auto;
        margin: 1 0;
    }
    
    .form_label {
        width: 16;
        color: $text-muted;
    }
    
    #test_section {
        height: auto;
        border: solid $warning;
        padding: 1;
        margin-top: 1;
        background: $surface;
    }
    
    #test_title {
        text-style: bold;
        color: $warning;
        margin-bottom: 1;
    }
    
    #test_result {
        color: $text;
        margin-top: 1;
    }
    
    .match_result {
        text-style: bold;
    }
    
    .match_success {
        color: $success;
    }
    
    .match_failure {
        color: $error;
    }
    
    Button {
        margin: 0 1;
    }
    
    Button:hover {
        background: $primary-hover;
    }
    
    DataTable {
        margin: 0;
    }
    
    SelectionList {
        margin: 0;
    }
    """

    def __init__(self, triggers: Optional[list[Trigger]] = None) -> None:
        """
        Initialize the Trigger Editor Dialog.

        Args:
            triggers: Optional list of triggers. Uses mock data if not provided.
        """
        super().__init__()
        self._triggers: list[Trigger] = triggers or list(MOCK_TRIGGERS)
        self._selected_index: int = -1
        self._edit_mode: bool = False
        self._test_result_text: str = ""

    def compose(self) -> ComposeResult:
        """Compose the dialog widgets."""
        with Vertical(id="dialog_container"):
            # Header
            yield Static("Trigger Editor", id="title")
            yield Static("Manage routing trigger phrases and patterns", id="subtitle")

            # Main content area
            with Container(id="main_content"):
                # Triggers table
                yield DataTable(id="triggers_table")

                # Action buttons
                with Horizontal(id="button_row"):
                    yield Button("Add", variant="primary", id="btn_add")
                    yield Button("Edit", variant="default", id="btn_edit")
                    yield Button("Remove", variant="error", id="btn_remove")
                    yield Button("Duplicate", variant="default", id="btn_duplicate")
                    yield Button("Test", variant="warning", id="btn_test")
                    yield Button("Close", variant="default", id="btn_close")

                # Editor section
                with Vertical(id="editor_section"):
                    yield Static("Trigger Configuration", id="editor_title")

                    # Phrase field
                    with Horizontal():
                        yield Label("Phrase:")
                        yield Input(placeholder="Trigger phrase...", id="input_phrase")

                    # Pattern type selection
                    with Horizontal():
                        yield Label("Pattern:")
                        yield Select(
                            options=[
                                ("exact", "Exact Match"),
                                ("prefix", "Prefix Match"),
                                ("regex", "Regex Pattern"),
                            ],
                            value="exact",
                            id="select_pattern_type",
                        )

                    # Handler type selection
                    with Horizontal():
                        yield Label("Handler:")
                        yield Select(
                            options=[
                                ("callback", "Callback"),
                                ("skill", "Skill"),
                                ("function", "Function"),
                                ("workflow", "Workflow"),
                            ],
                            value="skill",
                            id="select_handler_type",
                        )

                    # Handler name field
                    with Horizontal():
                        yield Label("Handler ID:")
                        yield Input(
                            placeholder="handler_identifier", id="input_handler"
                        )

                    # Description field
                    with Horizontal():
                        yield Label("Description:")
                        yield Input(
                            placeholder="Description text...", id="input_description"
                        )

                    # Priority field
                    with Horizontal():
                        yield Label("Priority:")
                        yield Input(value="0", placeholder="0", id="input_priority")

                    # Enabled checkbox
                    with Horizontal():
                        yield Label("Enabled:")
                        yield Select(
                            options=[
                                ("true", "Yes"),
                                ("false", "No"),
                            ],
                            value="true",
                            id="select_enabled",
                        )

                # Test section
                with Vertical(id="test_section"):
                    yield Static("Test Trigger", id="test_title")

                    with Horizontal():
                        yield Label("Test String:", classes="form_label")
                        yield Input(
                            placeholder="Enter test string...", id="input_test_string"
                        )
                        yield Button("Test", variant="warning", id="btn_run_test")

                    yield Static("", id="test_result")

            # Footer with status
            yield Static("Use arrow keys to navigate, Enter to edit", id="footer")

    def on_mount(self) -> None:
        """Initialize the dialog on mount."""
        table = self.query_one("#triggers_table", DataTable)

        # Add columns
        table.add_columns(
            "Priority", "Phrase", "Pattern", "Handler Type", "Handler", "Enabled"
        )

        # Populate with triggers
        self._refresh_table()

        # Select first row if available
        if self._triggers:
            table.cursor_type = "row"

    def _refresh_table(self) -> None:
        """Refresh the triggers table with current data."""
        table = self.query_one("#triggers_table", DataTable)
        table.clear()

        # Sort by priority
        sorted_triggers = sorted(self._triggers, key=lambda t: t.priority)

        for trigger in sorted_triggers:
            enabled_str = "✓" if trigger.enabled else "✗"
            table.add_row(
                str(trigger.priority),
                trigger.phrase,
                trigger.pattern_type,
                trigger.handler_type,
                trigger.handler,
                enabled_str,
            )

    def _populate_editor(self, trigger: Optional[Trigger] = None) -> None:
        """Populate the editor fields with trigger data.

        Args:
            trigger: Trigger to populate from. Clears fields if None.
        """
        phrase_input = self.query_one("#input_phrase", Input)
        pattern_select = self.query_one("#select_pattern_type", Select)
        handler_type_select = self.query_one("#select_handler_type", Select)
        handler_input = self.query_one("#input_handler", Input)
        desc_input = self.query_one("#input_description", Input)
        priority_input = self.query_one("#input_priority", Input)
        enabled_select = self.query_one("#select_enabled", Select)

        if trigger:
            phrase_input.value = trigger.phrase
            pattern_select.value = trigger.pattern_type
            handler_type_select.value = trigger.handler_type
            handler_input.value = trigger.handler
            desc_input.value = trigger.description
            priority_input.value = str(trigger.priority)
            enabled_select.value = "true" if trigger.enabled else "false"
        else:
            phrase_input.value = ""
            pattern_select.value = "exact"
            handler_type_select.value = "skill"
            handler_input.value = ""
            desc_input.value = ""
            priority_input.value = "0"
            enabled_select.value = "true"

    def _collect_trigger_from_editor(self) -> Optional[Trigger]:
        """Collect trigger data from editor fields.

        Returns:
            Trigger instance if all required fields are valid, None otherwise.
        """
        phrase_input = self.query_one("#input_phrase", Input)
        pattern_select = self.query_one("#select_pattern_type", Select)
        handler_type_select = self.query_one("#select_handler_type", Select)
        handler_input = self.query_one("#input_handler", Input)
        desc_input = self.query_one("#input_description", Input)
        priority_input = self.query_one("#input_priority", Input)
        enabled_select = self.query_one("#select_enabled", Select)

        phrase = phrase_input.value.strip()
        handler = handler_input.value.strip()

        if not phrase or not handler:
            self.notify("Phrase and Handler ID are required", severity="error")
            return None

        try:
            priority = int(priority_input.value)
        except ValueError:
            priority = 0

        # Get values from Select widgets - handle NoSelection type
        pattern_val = pattern_select.value
        pattern_type = str(pattern_val) if pattern_val else "exact"

        handler_type_val = handler_type_select.value
        handler_type = str(handler_type_val) if handler_type_val else "skill"

        enabled_val = enabled_select.value
        enabled = str(enabled_val) == "true"

        return Trigger(
            phrase=phrase,
            pattern_type=pattern_type,
            handler=handler,
            handler_type=handler_type,
            description=desc_input.value.strip(),
            priority=priority,
            enabled=enabled,
        )

    def _test_trigger(self) -> None:
        """Test the currently selected trigger against the test string."""
        test_input = self.query_one("#input_test_string", Input)
        test_string = test_input.value.strip()

        result_label = self.query_one("#test_result", Static)

        if not test_string:
            result_label.update("Enter a test string to test the trigger")
            return

        if self._selected_index < 0 or self._selected_index >= len(self._triggers):
            result_label.update("No trigger selected")
            return

        # Get sorted triggers to match table selection
        sorted_triggers = sorted(self._triggers, key=lambda t: t.priority)
        trigger = sorted_triggers[self._selected_index]

        matches = trigger.matches(test_string)

        if matches:
            result_label.update(
                f"[match_success class='match_result']MATCHED[/] - Trigger '{trigger.phrase}' ({trigger.pattern_type}) matches '{test_string}'"
            )
        else:
            result_label.update(
                f"[match_failure class='match_result']NO MATCH[/] - Trigger '{trigger.phrase}' ({trigger.pattern_type}) does not match '{test_string}'"
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id

        if button_id == "btn_add":
            self._selected_index = -1
            self._populate_editor(None)
            self.notify("Add mode: Fill in trigger details", severity="information")
        elif button_id == "btn_edit":
            if self._selected_index >= 0:
                sorted_triggers = sorted(self._triggers, key=lambda t: t.priority)
                trigger = sorted_triggers[self._selected_index]
                self._populate_editor(trigger)
                self.notify("Edit mode: Modify trigger details", severity="information")
            else:
                self.notify("Select a trigger to edit", severity="warning")
        elif button_id == "btn_remove":
            if self._selected_index >= 0:
                sorted_triggers = sorted(self._triggers, key=lambda t: t.priority)
                trigger = sorted_triggers[self._selected_index]
                self._triggers.remove(trigger)
                self._selected_index = -1
                self._refresh_table()
                self._populate_editor(None)
                self.notify(
                    f"Removed trigger: {trigger.phrase}", severity="information"
                )
            else:
                self.notify("Select a trigger to remove", severity="warning")
        elif button_id == "btn_duplicate":
            if self._selected_index >= 0:
                sorted_triggers = sorted(self._triggers, key=lambda t: t.priority)
                trigger = sorted_triggers[self._selected_index]
                # Create duplicate with modified phrase
                new_trigger = Trigger(
                    phrase=f"{trigger.phrase}_copy",
                    pattern_type=trigger.pattern_type,
                    handler=trigger.handler,
                    handler_type=trigger.handler_type,
                    description=trigger.description,
                    priority=trigger.priority + 1,
                    enabled=trigger.enabled,
                )
                self._triggers.append(new_trigger)
                self._refresh_table()
                self.notify(
                    f"Duplicated trigger: {trigger.phrase}", severity="information"
                )
            else:
                self.notify("Select a trigger to duplicate", severity="warning")
        elif button_id == "btn_test":
            self._test_trigger()
        elif button_id == "btn_run_test":
            self._test_trigger()
        elif button_id == "btn_close":
            # Save any pending changes from editor
            if self._edit_mode or self._selected_index == -1:
                new_trigger = self._collect_trigger_from_editor()
                if new_trigger:
                    if self._selected_index >= 0:
                        # Update existing
                        sorted_triggers = sorted(
                            self._triggers, key=lambda t: t.priority
                        )
                        old_trigger = sorted_triggers[self._selected_index]
                        # Replace in original list
                        idx = self._triggers.index(old_trigger)
                        self._triggers[idx] = new_trigger
                    else:
                        # Add new
                        self._triggers.append(new_trigger)
                    self._refresh_table()
                    self.notify("Trigger saved", severity="information")
            self.app.pop_screen()

    def on_data_table_row_selected(self, event) -> None:
        """Handle row selection in the triggers table."""
        # Update selected index based on cursor position
        table = self.query_one("#triggers_table", DataTable)
        if table.cursor_row is not None:
            self._selected_index = table.cursor_row

    def on_data_table_row_activated(self, event) -> None:
        """Handle row activation (Enter key) in the triggers table."""
        # Populate editor with selected trigger
        if self._selected_index >= 0:
            sorted_triggers = sorted(self._triggers, key=lambda t: t.priority)
            if self._selected_index < len(sorted_triggers):
                trigger = sorted_triggers[self._selected_index]
                self._populate_editor(trigger)
