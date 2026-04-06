"""
Memory Explorer Dialog for N-Xyme MIND Dashboard TUI.

Provides a modal dialog for exploring knowledge graph and memory sources.
Features:
- Tree view of memory sources (11 sources)
- Entity list with search/filter
- Relationship viewer (from/to connections)
- Entity detail panel with observations
- Memory source enable/disable toggles
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Header,
    Static,
    Label,
    Input,
    Switch,
    Tree,
    Pretty,
)


# Mock data for memory sources (11 sources from dashboard)
MEMORY_SOURCES = [
    {"id": "session", "name": "Session Memory", "enabled": True, "type": "episodic"},
    {
        "id": "athena",
        "name": "Athena Knowledge Base",
        "enabled": True,
        "type": "semantic",
    },
    {
        "id": "file_content",
        "name": "File Content Index",
        "enabled": True,
        "type": "content",
    },
    {"id": "mcp", "name": "MCP Tools Memory", "enabled": True, "type": "tools"},
    {"id": "unified", "name": "Unified Memory", "enabled": True, "type": "hybrid"},
    {"id": "github", "name": "GitHub Context", "enabled": False, "type": "external"},
    {"id": "git", "name": "Git History", "enabled": True, "type": "version_control"},
    {
        "id": "context7",
        "name": "Context7 Docs",
        "enabled": True,
        "type": "documentation",
    },
    {"id": "slack", "name": "Slack History", "enabled": False, "type": "external"},
    {"id": "notion", "name": "Notion Pages", "enabled": False, "type": "external"},
    {"id": "project", "name": "Project Manifest", "enabled": True, "type": "metadata"},
]

# Mock data for entities
MOCK_ENTITIES = [
    {
        "id": "ent_001",
        "name": "Sisyphus",
        "entity_type": "agent",
        "observations": [
            "Primary orchestrator agent for N-Xyme MIND",
            "Handles task delegation and workflow management",
            "Uses subagent system for specialized tasks",
        ],
    },
    {
        "id": "ent_002",
        "name": "Hephaestus",
        "entity_type": "agent",
        "observations": [
            "Implementation agent",
            "Writes code directly to files",
            "Specializes in code generation and file operations",
        ],
    },
    {
        "id": "ent_003",
        "name": "Oracle",
        "entity_type": "agent",
        "observations": [
            "Architecture review agent",
            "Provides guidance on design decisions",
            "High-cost reasoning model",
        ],
    },
    {
        "id": "ent_004",
        "name": "Memory System",
        "entity_type": "system",
        "observations": [
            "Manages 11 memory sources",
            "Supports semantic, episodic, and hybrid memory",
            "Integrated with Athena knowledge base",
        ],
    },
    {
        "id": "ent_005",
        "name": "ActivityLogger",
        "entity_type": "component",
        "observations": [
            "Tracks dashboard activity events",
            "Supports filtering by event type",
            "Can export logs to CSV",
        ],
    },
    {
        "id": "ent_006",
        "name": "N-Xyme MIND",
        "entity_type": "project",
        "observations": [
            "AI-powered development assistant",
            "Uses BMAD workflow system",
            "Supports TUI and web interfaces",
        ],
    },
]

# Mock data for relationships
MOCK_RELATIONSHIPS = [
    {"from": "Sisyphus", "to": "Hephaestus", "relation": "delegates_to"},
    {"from": "Sisyphus", "to": "Oracle", "relation": "consults"},
    {"from": "Sisyphus", "to": "Memory System", "relation": "uses"},
    {"from": "Hephaestus", "to": "N-Xyme MIND", "relation": "writes_to"},
    {"from": "Oracle", "to": "N-Xyme MIND", "relation": "reviews"},
    {
        "from": "Memory System",
        "to": "Athena Knowledge Base",
        "relation": "integrates_with",
    },
    {"from": "ActivityLogger", "to": "N-Xyme MIND", "relation": "logs_events"},
    {"from": "Sisyphus", "to": "Project Manifest", "relation": "reads_from"},
]


@dataclass
class Entity:
    """Represents an entity in the knowledge graph."""

    id: str
    name: str
    entity_type: str
    observations: list[str] = field(default_factory=list)


@dataclass
class Relationship:
    """Represents a relationship between entities."""

    from_entity: str
    to_entity: str
    relation: str


class MemoryExplorerDialog(ModalScreen):
    """
    Modal dialog for exploring knowledge graph and memory sources.

    Features:
    - Left panel: Tree view of memory sources with enable/disable toggles
    - Center panel: Entity list with search/filter
    - Right panel: Entity details with observations and relationships
    """

    CSS = """
    MemoryExplorerDialog {
        background: $surface;
    }

    #dialog_container {
        width: 90%;
        height: 85%;
        border: solid $primary;
        background: $panel;
        padding: 1;
    }

    #title_bar {
        height: auto;
        padding: 1;
        background: $primary;
        text-align: center;
    }

    #title {
        text-style: bold;
        color: $text;
    }

    #main_content {
        height: 1fr;
        layout: horizontal;
    }

    #left_panel {
        width: 25%;
        border: solid $primary;
        padding: 1;
    }

    #center_panel {
        width: 35%;
        border: solid $primary;
        padding: 1;
    }

    #right_panel {
        width: 40%;
        border: solid $primary;
        padding: 1;
    }

    .panel_header {
        text-style: bold;
        padding: 0 1;
        background: $primary-darken-1;
        color: $text;
    }

    #source_tree {
        height: 1fr;
        margin-top: 1;
    }

    #entity_search {
        margin: 1 0;
    }

    #entity_table {
        height: 1fr;
        margin-top: 1;
    }

    #detail_panel {
        height: 1fr;
    }

    #observations {
        height: 1fr;
        border: solid $primary;
        margin-top: 1;
    }

    #relationships {
        height: 1fr;
        border: solid $primary;
        margin-top: 1;
    }

    #close_button {
        height: auto;
        align: center middle;
        padding: 1;
    }

    .source_row {
        height: auto;
        layout: horizontal;
    }

    .source_label {
        width: 1fr;
    }

    Switch {
        margin: 0 1;
    }

    DataTable {
        margin: 0;
    }

    Pretty {
        margin: 0;
        padding: 0;
    }
    """

    def __init__(self) -> None:
        """Initialize the Memory Explorer Dialog."""
        super().__init__()
        self._entities = [Entity(**e) for e in MOCK_ENTITIES]
        self._relationships = [Relationship(**r) for r in MOCK_RELATIONSHIPS]
        self._sources = {s["id"]: s.copy() for s in MEMORY_SOURCES}
        self._selected_entity: Optional[Entity] = None
        self._search_filter: str = ""

    def compose(self) -> ComposeResult:
        """Compose the dialog widgets."""
        with Container(id="dialog_container"):
            # Title bar
            with Vertical(id="title_bar"):
                yield Static("Memory Explorer", id="title")

            # Main content area with three panels
            with Horizontal(id="main_content"):
                # Left panel: Memory sources tree
                with Vertical(id="left_panel"):
                    yield Static("Memory Sources", classes="panel_header")
                    yield Tree("", id="source_tree")

                # Center panel: Entity list
                with Vertical(id="center_panel"):
                    yield Static("Entities", classes="panel_header")
                    yield Input(placeholder="Search entities...", id="entity_search")
                    yield DataTable(id="entity_table")

                # Right panel: Entity details
                with Vertical(id="right_panel"):
                    yield Static("Entity Details", classes="panel_header")
                    with Container(id="detail_panel"):
                        yield Static("Select an entity...", id="entity_name")
                        with Container(id="observations"):
                            yield Static("Observations:", classes="panel_header")
                            yield Pretty([], id="observations_list")
                        with Container(id="relationships"):
                            yield Static("Relationships:", classes="panel_header")
                            yield Pretty([], id="relationships_list")

            # Close button
            with Horizontal(id="close_button"):
                yield Button("Close", variant="default", id="btn_close")

    def on_mount(self) -> None:
        """Initialize the dialog on mount."""
        self._setup_source_tree()
        self._setup_entity_table()
        self._bind_events()

    def _setup_source_tree(self) -> None:
        """Set up the memory sources tree view."""
        tree = self.query_one("#source_tree", Tree)

        # Root node
        tree.root.label = "Sources"

        # Add source nodes
        for source in MEMORY_SOURCES:
            tree.root.add(
                f"{source['name']} ({source['type']})",
                data=source,
            )

        tree.refresh()

    def _setup_entity_table(self) -> None:
        """Set up the entity table."""
        table = self.query_one("#entity_table", DataTable)
        table.add_columns("Name", "Type")

        self._refresh_entity_table()

    def _refresh_entity_table(self) -> None:
        """Refresh the entity table based on current filter."""
        table = self.query_one("#entity_table", DataTable)
        table.clear()

        filtered_entities = self._entities
        if self._search_filter:
            filter_lower = self._search_filter.lower()
            filtered_entities = [
                e
                for e in self._entities
                if filter_lower in e.name.lower()
                or filter_lower in e.entity_type.lower()
            ]

        for entity in filtered_entities:
            table.add_row(entity.name, entity.entity_type)

    def _bind_events(self) -> None:
        """Bind event handlers."""
        pass

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input change events."""
        if event.input.id == "entity_search":
            self._search_filter = event.input.value
            self._refresh_entity_table()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submit events."""
        if event.input.id == "entity_search":
            self._search_filter = event.input.value
            self._refresh_entity_table()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle entity table row selection."""
        row_idx = event.cursor_row

        if row_idx is not None:
            filtered_entities = self._entities
            if self._search_filter:
                filter_lower = self._search_filter.lower()
                filtered_entities = [
                    e
                    for e in self._entities
                    if filter_lower in e.name.lower()
                    or filter_lower in e.entity_type.lower()
                ]

            if 0 <= row_idx < len(filtered_entities):
                self._selected_entity = filtered_entities[row_idx]
                self._update_detail_panel()

    def _update_detail_panel(self) -> None:
        """Update the entity detail panel."""
        if self._selected_entity is None:
            return

        # Update entity name
        name_label = self.query_one("#entity_name", Static)
        name_label.update(
            f"{self._selected_entity.name} ({self._selected_entity.entity_type})"
        )

        # Update observations
        observations_list = self.query_one("#observations_list", Pretty)
        observations_list.update(self._selected_entity.observations)

        # Update relationships
        rels = [
            f"{r.from_entity} --[{r.relation}]--> {r.to_entity}"
            for r in self._relationships
            if r.from_entity == self._selected_entity.name
            or r.to_entity == self._selected_entity.name
        ]
        if not rels:
            rels = ["No relationships found"]
        relationships_list = self.query_one("#relationships_list", Pretty)
        relationships_list.update(rels)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "btn_close":
            self.app.pop_screen()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle tree node selection."""
        node = event.node
        if node.data and isinstance(node.data, dict):
            source_id = node.data.get("id")
            if source_id and source_id in self._sources:
                # Toggle enabled state
                self._sources[source_id]["enabled"] = not self._sources[source_id][
                    "enabled"
                ]
                self.notify(
                    f"Source '{self._sources[source_id]['name']}' "
                    f"{'enabled' if self._sources[source_id]['enabled'] else 'disabled'}"
                )


# Module-level dialog function for easy access
def show_memory_explorer(app) -> None:
    """
    Show the Memory Explorer dialog.

    Args:
        app: The Textual app instance to push the dialog onto.
    """
    app.push_screen(MemoryExplorerDialog())
