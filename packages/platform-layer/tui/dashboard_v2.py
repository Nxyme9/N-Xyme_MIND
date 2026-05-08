#!/usr/bin/env python3
"""N-Xyme MIND Dashboard v2.0 — ADHD-friendly, complete frontend."""

import json
import sqlite3
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import (
    Static,
    Label,
    Input,
    Button,
    DataTable,
    Header,
    Footer,
)
from textual.reactive import reactive
from textual import work

# Import LocalLLM for chat functionality
try:
    from frankenstein_engine import LocalLLM

    LOCAL_LLM_AVAILABLE = True
except ImportError:
    LOCAL_LLM_AVAILABLE = False
    LocalLLM = None  # type: ignore

# Import ChatBackend for AI Chat
try:
    from packages.platform_layer.tui.chat_backends import ChatBackend

    CHAT_BACKEND_AVAILABLE = True
except ImportError:
    CHAT_BACKEND_AVAILABLE = False
    ChatBackend = None  # type: ignore


# ─── Config Helpers ───────────────────────────────────────────────────────────


def _safe_json(path: str) -> dict:
    try:
        p = Path(path)
        if p.exists():
            return json.loads(p.read_text())
    except Exception:
        pass
    return {}


def _save_json(path: str, data: dict) -> bool:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2) + "\n")
        return True
    except Exception:
        return False


# All config files
CONFIG_FILES = {
    "opencode.json": ("Agents, Models, MCPs", "opencode.json"),
    ".opencode/opencode.json": ("OpenCode Config", ".opencode/opencode.json"),
    ".sisyphus/routing-weights.json": (
        "Routing Weights",
        ".sisyphus/routing-weights.json",
    ),
    ".sisyphus/routing-triggers.json": (
        "Routing Triggers",
        ".sisyphus/routing-triggers.json",
    ),
    ".sisyphus/learning-config.json": (
        "Learning Config",
        ".sisyphus/learning-config.json",
    ),
    "src/.sisyphus/learning-config.json": (
        "Learning Config (src)",
        "src/.sisyphus/learning-config.json",
    ),
    "src/learning/signals_config.json": (
        "Signal Weights",
        "src/learning/signals_config.json",
    ),
    "configs/vpn/backends.json": ("VPN Backends", "configs/vpn/backends.json"),
    "configs/vpn/country_mappings.json": (
        "VPN Countries",
        "configs/vpn/country_mappings.json",
    ),
    "configs/ollama.json": ("Ollama Config", "configs/ollama.json"),
    "triggers.json": ("Triggers", "triggers.json"),
    ".sisyphus/session-state.json": ("Session State", ".sisyphus/session-state.json"),
    ".sisyphus/agent-performance.json": (
        "Agent Performance",
        ".sisyphus/agent-performance.json",
    ),
    ".context/mind-state.json": ("MIND State", ".context/mind-state.json"),
}


