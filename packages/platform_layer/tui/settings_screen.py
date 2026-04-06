#!/usr/bin/env python3
"""Unified System Settings — 9 panels, lazy-loaded, all configs editable."""

import json
import subprocess
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import (
    Static,
    Label,
    Input,
    Button,
    DataTable,
    Switch,
    Select,
)
from textual.reactive import reactive


# ─── Config Helpers ───────────────────────────────────────────────────────────


def get_learning_config():
    try:
        from packages.memory_core.learning_config import get_config as _gc

        return _gc()
    except Exception:
        return {}


def save_learning_config(updates: dict) -> bool:
    try:
        from packages.memory_core.learning_config import get_config, save_config

        config = get_config()
        config.update(updates)
        save_config(config)
        return True
    except Exception:
        return False


def reset_learning_config() -> bool:
    try:
        from packages.memory_core.learning_config import reset_config

        reset_config()
        for p in [
            Path(".sisyphus/learning-config.json"),
            Path("src/.sisyphus/learning-config.json"),
        ]:
            if p.exists():
                p.unlink()
        import src.memory.learning_config as lc

        lc._config_cache = None
        return True
    except Exception:
        return False


def get_drive_status():
    try:
        from packages.memory_core.config import health_check_drives, list_drives

        drives = list_drives()
        health = health_check_drives()
        return {
            "drives": [
                {
                    "name": d.name,
                    "path": str(d.path),
                    "exists": d.exists,
                    "healthy": health.get(d.name, {}).get("healthy", False),
                }
                for d in drives
            ]
        }
    except Exception:
        return {"drives": []}


def get_agent_config():
    try:
        p = Path("opencode.json")
        if p.exists():
            with open(p) as f:
                data = json.load(f)
            agents = data.get("agent", {})
            return {
                "agents": [
                    {
                        "name": n,
                        "model": c.get("model", "default"),
                        "edit": c.get("permission", {}).get("edit", "inherit"),
                        "bash": c.get("permission", {})
                        .get("bash", {})
                        .get("*", "inherit"),
                    }
                    for n, c in agents.items()
                ]
            }
    except Exception:
        pass
    return {"agents": []}


def get_mcp_config():
    try:
        p = Path("opencode.json")
        if p.exists():
            with open(p) as f:
                data = json.load(f)
            mcps = data.get("mcp", {})
            return {
                "mcps": [
                    {
                        "name": n,
                        "type": c.get("type", "unknown"),
                        "command": " ".join(c.get("command", [])[:3]),
                    }
                    for n, c in mcps.items()
                ]
            }
    except Exception:
        pass
    return {"mcps": []}


def get_vpn_backends():
    try:
        p = Path("configs/vpn/backends.json")
        if p.exists():
            with open(p) as f:
                return json.load(f)
    except Exception:
        pass
    return {"backends": []}


def save_vpn_backends(data: dict) -> bool:
    try:
        p = Path("configs/vpn/backends.json")
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


def get_signals_config():
    try:
        p = Path("src/learning/signals_config.json")
        if p.exists():
            with open(p) as f:
                return json.load(f)
    except Exception:
        pass
    return {"categories": {}}


def save_signals_config(data: dict) -> bool:
    try:
        p = Path("src/learning/signals_config.json")
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


def get_routing_weights():
    try:
        p = Path(".sisyphus/routing-weights.json")
        if p.exists():
            with open(p) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_routing_weights(data: dict) -> bool:
    try:
        p = Path(".sisyphus/routing-weights.json")
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


def get_ollama_config():
    try:
        p = Path("configs/ollama.json")
        if p.exists():
            with open(p) as f:
                return json.load(f)
    except Exception:
        pass
    return {"LLM": {"concurrency": 1}}


def save_ollama_config(data: dict) -> bool:
    try:
        p = Path("configs/ollama.json")
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


