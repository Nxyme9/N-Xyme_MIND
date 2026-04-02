#!/usr/bin/env python3
"""
N-Xyme Catalyst Hub — System Tray Control Center
Controls: Jarvis, Graphiti, Ollama, Neo4j, Auto-capture, Session Archiver
"""

import sys
import os
import time
import threading
import queue
import json
import socket
import subprocess
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:
    requests = None

try:
    import customtkinter as ctk
except ImportError:
    print("Install: pip install customtkinter")
    sys.exit(1)

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    print("Install: pip install pystray Pillow")
    sys.exit(1)

from typing import Any, Callable, Optional

# Import centralized configuration
try:
    from jarvis.config.graphiti_config import (
        OLLAMA_URL,
        OLLAMA_TAGS_URL,
        NEO4J_URL,
        GRAPHITI_HEALTH_URL,
        GRAPHITI_RPC_URL,
        AUTO_CAPTURE_HEALTH_URL,
        SECURITY_AGENT_HEALTH_URL,
    )
except ImportError:
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_TAGS_URL = os.getenv("OLLAMA_TAGS_URL", f"{OLLAMA_URL}/api/tags")
    NEO4J_URL = os.getenv("NEO4J_URL", "http://localhost:7474")
    GRAPHITI_URL = os.getenv("GRAPHITI_URL", "http://localhost:8001")
    GRAPHITI_HEALTH_URL = os.getenv("GRAPHITI_HEALTH_URL", f"{GRAPHITI_URL}/health")
    GRAPHITI_RPC_URL = os.getenv("GRAPHITI_RPC_URL", f"{GRAPHITI_URL}/json-rpc")
    AUTO_CAPTURE_HEALTH_URL = os.getenv("AUTO_CAPTURE_HEALTH_URL", "http://localhost:5003/health")
    SECURITY_AGENT_HEALTH_URL = os.getenv(
        "SECURITY_AGENT_HEALTH_URL", "http://localhost:5002/health"
    )

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
COLORS = {
    "bg": "#0d1117",
    "bg_card": "#161b22",
    "accent": "#58a6ff",
    "green": "#3fb950",
    "yellow": "#f0883e",
    "red": "#f85149",
    "gray": "#8b949e",
    "text": "#c9d1d9",
    "border": "#30363d",
}

PERSONALITIES = {
    "butler": {
        "name": "Jarvis",
        "greeting": "At your service, sir.",
        "style": "formal",
    },
    "friend": {"name": "Dude", "greeting": "Hey! What's up?", "style": "casual"},
    "therapist": {
        "name": "Doc",
        "greeting": "I'm here. How are you feeling?",
        "style": "empathetic",
    },
    "comedian": {
        "name": "Gags",
        "greeting": "What's the deal with AI assistants?",
        "style": "humorous",
    },
    "coach": {
        "name": "Coach",
        "greeting": "Let's get to work. What's the plan?",
        "style": "motivational",
    },
    "narrator": {"name": "Observer", "greeting": "Observing.", "style": "neutral"},
}

SERVICES = {
    "Neo4j": {"port": 7687, "health_url": NEO4J_URL, "type": "database"},
    "Graphiti": {
        "port": 8001,
        "health_url": GRAPHITI_HEALTH_URL,
        "type": "memory",
    },
    "Ollama": {
        "port": 11434,
        "health_url": OLLAMA_TAGS_URL,
        "type": "llm",
    },
    "Auto-capture": {
        "port": 5003,
        "health_url": AUTO_CAPTURE_HEALTH_URL,
        "type": "capture",
    },
    "Security Agent": {
        "port": 5002,
        "health_url": SECURITY_AGENT_HEALTH_URL,
        "type": "security",
    },
}

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "configs"
JARVIS_CONFIG_DIR = CONFIG_DIR / "jarvis"
HUB_SETTINGS_FILE = JARVIS_CONFIG_DIR / "hub-settings.json"
PERSONALITIES_FILE = JARVIS_CONFIG_DIR / "personalities.json"


# ─── SHARED STATE ─────────────────────────────────────────────────────────────
class HubState:
    """Thread-safe shared state for the hub."""

    def __init__(self):
        self._lock = threading.Lock()
        # Jarvis state
        self.jarvis_mode = "friend"
        self.jarvis_personality = "butler"
        self.voice_input = False
        self.voice_output = False
        self.jarvis_active = False
        # Service states
        self.service_status = {name: "unknown" for name in SERVICES}
        self.service_pids = {name: None for name in SERVICES}
        # Health
        self.overall_health = "unknown"
        # Memory stats
        self.episode_count = 0
        self.entity_count = 0
        # Auto-capture
        self.screen_capture = False
        self.clipboard_capture = False
        # Activity log
        self.activity_log = []
        self.log_entries = []
        # Uptime
        self.start_time = datetime.now()

    def update(self, **kwargs):
        with self._lock:
            for k, v in kwargs.items():
                setattr(self, k, v)

    def get(self, key, default=None):
        with self._lock:
            return getattr(self, key, default)

    def add_activity(self, text: str):
        with self._lock:
            entry = f"[{datetime.now().strftime('%H:%M:%S')}] {text}"
            self.activity_log.append(entry)
            if len(self.activity_log) > 50:
                self.activity_log = self.activity_log[-50:]

    def add_log(self, text: str, level: str = "INFO"):
        with self._lock:
            entry = f"[{datetime.now().strftime('%H:%M:%S')}] [{level}] {text}"
            self.log_entries.append(entry)
            if len(self.log_entries) > 200:
                self.log_entries = self.log_entries[-200:]

    def refresh_graphiti_stats(self) -> None:
        """Fetch Graphiti episode/entity counts and update hub state."""
        if requests is None:
            self.add_log("requests module not available; cannot fetch Graphiti stats", "HEALTH")
            return
        try:
            # Graphiti episodes
            payload_ep = {
                "jsonrpc": "2.0",
                "method": "graphiti_get_episodes",
                "params": {"limit": 50},
                "id": "count_episodes",
            }
            resp_ep = requests.post(GRAPHITI_RPC_URL, json=payload_ep, timeout=5)
            episodes = None
            if resp_ep.ok:
                data_ep = resp_ep.json() or {}
                episodes = data_ep.get("result", {}).get("total")

            # Graphiti entities
            payload_ent = {
                "jsonrpc": "2.0",
                "method": "graphiti_get_entities",
                "params": {"limit": 50},
                "id": "count_entities",
            }
            resp_ent = requests.post(GRAPHITI_RPC_URL, json=payload_ent, timeout=5)
            entities = None
            if resp_ent.ok:
                data_ent = resp_ent.json() or {}
                entities = data_ent.get("result", {}).get("total")

            # Only update with valid integers
            new_ep = episodes if isinstance(episodes, int) else self.episode_count
            new_ent = entities if isinstance(entities, int) else self.entity_count
            self.update(episode_count=new_ep, entity_count=new_ent)
            if isinstance(episodes, int) or isinstance(entities, int):
                self.add_log(
                    f"Graphiti stats updated: episodes={episodes}, entities={entities}",
                    "HEALTH",
                )
        except Exception as e:
            self.add_log(f"Graphiti stats fetch failed: {e}", "HEALTH")


