"""
Proxy Manager Module for N-Xyme MIND Dashboard TUI.

Provides a modal dialog for managing SOCKS5 proxies with status monitoring,
connection testing, and IP rotation capabilities.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import DataTable, Header, Static, Label, Button, Switch


@dataclass
class ProxyInfo:
    """Represents a SOCKS5 proxy configuration."""

    id: int
    host: str
    port: int
    protocol: str = "socks5"
    username: Optional[str] = None
    password: Optional[str] = None
    status: str = "inactive"  # "active", "inactive", "error"
    latency_ms: int = 0
    uptime_seconds: int = 0
    last_error: Optional[str] = None


class ProxyManagerDialog(ModalScreen):
    """
    Textual Modal Screen for managing SOCKS5 proxies.

    Features:
    - DataTable displaying all proxy configurations
    - Status indicators (active/inactive/error)
    - Add/Edit/Remove proxy buttons
    - Test connection button per proxy
    - Global enable/disable toggle
    - IP rotation button
    """

    CSS = """
    ProxyManagerDialog {
        background: $surface;
    }

    #dialog-container {
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
        margin-bottom: 1;
    }

    #controls {
        height: auto;
        padding: 1;
        background: $surface;
    }

    #global_controls {
        height: auto;
        margin-bottom: 1;
        padding: 1;
        background: $panel;
        border: solid $primary;
    }

    #button_row {
        height: auto;
        align: center middle;
    }

    #action_buttons {
        height: auto;
        margin-top: 1;
    }

    DataTable {
        margin: 1;
        border: solid $primary;
    }

    Button {
        margin: 0 1;
    }

    .status-active {
        color: $success;
    }

    .status-inactive {
        color: $text-muted;
    }

    .status-error {
        color: $error;
    }
    """

    # Mock proxy data - 8 proxies on ports 1080-1087
    DEFAULT_PROXIES: list[ProxyInfo] = [
        ProxyInfo(
            id=1,
            host="127.0.0.1",
            port=1080,
            status="active",
            latency_ms=12,
            uptime_seconds=86400,
        ),
        ProxyInfo(
            id=2,
            host="127.0.0.1",
            port=1081,
            status="active",
            latency_ms=15,
            uptime_seconds=86400,
        ),
        ProxyInfo(
            id=3,
            host="127.0.0.1",
            port=1082,
            status="inactive",
            latency_ms=0,
            uptime_seconds=0,
        ),
        ProxyInfo(
            id=4,
            host="127.0.0.1",
            port=1083,
            status="active",
            latency_ms=18,
            uptime_seconds=43200,
        ),
        ProxyInfo(
            id=5,
            host="127.0.0.1",
            port=1084,
            status="error",
            latency_ms=0,
            uptime_seconds=0,
            last_error="Connection refused",
        ),
        ProxyInfo(
            id=6,
            host="127.0.0.1",
            port=1085,
            status="active",
            latency_ms=22,
            uptime_seconds=7200,
        ),
        ProxyInfo(
            id=7,
            host="127.0.0.1",
            port=1086,
            status="inactive",
            latency_ms=0,
            uptime_seconds=0,
        ),
        ProxyInfo(
            id=8,
            host="127.0.0.1",
            port=1087,
            status="active",
            latency_ms=25,
            uptime_seconds=3600,
        ),
    ]

    def __init__(
        self,
        proxies: Optional[list[ProxyInfo]] = None,
        enabled: bool = True,
    ) -> None:
        """
        Initialize the Proxy Manager Dialog.

        Args:
            proxies: List of ProxyInfo instances. Uses default mock data if not provided.
            enabled: Global enable/disable state for proxy rotation.
        """
        super().__init__()
        self._proxies: list[ProxyInfo] = proxies or self.DEFAULT_PROXIES.copy()
        self._enabled = enabled
        self._selected_proxy_id: Optional[int] = None

    def compose(self) -> ComposeResult:
        """Compose the modal dialog widgets."""
        with Container(id="dialog-container"):
            # Title
            yield Static("SOCKS5 Proxy Manager", id="title")

            # Global controls
            with Container(id="global_controls"):
                with Horizontal():
                    yield Label("Proxy Rotation:")
                    yield Switch(id="global_enable", value=self._enabled)
                    yield Button("Rotate IP", variant="primary", id="btn_rotate")
                    yield Button("Refresh All", variant="default", id="btn_refresh_all")

            # Proxy list table
            yield DataTable(id="proxy_table")

            # Action buttons
            with Container(id="action_buttons"):
                with Horizontal(id="button_row"):
                    yield Button("Add Proxy", variant="success", id="btn_add")
                    yield Button("Edit", variant="primary", id="btn_edit")
                    yield Button("Remove", variant="error", id="btn_remove")
                    yield Button("Test Selected", variant="default", id="btn_test")
                    yield Button("Close", variant="default", id="btn_close")

    def on_mount(self) -> None:
        """Initialize the dialog on mount."""
        table = self.query_one("#proxy_table", DataTable)

        # Add columns
        table.add_columns(
            "ID", "Host", "Port", "Protocol", "Status", "Latency", "Uptime"
        )

        # Populate with proxy data
        self._refresh_table()

        # Set up switch callback
        switch = self.query_one("#global_enable", Switch)
        switch.value = self._enabled

    def _refresh_table(self) -> None:
        """Refresh the data table with current proxy data."""
        table = self.query_one("#proxy_table", DataTable)
        table.clear()

        for proxy in self._proxies:
            status_str = proxy.status.upper()
            latency_str = f"{proxy.latency_ms}ms" if proxy.latency_ms > 0 else "-"
            uptime_str = self._format_uptime(proxy.uptime_seconds)

            table.add_row(
                str(proxy.id),
                proxy.host,
                str(proxy.port),
                proxy.protocol.upper(),
                status_str,
                latency_str,
                uptime_str,
            )

    def _format_uptime(self, seconds: int) -> str:
        """Format uptime seconds into human-readable string."""
        if seconds == 0:
            return "-"
        if seconds < 60:
            return f"{seconds}s"
        if seconds < 3600:
            return f"{seconds // 60}m"
        if seconds < 86400:
            return f"{seconds // 3600}h"
        return f"{seconds // 86400}d"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id

        if button_id == "btn_close":
            self.app.pop_screen()
        elif button_id == "btn_add":
            self._add_proxy()
        elif button_id == "btn_edit":
            self._edit_proxy()
        elif button_id == "btn_remove":
            self._remove_proxy()
        elif button_id == "btn_test":
            self._test_proxy()
        elif button_id == "btn_rotate":
            self._rotate_ip()
        elif button_id == "btn_refresh_all":
            self._refresh_all()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle data table row selection."""
        table = self.query_one("#proxy_table", DataTable)
        row = event.row_key
        if row is not None:
            # Get the proxy ID from the first column
            self._selected_proxy_id = int(table.get_row(row)[0])

    def on_switch_changed(self, event: Switch.Changed) -> None:
        """Handle global enable/disable switch."""
        if event.switch.id == "global_enable":
            self._enabled = event.value
            status = "enabled" if self._enabled else "disabled"
            self.notify(f"Proxy rotation {status}", severity="information")

    def _add_proxy(self) -> None:
        """Add a new proxy (mock implementation)."""
        # Generate new ID
        new_id = max((p.id for p in self._proxies), default=0) + 1

        # Create new proxy with mock values
        new_proxy = ProxyInfo(
            id=new_id,
            host="127.0.0.1",
            port=1080 + new_id,
            status="inactive",
        )

        self._proxies.append(new_proxy)
        self._refresh_table()
        self.notify(f"Added new proxy (ID: {new_id})", severity="information")

    def _edit_proxy(self) -> None:
        """Edit selected proxy (mock implementation)."""
        if self._selected_proxy_id is None:
            self.notify("No proxy selected", severity="warning")
            return

        proxy = next(
            (p for p in self._proxies if p.id == self._selected_proxy_id), None
        )
        if proxy:
            # Toggle status as mock edit
            proxy.status = "active" if proxy.status != "active" else "inactive"
            self._refresh_table()
            self.notify(
                f"Proxy {proxy.id} status toggled to {proxy.status}",
                severity="information",
            )
        else:
            self.notify("Proxy not found", severity="error")

    def _remove_proxy(self) -> None:
        """Remove selected proxy."""
        if self._selected_proxy_id is None:
            self.notify("No proxy selected", severity="warning")
            return

        self._proxies = [p for p in self._proxies if p.id != self._selected_proxy_id]
        self._selected_proxy_id = None
        self._refresh_table()
        self.notify("Proxy removed", severity="information")

    def _test_proxy(self) -> None:
        """Test connection to selected proxy (mock implementation)."""
        if self._selected_proxy_id is None:
            self.notify("No proxy selected", severity="warning")
            return

        proxy = next(
            (p for p in self._proxies if p.id == self._selected_proxy_id), None
        )
        if proxy:
            # Mock connection test - randomly succeed/fail based on current status
            if proxy.status == "active":
                proxy.latency_ms = 10 + (proxy.id * 5)
                proxy.uptime_seconds = 3600
                self.notify(
                    f"Proxy {proxy.id} connection OK ({proxy.latency_ms}ms)",
                    severity="information",
                )
            else:
                self.notify(f"Proxy {proxy.id} connection failed", severity="error")
            self._refresh_table()
        else:
            self.notify("Proxy not found", severity="error")

    def _rotate_ip(self) -> None:
        """Rotate to next available proxy (mock implementation)."""
        active_proxies = [p for p in self._proxies if p.status == "active"]

        if not active_proxies:
            self.notify("No active proxies available", severity="error")
            return

        # Find current active proxy
        current_idx = 0
        for i, p in enumerate(active_proxies):
            if p.id == self._selected_proxy_id:
                current_idx = i
                break

        # Move to next proxy (rotate)
        next_idx = (current_idx + 1) % len(active_proxies)
        self._selected_proxy_id = active_proxies[next_idx].id

        self.notify(
            f"Rotated to proxy {self._selected_proxy_id}", severity="information"
        )

    def _refresh_all(self) -> None:
        """Refresh all proxy statuses (mock implementation)."""
        for proxy in self._proxies:
            if proxy.status == "active":
                # Simulate latency fluctuation
                proxy.latency_ms = (
                    10 + (proxy.id * 3) + (hash(str(datetime.now())) % 20)
                )

        self._refresh_table()
        self.notify("All proxies refreshed", severity="information")


# Module-level default proxies for global use
_default_proxies: Optional[list[ProxyInfo]] = None
_proxy_enabled: bool = True


def get_proxy_manager() -> tuple[list[ProxyInfo], bool]:
    """
    Get the default proxy configuration.

    Returns:
        Tuple of (proxies list, enabled state).
    """
    global _default_proxies, _proxy_enabled
    if _default_proxies is None:
        _default_proxies = ProxyManagerDialog.DEFAULT_PROXIES.copy()
    return _default_proxies, _proxy_enabled


def set_proxy_enabled(enabled: bool) -> None:
    """Set the global proxy enabled state."""
    global _proxy_enabled
    _proxy_enabled = enabled
