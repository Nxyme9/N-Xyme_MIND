#!/usr/bin/env python3
"""
Echo Jarvis UI - System Tray + Dashboard
Uses pystray (tray) + customtkinter (dashboard)
"""

import sys
import os
import time
import threading
import queue
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


# ─── SHARED STATE ────────────────────────────────────────────────────────────
class EchoState:
    """Shared state between UI and Core."""

    def __init__(self):
        self.mode = "friend"  # silent/narrator/friend/delegate
        self.is_active = False
        self.voice_input = True
        self.voice_output = True
        self.is_speaking = False
        self.is_listening = False
        self.last_activity = []
        self.uptime_start = None
        self.gpu_temp = 0
        self.gpu_vram_free = 0
        self.gpu_util = 0
        self.ram_used_pct = 0
        self.ram_free_gb = 0
        self.cpu_load = 0
        self.nvme_free_gb = 0
        self._lock = threading.Lock()

    def update(self, **kwargs):
        with self._lock:
            for k, v in kwargs.items():
                setattr(self, k, v)

    def get(self, key, default=None):
        with self._lock:
            return getattr(self, key, default)

    def add_activity(self, text: str):
        with self._lock:
            self.last_activity.append(f"{datetime.now().strftime('%H:%M')} {text}")
            if len(self.last_activity) > 20:
                self.last_activity = self.last_activity[-20:]


# ─── TRAY ICON ───────────────────────────────────────────────────────────────
def create_tray(state: EchoState, event_queue: queue.Queue):
    """Create system tray icon with menu."""
    try:
        import pystray
        from PIL import Image, ImageDraw
    except ImportError:
        print("Install: pip install pystray Pillow")
        return None

    def make_icon(color):
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        colors = {
            "green": (0, 200, 0, 255),
            "yellow": (255, 200, 0, 255),
            "red": (200, 0, 0, 255),
            "gray": (100, 100, 100, 255),
        }
        draw.ellipse([8, 8, 56, 56], fill=colors.get(color, (100, 100, 100, 255)))
        return img

    def on_dashboard(icon, item):
        event_queue.put(("show_dashboard", None))

    def on_toggle(icon, item):
        event_queue.put(("toggle", None))

    def on_mode(icon, item):
        mode = str(item).lower()
        event_queue.put(("set_mode", mode))

    def on_voice(icon, item):
        event_queue.put(("toggle_voice", None))

    def on_speaker(icon, item):
        event_queue.put(("toggle_speaker", None))

    def on_stop(icon, item):
        event_queue.put(("stop", None))

    def on_exit(icon, item):
        event_queue.put(("exit", None))
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem("Echo Jarvis", None, enabled=False),
        pystray.MenuItem("Open Dashboard", on_dashboard),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Silent", on_mode),
        pystray.MenuItem("Narrator", on_mode),
        pystray.MenuItem("Friend", on_mode),
        pystray.MenuItem("Delegate", on_mode),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Voice: ON", on_voice),
        pystray.MenuItem("Speaker: ON", on_speaker),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Stop Echo", on_stop),
        pystray.MenuItem("Exit", on_exit),
    )

    icon = pystray.Icon("echo_jarvis", make_icon("gray"), "Echo Jarvis", menu)
    return icon


