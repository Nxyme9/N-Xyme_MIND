#!/usr/bin/env python3
"""
Navigation widgets for N-Xyme MIND Dashboard TUI.

Provides TabNavigation, BreadcrumbNav, SideNav, and QuickSwitcher widgets
for dashboard navigation with keyboard support.
"""

from typing import Callable, List, Optional, Set

from textual.app import ComposeResult
from textual.css.query import DOMQuery
from textual.events import Key
from textual.geometry import Offset, Size
from textual.widget import Widget
from textual.widgets import Static


class TabNavigation(Static):
    """
    Horizontal tab bar with keyboard shortcuts (1-8).

    Displays tabs that can be selected via click or keyboard.
    Supports keyboard navigation with number keys and arrow keys.
    """

    def __init__(
        self,
        tabs: Optional[List[str]] = None,
        active: int = 0,
        **kwargs,
    ):
        """Initialize the tab navigation widget.

        Args:
            tabs: List of tab labels. Defaults to empty list.
            active: Index of the active tab (0-based). Default 0.
            **kwargs: Additional Static widget arguments.
        """
        super().__init__(**kwargs)
        self._tabs: List[str] = tabs or []
        self._active: int = active
        self._disabled: Set[int] = set()
        self._focused: int = -1
        self._on_change: Optional[Callable[[int], None]] = None
        self._update_content()

    def set_tabs(self, tabs: List[str]) -> None:
        """Set the tab labels.

        Args:
            tabs: List of tab label strings.
        """
        self._tabs = list(tabs)
        if self._active >= len(self._tabs):
            self._active = max(0, len(self._tabs) - 1) if self._tabs else 0
        self._focused = -1
        self._update_content()

    def set_active(self, index: int) -> None:
        """Set the active tab.

        Args:
            index: Index of the tab to make active (0-based).
        """
        if not self._tabs:
            return
        if index in self._disabled:
            return
        self._active = max(0, min(index, len(self._tabs) - 1))
        self._update_content()

    def set_disabled(self, index: int, disabled: bool = True) -> None:
        """Set a tab as disabled/enabled.

        Args:
            index: Index of the tab to modify.
            disabled: True to disable, False to enable.
        """
        if 0 <= index < len(self._tabs):
            if disabled:
                self._disabled.add(index)
            else:
                self._disabled.discard(index)
            self._update_content()

    def bind_on_change(self, callback: Callable[[int], None]) -> None:
        """Bind a callback for tab changes.

        Args:
            callback: Function to call when active tab changes. Receives new index.
        """
        self._on_change = callback

    def _update_content(self) -> None:
        """Update the widget content."""
        if not self._tabs:
            self.update("")
            return

        parts: List[str] = []
        for i, tab in enumerate(self._tabs):
            is_active = i == self._active
            is_disabled = i in self._disabled
            is_focused = i == self._focused

            # Build tab representation
            if is_disabled:
                parts.append(f"[dim]{tab}[/dim]")
            elif is_active:
                parts.append(f"[bold white on blue]{tab}[/bold white on blue]")
            elif is_focused:
                parts.append(f"[bold cyan]{tab}[/bold cyan]")
            else:
                parts.append(f"cyan:{tab}")

            # Add separator if not last
            if i < len(self._tabs) - 1:
                parts.append(" | ")

        self.update("".join(parts))

    def on_mount(self) -> None:
        """Handle mount event."""
        self._focused = self._active
        self._update_content()

    def _handle_left(self) -> None:
        """Move focus left."""
        if not self._tabs:
            return
        # Find previous non-disabled tab
        for offset in range(len(self._tabs) - 1):
            new_idx = (self._focused - 1 - offset) % len(self._tabs)
            if new_idx not in self._disabled:
                self._focused = new_idx
                self._update_content()
                return

    def _handle_right(self) -> None:
        """Move focus right."""
        if not self._tabs:
            return
        # Find next non-disabled tab
        for offset in range(len(self._tabs)):
            new_idx = (self._focused + 1 + offset) % len(self._tabs)
            if new_idx not in self._disabled:
                self._focused = new_idx
                self._update_content()
                return

    def _handle_enter(self) -> None:
        """Select the focused tab."""
        if self._focused >= 0 and self._focused not in self._disabled:
            self._active = self._focused
            self._update_content()
            if self._on_change:
                self._on_change(self._active)

    def _handle_number(self, key: str) -> bool:
        """Handle number key press for shortcuts.

        Args:
            key: The key pressed (e.g., "1", "2").

        Returns:
            True if handled, False otherwise.
        """
        try:
            num = int(key) - 1  # Convert 1-based to 0-based
            if 0 <= num < len(self._tabs) and num not in self._disabled:
                self._active = num
                self._focused = num
                self._update_content()
                if self._on_change:
                    self._on_change(self._active)
                return True
        except ValueError:
            pass
        return False

    def on_key(self, event: Key) -> None:
        """Handle key events."""
        key = event.key

        if key == "left":
            self._handle_left()
        elif key == "right":
            self._handle_right()
        elif key == "enter":
            self._handle_enter()
        elif key == "escape":
            self.focus(False)
        elif len(key) == 1 and key.isdigit():
            self._handle_number(key)