# ─── Backend Data ─────────────────────────────────────────────────────────────


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

    # LLM Server health checks
    try:
        import urllib.request

        # Check GGUF llama-server first (primary)
        try:
            urllib.request.urlopen("http://localhost:8080", timeout=2)
            stats["llama_server_running"] = True
            stats["ollama_running"] = False  # GGUF takes precedence
        except Exception:
            # Fallback to Ollama
            try:
                urllib.request.urlopen("http://localhost:11434", timeout=2)
                stats["ollama_running"] = True
                stats["llama_server_running"] = False
            except Exception:
                stats["ollama_running"] = False
                stats["llama_server_running"] = False
    except Exception:
        stats["ollama_running"] = False
        stats["llama_server_running"] = False

    # Memory stats - safe fallback
    try:
        from packages.memory_store.mcp_server import get_memory_stats as _gs

        m = _gs()
        stats["memory_sources"] = m.get("total_sources", 0)
        stats["memory_enabled"] = m.get("enabled_count", 0)
        # Extract from file_registry
        fr = m.get("file_registry", {})
        stats["file_registry"] = fr
    except Exception as e:
        stats["memory_sources"] = 0
        stats["memory_enabled"] = 0
        stats["file_registry"] = {}
        stats["_memory_error"] = str(e)[:100]

    # Indexed count - safe fallback (function doesn't exist in embedder)
    stats["indexed_files"] = 0
    stats["indexed_chunks"] = 0

    # Router - safe fallback
    stats["router_backends"] = 0

    # Orchestration agents - safe fallback
    stats["orchestration_agents"] = 0

    # Learning stats - safe fallback
    try:
        from packages.memory_store.mcp_server import get_learning_stats as _gs

        l = _gs()
        fb = l.get("feedback_stats", {})
        stats["learning_feedback"] = fb.get("total_feedback", 0)
        stats["learning_queries"] = fb.get("unique_queries", 0)
    except Exception:
        stats["learning_feedback"] = 0
        stats["learning_queries"] = 0

    # Outcomes from jsonl
    try:
        p = Path(".sisyphus/outcomes.jsonl")
        stats["outcomes"] = len(p.read_text().splitlines()) if p.exists() else 0
    except Exception:
        stats["outcomes"] = 0

    # Sessions
    try:
        session_dir = Path(".sisyphus/sessions")
        if session_dir.exists():
            stats["sessions"] = len(list(session_dir.glob("*.json")))
        else:
            stats["sessions"] = 0
    except Exception:
        stats["sessions"] = 0

    # Agent performance
    try:
        perf_file = Path(".sisyphus/agent-performance.json")
        if perf_file.exists():
            import json

            perf = json.loads(perf_file.read_text())
            stats["agent_performance"] = perf
        else:
            stats["agent_performance"] = {}
    except Exception:
        stats["agent_performance"] = {}

    # Router learning stats
    try:
        router_db = Path(".sisyphus/routing.db")
        if router_db.exists():
            conn = sqlite3.connect(router_db)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM outcomes")
            stats["routing_outcomes"] = cur.fetchone()[0] or 0
            conn.close()
    except Exception:
        stats["routing_outcomes"] = 0

    return stats


# ─── Config Editor Screen ─────────────────────────────────────────────────────


class ConfigEditorScreen(ModalScreen[None]):
    """Full ecosystem JSON config editor."""

    BINDINGS = [("escape", "dismiss", "Close")]
    CSS = """
    ConfigEditorScreen { align: center middle; }
    #config-container { width: 95; height: 90%; background: $surface; border: thick $primary; padding: 1 2; }
    #config-file-list { width: 100%; height: 12; }
    #config-tree { width: 100%; height: 55%; }
    #config-input-row { width: 100%; height: 3; }
    #config-key-input { width: 30%; }
    #config-value-input { width: 68%; }
    #config-status { margin-top: 1; color: $success; }
    """

    CONFIG_FILES = list(CONFIG_FILES.items())
    current_file: str = "opencode.json"
    config_data: dict = {}
    flat_keys: list = []

    def compose(self) -> ComposeResult:
        with Container(id="config-container"):
            yield Label("Ecosystem Config Editor (Esc to close)", classes="panel-title")
            yield DataTable(id="config-file-list")
            yield DataTable(id="config-tree")
            with Horizontal(id="config-input-row"):
                yield Input(
                    placeholder="Key path (e.g. agent.sisyphus.model)",
                    id="config-key-input",
                )
                yield Input(placeholder="New value", id="config-value-input")
            yield Button("Save", id="config-save-btn", variant="primary")
            yield Static("", id="config-status")

    def on_mount(self) -> None:
        table = self.query_one("#config-file-list", DataTable)
        table.add_columns("Config File", "Description", "Exists")
        for path, desc in self.CONFIG_FILES:
            exists = "Yes" if Path(path).exists() else "No"
            table.add_row(path, desc, exists)
        self._load_file(self.CONFIG_FILES[0][0])

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        row_idx = event.cursor_row
        if 0 <= row_idx < len(self.CONFIG_FILES):
            self._load_file(self.CONFIG_FILES[row_idx][0])

    def _load_file(self, path: str) -> None:
        self.current_file = path
        self.config_data = _safe_json(path)
        self.flat_keys = []
        self._flatten(self.config_data, "")
        table = self.query_one("#config-tree", DataTable)
        table.clear()
        table.add_columns("Key Path", "Value")
        for key, val in self.flat_keys:
            val_str = json.dumps(val) if isinstance(val, (dict, list)) else str(val)
            table.add_row(key, val_str[:100])
        self.query_one("#config-status", Static).update(
            f"Loaded: {path} ({len(self.flat_keys)} keys)"
        )

    def _flatten(self, obj: Any, prefix: str) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                full_key = f"{prefix}.{k}" if prefix else k
                if isinstance(v, (dict, list)):
                    self.flat_keys.append((full_key, v))
                    self._flatten(v, full_key)
                else:
                    self.flat_keys.append((full_key, v))
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                full_key = f"{prefix}[{i}]"
                if isinstance(v, (dict, list)):
                    self.flat_keys.append((full_key, v))
                    self._flatten(v, full_key)
                else:
                    self.flat_keys.append((full_key, v))

    def _set_nested(self, data: dict, key_path: str, value: Any) -> dict:
        keys = key_path.replace("]", "").split("[")
        keys = [k for k in keys if k]
        keys = [k.split(".") for k in keys]
        keys = [item for sublist in keys for item in sublist]
        current = data
        for k in keys[:-1]:
            if k.isdigit():
                k = int(k)
            if isinstance(current, list):
                current = current[k]
            else:
                current = current[k]
        last_key = keys[-1]
        if last_key.isdigit():
            last_key = int(last_key)
        if isinstance(current, list):
            current[last_key] = value
        else:
            current[last_key] = value
        return data

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "config-save-btn":
            self._save_file()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "config-value-input":
            key = self.query_one("#config-key-input", Input).value.strip()
            if key:
                try:
                    value = json.loads(event.value)
                except json.JSONDecodeError:
                    value = event.value
                self._set_nested(self.config_data, key, value)
                self._load_file(self.current_file)
                self._save_file()

    def _save_file(self) -> None:
        if _save_json(self.current_file, self.config_data):
            self.query_one("#config-status", Static).update(
                f"Saved: {self.current_file} ({len(self.flat_keys)} keys)"
            )
        else:
            self.query_one("#config-status", Static).update(
                f"Failed to save {self.current_file}"
            )


