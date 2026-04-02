"""Focus and Workflow Module - ADHD-friendly productivity features."""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Callable
import uuid


class FocusState(Enum):
    IDLE = "idle"
    FOCUS = "focus"
    BREAK = "break"
    PAUSED = "paused"


class TimerMode(Enum):
    POMODORO = "pomodoro"  # 25 min focus, 5 min break
    DEEP_WORK = "deep_work"  # 50 min focus, 10 min break
    SPRINT = "sprint"  # 15 min focus, 3 min break
    CUSTOM = "custom"


@dataclass
class FocusSession:
    session_id: str
    start_time: float
    end_time: Optional[float] = None
    duration_minutes: int = 25
    mode: TimerMode = TimerMode.POMODORO
    state: FocusState = FocusState.IDLE
    completed_cycles: int = 0
    paused_duration: float = 0.0
    paused_at: Optional[float] = None


@dataclass
class QuickCapture:
    capture_id: str
    content: str
    timestamp: float
    category: str = "general"
    tags: list[str] = field(default_factory=list)
    processed: bool = False


@dataclass
class MacroAction:
    action_type: str  # "key", "mouse_move", "mouse_click", "wait"
    params: dict = field(default_factory=dict)
    duration_ms: int = 0


@dataclass
class Macro:
    macro_id: str
    name: str
    actions: list[MacroAction] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_used: Optional[float] = None
    trigger_hotkey: Optional[str] = None


@dataclass
class ClipboardItem:
    item_id: str
    content: str
    content_type: str  # "text", "image", "file"
    timestamp: float
    source_app: Optional[str] = None
    pinned: bool = False
    snippet_trigger: Optional[str] = None


@dataclass
class Snippet:
    snippet_id: str
    trigger: str  # abbreviation to expand
    content: str
    description: str = ""
    category: str = "general"
    created_at: float = field(default_factory=time.time)