# ─── DASHBOARD ───────────────────────────────────────────────────────────────
def create_dashboard(state: EchoState, event_queue: queue.Queue):
    """Create floating dashboard window."""
    try:
        import customtkinter as ctk
    except ImportError:
        print("Install: pip install customtkinter")
        return None

    class Dashboard(ctk.CTk):
        def __init__(self):
            super().__init__()
            self.state = state
            self.event_queue = event_queue

            # Window setup
            self.title("Echo Jarvis")
            self.geometry("350x550")
            self.attributes("-topmost", True)
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("blue")

            # Colors
            self.COLORS = {
                "bg": "#0d1117",
                "accent": "#58a6ff",
                "green": "#3fb950",
                "yellow": "#f0883e",
                "red": "#f85149",
                "gray": "#8b949e",
            }

            self.configure(fg_color=self.COLORS["bg"])
            self._build_ui()
            self._update_loop()

        def _build_ui(self):
            # Title
            title = ctk.CTkLabel(
                self,
                text="ECHO JARVIS",
                font=("Segoe UI", 20, "bold"),
                text_color=self.COLORS["accent"],
            )
            title.pack(pady=(20, 5))

            # Status indicator
            self.status_frame = ctk.CTkFrame(self, fg_color="transparent")
            self.status_frame.pack(pady=10)

            self.status_dot = ctk.CTkLabel(
                self.status_frame,
                text="●",
                font=("Segoe UI", 48),
                text_color=self.COLORS["gray"],
            )
            self.status_dot.pack()

            self.status_text = ctk.CTkLabel(
                self.status_frame, text="OFFLINE", font=("Segoe UI", 16, "bold")
            )
            self.status_text.pack()

            # Control button
            self.control_btn = ctk.CTkButton(
                self,
                text="▶ START",
                font=("Segoe UI", 16, "bold"),
                width=200,
                height=50,
                corner_radius=25,
                command=self._toggle,
            )
            self.control_btn.pack(pady=15)

            # Mode selector
            mode_label = ctk.CTkLabel(self, text="MODE", font=("Segoe UI", 10))
            mode_label.pack(pady=(10, 0))

            self.mode_menu = ctk.CTkOptionMenu(
                self,
                values=["Silent", "Narrator", "Friend", "Delegate"],
                width=200,
                command=self._set_mode,
            )
            self.mode_menu.pack(pady=5)

            # Voice toggles
            toggle_frame = ctk.CTkFrame(self, fg_color="transparent")
            toggle_frame.pack(pady=10)

            self.voice_switch = ctk.CTkSwitch(
                toggle_frame, text="🎤 Voice Input", command=self._toggle_voice
            )
            self.voice_switch.pack(side="left", padx=10)
            if state.get("voice_input"):
                self.voice_switch.select()

            self.speaker_switch = ctk.CTkSwitch(
                toggle_frame, text="🔊 Speaker", command=self._toggle_speaker
            )
            self.speaker_switch.pack(side="left", padx=10)
            if state.get("voice_output"):
                self.speaker_switch.select()

            # Resources
            res_label = ctk.CTkLabel(
                self,
                text="─── RESOURCES ───",
                font=("Segoe UI", 10),
                text_color=self.COLORS["gray"],
            )
            res_label.pack(pady=(15, 5))

            self.gpu_label = ctk.CTkLabel(self, text="GPU: ---", font=("Consolas", 11), anchor="w")
            self.gpu_label.pack(fill="x", padx=20)

            self.ram_label = ctk.CTkLabel(self, text="RAM: ---", font=("Consolas", 11), anchor="w")
            self.ram_label.pack(fill="x", padx=20)

            self.cpu_label = ctk.CTkLabel(self, text="CPU: ---", font=("Consolas", 11), anchor="w")
            self.cpu_label.pack(fill="x", padx=20)

            # Activity log
            act_label = ctk.CTkLabel(
                self,
                text="─── ACTIVITY ───",
                font=("Segoe UI", 10),
                text_color=self.COLORS["gray"],
            )
            act_label.pack(pady=(15, 5))

            self.activity_box = ctk.CTkTextbox(self, height=100, width=310, font=("Consolas", 10))
            self.activity_box.pack(padx=20)
            self.activity_box.configure(state="disabled")

            # Minimize button
            ctk.CTkButton(self, text="Minimize to Tray", width=200, command=self.withdraw).pack(
                pady=15
            )

        def _toggle(self):
            self.event_queue.put(("toggle", None))

        def _set_mode(self, mode):
            self.event_queue.put(("set_mode", mode.lower()))

        def _toggle_voice(self):
            self.event_queue.put(("toggle_voice", None))

        def _toggle_speaker(self):
            self.event_queue.put(("toggle_speaker", None))

        def _update_loop(self):
            """Update UI from state every 500ms."""
            # Status
            if state.get("is_active"):
                if state.get("is_speaking"):
                    self.status_dot.configure(text_color=self.COLORS["yellow"])
                    self.status_text.configure(text="SPEAKING")
                    self.control_btn.configure(text="⏹ STOP", fg_color=self.COLORS["red"])
                elif state.get("is_listening"):
                    self.status_dot.configure(text_color=self.COLORS["green"])
                    self.status_text.configure(text="LISTENING")
                    self.control_btn.configure(text="⏹ STOP", fg_color=self.COLORS["red"])
                else:
                    self.status_dot.configure(text_color=self.COLORS["green"])
                    self.status_text.configure(text="ACTIVE")
                    self.control_btn.configure(text="⏹ STOP", fg_color=self.COLORS["red"])
            else:
                self.status_dot.configure(text_color=self.COLORS["gray"])
                self.status_text.configure(text="OFFLINE")
                self.control_btn.configure(text="▶ START", fg_color=self.COLORS["accent"])

            # Mode
            mode = state.get("mode", "friend").capitalize()
            self.mode_menu.set(mode)

            # Resources
            gpu_temp = state.get("gpu_temp", 0)
            gpu_vram = state.get("gpu_vram_free", 0)
            gpu_util = state.get("gpu_util", 0)
            self.gpu_label.configure(text=f"GPU: {gpu_util}% | {gpu_vram}MB free | {gpu_temp}°C")

            ram_pct = state.get("ram_used_pct", 0)
            ram_free = state.get("ram_free_gb", 0)
            self.ram_label.configure(text=f"RAM: {ram_pct}% | {ram_free}GB free")

            cpu_load = state.get("cpu_load", 0)
            self.cpu_label.configure(text=f"CPU: {cpu_load}%")

            # Activity
            activities = state.get("last_activity", [])
            self.activity_box.configure(state="normal")
            self.activity_box.delete("1.0", "end")
            for act in activities[-8:]:
                self.activity_box.insert("end", act + "\n")
            self.activity_box.configure(state="disabled")

            self.after(500, self._update_loop)

    return Dashboard()