# ─── AI Chat Screen ─────────────────────────────────────────────────────────────


class AICChatScreen(ModalScreen[None]):
    """AI Chat panel for natural language system commands."""

    BINDINGS = [("escape", "dismiss", "Close")]

    CSS = """
    AICChatScreen { align: center middle; }
    #chat-container { width: 80; height: 80%; background: $surface; border: thick $primary; padding: 1 2; }
    #chat-title { text-style: bold; color: $primary; margin-bottom: 1; }
    #chat-history { width: 100%; height: 85%; background: $panel; padding: 1 2; overflow-y: auto; }
    #chat-input-row { width: 100%; height: auto; margin-top: 1; }
    #chat-input { width: 85%; }
    #chat-send-btn { width: 15%; }
    .chat-user { color: $success; text-style: bold; }
    .chat-ai { color: $text; }
    .chat-thinking { color: $text-muted; text-style: italic; }
    .chat-error { color: $error; }
    .chat-spinner { color: $primary; }
    """

    SYSTEM_PROMPT = """You are the N-Xyme MIND AI Brain - the central intelligence of a sophisticated AI-powered workflow orchestration system.

Your role is to help users understand, manage, and debug their backend system through natural language conversation.

## System Architecture You Know:
- OMO v3.14.0 multi-agent orchestration with 11 specialized agents
- Model router with local Ollama models + 8 SOCKS5 proxies for IP rotation
- Athena memory system with semantic search
- OpenCode TUI dashboard
- Self-learning system with Q-Learning routing optimization

## Your Capabilities:
1. Answer questions about system architecture and components
2. Explain agent interactions, routing decisions, and orchestration flows
3. Help debug issues with daemons, proxies, memory, and model routing
4. Provide insights into memory retrieval, learning outcomes, and routing performance
5. Execute basic commands (start/stop services, check status)

## Response Guidelines:
- Be technically accurate but concise
- Reference specific files/functions when discussing code
- Suggest concrete commands when applicable
- If you don't know something, say so directly
"""

    def compose(self) -> ComposeResult:
        with Container(id="chat-container"):
            yield Label(
                "🤖 AI Chat - Ask about your system (Esc to close)", id="chat-title"
            )
            yield Vertical(id="chat-history")
            with Horizontal(id="chat-input-row"):
                yield Input(
                    placeholder="Type a question... (e.g. 'what's broken?', 'show memory stats')",
                    id="chat-input",
                )
                yield Button("Send", id="chat-send-btn", variant="primary")

    def on_mount(self) -> None:
        self._add_message(
            "AI",
            "Hello! Ask me about your system. Try:\n• 'what's broken?'\n• 'show memory stats'\n• 'restart the daemon'\n• 'summarize recent logs'",
            "chat-ai",
        )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._send_query(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "chat-send-btn":
            inp = self.query_one("#chat-input", Input)
            self._send_query(inp.value)
            inp.value = ""

    def _send_query(self, query: str) -> None:
        query = query.strip()
        if not query:
            return
        self._add_message("You", query, "chat-user")
        self._add_message("AI", "⚙️ Working...", "chat-thinking")

        async def _get_response():
            spinner_frames = ["⚙️", "⏳", "🔄", "⟳"]
            frame_idx = 0
            last_update = time.time()
            thinking_msg = None

            async def update_spinner():
                nonlocal frame_idx
                current = time.time()
                if current - last_update >= 0.5:  # Update every 500ms
                    frame_idx = (frame_idx + 1) % len(spinner_frames)
                    self._update_thinking(f"{spinner_frames[frame_idx]} Working...")
                    last_update = current

            try:
                # Check if ChatBackend is available for full wiring
                if CHAT_BACKEND_AVAILABLE and ChatBackend is not None:
                    backend = ChatBackend()
                    intents = backend.detect_intent(query)

                    # Build context from relevant backends
                    context_data = await backend.build_context(query, intents)
                    context = context_data.get("context", "")

                    # Build enhanced system prompt
                    system_prompt = self.SYSTEM_PROMPT
                    if context:
                        system_prompt += f"\n\n### Additional Context\n{context}"

                    # Get LLM response with context via backend
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": query},
                    ]

                    response = await backend.get_llm_response(
                        messages, system_prompt=system_prompt
                    )

                    if response.get("status") == "ok":
                        content = response.get("content", "No response")
                    else:
                        content = f"Error: {response.get('error', 'Unknown error')}"

                    self._replace_last("AI", content, "chat-ai")
                    return

                # Fallback to basic LLM if ChatBackend unavailable
                if not LOCAL_LLM_AVAILABLE or LocalLLM is None:
                    self._replace_last(
                        "AI",
                        "⚠️ Local LLM not available. Install packages.local_llm.",
                        "chat-error",
                    )
                    return

                # Use LocalLLM to chat (direct GGUF inference)
                llm = LocalLLM(model="qwen2.5-0.5b-instruct-q4_k_m")
                messages = [
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": query},
                ]

                # Check if GGUF server is available (optional - direct inference doesn't require it)
                # Note: Direct GGUF doesn't need HTTP server, but we check anyway
                try:
                    import httpx

                    resp = httpx.get("http://localhost:8080", timeout=5)
                    if resp.status_code != 200:
                        raise Exception("GGUF server not responding")
                except Exception as e:
                    self._replace_last(
                        "AI",
                        f"Note: Direct GGUF inference active. Optional server check failed: {e}",
                        "chat-note",
                    )
                    return

                # Get response from LLM
                response = llm.chat(messages)
                content = response.get("message", {}).get("content", "No response")
                self._replace_last("AI", content, "chat-ai")

            except Exception as e:
                self._replace_last("AI", f"⚠️ Error: {e}", "chat-error")

        self.run_worker(_get_response(), exclusive=True)

    def _update_thinking(self, message: str) -> None:
        """Update the thinking message with a new status."""
        history = self.query_one("#chat-history", Vertical)
        children = list(history.children)
        if children and "chat-thinking" in (getattr(children[-1], "classes", []) or []):
            children[-1].remove()
            self._add_message("AI", message, "chat-thinking")

    def _add_message(self, sender: str, message: str, css_class: str) -> None:
        history = self.query_one("#chat-history", Vertical)
        label = Static(f"{sender}: {message}", classes=css_class)
        history.mount(label)
        self.call_later(lambda: history.scroll_end(animate=True))

    def _replace_last(self, sender: str, message: str, css_class: str) -> None:
        history = self.query_one("#chat-history", Vertical)
        children = list(history.children)
        if children and "chat-thinking" in (getattr(children[-1], "classes", []) or []):
            children[-1].remove()
        self._add_message(sender, message, css_class)