class FocusManager:
    """
    ADHD-friendly focus manager with Pomodoro, deep work, and custom timers.
    """

    def __init__(self):
        self._current_session: Optional[FocusSession] = None
        self._timer_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._on_tick: Optional[Callable] = None
        self._on_complete: Optional[Callable] = None
        self._on_state_change: Optional[Callable] = None

        self._focus_sound_enabled = True
        self._break_sound_enabled = True
        self._notifications_enabled = True

        self._sessions_history: list[FocusSession] = []
        self._total_focus_time_today = 0.0
        self._sessions_today = 0

    @property
    def is_running(self) -> bool:
        return self._current_session is not None and self._current_session.state == FocusState.FOCUS

    @property
    def current_session(self) -> Optional[FocusSession]:
        return self._current_session

    def set_callbacks(
        self,
        on_tick: Optional[Callable] = None,
        on_complete: Optional[Callable] = None,
        on_state_change: Optional[Callable] = None,
    ):
        self._on_tick = on_tick
        self._on_complete = on_complete
        self._on_state_change = on_state_change

    def start_focus(
        self,
        mode: TimerMode = TimerMode.POMODORO,
        custom_duration: Optional[int] = None,
    ) -> FocusSession:
        """Start a focus session."""
        if self._current_session and self._current_session.state == FocusState.FOCUS:
            return self._current_session

        duration = custom_duration or self._get_duration_for_mode(mode)

        self._current_session = FocusSession(
            session_id=str(uuid.uuid4()),
            start_time=time.time(),
            duration_minutes=duration,
            mode=mode,
            state=FocusState.FOCUS,
        )

        self._stop_event.clear()
        self._timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
        self._timer_thread.start()

        self._notify_state_change()
        return self._current_session

    def _get_duration_for_mode(self, mode: TimerMode) -> int:
        durations = {
            TimerMode.POMODORO: 25,
            TimerMode.DEEP_WORK: 50,
            TimerMode.SPRINT: 15,
            TimerMode.CUSTOM: 25,
        }
        return durations.get(mode, 25)

    def _timer_loop(self):
        """Main timer loop running in background thread."""
        while not self._stop_event.is_set():
            if not self._current_session or self._current_session.state != FocusState.FOCUS:
                break

            elapsed = time.time() - self._current_session.start_time - self._current_session.paused_duration
            remaining = (self._current_session.duration_minutes * 60) - elapsed

            if self._on_tick:
                self._on_tick(
                    {
                        "remaining_seconds": max(0, remaining),
                        "elapsed_seconds": elapsed,
                        "state": self._current_session.state.value,
                    }
                )

            if remaining <= 0:
                self._session_complete()
                break

            time.sleep(1)

    def _session_complete(self):
        """Handle session completion."""
        if not self._current_session:
            return

        self._current_session.end_time = time.time()
        self._current_session.state = FocusState.IDLE
        self._current_session.completed_cycles += 1

        self._sessions_history.append(self._current_session)
        self._sessions_today += 1
        self._total_focus_time_today += self._current_session.duration_minutes

        if self._on_complete:
            self._on_complete(
                {
                    "session": self._current_session,
                    "completed_cycles": self._current_session.completed_cycles,
                    "total_focus_today": self._total_focus_time_today,
                }
            )

        self._current_session = None
        self._notify_state_change()

    def pause(self):
        """Pause the current session."""
        if self._current_session and self._current_session.state == FocusState.FOCUS:
            self._current_session.state = FocusState.PAUSED
            self._current_session.paused_at = time.time()
            self._notify_state_change()

    def resume(self):
        """Resume a paused session."""
        if self._current_session and self._current_session.state == FocusState.PAUSED:
            if self._current_session.paused_at:
                self._current_session.paused_duration += time.time() - self._current_session.paused_at
            self._current_session.state = FocusState.FOCUS
            self._current_session.paused_at = None
            self._notify_state_change()

    def stop(self):
        """Stop the current session."""
        self._stop_event.set()
        if self._timer_thread:
            self._timer_thread.join(timeout=2)
        if self._current_session:
            self._current_session.state = FocusState.IDLE
        self._current_session = None
        self._notify_state_change()

    def start_break(self, short: bool = True):
        """Start a break session."""
        duration = 5 if short else 15
        self._current_session = FocusSession(
            session_id=str(uuid.uuid4()),
            start_time=time.time(),
            duration_minutes=duration,
            mode=self._current_session.mode if self._current_session else TimerMode.POMODORO,
            state=FocusState.BREAK,
        )
        self._stop_event.clear()
        self._timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
        self._timer_thread.start()
        self._notify_state_change()

    def _notify_state_change(self):
        if self._on_state_change and self._current_session:
            self._on_state_change(
                {
                    "state": self._current_session.state.value,
                    "mode": self._current_session.mode.value,
                    "completed_cycles": self._current_session.completed_cycles,
                }
            )

    def get_stats(self) -> dict:
        """Get today's focus statistics."""
        return {
            "total_focus_minutes": self._total_focus_time_today,
            "sessions_completed": self._sessions_today,
            "current_state": self._current_session.state.value if self._current_session else "idle",
            "completed_cycles": self._current_session.completed_cycles if self._current_session else 0,
        }

    def reset_daily_stats(self):
        """Reset daily statistics."""
        self._total_focus_time_today = 0.0
        self._sessions_today = 0