def get_system_stats():
    stats = {}
    try:
        r = subprocess.run(
            ["pgrep", "-f", "src.memory.daemon"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        stats["daemon_running"] = r.returncode == 0 and r.stdout.strip()
        stats["daemon_pid"] = (
            r.stdout.strip().split("\n")[0] if stats["daemon_running"] else "N/A"
        )
    except Exception:
        stats["daemon_running"] = False
        stats["daemon_pid"] = "N/A"
    try:
        import urllib.request

        urllib.request.urlopen("http://localhost:11434", timeout=2)
        stats["ollama_running"] = True
    except Exception:
        stats["ollama_running"] = False
    try:
        from packages.memory_core.mcp_server import get_memory_stats as _gs

        m = _gs()
        stats["memory_sources"] = m.get("total_sources", 0)
        stats["memory_enabled"] = m.get("enabled_count", 0)
    except Exception:
        stats["memory_sources"] = 0
        stats["memory_enabled"] = 0
    try:
        from packages.memory_core.indexing.embedder import get_indexed_count as _gc

        i = _gc()
        stats["indexed_files"] = i.get("total_files", 0)
        stats["indexed_chunks"] = i.get("total_chunks", 0)
    except Exception:
        stats["indexed_files"] = 0
        stats["indexed_chunks"] = 0
    try:
        from packages.memory_core.memory_router import get_router

        stats["router_backends"] = len(get_router().backends)
    except Exception:
        stats["router_backends"] = 0
    try:
        from packages.orchestration.agents.registry import get_agent_registry

        stats["orchestration_agents"] = len(get_agent_registry().get_all_agents())
    except Exception:
        stats["orchestration_agents"] = 0
    try:
        from packages.memory_core.mcp_server import get_learning_stats as _gs

        l = _gs()
        fb = l.get("feedback_stats", {})
        stats["learning_feedback"] = fb.get("total_feedback", 0)
        stats["learning_queries"] = fb.get("unique_queries", 0)
    except Exception:
        stats["learning_feedback"] = 0
        stats["learning_queries"] = 0
    try:
        p = Path(".sisyphus/outcomes.jsonl")
        stats["outcomes"] = len(p.read_text().splitlines()) if p.exists() else 0
    except Exception:
        stats["outcomes"] = 0
    return stats


# ─── Settings Screen ─────────────────────────────────────────────────────────


class SettingsScreen(ModalScreen[None]):
    """Unified system settings — 9 panels, lazy-loaded, all configs editable."""

    BINDINGS = [("escape", "dismiss", "Close")]
    CSS = """
    SettingsScreen { layout: vertical; }
    #settings-header { height: 3; background: $panel; content-align: center middle; border-bottom: thick $primary; }
    #settings-body { width: 1fr; }
    #settings-sidebar { width: 24; background: $surface; border-right: thick $primary; }
    #settings-sidebar Button { width: 100%; margin: 0 0 1 0; }
    #settings-sidebar .section-title { text-style: bold; color: $warning; padding: 1 1; }
    #settings-content { width: 1fr; padding: 1 2; }
    #settings-footer { height: 3; background: $panel; content-align: center middle; border-top: thick $primary; }
    .panel-title { text-style: bold; color: $warning; padding: 0 1; }
    DataTable { width: 100%; height: 15; }
    .toggle-label { width: 35; text-style: bold; }
    .toggle-desc { width: 100%; color: $text-muted; height: 1; }
    .input-label { width: 35; text-style: bold; }
    .input-widget { width: 20; }
    .section-header { text-style: bold; color: $primary; padding: 1 0; }
    #learning-panel, #agents-panel, #mcps-panel, #vpn-panel, #signals-panel, #routing-panel, #ollama-panel, #stats-panel, #controls-panel {
        width: 100%;
    }
    """

    current_category: reactive[str] = reactive("learning")
    _panels_built: set = reactive(set())

    ALL_CATEGORIES = [
        "learning",
        "agents",
        "mcps",
        "vpn",
        "signals",
        "routing",
        "ollama",
        "stats",
        "controls",
    ]
    ALL_PANELS = [f"{c}-panel" for c in ALL_CATEGORIES]
    ALL_BTN_IDS = [f"btn-{c}" for c in ALL_CATEGORIES]

    def compose(self) -> ComposeResult:
        yield Label("System Settings (Esc to close)", id="settings-header")
        with Horizontal(id="settings-body"):
            with Vertical(id="settings-sidebar"):
                yield Label("Categories", classes="section-title")
                for cat in self.ALL_CATEGORIES:
                    variant = "primary" if cat == "learning" else "default"
                    label = cat.capitalize()
                    if cat == "vpn":
                        label = "VPN"
                    if cat == "mcps":
                        label = "MCPs"
                    if cat == "ollama":
                        label = "Ollama"
                    yield Button(label, id=f"btn-{cat}", variant=variant)
                yield Label("Actions", classes="section-title")
                yield Button("Reset Learning", id="btn-reset-learning")
                yield Button("Refresh All", id="btn-apply")
            with ScrollableContainer(id="settings-content"):
                for cat in self.ALL_CATEGORIES:
                    yield Container(id=f"{cat}-panel")
        yield Static(
            "Toggles auto-save. Inputs: Enter to save. Esc to close.",
            id="settings-footer",
        )

    def on_mount(self) -> None:
        self._build_panel("learning")
        self._update_panel_visibility()

    def _build_panel(self, cat: str) -> None:
        if cat in self._panels_built:
            return
        panel = self.query_one(f"#{cat}-panel", Container)
        builders = {
            "learning": self._build_learning_widgets,
            "agents": self._build_agents_widgets,
            "mcps": self._build_mcps_widgets,
            "vpn": self._build_vpn_widgets,
            "signals": self._build_signals_widgets,
            "routing": self._build_routing_widgets,
            "ollama": self._build_ollama_widgets,
            "stats": self._build_stats_widgets,
            "controls": self._build_controls_widgets,
        }
        fn = builders.get(cat)
        if fn:
            for w in fn():
                panel.mount(w)
            self._panels_built = self._panels_built | {cat}

    def _set_category(self, cat: str) -> None:
        self.current_category = cat
        self._build_panel(cat)
        self._update_panel_visibility()
        for btn_id in self.ALL_BTN_IDS:
            try:
                btn = self.query_one(f"#{btn_id}", Button)
                btn.variant = "primary" if btn_id == f"btn-{cat}" else "default"
            except Exception:
                pass

    def _update_panel_visibility(self) -> None:
        active = f"{self.current_category}-panel"
        for panel_id in self.ALL_PANELS:
            try:
                panel = self.query_one(f"#{panel_id}", Container)
                panel.display = panel_id == active
            except Exception:
                pass
        self.query_one("#settings-footer", Static).update(
            f"Category: {self.current_category.capitalize()} | Toggles auto-save | Inputs: Enter to save | Esc to close"
        )

    # ── Widget builders ──────────────────────────────────────────────────

    def _build_learning_widgets(self):
        config = get_learning_config()
        stats = get_system_stats()
        yield Label(
            f"LEARNING SYSTEM — Feedback: {stats.get('learning_feedback', 0)} | Queries: {stats.get('learning_queries', 0)}",
            classes="panel-title",
        )
        yield Label("Master Switches", classes="section-header")
        for key in [
            "enabled",
            "rerank_enabled",
            "consolidate_enabled",
            "forget_enabled",
            "tempr_enabled",
        ]:
            val = config.get(key, False)
            yield Label(f"  {key}", classes="toggle-label")
            yield Switch(value=val, id=f"sw_{key}")
        yield Label("Feature Flags", classes="section-header")
        for key in [
            "singleton_enabled",
            "health_metrics_enabled",
            "recovery_enabled",
            "thread_safety_enabled",
            "signals_enabled",
            "event_bus_enabled",
            "etgpo_enabled",
            "evoskill_enabled",
        ]:
            val = config.get(key, False)
            yield Label(f"  {key}", classes="toggle-label")
            yield Switch(value=val, id=f"sw_{key}")
        yield Label("Thresholds & Timing", classes="section-header")
        for key in [
            "min_confidence",
            "exploration_rate",
            "consolidation_threshold",
            "learning_cycle_minutes",
            "feedback_ttl_days",
            "mandatory_retention_days",
        ]:
            val = config.get(key, "")
            yield Label(f"  {key}", classes="input-label")
            yield Input(value=str(val), id=f"inp_{key}", classes="input-widget")

    def _build_agents_widgets(self):
        agents = get_agent_config()
        yield Label("AGENT CONFIGURATION (opencode.json)", classes="panel-title")
        table = DataTable()
        table.add_columns("Agent", "Model", "Edit", "Bash")
        for a in agents.get("agents", []):
            table.add_row(a["name"], a["model"], a["edit"], a["bash"])
        yield table
        yield Label(
            "Edit opencode.json to change agent models or permissions.",
            classes="toggle-desc",
        )

    def _build_mcps_widgets(self):
        mcps = get_mcp_config()
        yield Label("MCP SERVER CONFIGURATION (opencode.json)", classes="panel-title")
        table = DataTable()
        table.add_columns("MCP Server", "Type", "Command")
        for m in mcps.get("mcps", []):
            table.add_row(m["name"], m["type"], m["command"])
        yield table
        yield Label(
            "Edit opencode.json to add/remove MCP servers.", classes="toggle-desc"
        )

    def _build_vpn_widgets(self):
        vpn = get_vpn_backends()
        yield Label("VPN BACKEND CONFIGURATION", classes="panel-title")
        table = DataTable()
        table.add_columns("Name", "Host", "Port", "Provider", "Country")
        for b in vpn.get("backends", []):
            table.add_row(
                b.get("name", "?"),
                b.get("socks_host", "?"),
                str(b.get("socks_port", "?")),
                b.get("provider", "?"),
                b.get("country", "?"),
            )
        yield table
        yield Label(
            "Edit configs/vpn/backends.json to add/remove proxies.",
            classes="toggle-desc",
        )

    def _build_signals_widgets(self):
        signals = get_signals_config()
        yield Label(
            "SIGNAL WEIGHTS (implicit feedback learning)", classes="panel-title"
        )
        cats = signals.get("categories", {})
        for cat_name, cat_data in cats.items():
            yield Label(f"  {cat_data.get('name', cat_name)}", classes="section-header")
            weights = cat_data.get("weights", {})
            for sig, weight in weights.items():
                yield Label(f"    {sig}", classes="input-label")
                yield Input(
                    value=str(weight),
                    id=f"inp_sig_{cat_name}_{sig}",
                    classes="input-widget",
                )
        yield Label(
            "Edit src/learning/signals_config.json for full config.",
            classes="toggle-desc",
        )

    def _build_routing_widgets(self):
        routing = get_routing_weights()
        yield Label("ROUTING WEIGHTS", classes="panel-title")
        if routing:
            table = DataTable()
            table.add_columns("Key", "Value")
            for k, v in routing.items():
                table.add_row(str(k), str(v))
            yield table
        else:
            yield Label("  No routing weights configured.", classes="toggle-desc")
        yield Label(
            "Edit .sisyphus/routing-weights.json to adjust.", classes="toggle-desc"
        )

    def _build_ollama_widgets(self):
        ollama = get_ollama_config()
        yield Label("OLLAMA CONFIGURATION", classes="panel-title")
        llm = ollama.get("LLM", {})
        yield Label("  concurrency", classes="input-label")
        yield Input(
            value=str(llm.get("concurrency", 1)),
            id="inp_ollama_concurrency",
            classes="input-widget",
        )
        yield Label("Edit configs/ollama.json for full config.", classes="toggle-desc")

    def _build_stats_widgets(self):
        stats = get_system_stats()
        yield Label("SYSTEM STATISTICS", classes="panel-title")
        table = DataTable()
        table.add_columns("Component", "Status", "Details")
        table.add_row(
            "Daemon",
            "Running" if stats.get("daemon_running") else "Stopped",
            f"PID: {stats.get('daemon_pid', 'N/A')}",
        )
        table.add_row(
            "Ollama",
            "Running" if stats.get("ollama_running") else "Stopped",
            "http://localhost:11434",
        )
        table.add_row(
            "Memory Sources",
            str(stats.get("memory_sources", 0)),
            f"Enabled: {stats.get('memory_enabled', 0)}",
        )
        table.add_row(
            "Indexed Files",
            str(stats.get("indexed_files", 0)),
            f"Chunks: {stats.get('indexed_chunks', 0)}",
        )
        table.add_row("Router Backends", str(stats.get("router_backends", 0)), "")
        table.add_row(
            "Orchestration", f"{stats.get('orchestration_agents', 0)} agents", ""
        )
        table.add_row(
            "Learning Feedback",
            str(stats.get("learning_feedback", 0)),
            f"Queries: {stats.get('learning_queries', 0)}",
        )
        table.add_row(
            "Outcomes", str(stats.get("outcomes", 0)), ".sisyphus/outcomes.jsonl"
        )
        yield table

    def _build_controls_widgets(self):
        stats = get_system_stats()
        yield Label("QUICK CONTROLS", classes="panel-title")
        yield Label("System Status", classes="section-header")
        for label_text, detail in [
            (
                "Daemon Running",
                f"{'Yes' if stats.get('daemon_running') else 'No'} | PID: {stats.get('daemon_pid', 'N/A')}",
            ),
            ("Ollama Running", f"{'Yes' if stats.get('ollama_running') else 'No'}"),
            (
                "Memory Sources",
                f"{stats.get('memory_sources', 0)} total | {stats.get('memory_enabled', 0)} enabled",
            ),
            (
                "Indexed Files",
                f"{stats.get('indexed_files', 0)} files | {stats.get('indexed_chunks', 0)} chunks",
            ),
            ("Router Backends", f"{stats.get('router_backends', 0)} backends"),
            ("Orchestration Agents", f"{stats.get('orchestration_agents', 0)} agents"),
            (
                "Learning Feedback",
                f"{stats.get('learning_feedback', 0)} events | {stats.get('learning_queries', 0)} queries",
            ),
            (
                "Outcomes Recorded",
                f"{stats.get('outcomes', 0)} in .sisyphus/outcomes.jsonl",
            ),
        ]:
            yield Label(f"  {label_text}", classes="toggle-label")
            yield Static(f"  {detail}", classes="toggle-desc")

    # ── Event handlers ───────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if bid in self.ALL_BTN_IDS:
            cat = bid.replace("btn-", "")
            self._set_category(cat)
            return
        if bid == "btn-reset-learning":
            self._reset_learning()
        elif bid == "btn-apply":
            self._apply_changes()

    def on_switch_changed(self, event: Switch.Changed) -> None:
        switch_id = event.switch.id
        if switch_id and switch_id.startswith("sw_"):
            key = switch_id[3:]
            if save_learning_config({key: event.value}):
                icon = "OK" if event.value else "OFF"
                self.query_one("#settings-footer", Static).update(
                    f"{icon} Saved: {key} = {event.value}"
                )
            else:
                self.query_one("#settings-footer", Static).update(
                    f"Failed to save {key}"
                )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        input_id = event.input.id
        if input_id and input_id.startswith("inp_"):
            if input_id.startswith("inp_sig_"):
                # Signal weight: inp_sig_{category}_{signal}
                parts = input_id.split("_")
                if len(parts) >= 5:
                    cat_name = "_".join(parts[3:-1])
                    sig_name = parts[-1]
                    try:
                        signals = get_signals_config()
                        signals["categories"][cat_name]["weights"][sig_name] = float(
                            event.value
                        )
                        if save_signals_config(signals):
                            self.query_one("#settings-footer", Static).update(
                                f"Saved signal weight: {cat_name}/{sig_name} = {event.value}"
                            )
                        else:
                            self.query_one("#settings-footer", Static).update(
                                "Failed to save signal weight"
                            )
                    except Exception as e:
                        self.query_one("#settings-footer", Static).update(f"Error: {e}")
            elif input_id == "inp_ollama_concurrency":
                try:
                    ollama = get_ollama_config()
                    ollama["LLM"]["concurrency"] = int(event.value)
                    if save_ollama_config(ollama):
                        self.query_one("#settings-footer", Static).update(
                            f"Saved: ollama concurrency = {event.value}"
                        )
                    else:
                        self.query_one("#settings-footer", Static).update(
                            "Failed to save ollama config"
                        )
                except Exception as e:
                    self.query_one("#settings-footer", Static).update(f"Error: {e}")
            else:
                key = input_id[4:]
                if save_learning_config({key: event.value}):
                    self.query_one("#settings-footer", Static).update(
                        f"Saved: {key} = {event.value}"
                    )
                else:
                    self.query_one("#settings-footer", Static).update(
                        f"Failed to save {key}"
                    )

    # ── Internal helpers ─────────────────────────────────────────────────

    def _reset_learning(self) -> None:
        if reset_learning_config():
            self.query_one("#settings-footer", Static).update(
                "Learning config reset to defaults"
            )
            panel = self.query_one("#learning-panel", Container)
            panel.remove_children()
            self._panels_built = self._panels_built - {"learning"}
            self._build_panel("learning")
        else:
            self.query_one("#settings-footer", Static).update(
                "Failed to reset learning config"
            )

    def _apply_changes(self) -> None:
        for cat in self.ALL_CATEGORIES:
            panel = self.query_one(f"#{cat}-panel", Container)
            panel.remove_children()
        self._panels_built = set()
        self._build_panel(self.current_category)
        self.query_one("#settings-footer", Static).update(
            "All settings refreshed from config files"
        )