class BreadcrumbNav(Static):
    """
    Breadcrumb trail for nested views.

    Displays a hierarchical navigation path with clickable segments.
    Supports keyboard navigation (left/right arrows, enter to select).
    """

    def __init__(
        self,
        path: Optional[List[str]] = None,
        root_label: str = "Home",
        **kwargs,
    ):
        """Initialize the breadcrumb navigation widget.

        Args:
            path: List of path segments. Defaults to empty list.
            root_label: Label for the root/home segment. Default "Home".
            **kwargs: Additional Static widget arguments.
        """
        super().__init__(**kwargs)
        self._root_label = root_label
        self._path: List[str] = path or []
        self._focused: int = -1  # -1 means root focused
        self._on_select: Optional[Callable[[int], None]] = None
        self._update_content()

    def set_path(self, path: List[str]) -> None:
        """Set the breadcrumb path.

        Args:
            path: List of path segment strings.
        """
        self._path = list(path)
        self._focused = len(self._path)  # Focus last item
        self._update_content()

    def push(self, segment: str) -> None:
        """Add a segment to the path.

        Args:
            segment: String to add as new path segment.
        """
        self._path.append(segment)
        self._focused = len(self._path)
        self._update_content()

    def pop(self) -> Optional[str]:
        """Remove the last segment from the path.

        Returns:
            The removed segment, or None if path was empty.
        """
        if self._path:
            removed = self._path.pop()
            self._focused = len(self._path)
            self._update_content()
            return removed
        return None

    def bind_on_select(self, callback: Callable[[int], None]) -> None:
        """Bind a callback for segment selection.

        Args:
            callback: Function to call when a segment is selected. Receives index.
        """
        self._on_select = callback

    def _update_content(self) -> None:
        """Update the widget content."""
        parts: List[str] = []

        # Add root
        is_focused = self._focused == -1
        if is_focused:
            parts.append(f"[bold white on cyan]{self._root_label}[/bold white on cyan]")
        else:
            parts.append(f"[link]{self._root_label}[/link]")

        # Add path segments
        for i, segment in enumerate(self._path):
            parts.append(" [dim]>[/dim] ")

            is_focused = self._focused == i
            if is_focused:
                parts.append(f"[bold white on cyan]{segment}[/bold white on cyan]")
            else:
                parts.append(f"[link]{segment}[/link]")

        self.update("".join(parts))

    def on_mount(self) -> None:
        """Handle mount event."""
        self._focused = len(self._path)
        self._update_content()

    def _handle_left(self) -> None:
        """Move focus left."""
        if self._focused > -1:
            self._focused -= 1
            self._update_content()

    def _handle_right(self) -> None:
        """Move focus right."""
        if self._focused < len(self._path):
            self._focused += 1
            self._update_content()

    def _handle_enter(self) -> None:
        """Select the focused segment."""
        if self._on_select and self._focused >= 0:
            self._on_select(self._focused)

    def on_key(self, event: Key) -> None:
        """Handle key events."""
        key = event.key

        if key == "left":
            self._handle_left()
        elif key == "right":
            self._handle_right()
        elif key == "enter":
            self._handle_enter()
        elif key == "escape":
            self.focus(False)