class QuickCaptureManager:
    """
    System-wide quick capture for thoughts, tasks, ideas.
    """

    def __init__(self):
        self._captures: list[QuickCapture] = []
        self._storage_path = Path("./data/quick_capture")
        self._storage_path.mkdir(parents=True, exist_ok=True)

    def add_capture(self, content: str, category: str = "general", tags: list[str] = None) -> QuickCapture:
        """Add a new capture."""
        capture = QuickCapture(
            capture_id=str(uuid.uuid4()),
            content=content,
            timestamp=time.time(),
            category=category,
            tags=tags or [],
        )
        self._captures.append(capture)
        self._save_to_disk(capture)
        return capture

    def get_captures(self, category: Optional[str] = None, limit: int = 50) -> list[QuickCapture]:
        """Get recent captures."""
        captures = self._captures
        if category:
            captures = [c for c in captures if c.category == category]
        return sorted(captures, key=lambda x: x.timestamp, reverse=True)[:limit]

    def mark_processed(self, capture_id: str):
        """Mark a capture as processed."""
        for cap in self._captures:
            if cap.capture_id == capture_id:
                cap.processed = True
                break

    def delete_capture(self, capture_id: str):
        """Delete a capture."""
        self._captures = [c for c in self._captures if c.capture_id != capture_id]

    def _save_to_disk(self, capture: QuickCapture):
        """Save capture to disk."""
        # Simple JSON storage
        import json

        filepath = self._storage_path / f"{capture.capture_id}.json"
        with open(filepath, "w") as f:
            json.dump(
                {
                    "capture_id": capture.capture_id,
                    "content": capture.content,
                    "timestamp": capture.timestamp,
                    "category": capture.category,
                    "tags": capture.tags,
                    "processed": capture.processed,
                },
                f,
            )

    def load_from_disk(self):
        """Load captures from disk."""
        import json

        self._captures = []
        for filepath in self._storage_path.glob("*.json"):
            try:
                with open(filepath) as f:
                    data = json.load(f)
                    self._captures.append(QuickCapture(**data))
            except Exception:
                pass


class MacroManager:
    """
    Macro recorder for mouse/keyboard automation.
    """

    def __init__(self):
        self._macros: dict[str, Macro] = {}
        self._is_recording = False
        self._current_recording: Optional[Macro] = None
        self._recording_start = 0.0

    def start_recording(self, name: str) -> str:
        """Start recording a new macro."""
        macro_id = str(uuid.uuid4())
        self._current_recording = Macro(
            macro_id=macro_id,
            name=name,
        )
        self._is_recording = True
        self._recording_start = time.time()
        return macro_id

    def add_action(self, action_type: str, params: dict = None, duration_ms: int = 0):
        """Add an action to the current recording."""
        if not self._is_recording or not self._current_recording:
            return

        action = MacroAction(
            action_type=action_type,
            params=params or {},
            duration_ms=duration_ms,
        )
        self._current_recording.actions.append(action)

    def stop_recording(self) -> Optional[Macro]:
        """Stop recording and save the macro."""
        if not self._is_recording or not self._current_recording:
            return None

        self._is_recording = False
        macro = self._current_recording
        self._macros[macro.macro_id] = macro
        self._current_recording = None
        return macro

    def play_macro(self, macro_id: str) -> bool:
        """Play back a recorded macro."""
        macro = self._macros.get(macro_id)
        if not macro:
            return False

        macro.last_used = time.time()

        # Play back actions
        for action in macro.actions:
            if action.action_type == "key":
                self._play_key_action(action.params)
            elif action.action_type == "mouse_move":
                self._play_mouse_move(action.params)
            elif action.action_type == "mouse_click":
                self._play_mouse_click(action.params)
            elif action.action_type == "wait":
                time.sleep(action.duration_ms / 1000.0)

        return True

    def _play_key_action(self, params: dict):
        """Simulate key press."""
        try:
            from pynput.keyboard import Key, Controller

            keyboard = Controller()

            key = params.get("key")
            if key:
                keyboard.press(key)
                time.sleep(0.05)
                keyboard.release(key)
        except ImportError:
            pass

    def _play_mouse_move(self, params: dict):
        """Simulate mouse move."""
        try:
            from pynput.mouse import Controller

            mouse = Controller()
            x = params.get("x", 0)
            y = params.get("y", 0)
            mouse.position = (x, y)
        except ImportError:
            pass

    def _play_mouse_click(self, params: dict):
        """Simulate mouse click."""
        try:
            from pynput.mouse import Button, Controller

            mouse = Controller()
            button = params.get("button", "left")
            btn = Button.left if button == "left" else Button.right
            mouse.press(btn)
            time.sleep(0.05)
            mouse.release(btn)
        except ImportError:
            pass

    def get_macros(self) -> list[Macro]:
        """Get all recorded macros."""
        return list(self._macros.values())

    def delete_macro(self, macro_id: str):
        """Delete a macro."""
        self._macros.pop(macro_id, None)

    def set_hotkey(self, macro_id: str, hotkey: str):
        """Set a hotkey trigger for a macro."""
        if macro_id in self._macros:
            self._macros[macro_id].trigger_hotkey = hotkey