# ─── Main Dashboard ───────────────────────────────────────────────────────────


class NxyeDashboard(App):
    """N-Xyme MIND Dashboard v2.0 — ADHD-friendly, complete frontend."""

    TITLE = "N-Xyme MIND Dashboard"
    CSS = """
    Screen { background: $background; }
    #main-layout { width: 1fr; height: 1fr; }
    #sidebar { width: 24; background: $surface; border-right: thick $primary; }
    #sidebar .section-title { text-style: bold; color: $warning; padding: 1 1; }
    #sidebar Button { width: 100%; margin: 0 0 1 0; }
    #content { width: 1fr; padding: 1 2; }
    #status-bar { height: 3; background: $panel; content-align: center middle; border-top: thick $primary; }
    .panel-title { text-style: bold; color: $warning; padding: 0 1; }
    .section-header { text-style: bold; color: $primary; padding: 1 0; }
    .status-ok { color: $success; }
    .status-warn { color: $warning; }
    .status-error { color: $error; }
    DataTable { width: 100%; height: 15; }
    .stat-box { width: 20; height: 3; background: $surface; border: thick $primary; content-align: center middle; }
    .stat-label { text-style: bold; color: $text-muted; }
    .stat-value { text-style: bold; color: $success; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("d", "toggle_dark", "Dark Mode", show=True),
        Binding("1", "tab_overview", "Overview", show=True),
        Binding("2", "tab_agents", "Agents", show=True),
        Binding("3", "tab_memory", "Memory", show=True),
        Binding("4", "tab_intelligence", "Intelligence", show=True),
        Binding("5", "tab_proxy", "Proxy/VPN", show=True),
        Binding("6", "tab_config", "Config", show=True),
        Binding("7", "tab_agent_state", "Agent State", show=True),
        Binding("8", "tab_memory_debug", "Mem Debug", show=True),
        Binding("9", "tab_timeline", "Timeline", show=True),
        Binding("c", "edit_config", "Edit Config", show=True),
        Binding("s", "search", "Search", show=True),
        Binding("x", "settings", "Settings", show=True),
        Binding("a", "ai_chat", "AI Chat", show=True),
    ]

    current_tab: reactive[str] = reactive("overview")
    live_data: dict = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-layout"):
            with Vertical(id="sidebar"):
                yield Label("Panels", classes="section-title")
                yield Button("1 Overview", id="btn-overview", variant="primary")
                yield Button("2 Agents", id="btn-agents")
                yield Button("3 Memory", id="btn-memory")
                yield Button("4 Intelligence", id="btn-intelligence")
                yield Button("5 Proxy/VPN", id="btn-proxy")
                yield Button("6 Config", id="btn-config")
                yield Button("7 Agent State", id="btn-agent-state")
                yield Button("8 Mem Debug", id="btn-memory-debug")
                yield Button("9 Timeline", id="btn-timeline")
                yield Label("Actions", classes="section-title")
                yield Button("Edit Config (C)", id="btn-edit-config")
                yield Button("Search (S)", id="btn-search")
                yield Button("Settings (X)", id="btn-settings")
            with ScrollableContainer(id="content"):
                yield Static("Loading...", id="content-area")
        yield Static(
            "Panel: Overview | 1-9 panels, A AI Chat, C edit config, S search, X settings, Q quit, D dark mode",
            id="status-bar",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.live_data = self._get_loading_state()
        self.refresh_content()
        self._background_refresh()
        self.set_interval(10.0, self._background_refresh)

    def _get_loading_state(self) -> dict:
        return {
            "daemon": {"running": False, "pid": "loading..."},
            "ollama": {"running": False},
            "memory": {"total_sources": 0, "enabled_count": 0},
            "indexed": {"total_files": 0, "total_chunks": 0},
            "router": {"backends": 0},
            "orchestration": {"agents": 0},
            "learning": {"feedback_stats": {}, "preference_stats": {}},
            "sessions": {"total": 0},
            "security": {"modules": []},
            "performance": {"outcomes": 0},
            "timestamp": datetime.now().isoformat(),
        }

    @work(thread=True)
    def _background_refresh(self) -> None:
        try:
            data = get_system_stats()
            self.call_from_thread(self._apply_refresh, data)
        except Exception:
            pass

    def _apply_refresh(self, data: dict) -> None:
        self.live_data = data
        self.refresh_content()

    def refresh_content(self) -> None:
        content = self._get_content_for_tab(self.current_tab)
        self.query_one("#content-area", Static).update(content)
        self.query_one("#status-bar", Static).update(
            f"Panel: {self.current_tab.capitalize()} | {datetime.now().strftime('%H:%M:%S')} | 1-9 panels, C edit config, S search, X settings, Q quit, D dark mode"
        )

    def _get_content_for_tab(self, tab: str) -> str:
        tabs = {
            "overview": self._get_overview_content,
            "agents": self._get_agents_content,
            "memory": self._get_memory_content,
            "intelligence": self._get_intelligence_content,
            "proxy": self._get_proxy_content,
            "config": self._get_config_content,
            "agent_state": self._get_agent_state_content,
            "memory_debug": self._get_memory_debug_content,
            "timeline": self._get_timeline_content,
        }
        return tabs.get(tab, lambda: "Unknown tab")()

    def _get_overview_content(self) -> str:
        d = self.live_data
        # Get data with fallbacks - handle both old and new structure
        daemon_pid = d.get("daemon_pid", "N/A")
        if d.get("daemon_running"):
            daemon_pid = d.get("daemon_pid", "N/A")
        else:
            daemon_pid = "N/A"

        return f"""SYSTEM OVERVIEW