class SideNav(Static):
    """
    Vertical sidebar for main sections.

    Displays a vertical list of navigation items with icons/labels.
    Supports keyboard navigation (up/down arrows, enter to select).
    """

    def __init__(
        self,
        items: Optional[List[str]] = None,
        active: int = 0,
        **kwargs,
    ):
        """Initialize the side navigation widget.

        Args:
            items: List of navigation item labels. Defaults to empty list.
            active: Index of the active item (0-based). Default 0.
            **kwargs: Additional Static widget arguments.
        """
        super().__init__(**kwargs)
        self._items: List[str] = items or []
        self._active: int = active
        self._focused: int = active
        self._disabled: Set[int] = set()
        self._on_change: Optional[Callable[[int], None]] = None
        self._update_content()

    def set_items(self, items: List[str]) -> None:
        """Set the navigation items.

        Args:
            items: List of navigation item strings.
        """
        self._items = list(items)
        if self._active >= len(self._items):
            self._active = max(0, len(self._items) - 1) if self._items else 0
        self._focused = self._active
        self._update_content()

    def set_active(self, index: int) -> None:
        """Set the active item.

        Args:
            index: Index of the item to make active (0-based).
        """
        if not self._items:
            return
        if index in self._disabled:
            return
        self._active = max(0, min(index, len(self._items) - 1))
        self._update_content()

    def set_disabled(self, index: int, disabled: bool = True) -> None:
        """Set an item as disabled/enabled.

        Args:
            index: Index of the item to modify.
            disabled: True to disable, False to enable.
        """
        if 0 <= index < len(self._items):
            if disabled:
                self._disabled.add(index)
            else:
                self._disabled.discard(index)
            self._update_content()

    def bind_on_change(self, callback: Callable[[int], None]) -> None:
        """Bind a callback for item selection.

        Args:
            callback: Function to call when active item changes. Receives new index.
        """
        self._on_change = callback

    def _update_content(self) -> None:
        """Update the widget content."""
        if not self._items:
            self.update("")
            return

        lines: List[str] = []
        for i, item in enumerate(self._items):
            is_active = i == self._active
            is_disabled = i in self._disabled
            is_focused = i == self._focused

            # Build item representation with prefix indicator
            if is_active:
                prefix = "[bold white on green]●[/bold white on green] "
                lines.append(prefix + f"[bold white]{item}[/bold white]")
            elif is_disabled:
                prefix = "[dim]○[/dim]  "
                lines.append(prefix + f"[dim]{item}[/dim]")
            elif is_focused:
                prefix = "[bold cyan]›[/bold cyan] "
                lines.append(prefix + f"[bold cyan]{item}[/bold cyan]")
            else:
                prefix = "[cyan]▸[/cyan]  "
                lines.append(prefix + f"[cyan]{item}[/cyan]")

        self.update("\n".join(lines))

    def on_mount(self) -> None:
        """Handle mount event."""
        self._focused = self._active
        self._update_content()

    def _handle_up(self) -> None:
        """Move focus up."""
        if not self._items:
            return
        # Find previous non-disabled item
        for offset in range(len(self._items) - 1):
            new_idx = (self._focused - 1 - offset) % len(self._items)
            if new_idx not in self._disabled:
                self._focused = new_idx
                self._update_content()
                return

    def _handle_down(self) -> None:
        """Move focus down."""
        if not self._items:
            return
        # Find next non-disabled item
        for offset in range(len(self._items)):
            new_idx = (self._focused + 1 + offset) % len(self._items)
            if new_idx not in self._disabled:
                self._focused = new_idx
                self._update_content()
                return

    def _handle_enter(self) -> None:
        """Select the focused item."""
        if self._focused >= 0 and self._focused not in self._disabled:
            self._active = self._focused
            self._update_content()
            if self._on_change:
                self._on_change(self._active)

    def on_key(self, event: Key) -> None:
        """Handle key events."""
        key = event.key

        if key == "up":
            self._handle_up()
        elif key == "down":
            self._handle_down()
        elif key == "enter":
            self._handle_enter()
        elif key == "escape":
            self.focus(False)