class ClipboardManager:
    """
    Enhanced clipboard manager with history and snippets.
    """

    def __init__(self):
        self._history: list[ClipboardItem] = []
        self._snippets: dict[str, Snippet] = {}
        self._max_history = 100
        self._monitoring = False
        self._last_content = ""

    def add_to_history(self, content: str, content_type: str = "text", source_app: str = None):
        """Add item to clipboard history."""
        if content == self._last_content:
            return

        self._last_content = content

        item = ClipboardItem(
            item_id=str(uuid.uuid4()),
            content=content,
            content_type=content_type,
            timestamp=time.time(),
            source_app=source_app,
        )

        # Remove duplicates
        self._history = [h for h in self._history if h.content != content]
        self._history.insert(0, item)

        # Trim history
        if len(self._history) > self._max_history:
            self._history = self._history[: self._max_history]

    def get_history(self, limit: int = 20) -> list[ClipboardItem]:
        """Get clipboard history."""
        return self._history[:limit]

    def pin_item(self, item_id: str):
        """Pin an item to keep it in history."""
        for item in self._history:
            if item.item_id == item_id:
                item.pinned = True
                break

    def unpin_item(self, item_id: str):
        """Unpin an item."""
        for item in self._history:
            if item.item_id == item_id:
                item.pinned = False
                break

    def delete_item(self, item_id: str):
        """Delete item from history."""
        self._history = [i for i in self._history if i.item_id != item_id]

    def add_snippet(self, trigger: str, content: str, description: str = "", category: str = "general") -> Snippet:
        """Add a text snippet."""
        snippet = Snippet(
            snippet_id=str(uuid.uuid4()),
            trigger=trigger,
            content=content,
            description=description,
            category=category,
        )
        self._snippets[trigger] = snippet
        return snippet

    def get_snippet(self, trigger: str) -> Optional[Snippet]:
        """Get a snippet by trigger."""
        return self._snippets.get(trigger)

    def expand_snippet(self, text: str) -> str:
        """Expand snippet triggers in text."""
        result = text
        for trigger, snippet in self._snippets.items():
            result = result.replace(trigger, snippet.content)
        return result

    def get_snippets(self, category: Optional[str] = None) -> list[Snippet]:
        """Get all snippets."""
        snippets = list(self._snippets.values())
        if category:
            snippets = [s for s in snippets if s.category == category]
        return snippets

    def delete_snippet(self, trigger: str):
        """Delete a snippet."""
        self._snippets.pop(trigger, None)