# ─── SERVICE MANAGER ──────────────────────────────────────────────────────────
class ServiceManager:
    """Health checks and service management."""

    def __init__(self, state: HubState):
        self.hub_state = state
        self.toast_callback: Optional[Callable[[str, str, str], None]] = None
        self._previous_statuses = {}

    def check_port(self, port: int, host: str = "localhost") -> bool:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except OSError:
            return False

    def check_http(self, url: str, timeout: int = 3) -> bool:
        if not requests:
            return False
        try:
            resp = requests.get(url, timeout=timeout)
            return resp.status_code < 500
        except (requests.RequestException, OSError):
            return False

    def check_service(self, name: str) -> str:
        svc = SERVICES.get(name)
        if not svc:
            return "unknown"
        port_open = self.check_port(svc["port"])
        http_ok = self.check_http(svc["health_url"]) if svc.get("health_url") else port_open
        if port_open and http_ok:
            return "running"
        elif port_open:
            return "degraded"
        else:
            return "stopped"

    def check_all(self):
        statuses = {}
        for name in SERVICES:
            status = self.check_service(name)
            statuses[name] = status
            self.hub_state.add_log(f"{name}: {status}", "HEALTH")

            # Check for status changes and trigger toast
            prev_status = self._previous_statuses.get(name, "unknown")
            if prev_status != status:
                if status == "stopped" and prev_status in ("running", "degraded"):
                    self._trigger_toast(
                        "warning",
                        "Service Down",
                        f"{name} is not responding",
                    )
                elif status == "running" and prev_status in (
                    "stopped",
                    "degraded",
                    "unknown",
                ):
                    self._trigger_toast(
                        "success",
                        "Service Up",
                        f"{name} is now running",
                    )
                elif status == "degraded":
                    self._trigger_toast(
                        "warning",
                        "Service Degraded",
                        f"{name} is experiencing issues",
                    )

        self._previous_statuses = statuses.copy()

        # Overall health
        all_running = all(s == "running" for s in statuses.values())
        any_running = any(s != "stopped" for s in statuses.values())
        if all_running:
            overall = "healthy"
        elif any_running:
            overall = "degraded"
        else:
            overall = "down"
        self.hub_state.update(service_status=statuses, overall_health=overall)
        return overall

    def _trigger_toast(self, toast_type: str, title: str, message: str):
        """Trigger a toast notification if callback is set."""
        self.hub_state.add_log(f"[NOTIFY] {title}: {message}", "NOTIFY")
        if self.toast_callback:
            try:
                self.toast_callback(title, message, toast_type)
            except Exception as e:
                logger.debug(f"Toast callback failed: {e}")

    def get_process_pid(self, port: int) -> int | None:
        try:
            result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=5)
            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    if parts:
                        return int(parts[-1])
        except Exception as e:
            logger.debug(f"Failed to get process PID for port {port}: {e}")
        return None