# ─── MAIN ────────────────────────────────────────────────────────────────────
def main():
    state = EchoState()
    event_queue = queue.Queue()

    print("=" * 50)
    print("  ECHO JARVIS UI")
    print("  Starting tray icon + dashboard...")
    print("=" * 50)

    # Start tray in background thread
    tray = create_tray(state, event_queue)
    if tray:
        tray_thread = threading.Thread(target=tray.run, daemon=True)
        tray_thread.start()
        print("Tray icon started!")

    # Start dashboard
    dashboard = create_dashboard(state, event_queue)
    if dashboard:
        print("Dashboard started!")

        # Process events from queue
        def process_events():
            while True:
                try:
                    event, data = event_queue.get(timeout=0.1)
                    if event == "toggle":
                        state.update(is_active=not state.get("is_active"))
                        state.add_activity("Toggled " + ("ON" if state.get("is_active") else "OFF"))
                    elif event == "set_mode":
                        state.update(mode=data)
                        state.add_activity(f"Mode: {data}")
                    elif event == "toggle_voice":
                        state.update(voice_input=not state.get("voice_input"))
                        state.add_activity(f"Voice: {'ON' if state.get('voice_input') else 'OFF'}")
                    elif event == "toggle_speaker":
                        state.update(voice_output=not state.get("voice_output"))
                        state.add_activity(
                            f"Speaker: {'ON' if state.get('voice_output') else 'OFF'}"
                        )
                    elif event == "show_dashboard":
                        dashboard.deiconify()
                    elif event == "stop":
                        state.update(is_active=False)
                        state.add_activity("Stopped")
                    elif event == "exit":
                        dashboard.quit()
                        return
                except queue.Empty:
                    logger.debug("Event queue empty, continuing")

        event_thread = threading.Thread(target=process_events, daemon=True)
        event_thread.start()

        dashboard.mainloop()


if __name__ == "__main__":
    main()
