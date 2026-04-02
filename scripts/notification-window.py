#!/usr/bin/env python3
"""
Notification Window - Jarvis task notifications popup
Shows task completions with time taken, auto-updates from Graphiti.
"""

import json
import logging
import threading
import time
from datetime import datetime
from typing import Any

import requests

# Centralized config
from jarvis.config.graphiti_config import GRAPHITI_RPC_URL, get_timeout

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("notification-window")


class NotificationWindow:
    """Small popup window showing Jarvis task notifications."""

    def __init__(self):
        self.running = True
        self.todos: dict[str, Any] = {}
        self.recent_completed: list[dict[str, Any]] = []
        self.update_interval = 10  # seconds
        self.timeout = get_timeout()

        # Colors
        self.COLORS = {
            "bg": "#0d1117",
            "accent": "#58a6ff",
            "green": "#3fb950",
            "yellow": "#f0883e",
            "red": "#f85149",
            "gray": "#8b949e",
            "text": "#c9d1d9",
        }

    def monitor_loop(self) -> None:
        """Background thread that reads from Graphiti memory."""
        log.info("Monitor loop started (interval: %ds)", self.update_interval)
        while self.running:
            try:
                self._fetch_todos()
            except Exception as e:
                log.warning("Monitor loop error: %s", e)
            time.sleep(self.update_interval)

    def _fetch_todos(self) -> None:
        """Fetch global-todos from Graphiti memory via JSON-RPC."""
        try:
            resp = requests.post(
                GRAPHITI_RPC_URL,
                json={
                    "jsonrpc": "2.0",
                    "method": "memory_search",
                    "params": {"query": "global-todos", "limit": 1},
                    "id": 1,
                },
                timeout=self.timeout,
            )
            if resp.ok:
                data = resp.json()
                results = data.get("result", {}).get("results", [])
                if results:
                    content = results[0].get("content", "")
                    self._parse_todos(content)
            else:
                log.warning("Graphiti RPC returned %d", resp.status_code)
        except requests.ConnectionError:
            log.debug("Graphiti connection refused (service may be down)")
        except requests.Timeout:
            log.debug("Graphiti request timed out")
        except Exception as e:
            log.warning("Failed to fetch todos: %s", e)

    def _parse_todos(self, content: str) -> None:
        """Parse todo content into structured data."""
        try:
            # Try JSON parse first
            data = json.loads(content)
            if isinstance(data, dict):
                self.todos = data
                self._update_recent_completed(data)
                return
        except json.JSONDecodeError as e:
            log.debug(f"JSON parse failed, falling back to text: {e}")

        # Fallback: parse text format
        lines = content.strip().split("\n")
        pending = 0
        working = 0
        done = 0

        for line in lines:
            line = line.strip().lower()
            if "[ ]" in line or "pending" in line:
                pending += 1
            elif "[~]" in line or "working" in line or "in progress" in line:
                working += 1
            elif "[x]" in line or "done" in line or "completed" in line:
                done += 1

        self.todos = {
            "pending": pending,
            "working": working,
            "done": done,
            "total": pending + working + done,
        }

    def _update_recent_completed(self, data: dict[str, Any]) -> None:
        """Extract recently completed tasks with timestamps."""
        completed = data.get("completed", data.get("done", []))
        if isinstance(completed, list):
            self.recent_completed = completed[-5:]  # Last 5 completed
        elif isinstance(completed, int):
            # Just a count, no details
            self.recent_completed = []

    def update_display(self) -> None:
        """Update the UI with current todo state."""
        if hasattr(self, "pending_label"):
            pending = self.todos.get("pending", 0)
            working = self.todos.get("working", 0)
            done = self.todos.get("done", 0)
            total = self.todos.get("total", pending + working + done)

            self.pending_label.configure(text=f"Pending: {pending}")
            self.working_label.configure(text=f"Working: {working}")
            self.done_label.configure(text=f"Done: {done}")

            # Update progress bar
            if total > 0:
                progress = done / total
                self.progress_bar.set(progress)
                self.progress_label.configure(text=f"{done}/{total} ({progress:.0%})")
            else:
                self.progress_bar.set(0)
                self.progress_label.configure(text="No tasks")

            # Update recent completed list
            self.completed_box.configure(state="normal")
            self.completed_box.delete("1.0", "end")

            if self.recent_completed:
                for task in self.recent_completed:
                    if isinstance(task, dict):
                        name = task.get("name", task.get("task", "Unknown"))
                        time_taken = task.get("time_taken", task.get("duration", ""))
                        timestamp = task.get("timestamp", task.get("completed_at", ""))
                        line = f"✓ {name}"
                        if time_taken:
                            line += f" ({time_taken})"
                        if timestamp:
                            line += f" @ {timestamp}"
                        self.completed_box.insert("end", line + "\n")
                    else:
                        self.completed_box.insert("end", f"✓ {task}\n")
            else:
                self.completed_box.insert("end", "No recent completions\n")

            self.completed_box.configure(state="disabled")

            # Update timestamp
            self.timestamp_label.configure(text=f"Updated: {datetime.now().strftime('%H:%M:%S')}")

    def _build_ui(self) -> None:
        """Build the notification window UI."""
        try:
            import customtkinter as ctk
        except ImportError:
            log.error("customtkinter not installed. Run: pip install customtkinter")
            raise

        self.root = ctk.CTk()
        self.root.title("Jarvis Tasks")
        self.root.geometry("300x400")

        # Position on right side of screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x_pos = screen_width - 320  # 300px width + 20px margin
        y_pos = 50  # Top margin
        self.root.geometry(f"300x400+{x_pos}+{y_pos}")

        # Always on top
        self.root.attributes("-topmost", True)

        # Dark theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.root.configure(fg_color=self.COLORS["bg"])

        # Title
        title = ctk.CTkLabel(
            self.root,
            text="JARVIS TASKS",
            font=("Segoe UI", 18, "bold"),
            text_color=self.COLORS["accent"],
        )
        title.pack(pady=(15, 10))

        # Status counts frame
        status_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        status_frame.pack(pady=5, padx=20, fill="x")

        self.pending_label = ctk.CTkLabel(
            status_frame,
            text="Pending: 0",
            font=("Segoe UI", 12),
            text_color=self.COLORS["yellow"],
        )
        self.pending_label.pack(anchor="w")

        self.working_label = ctk.CTkLabel(
            status_frame,
            text="Working: 0",
            font=("Segoe UI", 12),
            text_color=self.COLORS["accent"],
        )
        self.working_label.pack(anchor="w")

        self.done_label = ctk.CTkLabel(
            status_frame,
            text="Done: 0",
            font=("Segoe UI", 12),
            text_color=self.COLORS["green"],
        )
        self.done_label.pack(anchor="w")

        # Progress bar
        progress_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        progress_frame.pack(pady=10, padx=20, fill="x")

        self.progress_label = ctk.CTkLabel(
            progress_frame,
            text="No tasks",
            font=("Segoe UI", 10),
            text_color=self.COLORS["gray"],
        )
        self.progress_label.pack(anchor="w")

        self.progress_bar = ctk.CTkProgressBar(
            progress_frame,
            width=260,
            height=12,
            corner_radius=6,
            fg_color=self.COLORS["gray"],
            progress_color=self.COLORS["green"],
        )
        self.progress_bar.pack(pady=(5, 0))
        self.progress_bar.set(0)

        # Recent completed section
        completed_label = ctk.CTkLabel(
            self.root,
            text="─── RECENT COMPLETED ───",
            font=("Segoe UI", 10),
            text_color=self.COLORS["gray"],
        )
        completed_label.pack(pady=(15, 5))

        self.completed_box = ctk.CTkTextbox(
            self.root,
            height=150,
            width=260,
            font=("Consolas", 10),
            fg_color="#161b22",
            text_color=self.COLORS["text"],
        )
        self.completed_box.pack(padx=20)
        self.completed_box.configure(state="disabled")

        # Timestamp
        self.timestamp_label = ctk.CTkLabel(
            self.root,
            text="Updated: --:--:--",
            font=("Segoe UI", 9),
            text_color=self.COLORS["gray"],
        )
        self.timestamp_label.pack(pady=(10, 15))

    def _start_update_loop(self) -> None:
        """Start the UI update loop (runs on main thread)."""
        self.update_display()
        self.root.after(self.update_interval * 1000, self._start_update_loop)

    def run(self) -> None:
        """Start the notification window."""
        log.info("Starting Notification Window...")

        # Build UI
        self._build_ui()

        # Start monitor thread
        monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        monitor_thread.start()
        log.info("Monitor thread started")

        # Start UI update loop
        self._start_update_loop()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        log.info("Notification Window ready")
        self.root.mainloop()

    def _on_close(self) -> None:
        """Handle window close event."""
        self.running = False
        self.root.destroy()


if __name__ == "__main__":
    window = NotificationWindow()
    window.run()