# ─── CONFIG MANAGER ───────────────────────────────────────────────────────────
class ConfigManager:
    """Read/write configuration files."""

    def __init__(self, state: HubState):
        self.hub_state = state
        self.personalities = PERSONALITIES.copy()

    def load_personalities(self):
        try:
            if PERSONALITIES_FILE.exists():
                with open(PERSONALITIES_FILE, "r", encoding="utf-8") as f:
                    self.personalities = json.load(f)
                self.hub_state.add_log("Loaded personalities from config", "CONFIG")
        except Exception as e:
            self.hub_state.add_log(f"Failed to load personalities: {e}", "ERROR")

    def load_hub_settings(self) -> dict:
        try:
            if HUB_SETTINGS_FILE.exists():
                with open(HUB_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            self.hub_state.add_log(f"Failed to load settings: {e}", "ERROR")
        return {}

    def save_hub_settings(self, settings: dict):
        try:
            JARVIS_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(HUB_SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)
            self.hub_state.add_log("Settings saved", "CONFIG")
        except Exception as e:
            self.hub_state.add_log(f"Failed to save settings: {e}", "ERROR")

    def get_greeting(self, personality_key: str) -> str:
        p = self.personalities.get(personality_key, {})
        return p.get("greeting", "Hello.")

    def get_personality_name(self, personality_key: str) -> str:
        p = self.personalities.get(personality_key, {})
        return p.get("name", personality_key.capitalize())


# ─── ICON FACTORY ─────────────────────────────────────────────────────────────
def make_icon(color: str) -> Image.Image:
    """Create a colored circle icon."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    colors = {
        "green": (63, 185, 80, 255),
        "yellow": (240, 136, 62, 255),
        "red": (248, 81, 73, 255),
        "gray": (139, 148, 158, 255),
    }
    fill = colors.get(color, colors["gray"])
    draw.ellipse([8, 8, 56, 56], fill=fill)
    return img


# ─── TOAST NOTIFICATIONS ───────────────────────────────────────────────────────
class ToastNotification:
    """Slide-in toast notifications from bottom-right corner."""

    TOAST_COLORS = {
        "info": {"bg": "#1f6feb", "icon": "ℹ️"},
        "success": {"bg": "#238636", "icon": "✅"},
        "warning": {"bg": "#9e6a03", "icon": "⚠️"},
        "error": {"bg": "#da3633", "icon": "❌"},
    }

    def __init__(self, parent_window=None):
        self.parent = parent_window
        self.active_toasts = []
        self._lock = threading.Lock()

    def show(self, title: str, message: str, toast_type: str = "info", duration: int = 4000):
        """Show a toast notification. Thread-safe."""
        if self.parent and self.parent.winfo_exists():
            self.parent.after(0, lambda: self._create_toast(title, message, toast_type, duration))
        else:
            # Fallback: print to console
            icon = self.TOAST_COLORS.get(toast_type, {}).get("icon", "📢")
            print(f"{icon} [{title}] {message}")

    def _create_toast(self, title: str, message: str, toast_type: str, duration: int):
        """Create and display a toast window."""
        colors = self.TOAST_COLORS.get(toast_type, self.TOAST_COLORS["info"])

        # Create toast window
        toast = ctk.CTkToplevel()
        toast.overrideredirect(True)  # No window decorations
        toast.attributes("-topmost", True)
        toast.configure(fg_color=colors["bg"])

        # Calculate position (bottom-right, stack upward)
        screen_w = toast.winfo_screenwidth()
        screen_h = toast.winfo_screenheight()
        toast_w, toast_h = 350, 80
        x = screen_w - toast_w - 20
        y = screen_h - toast_h - 60 - (len(self.active_toasts) * (toast_h + 10))
        toast.geometry(f"{toast_w}x{toast_h}+{x}+{y}")

        # Content frame
        content = ctk.CTkFrame(toast, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=12, pady=10)

        # Icon + Title row
        header_frame = ctk.CTkFrame(content, fg_color="transparent")
        header_frame.pack(fill="x")

        icon_label = ctk.CTkLabel(
            header_frame,
            text=colors["icon"],
            font=("Segoe UI", 14),
            width=30,
        )
        icon_label.pack(side="left")

        title_label = ctk.CTkLabel(
            header_frame,
            text=title,
            font=("Segoe UI", 13, "bold"),
            text_color="white",
            anchor="w",
        )
        title_label.pack(side="left", fill="x", expand=True)

        # Close button
        close_btn = ctk.CTkLabel(
            header_frame,
            text="✕",
            font=("Segoe UI", 12),
            text_color="#ffffff80",
            width=20,
            cursor="hand2",
        )
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: self._dismiss(toast))

        # Message
        msg_label = ctk.CTkLabel(
            content,
            text=message,
            font=("Segoe UI", 11),
            text_color="#ffffffcc",
            anchor="w",
            wraplength=320,
        )
        msg_label.pack(fill="x", pady=(4, 0))

        # Track and auto-dismiss
        with self._lock:
            self.active_toasts.append(toast)

        toast.after(duration, lambda: self._dismiss(toast))

        # Slide-in animation
        toast.attributes("-alpha", 0.0)
        self._animate_in(toast, 0.0)

    def _animate_in(self, toast, alpha: float):
        """Fade-in animation."""
        if not toast.winfo_exists():
            return
        alpha = min(alpha + 0.1, 1.0)
        toast.attributes("-alpha", alpha)
        if alpha < 1.0:
            toast.after(20, lambda: self._animate_in(toast, alpha))

    def _dismiss(self, toast):
        """Dismiss a toast notification."""
        try:
            if toast.winfo_exists():
                with self._lock:
                    if toast in self.active_toasts:
                        self.active_toasts.remove(toast)
                toast.destroy()
        except Exception as e:
            logger.debug(f"Failed to dismiss toast: {e}")


# ─── TRAY APP ─────────────────────────────────────────────────────────────────
class TrayApp:
    """System tray icon and menu."""

    def __init__(self, state: HubState, event_queue: queue.Queue, config: ConfigManager):
        self.hub_state = state
        self.event_queue = event_queue
        self.config = config
        self.icon = None
        self.toast = ToastNotification(None)  # No parent for tray notifications

    def create(self) -> Any:
        def on_dashboard(icon, item):
            self.event_queue.put(("show_dashboard", None))

        def on_jarvis_mode(icon, item):
            mode = str(item).lower()
            self.event_queue.put(("set_jarvis_mode", mode))

        def on_jarvis_personality(icon, item):
            pers = str(item).lower()
            self.event_queue.put(("set_jarvis_personality", pers))

        def on_toggle_voice_input(icon, item):
            self.event_queue.put(("toggle_voice_input", None))

        def on_toggle_voice_output(icon, item):
            self.event_queue.put(("toggle_voice_output", None))

        def on_start_all(icon, item):
            self.event_queue.put(("start_all_services", None))

        def on_stop_all(icon, item):
            self.event_queue.put(("stop_all_services", None))

        def on_settings(icon, item):
            self.event_queue.put(("show_settings", None))

        def on_exit(icon, item):
            self.event_queue.put(("exit", None))
            icon.stop()

        # Build personality submenu items
        pers_items = []
        for key in PERSONALITIES:
            name = PERSONALITIES[key].get("name", key.capitalize())
            pers_items.append(pystray.MenuItem(name, on_jarvis_personality))

        # Build service status items
        svc_items = []
        for name in SERVICES:
            svc_items.append(pystray.MenuItem(f"● {name}: Checking...", None, enabled=False))
        svc_items.append(pystray.Menu.SEPARATOR)
        svc_items.append(pystray.MenuItem("Start All", on_start_all))
        svc_items.append(pystray.MenuItem("Stop All", on_stop_all))

        menu = pystray.Menu(
            pystray.MenuItem("N-Xyme Catalyst", None, enabled=False),
            pystray.MenuItem("● Status: Checking...", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Jarvis",
                pystray.Menu(
                    pystray.MenuItem(
                        "Mode",
                        pystray.Menu(
                            pystray.MenuItem("Silent", on_jarvis_mode),
                            pystray.MenuItem("Narrator", on_jarvis_mode),
                            pystray.MenuItem("Friend", on_jarvis_mode),
                            pystray.MenuItem("Delegate", on_jarvis_mode),
                        ),
                    ),
                    pystray.MenuItem("Personality", pystray.Menu(*pers_items)),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem("☐ Voice Input", on_toggle_voice_input),
                    pystray.MenuItem("☐ Voice Output", on_toggle_voice_output),
                ),
            ),
            pystray.MenuItem("Services", pystray.Menu(*svc_items)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Open Dashboard", on_dashboard),
            pystray.MenuItem("Settings", on_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", on_exit),
        )

        self.icon = pystray.Icon("nxyme_hub", make_icon("gray"), "N-Xyme Catalyst", menu)
        return self.icon

    def update_icon(self):
        """Update tray icon based on health."""
        if not self.icon:
            return
        health = str(self.hub_state.get("overall_health", "unknown"))
        color_map = {"healthy": "green", "degraded": "yellow", "down": "red"}
        color = color_map.get(health, "gray")
        self.icon.icon = make_icon(color)


# ─── DASHBOARD ────────────────────────────────────────────────────────────────
class Dashboard(ctk.CTk):
    """Main dashboard window with tabs."""

    def __init__(
        self,
        hub_state: HubState,
        event_queue: queue.Queue,
        config: ConfigManager,
        service_mgr: ServiceManager,
    ):
        super().__init__()
        self.hub_state = hub_state
        self.event_queue = event_queue
        self.config = config
        self.service_mgr = service_mgr

        # Window setup
        self.title("N-Xyme Catalyst Hub")
        self.geometry("920x640")
        self.minsize(800, 500)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=COLORS["bg"])

        # Intercept close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self.toast = ToastNotification(self)
        # Schedule Graphiti stats refresh (memory counts)
        self._graphiti_stats_interval = 60  # seconds
        self._graphiti_next_update = time.time() + self._graphiti_stats_interval
        self._update_loop()

    def _on_close(self):
        """Minimize to tray instead of closing."""
        self.withdraw()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], height=50)
        header.pack(fill="x", padx=10, pady=(10, 0))
        header.pack_propagate(False)

        title = ctk.CTkLabel(
            header,
            text="N-XYME CATALYST HUB",
            font=("Segoe UI", 18, "bold"),
            text_color=COLORS["accent"],
        )
        title.pack(side="left", padx=15, pady=10)

        self.health_indicator = ctk.CTkLabel(
            header,
            text="● Checking...",
            font=("Segoe UI", 12),
            text_color=COLORS["gray"],
        )
        self.health_indicator.pack(side="right", padx=15)

        # Notification bell
        self.notification_bell = ctk.CTkLabel(
            header,
            text="🔔",
            font=("Segoe UI", 16),
            text_color=COLORS["gray"],
            cursor="hand2",
        )
        self.notification_bell.pack(side="right", padx=5)
        self.notification_bell.bind("<Button-1>", lambda e: self._show_notification_history())
        self.notification_count = 0

        self.uptime_label = ctk.CTkLabel(
            header,
            text="Uptime: 0:00:00",
            font=("Consolas", 10),
            text_color=COLORS["gray"],
        )
        self.uptime_label.pack(side="right", padx=15)

        # Tab view
        self.tabview = ctk.CTkTabview(self, fg_color=COLORS["bg_card"])
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        # Create tabs
        self.tab_overview = self.tabview.add("Overview")
        self.tab_jarvis = self.tabview.add("Jarvis")
        self.tab_memory = self.tabview.add("Memory")
        self.tab_services = self.tabview.add("Services")
        self.tab_settings = self.tabview.add("Settings")
        self.tab_logs = self.tabview.add("Logs")

        self._build_overview_tab()
        self._build_jarvis_tab()
        self._build_memory_tab()
        self._build_services_tab()
        self._build_settings_tab()
        self._build_logs_tab()

    def _show_notification_history(self):
        """Show notification history in a popup."""
        popup = ctk.CTkToplevel(self)
        popup.title("Notification History")
        popup.geometry("400x300")
        popup.configure(fg_color=COLORS["bg"])
        popup.attributes("-topmost", True)

        # Header
        header = ctk.CTkFrame(popup, fg_color=COLORS["bg_card"], height=40)
        header.pack(fill="x", padx=10, pady=(10, 0))
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="🔔 Recent Notifications",
            font=("Segoe UI", 14, "bold"),
            text_color=COLORS["accent"],
        ).pack(side="left", padx=10)

        # Notification list
        notif_frame = ctk.CTkScrollableFrame(popup, fg_color="transparent")
        notif_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Get notification entries from log
        log_entries = self.hub_state.get("log_entries", [])
        notif_entries = (
            [e for e in log_entries if "[NOTIFY]" in e] if isinstance(log_entries, list) else []
        )

        if notif_entries:
            for entry in notif_entries[-20:]:
                ctk.CTkLabel(
                    notif_frame,
                    text=entry,
                    font=("Consolas", 10),
                    text_color=COLORS["text"],
                    anchor="w",
                ).pack(fill="x", pady=2)
        else:
            ctk.CTkLabel(
                notif_frame,
                text="No notifications yet",
                font=("Segoe UI", 11),
                text_color=COLORS["gray"],
            ).pack(pady=20)

    # ── Overview Tab ──────────────────────────────────────────────────────────
    def _build_overview_tab(self):
        frame = self.tab_overview
        frame.grid_columnconfigure((0, 1, 2), weight=1)
        frame.grid_rowconfigure((0, 1), weight=1)

        self.overview_cards = {}
        services_list = list(SERVICES.keys()) + ["Jarvis"]
        for idx, name in enumerate(services_list):
            row, col = divmod(idx, 3)
            card_dict = self._create_status_card(frame, name)
            card_dict["frame"].grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            self.overview_cards[name] = card_dict

    def _create_status_card(self, parent, name: str) -> dict:
        card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["bg"],
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"],
        )

        name_label = ctk.CTkLabel(
            card, text=name, font=("Segoe UI", 13, "bold"), text_color=COLORS["text"]
        )
        name_label.pack(pady=(12, 2))

        dot = ctk.CTkLabel(card, text="●", font=("Segoe UI", 28), text_color=COLORS["gray"])
        dot.pack()

        status_label = ctk.CTkLabel(
            card, text="Unknown", font=("Segoe UI", 10), text_color=COLORS["gray"]
        )
        status_label.pack()

        info_label = ctk.CTkLabel(card, text="", font=("Consolas", 9), text_color=COLORS["gray"])
        info_label.pack(pady=(0, 10))

        return {
            "frame": card,
            "dot": dot,
            "status_label": status_label,
            "info_label": info_label,
        }

    # ── Jarvis Tab ────────────────────────────────────────────────────────────
    def _build_jarvis_tab(self):
        frame = self.tab_jarvis
        frame.grid_columnconfigure(0, weight=1)

        # Mode section
        mode_frame = ctk.CTkFrame(frame, fg_color=COLORS["bg"], corner_radius=8)
        mode_frame.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="ew")

        ctk.CTkLabel(
            mode_frame,
            text="JARVIS MODE",
            font=("Segoe UI", 11, "bold"),
            text_color=COLORS["accent"],
        ).pack(pady=(10, 5), padx=15, anchor="w")

        self.mode_var = ctk.StringVar(value="friend")
        modes = ["Silent", "Narrator", "Friend", "Delegate"]
        mode_radio_frame = ctk.CTkFrame(mode_frame, fg_color="transparent")
        mode_radio_frame.pack(pady=(0, 10), padx=15, fill="x")
        for m in modes:
            ctk.CTkRadioButton(
                mode_radio_frame,
                text=m,
                variable=self.mode_var,
                value=m.lower(),
                font=("Segoe UI", 11),
                command=lambda: self.event_queue.put(("set_jarvis_mode", self.mode_var.get())),
            ).pack(side="left", padx=10)

        # Personality section
        pers_frame = ctk.CTkFrame(frame, fg_color=COLORS["bg"], corner_radius=8)
        pers_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        ctk.CTkLabel(
            pers_frame,
            text="PERSONALITY",
            font=("Segoe UI", 11, "bold"),
            text_color=COLORS["accent"],
        ).pack(pady=(10, 5), padx=15, anchor="w")

        pers_names = [PERSONALITIES[k]["name"] for k in PERSONALITIES]
        self.pers_menu = ctk.CTkOptionMenu(
            pers_frame,
            values=pers_names,
            width=200,
            command=self._on_personality_change,
        )
        self.pers_menu.pack(pady=5, padx=15, anchor="w")

        self.greeting_label = ctk.CTkLabel(
            pers_frame,
            text="",
            font=("Consolas", 10),
            text_color=COLORS["gray"],
            wraplength=400,
        )
        self.greeting_label.pack(pady=(0, 10), padx=15, anchor="w")

        # Voice section
        voice_frame = ctk.CTkFrame(frame, fg_color=COLORS["bg"], corner_radius=8)
        voice_frame.grid(row=2, column=0, padx=20, pady=5, sticky="ew")

        ctk.CTkLabel(
            voice_frame,
            text="VOICE",
            font=("Segoe UI", 11, "bold"),
            text_color=COLORS["accent"],
        ).pack(pady=(10, 5), padx=15, anchor="w")

        voice_toggle_frame = ctk.CTkFrame(voice_frame, fg_color="transparent")
        voice_toggle_frame.pack(pady=(0, 10), padx=15, fill="x")

        self.voice_input_switch = ctk.CTkSwitch(
            voice_toggle_frame,
            text="🎤 Voice Input",
            command=lambda: self.event_queue.put(("toggle_voice_input", None)),
        )
        self.voice_input_switch.pack(side="left", padx=10)

        self.voice_output_switch = ctk.CTkSwitch(
            voice_toggle_frame,
            text="🔊 Voice Output",
            command=lambda: self.event_queue.put(("toggle_voice_output", None)),
        )
        self.voice_output_switch.pack(side="left", padx=10)

        # Activity log
        act_frame = ctk.CTkFrame(frame, fg_color=COLORS["bg"], corner_radius=8)
        act_frame.grid(row=3, column=0, padx=20, pady=5, sticky="nsew")
        frame.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(
            act_frame,
            text="ACTIVITY LOG",
            font=("Segoe UI", 11, "bold"),
            text_color=COLORS["accent"],
        ).pack(pady=(10, 5), padx=15, anchor="w")

        self.activity_box = ctk.CTkTextbox(
            act_frame, font=("Consolas", 10), fg_color=COLORS["bg_card"]
        )
        self.activity_box.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        self.activity_box.configure(state="disabled")

    def _on_personality_change(self, name: str):
        for key, val in PERSONALITIES.items():
            if val["name"] == name:
                self.event_queue.put(("set_jarvis_personality", key))
                break

    # ── Memory Tab ────────────────────────────────────────────────────────────
    def _build_memory_tab(self):
        frame = self.tab_memory
        frame.grid_columnconfigure(0, weight=1)

        # Stats
        stats_frame = ctk.CTkFrame(frame, fg_color=COLORS["bg"], corner_radius=8)
        stats_frame.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="ew")

        ctk.CTkLabel(
            stats_frame,
            text="GRAPHITI MEMORY",
            font=("Segoe UI", 11, "bold"),
            text_color=COLORS["accent"],
        ).pack(pady=(10, 5), padx=15, anchor="w")

        stats_grid = ctk.CTkFrame(stats_frame, fg_color="transparent")
        stats_grid.pack(pady=(0, 10), padx=15, fill="x")

        self.episode_label = ctk.CTkLabel(
            stats_grid,
            text="Episodes: --",
            font=("Consolas", 12),
            text_color=COLORS["text"],
        )
        self.episode_label.pack(side="left", padx=20)

        self.entity_label = ctk.CTkLabel(
            stats_grid,
            text="Entities: --",
            font=("Consolas", 12),
            text_color=COLORS["text"],
        )
        self.entity_label.pack(side="left", padx=20)

        # Search
        search_frame = ctk.CTkFrame(frame, fg_color=COLORS["bg"], corner_radius=8)
        search_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        ctk.CTkLabel(
            search_frame,
            text="SEARCH MEMORY",
            font=("Segoe UI", 11, "bold"),
            text_color=COLORS["accent"],
        ).pack(pady=(10, 5), padx=15, anchor="w")

        search_input_frame = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_input_frame.pack(pady=(0, 10), padx=15, fill="x")

        self.search_entry = ctk.CTkEntry(
            search_input_frame, placeholder_text="Search episodes...", width=400
        )
        self.search_entry.pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            search_input_frame, text="Search", width=80, command=self._search_memory
        ).pack(side="left")

        # Results
        results_frame = ctk.CTkFrame(frame, fg_color=COLORS["bg"], corner_radius=8)
        results_frame.grid(row=2, column=0, padx=20, pady=5, sticky="nsew")
        frame.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            results_frame,
            text="RESULTS",
            font=("Segoe UI", 11, "bold"),
            text_color=COLORS["accent"],
        ).pack(pady=(10, 5), padx=15, anchor="w")

        self.results_box = ctk.CTkTextbox(
            results_frame, font=("Consolas", 10), fg_color=COLORS["bg_card"]
        )
        self.results_box.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        self.results_box.configure(state="disabled")

    def _search_memory(self):
        query = self.search_entry.get().strip()
        if query:
            self.event_queue.put(("search_memory", query))

    # ── Services Tab ──────────────────────────────────────────────────────────
    def _build_services_tab(self):
        frame = self.tab_services
        frame.grid_columnconfigure(0, weight=1)

        # Header
        header_frame = ctk.CTkFrame(frame, fg_color=COLORS["bg"], corner_radius=8)
        header_frame.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="ew")

        ctk.CTkLabel(
            header_frame,
            text="SERVICES",
            font=("Segoe UI", 11, "bold"),
            text_color=COLORS["accent"],
        ).pack(pady=(10, 5), padx=15, anchor="w")

        # Service rows container
        self.service_rows = {}
        services_container = ctk.CTkFrame(frame, fg_color="transparent")
        services_container.grid(row=1, column=0, padx=20, pady=5, sticky="nsew")
        frame.grid_rowconfigure(1, weight=1)

        for idx, (name, svc) in enumerate(SERVICES.items()):
            row_frame = ctk.CTkFrame(
                services_container, fg_color=COLORS["bg"], corner_radius=8, height=50
            )
            row_frame.pack(fill="x", pady=3)
            row_frame.pack_propagate(False)

            # Status dot
            dot = ctk.CTkLabel(
                row_frame, text="●", font=("Segoe UI", 18), text_color=COLORS["gray"]
            )
            dot.pack(side="left", padx=(15, 5))

            # Name
            ctk.CTkLabel(
                row_frame,
                text=name,
                font=("Segoe UI", 12, "bold"),
                text_color=COLORS["text"],
                width=100,
            ).pack(side="left", padx=5)

            # Status
            status_lbl = ctk.CTkLabel(
                row_frame,
                text="Unknown",
                font=("Segoe UI", 10),
                text_color=COLORS["gray"],
                width=80,
            )
            status_lbl.pack(side="left", padx=5)

            # Port
            port_lbl = ctk.CTkLabel(
                row_frame,
                text=f"Port: {svc['port']}",
                font=("Consolas", 10),
                text_color=COLORS["gray"],
                width=100,
            )
            port_lbl.pack(side="left", padx=5)

            # PID
            pid_lbl = ctk.CTkLabel(
                row_frame,
                text="PID: --",
                font=("Consolas", 10),
                text_color=COLORS["gray"],
                width=80,
            )
            pid_lbl.pack(side="left", padx=5)

            # Buttons
            btn_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            btn_frame.pack(side="right", padx=10)

            ctk.CTkButton(
                btn_frame,
                text="Start",
                width=60,
                height=28,
                fg_color=COLORS["green"],
                hover_color="#2ea043",
                command=lambda n=name: self.event_queue.put(("start_service", n)),
            ).pack(side="left", padx=2)

            ctk.CTkButton(
                btn_frame,
                text="Stop",
                width=60,
                height=28,
                fg_color=COLORS["red"],
                hover_color="#da3633",
                command=lambda n=name: self.event_queue.put(("stop_service", n)),
            ).pack(side="left", padx=2)

            self.service_rows[name] = {
                "dot": dot,
                "status": status_lbl,
                "port": port_lbl,
                "pid": pid_lbl,
            }

        # Bulk actions
        bulk_frame = ctk.CTkFrame(frame, fg_color=COLORS["bg"], corner_radius=8)
        bulk_frame.grid(row=2, column=0, padx=20, pady=5, sticky="ew")

        ctk.CTkButton(
            bulk_frame,
            text="Start All",
            width=120,
            fg_color=COLORS["green"],
            hover_color="#2ea043",
            command=lambda: self.event_queue.put(("start_all_services", None)),
        ).pack(side="left", padx=15, pady=10)

        ctk.CTkButton(
            bulk_frame,
            text="Stop All",
            width=120,
            fg_color=COLORS["red"],
            hover_color="#da3633",
            command=lambda: self.event_queue.put(("stop_all_services", None)),
        ).pack(side="left", padx=5, pady=10)

        ctk.CTkButton(
            bulk_frame,
            text="Refresh",
            width=120,
            command=lambda: self.event_queue.put(("refresh_services", None)),
        ).pack(side="right", padx=15, pady=10)

    # ── Settings Tab ──────────────────────────────────────────────────────────
    def _build_settings_tab(self):
        frame = self.tab_settings
        frame.grid_columnconfigure(0, weight=1)

        # Scrollable container
        scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        scroll.grid_columnconfigure(1, weight=1)

        # Jarvis settings
        ctk.CTkLabel(
            scroll,
            text="JARVIS",
            font=("Segoe UI", 12, "bold"),
            text_color=COLORS["accent"],
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))

        ctk.CTkLabel(scroll, text="Default Mode:", font=("Segoe UI", 11)).grid(
            row=1, column=0, sticky="w", padx=10, pady=3
        )
        self.setting_mode = ctk.CTkOptionMenu(
            scroll, values=["Silent", "Narrator", "Friend", "Delegate"], width=200
        )
        self.setting_mode.grid(row=1, column=1, sticky="w", padx=10, pady=3)

        ctk.CTkLabel(scroll, text="Default Personality:", font=("Segoe UI", 11)).grid(
            row=2, column=0, sticky="w", padx=10, pady=3
        )
        pers_names = [PERSONALITIES[k]["name"] for k in PERSONALITIES]
        self.setting_personality = ctk.CTkOptionMenu(scroll, values=pers_names, width=200)
        self.setting_personality.grid(row=2, column=1, sticky="w", padx=10, pady=3)

        # Graphiti settings
        ctk.CTkLabel(
            scroll,
            text="GRAPHITI",
            font=("Segoe UI", 12, "bold"),
            text_color=COLORS["accent"],
        ).grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=(15, 5))

        ctk.CTkLabel(scroll, text="Graphiti URL:", font=("Segoe UI", 11)).grid(
            row=4, column=0, sticky="w", padx=10, pady=3
        )
        self.setting_graphiti_url = ctk.CTkEntry(
            scroll, width=300, placeholder_text=GRAPHITI_RPC_URL.replace("/json-rpc", "")
        )
        self.setting_graphiti_url.grid(row=4, column=1, sticky="w", padx=10, pady=3)

        # Ollama settings
        ctk.CTkLabel(
            scroll,
            text="OLLAMA",
            font=("Segoe UI", 12, "bold"),
            text_color=COLORS["accent"],
        ).grid(row=5, column=0, columnspan=2, sticky="w", padx=10, pady=(15, 5))

        ctk.CTkLabel(scroll, text="Ollama URL:", font=("Segoe UI", 11)).grid(
            row=6, column=0, sticky="w", padx=10, pady=3
        )
        self.setting_ollama_url = ctk.CTkEntry(scroll, width=300, placeholder_text=OLLAMA_URL)
        self.setting_ollama_url.grid(row=6, column=1, sticky="w", padx=10, pady=3)

        # Neo4j settings
        ctk.CTkLabel(
            scroll,
            text="NEO4J",
            font=("Segoe UI", 12, "bold"),
            text_color=COLORS["accent"],
        ).grid(row=7, column=0, columnspan=2, sticky="w", padx=10, pady=(15, 5))

        ctk.CTkLabel(scroll, text="Neo4j URI:", font=("Segoe UI", 11)).grid(
            row=8, column=0, sticky="w", padx=10, pady=3
        )
        self.setting_neo4j_uri = ctk.CTkEntry(
            scroll,
            width=300,
            placeholder_text=NEO4J_URL.replace("http://", "bolt://").replace(":7474", ":7687"),
        )
        self.setting_neo4j_uri.grid(row=8, column=1, sticky="w", padx=10, pady=3)

        # Auto-capture settings
        ctk.CTkLabel(
            scroll,
            text="AUTO-CAPTURE",
            font=("Segoe UI", 12, "bold"),
            text_color=COLORS["accent"],
        ).grid(row=9, column=0, columnspan=2, sticky="w", padx=10, pady=(15, 5))

        self.setting_screen_capture = ctk.CTkSwitch(scroll, text="Screen Capture")
        self.setting_screen_capture.grid(
            row=10, column=0, columnspan=2, sticky="w", padx=10, pady=3
        )

        self.setting_clipboard_capture = ctk.CTkSwitch(scroll, text="Clipboard Capture")
        self.setting_clipboard_capture.grid(
            row=11, column=0, columnspan=2, sticky="w", padx=10, pady=3
        )

        # Save button
        ctk.CTkButton(scroll, text="Save Settings", width=150, command=self._save_settings).grid(
            row=12, column=0, columnspan=2, pady=20
        )

    def _save_settings(self):
        settings = {
            "jarvis_mode": self.setting_mode.get().lower(),
            "jarvis_personality": self.setting_personality.get().lower(),
            "graphiti_url": self.setting_graphiti_url.get(),
            "ollama_url": self.setting_ollama_url.get(),
            "neo4j_uri": self.setting_neo4j_uri.get(),
            "screen_capture": bool(self.setting_screen_capture.get()),
            "clipboard_capture": bool(self.setting_clipboard_capture.get()),
        }
        self.event_queue.put(("save_settings", settings))

    # ── Logs Tab ──────────────────────────────────────────────────────────────
    def _build_logs_tab(self):
        frame = self.tab_logs
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        # Filter bar
        filter_frame = ctk.CTkFrame(frame, fg_color=COLORS["bg"], corner_radius=8)
        filter_frame.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="ew")

        ctk.CTkLabel(filter_frame, text="Filter:", font=("Segoe UI", 11)).pack(
            side="left", padx=10, pady=8
        )

        self.log_filter = ctk.CTkOptionMenu(
            filter_frame,
            values=["ALL", "INFO", "HEALTH", "CONFIG", "ERROR", "NOTIFY"],
            width=120,
            command=self._filter_logs,
        )
        self.log_filter.pack(side="left", padx=5, pady=8)

        ctk.CTkButton(filter_frame, text="Clear", width=80, command=self._clear_logs).pack(
            side="right", padx=10, pady=8
        )

        # Log textbox
        self.log_box = ctk.CTkTextbox(frame, font=("Consolas", 10), fg_color=COLORS["bg_card"])
        self.log_box.grid(row=1, column=0, padx=20, pady=(5, 10), sticky="nsew")
        self.log_box.configure(state="disabled")

    def _filter_logs(self, level: str):
        self.event_queue.put(("filter_logs", level))

    def _clear_logs(self):
        self.event_queue.put(("clear_logs", None))

    # ── Update Loop ───────────────────────────────────────────────────────────
    def _update_loop(self):
        """Update all UI elements from state."""
        # Periodic Graphiti stats refresh
        if (
            getattr(self, "_graphiti_next_update", None) is not None
            and time.time() >= self._graphiti_next_update
        ):
            try:
                self.hub_state.refresh_graphiti_stats()
            except Exception as e:
                logger.debug(f"Failed to refresh Graphiti stats: {e}")
            self._graphiti_next_update = time.time() + self._graphiti_stats_interval
        # Health indicator
        health = str(self.hub_state.get("overall_health", "unknown"))
        health_colors = {
            "healthy": COLORS["green"],
            "degraded": COLORS["yellow"],
            "down": COLORS["red"],
        }
        health_texts = {
            "healthy": "● Healthy",
            "degraded": "⚠ Degraded",
            "down": "✖ Down",
        }
        self.health_indicator.configure(
            text=health_texts.get(health, "● Unknown"),
            text_color=health_colors.get(health, COLORS["gray"]),
        )

        # Uptime
        start_time = self.hub_state.get("start_time", datetime.now())
        if isinstance(start_time, datetime):
            uptime = datetime.now() - start_time
        else:
            uptime = datetime.now() - datetime.now()
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        self.uptime_label.configure(text=f"Uptime: {hours}:{minutes:02d}:{seconds:02d}")

        # Overview cards
        for name, card in self.overview_cards.items():
            if name in SERVICES:
                service_status = self.hub_state.get("service_status", {})
                if isinstance(service_status, dict):
                    status = service_status.get(name, "unknown")
                else:
                    status = "unknown"
                svc = SERVICES[name]
                # Special info display for Auto-capture
                if name == "Auto-capture":
                    screen = self.hub_state.get("screen_capture", False)
                    clip = self.hub_state.get("clipboard_capture", False)
                    card["info_label"].configure(
                        text=f"Port: {svc['port']} | Screen: {'ON' if screen else 'OFF'} | Clip: {'ON' if clip else 'OFF'}"
                    )
                else:
                    card["info_label"].configure(text=f"Port: {svc['port']}")
            elif name == "Jarvis":
                status = "running" if self.hub_state.get("jarvis_active") else "standby"
                mode = str(self.hub_state.get("jarvis_mode", "friend"))
                card["info_label"].configure(text=f"Mode: {mode.capitalize()}")
            else:
                status = "unknown"

            dot_colors = {
                "running": COLORS["green"],
                "degraded": COLORS["yellow"],
                "stopped": COLORS["red"],
                "standby": COLORS["accent"],
            }
            status_texts = {
                "running": "Running",
                "degraded": "Degraded",
                "stopped": "Stopped",
                "standby": "Standby",
                "unknown": "Unknown",
            }
            card["dot"].configure(text_color=dot_colors.get(status, COLORS["gray"]))
            card["status_label"].configure(
                text=status_texts.get(status, "Unknown"),
                text_color=dot_colors.get(status, COLORS["gray"]),
            )

        # Jarvis tab
        self.mode_var.set(str(self.hub_state.get("jarvis_mode", "friend")))
        pers_key = str(self.hub_state.get("jarvis_personality", "butler"))
        pers_name = PERSONALITIES.get(pers_key, {}).get("name", "Jarvis")
        self.pers_menu.set(pers_name)
        self.greeting_label.configure(
            text=f'"{PERSONALITIES.get(pers_key, {}).get("greeting", "")}"'
        )

        if self.hub_state.get("voice_input"):
            self.voice_input_switch.select()
        else:
            self.voice_input_switch.deselect()
        if self.hub_state.get("voice_output"):
            self.voice_output_switch.select()
        else:
            self.voice_output_switch.deselect()

        # Activity log
        self.activity_box.configure(state="normal")
        self.activity_box.delete("1.0", "end")
        activity_log = self.hub_state.get("activity_log", [])
        if isinstance(activity_log, list):
            for entry in activity_log[-15:]:
                self.activity_box.insert("end", entry + "\n")
        self.activity_box.configure(state="disabled")

        # Memory stats
        self.episode_label.configure(text=f"Episodes: {self.hub_state.get('episode_count', '--')}")
        self.entity_label.configure(text=f"Entities: {self.hub_state.get('entity_count', '--')}")

        # Services tab
        for name, row in self.service_rows.items():
            service_status = self.hub_state.get("service_status", {})
            if isinstance(service_status, dict):
                status = service_status.get(name, "unknown")
            else:
                status = "unknown"
            dot_colors = {
                "running": COLORS["green"],
                "degraded": COLORS["yellow"],
                "stopped": COLORS["red"],
            }
            status_texts = {
                "running": "Running",
                "degraded": "Degraded",
                "stopped": "Stopped",
                "unknown": "Unknown",
            }
            row["dot"].configure(text_color=dot_colors.get(status, COLORS["gray"]))
            row["status"].configure(
                text=status_texts.get(status, "Unknown"),
                text_color=dot_colors.get(status, COLORS["gray"]),
            )
            service_pids = self.hub_state.get("service_pids", {})
            if isinstance(service_pids, dict):
                pid = service_pids.get(name)
            else:
                pid = None
            row["pid"].configure(text=f"PID: {pid if pid else '--'}")

        # Logs
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        log_entries = self.hub_state.get("log_entries", [])
        if isinstance(log_entries, list):
            for entry in log_entries[-100:]:
                self.log_box.insert("end", entry + "\n")
        self.log_box.configure(state="disabled")

        self.after(500, self._update_loop)


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    state = HubState()
    event_queue = queue.Queue()
    config = ConfigManager(state)
    service_mgr = ServiceManager(state)

    print("=" * 60)
    print("  N-XYME CATALYST HUB")
    print("  System Tray Control Center")
    print("=" * 60)

    # Load configs
    config.load_personalities()
    settings = config.load_hub_settings()
    if settings:
        state.update(
            jarvis_mode=settings.get("jarvis_mode", "friend"),
            jarvis_personality=settings.get("jarvis_personality", "butler"),
            screen_capture=settings.get("screen_capture", False),
            clipboard_capture=settings.get("clipboard_capture", False),
        )
        state.add_log("Loaded hub settings", "CONFIG")

    # Initial health check
    state.add_log("Performing initial health check...", "HEALTH")
    service_mgr.check_all()

    # Start tray
    tray_app = TrayApp(state, event_queue, config)
    tray = tray_app.create()
    tray_thread = threading.Thread(target=tray.run, daemon=True)
    tray_thread.start()
    state.add_log("Tray icon started", "INFO")

    # Start dashboard
    dashboard = Dashboard(state, event_queue, config, service_mgr)
    service_mgr.toast_callback = dashboard.toast.show
    state.add_log("Dashboard started", "INFO")

    # Health check thread
    def health_check_loop():
        while True:
            time.sleep(30)
            service_mgr.check_all()
            tray_app.update_icon()

    health_thread = threading.Thread(target=health_check_loop, daemon=True)
    health_thread.start()

    # Event processor
    def process_events():
        while True:
            try:
                event, data = event_queue.get(timeout=0.1)

                if event == "show_dashboard":
                    dashboard.deiconify()
                    dashboard.lift()
                    dashboard.focus_force()

                elif event == "set_jarvis_mode":
                    state.update(jarvis_mode=data)
                    state.add_activity(f"Jarvis mode: {data}")
                    state.add_log(f"Jarvis mode changed to {data}", "CONFIG")
                    state.add_log(f"[NOTIFY] Jarvis Mode: Switched to {data} mode", "NOTIFY")
                    dashboard.toast.show("Jarvis Mode", f"Switched to {data} mode", "info")
                    # Persist mode change to config
                    settings = config.load_hub_settings()
                    settings["jarvis_mode"] = data
                    config.save_hub_settings(settings)

                elif event == "set_jarvis_personality":
                    state.update(jarvis_personality=data)
                    name = config.get_personality_name(data)
                    state.add_activity(f"Personality: {name}")
                    state.add_log(f"Personality changed to {name}", "CONFIG")
                    state.add_log(f"[NOTIFY] Personality: Switched to {name}", "NOTIFY")
                    dashboard.toast.show("Personality", f"Switched to {name}", "info")
                    # Persist personality change to config
                    settings = config.load_hub_settings()
                    settings["jarvis_personality"] = data
                    config.save_hub_settings(settings)

                elif event == "toggle_voice_input":
                    current = state.get("voice_input", False)
                    state.update(voice_input=not current)
                    state.add_activity(f"Voice Input: {'ON' if not current else 'OFF'}")

                elif event == "toggle_voice_output":
                    current = state.get("voice_output", False)
                    state.update(voice_output=not current)
                    state.add_activity(f"Voice Output: {'ON' if not current else 'OFF'}")

                elif event == "start_service":
                    state.add_log(f"Start requested: {data}", "INFO")
                    state.add_activity(f"Starting {data}...")

                elif event == "stop_service":
                    state.add_log(f"Stop requested: {data}", "INFO")
                    state.add_activity(f"Stopping {data}...")

                elif event == "start_all_services":
                    state.add_log("Starting all services...", "INFO")
                    state.add_activity("Starting all services...")
                    service_mgr.check_all()

                elif event == "stop_all_services":
                    state.add_log("Stopping all services...", "INFO")
                    state.add_activity("Stopping all services...")

                elif event == "refresh_services":
                    state.add_log("Refreshing service status...", "HEALTH")
                    service_mgr.check_all()
                    tray_app.update_icon()

                elif event == "search_memory":
                    state.add_log(f"Memory search: {data}", "INFO")
                    # Placeholder - would call Graphiti API
                    results = f"Search results for: {data}\n(Graphiti API integration pending)"
                    dashboard.results_box.configure(state="normal")
                    dashboard.results_box.delete("1.0", "end")
                    dashboard.results_box.insert("1.0", results)
                    dashboard.results_box.configure(state="disabled")

                elif event == "save_settings":
                    config.save_hub_settings(data)
                    state.update(
                        jarvis_mode=data.get("jarvis_mode", state.get("jarvis_mode")),
                        jarvis_personality=data.get(
                            "jarvis_personality", state.get("jarvis_personality")
                        ),
                        screen_capture=data.get("screen_capture", False),
                        clipboard_capture=data.get("clipboard_capture", False),
                    )
                    state.add_activity("Settings saved")

                elif event == "filter_logs":
                    state.add_log(f"Log filter: {data}", "INFO")

                elif event == "clear_logs":
                    state.update(log_entries=[])
                    state.add_log("Logs cleared", "INFO")

                elif event == "show_settings":
                    dashboard.deiconify()
                    dashboard.lift()
                    dashboard.focus_force()
                    dashboard.tabview.set("Settings")

                elif event == "exit":
                    dashboard.quit()
                    return

            except queue.Empty:
                logger.debug("Event queue empty, continuing")

    event_thread = threading.Thread(target=process_events, daemon=True)
    event_thread.start()

    # Run dashboard mainloop
    dashboard.mainloop()


if __name__ == "__main__":
    main()