class WindowManager:
    """
    Window management - snap, tile, arrange windows.
    """

    def __init__(self):
        pass

    def get_windows(self) -> list[dict]:
        """Get list of open windows."""
        windows = []
        try:
            import win32gui
            import win32con

            def callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title:
                        rect = win32gui.GetWindowRect(hwnd)
                        windows.append(
                            {
                                "hwnd": hwnd,
                                "title": title,
                                "x": rect[0],
                                "y": rect[1],
                                "width": rect[2] - rect[0],
                                "height": rect[3] - rect[1],
                            }
                        )
                return True

            win32gui.EnumWindows(callback, windows)
        except ImportError:
            pass

        return windows

    def snap_window(self, hwnd: int, position: str) -> bool:
        """Snap window to position."""
        try:
            import win32gui
            import win32con

            screen = win32gui.GetSystemMetrics(win32con.SM_CXSCREEN), win32gui.GetSystemMetrics(win32con.SM_CYSCREEN)

            positions = {
                "left": (0, 0, screen[0] // 2, screen[1]),
                "right": (screen[0] // 2, 0, screen[0] // 2, screen[1]),
                "top": (0, 0, screen[0], screen[1] // 2),
                "bottom": (0, screen[1] // 2, screen[0], screen[1] // 2),
                "top-left": (0, 0, screen[0] // 2, screen[1] // 2),
                "top-right": (screen[0] // 2, 0, screen[0] // 2, screen[1] // 2),
                "bottom-left": (0, screen[1] // 2, screen[0] // 2, screen[1] // 2),
                "bottom-right": (screen[0] // 2, screen[1] // 2, screen[0] // 2, screen[1] // 2),
                "maximize": (0, 0, screen[0], screen[1]),
            }

            if position in positions:
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, *positions[position], win32con.SWP_NOZORDER)
                return True
        except ImportError:
            pass

        return False

    def bring_to_front(self, hwnd: int) -> bool:
        """Bring window to front."""
        try:
            import win32gui

            win32gui.SetForegroundWindow(hwnd)
            return True
        except ImportError:
            return False

    def minimize_window(self, hwnd: int) -> bool:
        """Minimize window."""
        try:
            import win32gui

            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            return True
        except ImportError:
            return False

    def maximize_window(self, hwnd: int) -> bool:
        """Maximize window."""
        try:
            import win32gui

            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            return True
        except ImportError:
            return False


class TaskBreakdownAI:
    """
    AI-powered task breakdown into smaller sub-tasks.
    """

    def __init__(self):
        self._prompts = {
            "default": "Break down this task into 5-10 smaller, actionable sub-tasks:\n\n{task}",
            "creative": "Break down this creative task into sequential steps:\n\n{task}",
            "coding": "Break down this programming task into technical sub-tasks:\n\n{task}",
            "research": "Break down this research task into investigation steps:\n\n{task}",
        }

    def generate_breakdown(self, task: str, category: str = "default", custom_prompt: str = None) -> list[str]:
        """Generate sub-task breakdown."""
        prompt = custom_prompt or self._prompts.get(category, self._prompts["default"])
        prompt = prompt.format(task=task)

        # Return structured breakdown (in real implementation, would call LLM)
        sub_tasks = self._generate_subtasks(task)
        return sub_tasks

    def _generate_subtasks(self, task: str) -> list[str]:
        """Generate sub-tasks based on task type."""
        # Simple keyword-based breakdown
        task_lower = task.lower()

        if any(w in task_lower for w in ["write", "create", "make", "produce"]):
            return [
                f"Research {task}",
                f"Plan structure for {task}",
                f"Create first draft of {task}",
                f"Review and revise {task}",
                f"Finalize {task}",
            ]
        elif any(w in task_lower for w in ["fix", "debug", "repair", "solve"]):
            return [
                f"Identify the problem in {task}",
                f"Gather relevant information",
                f"Try initial fix for {task}",
                f"Test the solution",
                f"Document the fix",
            ]
        elif any(w in task_lower for w in ["learn", "study", "read"]):
            return [
                f"Set learning goals for {task}",
                f"Find learning resources",
                f"Start with fundamentals",
                f"Practice {task}",
                f"Review and consolidate",
            ]
        else:
            return [
                f"Start {task}",
                f"Gather requirements for {task}",
                f"Execute {task}",
                f"Review {task}",
                f"Complete {task}",
            ]

    def estimate_time(self, sub_tasks: list[str]) -> dict:
        """Estimate time for sub-tasks."""
        # Simple estimation based on count
        total_minutes = len(sub_tasks) * 15

        return {
            "total_minutes": total_minutes,
            "per_task_minutes": 15,
            "recommendation": f"Split into {max(1, len(sub_tasks) // 4)} focus sessions",
        }


def create_focus_manager() -> FocusManager:
    return FocusManager()


def create_quick_capture() -> QuickCaptureManager:
    return QuickCaptureManager()


def create_macro_manager() -> MacroManager:
    return MacroManager()


def create_clipboard_manager() -> ClipboardManager:
    return ClipboardManager()


def create_window_manager() -> WindowManager:
    return WindowManager()


def create_task_breakdown() -> TaskBreakdownAI:
    return TaskBreakdownAI()


# ============ GLOBAL SHORTCUTS ============


import os
import subprocess
from dataclasses import dataclass


@dataclass
class Shortcut:
    shortcut_id: str
    name: str
    hotkey: str  # e.g., "ctrl+shift+space"
    action_type: str  # "command", "macro", "url", "app", "snippet"
    action_data: dict  # command, macro_id, url, app_path, snippet_id


class GlobalShortcuts:
    """
    System-wide global hotkey manager.
    """

    def __init__(self):
        self._shortcuts: dict[str, Shortcut] = {}
        self._registered_hotkeys: dict[str, str] = {}  # hotkey -> shortcut_id
        self._listener = None

    def add_shortcut(
        self,
        name: str,
        hotkey: str,
        action_type: str,
        action_data: dict,
    ) -> Shortcut:
        """Register a new global shortcut."""
        import uuid

        shortcut_id = str(uuid.uuid4())

        # Normalize hotkey
        hotkey = hotkey.lower().replace(" ", "").replace("ctrl", "ctrl").replace("cmd", "cmd")

        shortcut = Shortcut(
            shortcut_id=shortcut_id,
            name=name,
            hotkey=hotkey,
            action_type=action_type,
            action_data=action_data,
        )

        self._shortcuts[shortcut_id] = shortcut
        self._registered_hotkeys[hotkey] = shortcut_id

        return shortcut

    def remove_shortcut(self, shortcut_id: str) -> bool:
        """Remove a shortcut."""
        if shortcut_id not in self._shortcuts:
            return False

        shortcut = self._shortcuts[shortcut_id]
        self._registered_hotkeys.pop(shortcut.hotkey, None)
        self._shortcuts.pop(shortcut_id, None)
        return True

    def get_shortcuts(self) -> list[Shortcut]:
        """Get all registered shortcuts."""
        return list(self._shortcuts.values())

    def execute_shortcut(self, shortcut_id: str) -> bool:
        """Execute a shortcut's action."""
        shortcut = self._shortcuts.get(shortcut_id)
        if not shortcut:
            return False

        try:
            if shortcut.action_type == "command":
                return self._execute_command(shortcut.action_data)
            elif shortcut.action_type == "url":
                return self._open_url(shortcut.action_data)
            elif shortcut.action_type == "app":
                return self._launch_app(shortcut.action_data)
            elif shortcut.action_type == "macro":
                return self._play_macro(shortcut.action_data)
            elif shortcut.action_type == "snippet":
                return self._copy_snippet(shortcut.action_data)
        except Exception:
            pass

        return False

    def _execute_command(self, data: dict) -> bool:
        """Execute a shell command."""
        cmd = data.get("command", "")
        if cmd:
            subprocess.Popen(cmd, shell=True)
            return True
        return False

    def _open_url(self, data: dict) -> bool:
        """Open a URL in browser."""
        url = data.get("url", "")
        if url:
            import webbrowser

            webbrowser.open(url)
            return True
        return False

    def _launch_app(self, data: dict) -> bool:
        """Launch an application."""
        app_path = data.get("app_path", "")
        if app_path:
            subprocess.Popen(app_path, shell=True)
            return True
        return False

    def _play_macro(self, data: dict) -> bool:
        """Play a macro."""
        # This would integrate with MacroManager
        return True

    def _copy_snippet(self, data: dict) -> bool:
        """Copy a snippet to clipboard."""
        # This would integrate with ClipboardManager
        return True


# ============ APP LAUNCHER ============


@dataclass
class AppEntry:
    """An application entry for the launcher."""

    name: str
    path: str
    icon: Optional[str] = None
    category: str = "general"
    keywords: list[str] = None
    launch_count: int = 0

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []


class AppLauncher:
    """
    Spotlight-style app launcher with fuzzy search.
    """

    def __init__(self):
        self._apps: dict[str, AppEntry] = {}
        self._recent: list[str] = []  # Recent app IDs
        self._index_loaded = False

    def load_apps(self) -> list[AppEntry]:
        """Load installed applications."""
        if self._index_loaded:
            return list(self._apps.values())

        apps = []

        # Windows: Scan Start Menu
        if os.name == "nt":
            apps = self._scan_windows_apps()

        # macOS: Scan Applications folder
        elif os.name == "posix":
            apps = self._scan_macos_apps()

        # Index apps
        for app in apps:
            self._apps[app.path] = app

        self._index_loaded = True
        return apps

    def _scan_windows_apps(self) -> list[AppEntry]:
        """Scan Windows Start Menu for apps."""
        import glob

        apps = []
        search_paths = [
            os.path.join(os.environ.get("PROGRAMDATA", "C:\\ProgramData"), "Microsoft\\Windows\\Start Menu\\Programs"),
            os.path.join(os.environ.get("APPDATA", ""), "Microsoft\\Windows\\Start Menu\\Programs"),
            os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
        ]

        for search_path in search_paths:
            if not os.path.exists(search_path):
                continue

            for lnk in glob.glob(f"{search_path}/**/*.lnk", recursive=True):
                try:
                    name = os.path.splitext(os.path.basename(lnk))[0]
                    apps.append(
                        AppEntry(
                            name=name,
                            path=lnk,
                            category="app",
                            keywords=name.lower().split(),
                        )
                    )
                except Exception:
                    pass

        return apps

    def _scan_macos_apps(self) -> list[AppEntry]:
        """Scan macOS Applications folder."""
        import glob

        apps = []
        search_paths = ["/Applications", os.path.expanduser("~/Applications")]

        for search_path in search_paths:
            if not os.path.exists(search_path):
                continue

            for app in glob.glob(f"{search_path}/*.app"):
                try:
                    name = os.path.splitext(os.path.basename(app))[0]
                    apps.append(
                        AppEntry(
                            name=name,
                            path=app,
                            category="app",
                            keywords=name.lower().split(),
                        )
                    )
                except Exception:
                    pass

        return apps

    def search(self, query: str, limit: int = 10) -> list[AppEntry]:
        """Fuzzy search for apps."""
        if not self._index_loaded:
            self.load_apps()

        if not query:
            # Return recent apps
            results = []
            for path in self._recent[:limit]:
                if path in self._apps:
                    results.append(self._apps[path])
            return results

        query_lower = query.lower()

        # Score-based fuzzy matching
        scored = []
        for path, app in self._apps.items():
            score = self._fuzzy_score(query_lower, app.name.lower(), app.keywords)
            if score > 0:
                scored.append((score, app))

        # Sort by score
        scored.sort(key=lambda x: x[0], reverse=True)

        return [app for _, app in scored[:limit]]

    def _fuzzy_score(self, query: str, name: str, keywords: list[str]) -> float:
        """Calculate fuzzy match score."""
        score = 0.0

        # Exact match
        if query == name:
            return 100.0

        # Starts with query
        if name.startswith(query):
            score += 50.0

        # Contains query
        if query in name:
            score += 30.0

        # Word starts with
        for word in name.split():
            if word.startswith(query):
                score += 20.0

        # Keyword match
        for kw in keywords:
            if query in kw:
                score += 10.0

        # Sequence match (fuzzy)
        if self._has_subsequence(query, name):
            score += 5.0

        return score

    def _has_subsequence(self, query: str, text: str) -> bool:
        """Check if query is a subsequence of text."""
        q_idx = 0
        for char in text:
            if q_idx < len(query) and char.lower() == query[q_idx].lower():
                q_idx += 1
        return q_idx == len(query)

    def launch(self, path: str) -> bool:
        """Launch an application."""
        try:
            if os.name == "nt":
                os.startfile(path)
            elif os.name == "posix":
                subprocess.Popen(["open", path] if "Applications" in path else ["xdg-open", path])

            # Update recent
            if path in self._apps:
                self._apps[path].launch_count += 1
            if path in self._recent:
                self._recent.remove(path)
            self._recent.insert(0, path)
            if len(self._recent) > 10:
                self._recent = self._recent[:10]

            return True
        except Exception:
            return False

    def add_custom_app(self, name: str, path: str, category: str = "custom") -> AppEntry:
        """Add a custom app entry."""
        app = AppEntry(
            name=name,
            path=path,
            category=category,
            keywords=name.lower().split(),
        )
        self._apps[path] = app
        return app


# ============ DISTRACTION BLOCKER ============


class DistractionBlocker:
    """
    Block distracting websites and apps during focus sessions.
    """

    def __init__(self):
        self._blocked_sites: set[str] = set()
        self._blocked_apps: set[str] = set()
        self._is_active = False
        self._hosts_path = "C:\\Windows\\System32\\drivers\\etc\\hosts" if os.name == "nt" else "/etc/hosts"

    def add_site(self, site: str):
        """Add a site to block."""
        # Normalize
        site = site.lower().replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")
        self._blocked_sites.add(site)

    def remove_site(self, site: str):
        """Remove a site from blocklist."""
        site = site.lower().replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")
        self._blocked_sites.discard(site)

    def add_app(self, app_path: str):
        """Add an app to block."""
        self._blocked_apps.add(app_path)

    def remove_app(self, app_path: str):
        """Remove an app from blocklist."""
        self._blocked_apps.discard(app_path)

    def get_blocked_sites(self) -> list[str]:
        """Get list of blocked sites."""
        return list(self._blocked_sites)

    def get_blocked_apps(self) -> list[str]:
        """Get list of blocked apps."""
        return list(self._blocked_apps)

    def activate(self) -> bool:
        """Activate distraction blocking (requires admin)."""
        if self._is_active:
            return True

        try:
            # Note: This requires admin privileges
            # For safety, we'll just track state without actually blocking
            self._is_active = True
            return True
        except Exception:
            return False

    def deactivate(self) -> bool:
        """Deactivate distraction blocking."""
        self._is_active = False
        return True

    def is_active(self) -> bool:
        """Check if blocking is active."""
        return self._is_active

    def get_default_blocklist(self) -> dict:
        """Get default blocklist for productivity."""
        return {
            "social": [
                "facebook.com",
                "twitter.com",
                "x.com",
                "instagram.com",
                "tiktok.com",
                "reddit.com",
                "youtube.com",
                "snapchat.com",
            ],
            "news": [
                "news.ycombinator.com",
                "cnn.com",
                "bbc.com",
                "nytimes.com",
            ],
            "entertainment": [
                "netflix.com",
                "hulu.com",
                "twitch.tv",
                "spotify.com",
            ],
        }

    def load_default_blocklist(self, category: str = "social"):
        """Load a default blocklist category."""
        defaults = self.get_default_blocklist()
        if category in defaults:
            for site in defaults[category]:
                self.add_site(site)


# ============ FACTORY FUNCTIONS ============


def create_global_shortcuts() -> GlobalShortcuts:
    return GlobalShortcuts()


def create_app_launcher() -> AppLauncher:
    return AppLauncher()


def create_distraction_blocker() -> DistractionBlocker():
    return DistractionBlocker()