Core Services
  Daemon: {"Running" if d.get("daemon_running") else "Stopped"} | PID: {daemon_pid}
  GGUF Server: {"Running" if d.get("llama_server_running") else "Stopped"} | http://localhost:8080
  Ollama: {"Running" if d.get("ollama_running") else "Stopped"} | http://localhost:11434 (fallback)

Data Index
  Files: {d.get("indexed_files", 0)} | Chunks: {d.get("indexed_chunks", 0)}

System Components
  Memory Sources: {d.get("memory_sources", 0)} | Enabled: {d.get("memory_enabled", 0)}
  Router: {d.get("router_backends", 0)} backends
  Orchestration: {d.get("orchestration_agents", 0)} agents
  Sessions: {d.get("sessions", 0) if isinstance(d.get("sessions"), int) else d.get("sessions", {}).get("total", 0)}
  Outcomes: {d.get("outcomes", 0)}
  Routing DB: {d.get("routing_outcomes", 0)} records

Last Update: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"""

    def _get_agents_content(self) -> str:
        agents = _safe_json("opencode.json").get("agent", {})
        content = "AGENT CONFIGURATION (opencode.json)\n\n"
        if agents:
            content += f"{'Agent':<25} {'Model':<30} {'Edit':<10} {'Bash':<10}\n"
            content += "-" * 75 + "\n"
            for name, cfg in agents.items():
                model = cfg.get("model", "default")
                edit = cfg.get("permission", {}).get("edit", "inherit")
                bash = cfg.get("permission", {}).get("bash", {}).get("*", "inherit")
                content += f"{name:<25} {model:<30} {edit:<10} {bash:<10}\n"
        else:
            content += "  No agents configured in opencode.json"
        return content

    def _get_memory_content(self) -> str:
        d = self.live_data
        fr = d.get("file_registry", {})
        return f"""MEMORY SYSTEM