class QuickSwitcher(Static):
    """
    Command palette style navigation (Ctrl+K).

    Displays an overlay with search input and filtered results.
    Supports fuzzy search, keyboard navigation, and action execution.
    """

    def __init__(
        self,
        items: Optional[List[dict]] = None,
        **kwargs,
    ):
        """Initialize the quick switcher widget.

        Args:
            items: List of item dicts with 'id', 'label', 'category' keys.
            **kwargs: Additional Static widget arguments.
        """
        super().__init__(**kwargs)
        self._items: List[dict] = items or []
        self._filtered: List[dict] = []
        self._query: str = ""
        self._focused: int = 0
        self._on_select: Optional[Callable[[str], None]] = None
        self._visible: bool = False
        self._update_filtered()

    def set_items(self, items: List[dict]) -> None:
        """Set the switcher items.

        Args:
            items: List of item dictionaries with 'id', 'label', 'category' keys.
        """
        self._items = list(items)
        self._update_filtered()

    def set_visible(self, visible: bool) -> None:
        """Show/hide the quick switcher.

        Args:
            visible: True to show, False to hide.
        """
        self._visible = visible
        if visible:
            self._query = ""
            self._focused = 0
            self._update_filtered()
        self._update_content()

    def bind_on_select(self, callback: Callable[[str], None]) -> None:
        """Bind a callback for item selection.

        Args:
            callback: Function to call when an item is selected. Receives item id.
        """
        self._on_select = callback

    def _fuzzy_match(self, query: str, text: str) -> bool:
        """Check if query matches text with fuzzy matching.

        Args:
            query: The search query.
            text: The text to match against.

        Returns:
            True if there's a match, False otherwise.
        """
        query = query.lower()
        text = text.lower()

        # Direct substring
        if query in text:
            return True

        # Fuzzy: all chars in order
        if all(c in text for c in query):
            return True

        return False

    def _update_filtered(self) -> None:
        """Update the filtered items based on query."""
        if not self._query:
            self._filtered = list(self._items)
        else:
            self._filtered = [
                item
                for item in self._items
                if self._fuzzy_match(self._query, item.get("label", ""))
            ]

        # Reset focused if out of bounds
        if self._focused >= len(self._filtered):
            self._focused = max(0, len(self._filtered) - 1)

    def set_query(self, query: str) -> None:
        """Set the search query.

        Args:
            query: The search query string.
        """
        self._query = query
        self._focused = 0
        self._update_filtered()
        self._update_content()

    def _update_content(self) -> None:
        """Update the widget content."""
        if not self._visible:
            self.update("")
            return

        lines: List[str] = []

        # Search input
        lines.append("[bold]Search:[/bold] " + self._query + "_")
        lines.append("")

        if not self._filtered:
            lines.append("[dim]No results[/dim]")
        else:
            # Results
            for i, item in enumerate(self._filtered[:10]):  # Limit to 10
                is_focused = i == self._focused
                label = item.get("label", "")
                category = item.get("category", "")

                if is_focused:
                    lines.append(f"[bold white on cyan]› {label}[/bold white on cyan]")
                    if category:
                        lines.append(f"  [dim]({category})[/dim]")
                else:
                    lines.append(f"[cyan]▸ {label}[/cyan]")
                    if category:
                        lines.append(f"  [dim]({category})[/dim]")

            # Hint
            if len(self._filtered) > 10:
                lines.append("")
                lines.append(f"[dim]... and {len(self._filtered) - 10} more[/dim]")

        lines.append("")
        lines.append("[dim]↑↓ Navigate | Enter Select | Esc Close[/dim]")

        self.update("\n".join(lines))

    def _handle_up(self) -> None:
        """Move focus up."""
        if self._filtered:
            self._focused = (self._focused - 1) % len(self._filtered)
            self._update_content()

    def _handle_down(self) -> None:
        """Move focus down."""
        if self._filtered:
            self._focused = (self._focused + 1) % len(self._filtered)
            self._update_content()

    def _handle_enter(self) -> None:
        """Select the focused item."""
        if self._filtered and self._on_select:
            item = self._filtered[self._focused]
            self._on_select(item.get("id", ""))
            self.set_visible(False)

    def _handle_escape(self) -> None:
        """Close the switcher."""
        self.set_visible(False)

    def _handle_char(self, char: str) -> None:
        """Handle character input for search.

        Args:
            char: Character to add to query.
        """
        self.set_query(self._query + char)

    def on_key(self, event: Key) -> None:
        """Handle key events."""
        if not self._visible:
            return

        key = event.key

        if key == "up":
            self._handle_up()
        elif key == "down":
            self._handle_down()
        elif key == "enter":
            self._handle_enter()
        elif key == "escape":
            self._handle_escape()
        elif key == "backspace":
            self.set_query(self._query[:-1])
        elif len(key) == 1:
            self._handle_char(key)