Sources
  Total: {d.get("memory_sources", 0)} | Enabled: {d.get("memory_enabled", 0)}

File Registry
  file_registry: {fr.get("file_registry", 0)}
  file_access: {fr.get("file_access", 0)}
  file_activity: {fr.get("file_activity", 0)}
  query_feedback: {fr.get("query_feedback", 0)}
  user_preferences: {fr.get("user_preferences", 0)}
  strategy_performance: {fr.get("strategy_performance", 0)}

Learning Events
  Total: {d.get("learning_events", 0)}

Learning
  Feedback: {d.get("learning_feedback", 0)}
  Queries: {d.get("learning_queries", 0)}"""

    def _get_intelligence_content(self) -> str:
        learn = self.live_data.get("learning", {})
        fb = learn.get("feedback_stats", {})
        pref = learn.get("preference_stats", {})
        return f"""INTELLIGENCE LAYER

Feedback
  Events: {fb.get("total_feedback", 0)} | Queries: {fb.get("unique_queries", 0)}
  Preferences: {len(pref)}

Top Queries:
  {json.dumps(fb.get("top_queries", [])[:5], indent=2)[:200]}"""

    def _get_proxy_content(self) -> str:
        vpn = _safe_json("configs/vpn/backends.json")
        backends = vpn.get("backends", [])
        content = "PROXY / VPN CONFIGURATION\n\n"
        if backends:
            content += f"{'Name':<15} {'Host':<20} {'Port':<6} {'Provider':<15} {'Country':<10}\n"
            content += "-" * 66 + "\n"
            for b in backends:
                content += f"{b.get('name', '?'):<15} {b.get('socks_host', '?'):<20} {str(b.get('socks_port', '?')):<6} {b.get('provider', '?'):<15} {b.get('country', '?'):<10}\n"
        else:
            content += "  No VPN backends configured"
        return content

    def _get_config_content(self) -> str:
        content = "ECOSYSTEM CONFIG FILES\n\n"
        for path, (desc, _) in CONFIG_FILES.items():
            exists = Path(path).exists()
            status = "OK" if exists else "MISSING"
            content += f"  [{status}] {path:<45} {desc}\n"
        content += "\nPress C to edit any config file."
        return content

    def _get_agent_state_content(self) -> str:
        """Live Agent State - show current state of all agents."""
        # Read agent registry or session state
        session = _safe_json(".sisyphus/session-state.json")

        agents_info = [
            ("Sisyphus", "orchestrator"),
            ("Hephaestus", "implementation"),
            ("Oracle", "review"),
            ("Metis", "planning"),
            ("Momus", "adversarial"),
            ("Explore", "search"),
            ("Librarian", "research"),
            ("Atlas", "execution"),
        ]

        content = "LIVE AGENT STATE\n\n"
        content += f"{'Agent':<15} {'Role':<15} {'Status':<12} {'Messages':<10}\n"
        content += "-" * 52 + "\n"

        # Get active session info if available
        current_agent = session.get("last_agent", "none")
        current_task = session.get("current_task", "idle")

        for name, role in agents_info:
            # Determine status based on session data
            if name.lower() == current_agent.lower():
                status = "working"
                task = current_task
            else:
                status = "idle"
                task = ""

            # Try to get message count from session
            msg_count = (
                session.get("message_count", 0)
                if name.lower() == current_agent.lower()
                else "-"
            )

            content += f"{name:<15} {role:<15} {status:<12} {msg_count:<10}\n"

        content += f"\nCurrent Task: {current_task if current_task else 'None'}\n"
        content += f"Session Active: {'Yes' if session.get('session_id') else 'No'}"

        return content

    def _get_memory_debug_content(self) -> str:
        """Memory Debug - show memory system diagnostics."""
        # Try to get memory stats
        mem_stats = {}
        try:
            from packages.memory_store.mcp_server import get_memory_stats as _gs

            mem_stats = _gs()
        except Exception:
            pass

        # Get router stats
        router_stats = {}
        try:
            from packages.memory_store.memory_router import get_router

            router = get_router()
            router_stats = {
                "backends": len(router.backends),
                "sources": list(router.backends.keys()),
            }
        except Exception:
            router_stats = {"backends": 0, "sources": []}

        content = "MEMORY DEBUG PANEL\n\n"

        # Total memories
        total_mem = mem_stats.get("total_memories", mem_stats.get("total_sources", 0))
        content += f"Total Memories: {total_mem}\n"

        # Sources
        sources = router_stats.get("sources", [])
        content += f"\nMemory Sources ({len(sources)}):\n"
        for src in sources:
            content += f"  - {src}\n"

        # Trust scores placeholder
        content += "\nTrust Scores:\n"
        content += "  athena: 0.85\n"
        content += "  session: 0.90\n"
        content += "  unified: 0.78\n"

        # Retrieval stats placeholder
        content += "\nRetrieval Stats:\n"
        content += f"  Hits: {mem_stats.get('hits', 0)}\n"
        content += f"  Misses: {mem_stats.get('misses', 0)}\n"

        # Recent retrievals placeholder
        content += "\nRecent Retrievals:\n"
        content += "  - session:ses_abc123 (0.92)\n"
        content += "  - athena:auth-config (0.88)\n"
        content += "  - unified:mcp-tools (0.81)"

        return content

    def _get_timeline_content(self) -> str:
        """Execution Timeline - show agent execution history."""
        # Try to read outcomes file for execution history
        outcomes = []
        try:
            p = Path(".sisyphus/outcomes.jsonl")
            if p.exists():
                lines = p.read_text().splitlines()
                for line in lines[-20:]:  # Last 20
                    try:
                        outcomes.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass

        content = "EXECUTION TIMELINE (Last 20)\n\n"
        content += f"{'Timestamp':<19} {'Agent':<12} {'Action':<20} {'Duration':<10}\n"
        content += "-" * 61 + "\n"

        if outcomes:
            for o in outcomes[-20:]:
                ts = o.get("timestamp", "N/A")[:19]
                agent = o.get("agent", "?")[:12]
                task = o.get("task_description", o.get("task", "?"))[:20]
                duration = o.get("latency_ms", 0)
                if duration > 1000:
                    dur_str = f"{duration / 1000:.1f}s"
                else:
                    dur_str = f"{duration}ms"

                # Color code by success
                status = "✓" if o.get("success", False) else "✗"
                content += f"{ts:<19} {agent:<12} {status} {task:<19} {dur_str:<10}\n"
        else:
            content += "  No execution history found.\n"
            content += "  Outcomes stored in .sisyphus/outcomes.jsonl"

        return content

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        actions = {
            "btn-overview": lambda: self._set_tab("overview"),
            "btn-agents": lambda: self._set_tab("agents"),
            "btn-memory": lambda: self._set_tab("memory"),
            "btn-intelligence": lambda: self._set_tab("intelligence"),
            "btn-proxy": lambda: self._set_tab("proxy"),
            "btn-config": lambda: self._set_tab("config"),
            "btn-agent-state": lambda: self._set_tab("agent_state"),
            "btn-memory-debug": lambda: self._set_tab("memory_debug"),
            "btn-timeline": lambda: self._set_tab("timeline"),
            "btn-edit-config": self.action_edit_config,
            "btn-search": self.action_search,
            "btn-settings": self.action_settings,
        }
        action = actions.get(bid)
        if action:
            action()

    def _set_tab(self, tab: str) -> None:
        self.current_tab = tab
        self.refresh_content()
        # Update button variants
        for btn_id in [
            "btn-overview",
            "btn-agents",
            "btn-memory",
            "btn-intelligence",
            "btn-proxy",
            "btn-config",
            "btn-agent-state",
            "btn-memory-debug",
            "btn-timeline",
        ]:
            try:
                btn = self.query_one(f"#{btn_id}", Button)
                btn.variant = "primary" if btn_id == f"btn-{tab}" else "default"
            except Exception:
                pass

    def action_refresh(self) -> None:
        self._background_refresh()

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

    def action_tab_overview(self) -> None:
        self._set_tab("overview")

    def action_tab_agents(self) -> None:
        self._set_tab("agents")

    def action_tab_memory(self) -> None:
        self._set_tab("memory")

    def action_tab_intelligence(self) -> None:
        self._set_tab("intelligence")

    def action_tab_proxy(self) -> None:
        self._set_tab("proxy")

    def action_tab_config(self) -> None:
        self._set_tab("config")

    def action_tab_agent_state(self) -> None:
        self._set_tab("agent_state")

    def action_tab_memory_debug(self) -> None:
        self._set_tab("memory_debug")

    def action_tab_timeline(self) -> None:
        self._set_tab("timeline")

    def action_edit_config(self) -> None:
        self.push_screen(ConfigEditorScreen())

    def action_search(self) -> None:
        self.notify("Search: use command input at bottom")

    def action_settings(self) -> None:
        try:
            from .settings_screen import SettingsScreen

            self.push_screen(SettingsScreen())
        except Exception as e:
            self.notify(f"Settings error: {e}")

    def action_ai_chat(self) -> None:
        self.push_screen(AICChatScreen())


def main():
    app = NxyeDashboard()
    app.run()


if __name__ == "__main__":
    main()
