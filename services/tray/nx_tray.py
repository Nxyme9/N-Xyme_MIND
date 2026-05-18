#!/usr/bin/env python3
"""
nx_tray.py — N-Xyme MIND System Tray Application.

Single self-contained PyQt6 system tray app that monitors:
  • nx-dictate mic status (via FIFO + systemd)
  • Jarvis bridge status
  • llama-server health & VRAM
  • Memory vector count
  • GPU stats (nvidia-smi)

Features:
  • Dynamic mic icon (idle/recording/processing)
  • Right-click menu with submenus for status, logs, quick actions
  • 5-second polling loop via QTimer
  • Systemd service control (start/stop/restart)
  • FIFO communication for dictation injection

Usage:
  python3 nx_tray.py                          # foreground (debug)
  python3 nx_tray.py --daemon                 # background
  bash run_tray.sh                            # launch via script
"""

from __future__ import annotations

import json
import logging
import math
import os
import subprocess
import sys
import time
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple

# ── Constants ─────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FIFO_PATH = "/tmp/jarvis_fifo"
STATE_FILE = "/tmp/nx_dictate_state.json"
SESSIONS_FILE = PROJECT_ROOT / "data" / "memory" / "vectors" / "sessions.jsonl"
POLL_INTERVAL_MS = 5000  # 5 seconds

SERVICE_NAMES = {
    "dictate": "nx-dictate.service",
    "jarvis": "jarvis-bridge.service",
    "memory": "nx-memory-watcher.service",
    "guardian": "nx-guardian.service",
}

# ── Logging ───────────────────────────────────────────────────────────────

LOG_DIR = PROJECT_ROOT / "data" / "memory" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

log_file = LOG_DIR / "nx_tray.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [TRAY] %(message)s",
    handlers=[
        logging.FileHandler(str(log_file)),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("nx_tray")

# ── Dictation State (standalone copy — no nx_dictate dependency) ──────────


class DictateState(str, Enum):
    """Mirrors nx_dictate.core.state.State but keeps app self-contained."""
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"
    STOPPED = "stopped"  # service not running
    ERROR = "error"

    @classmethod
    def from_service(cls, active: bool) -> "DictateState":
        return cls.IDLE if active else cls.STOPPED


STATE_COLORS = {
    DictateState.IDLE: (140, 140, 140),        # gray
    DictateState.RECORDING: (255, 60, 60),     # red
    DictateState.PROCESSING: (255, 170, 40),   # amber
    DictateState.STOPPED: (80, 80, 80),        # dark gray
    DictateState.ERROR: (255, 40, 40),         # red
}

STATE_LABELS = {
    DictateState.IDLE: "🎤 Idle — listening",
    DictateState.RECORDING: "🔴 Recording…",
    DictateState.PROCESSING: "⏳ Processing…",
    DictateState.STOPPED: "⏹ Stopped",
    DictateState.ERROR: "⚠️ Error",
}


# ── Icon Drawing (adapted from nx_dictate/ui/tray.py) ──────────────────

def _draw_mic_icon(
    color: Tuple[int, int, int],
    size: int = 64,
    state: DictateState = DictateState.IDLE,
) -> "QIcon":
    """Draw a proper microphone icon using QPainter.

    Mic body + mic stand + optional recording rings / processing arcs.
    """
    from PyQt6.QtGui import QPixmap, QPainter, QColor, QIcon, QBrush, QPen
    from PyQt6.QtCore import Qt, QPointF

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    cx, cy = size // 2, size // 2
    scale = size / 64.0

    # Background circle (subtle)
    bg_color = QColor(*color)
    bg_color.setAlpha(30)
    p.setBrush(QBrush(bg_color))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QPointF(cx, cy), 28 * scale, 28 * scale)

    # Mic body dimensions
    body_w = 14 * scale
    body_h = 22 * scale
    body_x = cx - body_w / 2
    body_y = cy - body_h / 2 - 4 * scale
    mic_color = QColor(*color)

    if state == DictateState.RECORDING:
        # Pulsing red — draw concentric rings
        p.setPen(QPen(mic_color, 2 * scale))
        p.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(3):
            r = (30 + i * 6) * scale
            ring_color = QColor(*color)
            ring_color.setAlpha(max(30, 100 - i * 30))
            p.setPen(QPen(ring_color, 1.5 * scale))
            p.drawEllipse(QPointF(cx, cy), r, r)
        p.setBrush(QBrush(mic_color))
        p.setPen(Qt.PenStyle.NoPen)

    elif state == DictateState.PROCESSING:
        # Spinning wedge — draw arc segments
        p.setPen(QPen(mic_color, 2 * scale))
        p.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(4):
            start_angle = i * 90 * 16
            span_angle = 45 * 16
            arc_color = QColor(*color)
            arc_color.setAlpha(max(50, 255 - i * 50))
            p.setPen(QPen(arc_color, 2 * scale))
            p.drawArc(
                int(cx - 24 * scale), int(cy - 24 * scale),
                int(48 * scale), int(48 * scale),
                start_angle, span_angle,
            )
        p.setBrush(QBrush(mic_color))
        p.setPen(Qt.PenStyle.NoPen)

    else:
        # Idle / stopped / error — solid fill
        p.setBrush(QBrush(mic_color))
        p.setPen(Qt.PenStyle.NoPen)

    # Mic capsule (rounded rect)
    p.drawRoundedRect(
        int(body_x), int(body_y),
        int(body_w), int(body_h),
        int(7 * scale), int(7 * scale),
    )

    # Mic stand (line going down)
    stand_y = body_y + body_h
    p.setPen(QPen(mic_color, 2.5 * scale))
    p.drawLine(QPointF(cx, stand_y), QPointF(cx, stand_y + 10 * scale))

    # Mic base (arc)
    base_w = 18 * scale
    p.drawArc(
        int(cx - base_w / 2), int(stand_y + 6 * scale),
        int(base_w), int(8 * scale),
        0, 180 * 16,
    )

    # Red recording dot for RECORDING state
    if state == DictateState.RECORDING:
        dot_color = QColor(255, 80, 80)
        p.setBrush(QBrush(dot_color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, stand_y + 14 * scale), 2.5 * scale, 2.5 * scale)

    p.end()
    return QIcon(pixmap)


# ── Helper Functions ──────────────────────────────────────────────────────


def _systemd_is_active(service: str) -> Tuple[bool, Optional[str]]:
    """Check if a systemd --user service is active.

    Returns (active: bool, status_string: str or None on error).
    """
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", service],
            capture_output=True, text=True, timeout=10,
        )
        status = result.stdout.strip()
        return status == "active", status
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.warning("systemctl check failed for %s: %s", service, e)
        return False, None


def _systemd_action(service: str, action: str) -> bool:
    """Run systemctl --user action on a service.

    Actions: start, stop, restart.
    """
    try:
        result = subprocess.run(
            ["systemctl", "--user", action, service],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            logger.warning("systemctl %s %s failed: %s", action, service, result.stderr.strip())
            return False
        logger.info("systemctl %s %s — OK", action, service)
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.warning("systemctl %s %s error: %s", action, service, e)
        return False


def _check_llama_process() -> Tuple[bool, int]:
    """Check if llama-server process exists.

    Returns (running: bool, pid: int or 0).
    """
    try:
        result = subprocess.run(
            ["pgrep", "-f", "llama-server"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().splitlines()
            return True, int(pids[0])
        return False, 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False, 0


def _get_gpu_stats() -> Tuple[int, int, int]:
    """Query nvidia-smi for VRAM used (MiB), total (MiB), temp (°C).

    Returns (used_mib, total_mib, temp_c). All 0 on failure.
    """
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return 0, 0, 0
        parts = result.stdout.strip().split(",")
        if len(parts) >= 3:
            return int(parts[0].strip()), int(parts[1].strip()), int(parts[2].strip())
        return 0, 0, 0
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError) as e:
        logger.warning("nvidia-smi query failed: %s", e)
        return 0, 0, 0


def _get_vector_count() -> int:
    """Count lines in sessions.jsonl as proxy for vector count."""
    try:
        if SESSIONS_FILE.exists():
            result = subprocess.run(
                ["wc", "-l", str(SESSIONS_FILE)],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                count = int(result.stdout.strip().split()[0])
                return count
        return 0
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        return 0


def _read_dictate_state() -> Optional[DictateState]:
    """Read dictation state from state file if it exists.

    Written by nx_dictate or a helper script.
    """
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE) as f:
                data = json.load(f)
            state_str = data.get("state", "idle")
            return DictateState(state_str)
    except (json.JSONDecodeError, OSError, ValueError) as e:
        logger.debug("State file read failed: %s", e)
    return None


def _write_state_file(state: DictateState):
    """Write dictation state to state file for other components to read."""
    try:
        with open(STATE_FILE, "w") as f:
            json.dump({"state": state.value, "timestamp": time.time()}, f)
    except OSError as e:
        logger.warning("Failed to write state file: %s", e)


def _send_to_fifo(message: str) -> bool:
    """Write a message to the Jarvis FIFO pipe."""
    try:
        with open(FIFO_PATH, "w") as fifo:
            fifo.write(message.strip() + "\n")
            fifo.flush()
        logger.info("Sent to FIFO: %s", message[:60])
        return True
    except (OSError, BrokenPipeError) as e:
        logger.warning("FIFO write failed: %s", e)
        return False


def _get_log_file_path(name: str) -> Optional[str]:
    """Resolve log file path by name."""
    log_map = {
        "jarvis": PROJECT_ROOT / "data" / "memory" / "logs" / "jarvis_bridge.log",
        "memory": PROJECT_ROOT / "data" / "memory" / "logs" / "memory_watcher.log",
        "dictate": PROJECT_ROOT / "data" / "memory" / "logs" / "dictate.log",
        "tray": log_file,
    }
    path = log_map.get(name)
    if path and path.exists():
        return str(path)
    # Fallback: try to find any relevant log
    alt = PROJECT_ROOT / "data" / "memory" / "logs" / f"{name}.log"
    if alt.exists():
        return str(alt)
    return None


def _open_log_file(path: str):
    """Open a log file with the default system editor."""
    try:
        # Try xdg-open first, then fallbacks
        for cmd in [
            ["xdg-open", path],
            ["gnome-text-editor", path],
            ["gedit", path],
            ["kate", path],
            ["nano", path],
            ["less", path],
        ]:
            try:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                logger.info("Opened log: %s via %s", path, cmd[0])
                return
            except FileNotFoundError:
                continue
        logger.warning("No editor found to open %s", path)
    except Exception as e:
        logger.warning("Failed to open log: %s", e)


# ── Poll Data Snapshot ────────────────────────────────────────────────────


class SystemSnapshot:
    """Holds the latest polled system state."""

    def __init__(self):
        self.dictate_active = False
        self.dictate_status_str = "unknown"
        self.dictate_state: DictateState = DictateState.IDLE
        self.jarvis_active = False
        self.jarvis_status_str = "unknown"
        self.llama_running = False
        self.llama_pid = 0
        self.gpu_used = 0
        self.gpu_total = 0
        self.gpu_temp = 0
        self.vector_count = 0
        self.timestamp = 0.0

    @property
    def gpu_percent(self) -> float:
        if self.gpu_total > 0:
            return (self.gpu_used / self.gpu_total) * 100.0
        return 0.0

    @property
    def tooltip(self) -> str:
        """Build a concise tooltip for the tray icon."""
        lines = ["N-Xyme MIND"]
        lines.append(f"🎤 {STATE_LABELS.get(self.dictate_state, self.dictate_status_str)}")
        if self.jarvis_active:
            lines.append("🟢 Jarvis: running")
        else:
            lines.append("🔴 Jarvis: stopped")
        if self.llama_running:
            lines.append(f"🖥️ llama-server: PID {self.llama_pid}")
        else:
            lines.append("🖥️ llama-server: stopped")
        if self.gpu_total > 0:
            lines.append(f"🎮 GPU: {self.gpu_used}/{self.gpu_total} MiB  {self.gpu_temp}°C")
        lines.append(f"🧠 Memory: {self.vector_count:,} vectors")
        return "\n".join(lines)

    @property
    def status_summary(self) -> str:
        """One-line status for menu headers."""
        gpu_str = f"{self.gpu_used}/{self.gpu_total}G" if self.gpu_total > 0 else "N/A"
        vec_str = f"{self.vector_count:,}" if self.vector_count else "?"
        return (
            f"N-Xyme MIND — "
            f"{'🎤 Idle' if self.dictate_active else '⏹ Dictate'} | "
            f"{'🟢 Jarvis' if self.jarvis_active else '🔴 Jarvis'} | "
            f"🖥️ GPU: {gpu_str} | "
            f"🧠 {vec_str} vecs"
        )


# ── System Tray Application ──────────────────────────────────────────────


class NXTrayApp:
    """Main system tray application for N-Xyme MIND."""

    def __init__(self):
        self.app: Optional["QApplication"] = None
        self.tray: Optional["QSystemTrayIcon"] = None
        self.timer: Optional["QTimer"] = None
        self.snapshot = SystemSnapshot()
        self._icon_cache: dict = {}
        self._spin_angle = 0  # for rotation animation in processing state

        # Menu actions (built in _build_menu)
        self._toggle_dictate_action: Optional["QAction"] = None
        self._status_summary_action: Optional["QAction"] = None
        self._dictate_status_action: Optional["QAction"] = None
        self._jarvis_status_action: Optional["QAction"] = None
        self._llama_status_action: Optional["QAction"] = None
        self._gpu_status_action: Optional["QAction"] = None
        self._memory_status_action: Optional["QAction"] = None

    # ── Icon Management ──────────────────────────────────────────────────

    def _get_icon(self, state: DictateState, size: int = 64) -> "QIcon":
        """Get or create cached icon for state."""
        key = (state.value, size, self._spin_angle)
        if key not in self._icon_cache:
            self._icon_cache[key] = _draw_mic_icon(STATE_COLORS.get(state, STATE_COLORS[DictateState.IDLE]), size, state)
        # Keep cache bounded
        if len(self._icon_cache) > 50:
            # Remove oldest entries (roughly)
            keys = list(self._icon_cache.keys())
            for k in keys[:-30]:
                del self._icon_cache[k]
        return self._icon_cache[key]

    # ── Poll Loop ────────────────────────────────────────────────────────

    def _poll(self):
        """Main poll loop — runs every POLL_INTERVAL_MS."""
        logger.debug("Polling system state…")

        # 1. Dictation service status
        dict_active, dict_status = _systemd_is_active(SERVICE_NAMES["dictate"])
        self.snapshot.dictate_active = dict_active
        self.snapshot.dictate_status_str = dict_status or "inactive"

        # Try to read fine-grained state from state file
        file_state = _read_dictate_state()
        if file_state is not None:
            self.snapshot.dictate_state = file_state
        elif dict_active:
            self.snapshot.dictate_state = DictateState.IDLE
        else:
            self.snapshot.dictate_state = DictateState.STOPPED

        # 2. Jarvis bridge status
        jarv_active, jarv_status = _systemd_is_active(SERVICE_NAMES["jarvis"])
        self.snapshot.jarvis_active = jarv_active
        self.snapshot.jarvis_status_str = jarv_status or "inactive"

        # 3. llama-server process
        llama_running, llama_pid = _check_llama_process()
        self.snapshot.llama_running = llama_running
        self.snapshot.llama_pid = llama_pid

        # 4. GPU stats
        used, total, temp = _get_gpu_stats()
        self.snapshot.gpu_used = used
        self.snapshot.gpu_total = total
        self.snapshot.gpu_temp = temp

        # 5. Memory vector count
        self.snapshot.vector_count = _get_vector_count()

        self.snapshot.timestamp = time.time()

        # Update UI
        self._update_ui()

    def _update_ui(self):
        """Refresh tray icon and menu text from current snapshot."""
        if self.tray is None:
            return

        # Animate spin_angle for PROCESSING state
        if self.snapshot.dictate_state == DictateState.PROCESSING:
            self._spin_angle = (self._spin_angle + 15) % 360
        else:
            self._spin_angle = 0

        # Update icon
        icon = self._get_icon(self.snapshot.dictate_state)
        self.tray.setIcon(icon)

        # Update tooltip
        self.tray.setToolTip(self.snapshot.tooltip)

        # Update menu items (if built)
        if self._status_summary_action:
            self._status_summary_action.setText(self.snapshot.status_summary)

        if self._dictate_status_action:
            if self.snapshot.dictate_state == DictateState.RECORDING:
                self._dictate_status_action.setText("🔴 Dictation: Recording…")
                self._dictate_status_action.setIcon(self._get_icon(DictateState.RECORDING, 16))
            elif self.snapshot.dictate_state == DictateState.PROCESSING:
                self._dictate_status_action.setText("⏳ Dictation: Processing…")
                self._dictate_status_action.setIcon(self._get_icon(DictateState.PROCESSING, 16))
            elif self.snapshot.dictate_active:
                self._dictate_status_action.setText("🎤 Dictation: Idle")
                self._dictate_status_action.setIcon(self._get_icon(DictateState.IDLE, 16))
            else:
                self._dictate_status_action.setText("⏹ Dictation: Stopped")
                self._dictate_status_action.setIcon(self._get_icon(DictateState.STOPPED, 16))

        if self._jarvis_status_action:
            if self.snapshot.jarvis_active:
                self._jarvis_status_action.setText("🟢 Jarvis Bridge: Running")
            else:
                self._jarvis_status_action.setText("🔴 Jarvis Bridge: Stopped")

        if self._llama_status_action:
            if self.snapshot.llama_running:
                self._llama_status_action.setText(
                    f"🖥️ llama-server: Running (PID {self.snapshot.llama_pid})"
                )
            else:
                self._llama_status_action.setText("🖥️ llama-server: Stopped")

        if self._gpu_status_action:
            if self.snapshot.gpu_total > 0:
                pct = self.snapshot.gpu_percent
                bars = "█" * max(1, int(pct / 10)) + "░" * max(0, 10 - int(pct / 10))
                self._gpu_status_action.setText(
                    f"🎮 GPU: {self.snapshot.gpu_used}/{self.snapshot.gpu_total} MiB "
                    f"| {self.snapshot.gpu_temp}°C | {bars}"
                )
            else:
                self._gpu_status_action.setText("🎮 GPU: N/A (no nvidia-smi)")

        if self._memory_status_action:
            count = self.snapshot.vector_count
            if count:
                self._memory_status_action.setText(f"🧠 Memory: {count:,} vectors")
            else:
                self._memory_status_action.setText("🧠 Memory: pending…")

        # Update toggle action text
        if self._toggle_dictate_action:
            if self.snapshot.dictate_state == DictateState.RECORDING:
                self._toggle_dictate_action.setText("⏹ Stop Dictation")
            else:
                self._toggle_dictate_action.setText("🎤 Start Dictation")

    # ── Menu Building ────────────────────────────────────────────────────

    def _build_menu(self) -> "QMenu":
        """Construct the full right-click context menu."""
        from PyQt6.QtWidgets import QMenu, QSystemTrayIcon
        from PyQt6.QtGui import QAction

        menu = QMenu()

        # ── Toggle Dictation ─────────────────────────────────────────────
        self._toggle_dictate_action = QAction("🎤 Toggle Dictation")
        self._toggle_dictate_action.triggered.connect(self._on_toggle_dictation)
        menu.addAction(self._toggle_dictate_action)

        menu.addSeparator()

        # ── Status Summary ───────────────────────────────────────────────
        self._status_summary_action = QAction("Loading…")
        self._status_summary_action.setEnabled(False)
        menu.addAction(self._status_summary_action)

        menu.addSeparator()

        # ── System Status Submenu ────────────────────────────────────────
        status_menu = menu.addMenu("📊 System Status")

        self._dictate_status_action = QAction("🎤 Dictation: …")
        self._dictate_status_action.setEnabled(False)
        status_menu.addAction(self._dictate_status_action)

        self._jarvis_status_action = QAction("🟢 Jarvis: …")
        self._jarvis_status_action.setEnabled(False)
        status_menu.addAction(self._jarvis_status_action)

        self._llama_status_action = QAction("🖥️ llama-server: …")
        self._llama_status_action.setEnabled(False)
        status_menu.addAction(self._llama_status_action)

        status_menu.addSeparator()

        self._gpu_status_action = QAction("🎮 GPU: …")
        self._gpu_status_action.setEnabled(False)
        status_menu.addAction(self._gpu_status_action)

        self._memory_status_action = QAction("🧠 Memory: …")
        self._memory_status_action.setEnabled(False)
        status_menu.addAction(self._memory_status_action)

        # ── Open Logs Submenu ────────────────────────────────────────────
        logs_menu = menu.addMenu("📝 Open Logs")

        jarvis_log_action = QAction("📋 Jarvis Bridge Log")
        jarvis_log_action.triggered.connect(lambda: self._on_open_log("jarvis"))
        logs_menu.addAction(jarvis_log_action)

        memory_log_action = QAction("📋 Memory Watcher Log")
        memory_log_action.triggered.connect(lambda: self._on_open_log("memory"))
        logs_menu.addAction(memory_log_action)

        dictate_log_action = QAction("📋 Dictate Log")
        dictate_log_action.triggered.connect(lambda: self._on_open_log("dictate"))
        logs_menu.addAction(dictate_log_action)

        logs_menu.addSeparator()

        tray_log_action = QAction("📋 Tray Log (this app)")
        tray_log_action.triggered.connect(lambda: self._on_open_log("tray"))
        logs_menu.addAction(tray_log_action)

        # ── Service Control Submenu ──────────────────────────────────────
        services_menu = menu.addMenu("🔄 Service Control")

        restart_jarvis_action = QAction("🔄 Restart Jarvis Bridge")
        restart_jarvis_action.triggered.connect(self._on_restart_jarvis)
        services_menu.addAction(restart_jarvis_action)

        restart_dictate_action = QAction("🔄 Restart Dictation")
        restart_dictate_action.triggered.connect(self._on_restart_dictate)
        services_menu.addAction(restart_dictate_action)

        services_menu.addSeparator()

        show_status_action = QAction("📋 Systemd Status (all)")
        show_status_action.triggered.connect(self._on_show_systemd_status)
        services_menu.addAction(show_status_action)

        # ── Quick Send Submenu ───────────────────────────────────────────
        quick_menu = menu.addMenu("⚡ Quick Send")

        hello_action = QAction("💬 \"Hello Jarvis\"")
        hello_action.triggered.connect(lambda: self._on_quick_send("Hello Jarvis"))
        quick_menu.addAction(hello_action)

        gpu_action = QAction("💬 \"GPU status\"")
        gpu_action.triggered.connect(lambda: self._on_quick_send("GPU status"))
        quick_menu.addAction(gpu_action)

        memory_action = QAction("💬 \"Memory count\"")
        memory_action.triggered.connect(lambda: self._on_quick_send("Memory count"))
        quick_menu.addAction(memory_action)

        quick_menu.addSeparator()

        custom_action = QAction("✏️ Custom message…")
        custom_action.triggered.connect(self._on_custom_send)
        quick_menu.addAction(custom_action)

        menu.addSeparator()

        # ── Quit ─────────────────────────────────────────────────────────
        quit_action = QAction("🚪 Quit")
        quit_action.triggered.connect(self._on_quit)
        menu.addAction(quit_action)

        return menu

    # ── Menu Action Handlers ─────────────────────────────────────────────

    def _on_toggle_dictation(self):
        """Toggle nx-dictate service on/off."""
        from PyQt6.QtWidgets import QMessageBox

        if self.snapshot.dictate_active:
            logger.info("Stopping nx-dictate service…")
            success = _systemd_action(SERVICE_NAMES["dictate"], "stop")
            if success:
                _write_state_file(DictateState.STOPPED)
        else:
            logger.info("Starting nx-dictate service…")
            success = _systemd_action(SERVICE_NAMES["dictate"], "start")
            if success:
                _write_state_file(DictateState.IDLE)

        if not success:
            # Show error notification
            self.tray.showMessage(
                "N-Xyme MIND",
                f"Failed to {'start' if not self.snapshot.dictate_active else 'stop'} dictation service.",
                self.tray.MessageIcon.Critical,
                3000,
            )

    def _on_open_log(self, name: str):
        """Open a log file."""
        path = _get_log_file_path(name)
        if path:
            _open_log_file(path)
        else:
            self.tray.showMessage(
                "N-Xyme MIND",
                f"Log file not found: {name}",
                self.tray.MessageIcon.Information,
                2000,
            )

    def _on_restart_jarvis(self):
        """Restart the Jarvis bridge service."""
        logger.info("Restarting jarvis-bridge service…")
        success = _systemd_action(SERVICE_NAMES["jarvis"], "restart")
        if success:
            self.tray.showMessage(
                "N-Xyme MIND",
                "🔄 Jarvis Bridge restarted.",
                self.tray.MessageIcon.Information,
                2000,
            )
        else:
            self.tray.showMessage(
                "N-Xyme MIND",
                "❌ Failed to restart Jarvis Bridge.",
                self.tray.MessageIcon.Critical,
                3000,
            )

    def _on_restart_dictate(self):
        """Restart the nx-dictate service."""
        logger.info("Restarting nx-dictate service…")
        success = _systemd_action(SERVICE_NAMES["dictate"], "restart")
        if success:
            self.tray.showMessage(
                "N-Xyme MIND",
                "🔄 Dictation restarted.",
                self.tray.MessageIcon.Information,
                2000,
            )
        else:
            self.tray.showMessage(
                "N-Xyme MIND",
                "❌ Failed to restart dictation.",
                self.tray.MessageIcon.Critical,
                3000,
            )

    def _on_show_systemd_status(self):
        """Show systemd --user status in a terminal window."""
        try:
            subprocess.Popen(
                [
                    "x-terminal-emulator", "-e",
                    "bash", "-c",
                    "systemctl --user status nx-dictate.service jarvis-bridge.service; "
                    "echo ''; "
                    "echo 'Press ENTER to close...'; read",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            # Fallback: try xterm
            try:
                subprocess.Popen(
                    [
                        "xterm", "-e",
                        "bash", "-c",
                        "systemctl --user status nx-dictate.service jarvis-bridge.service; "
                        "echo ''; echo 'Press ENTER to close...'; read",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except FileNotFoundError:
                self.tray.showMessage(
                    "N-Xyme MIND",
                    "No terminal emulator found to show status.",
                    self.tray.MessageIcon.Information,
                    2000,
                )

    def _on_quick_send(self, message: str):
        """Send a predefined message to the Jarvis FIFO."""
        success = _send_to_fifo(message)
        if success:
            self.tray.showMessage(
                "N-Xyme MIND",
                f"⚡ Sent to Jarvis: \"{message[:40]}\"",
                self.tray.MessageIcon.Information,
                2000,
            )
        else:
            self.tray.showMessage(
                "N-Xyme MIND",
                "❌ FIFO not available. Is Jarvis running?",
                self.tray.MessageIcon.Critical,
                3000,
            )

    def _on_custom_send(self):
        """Prompt for a custom message and send to FIFO."""
        from PyQt6.QtWidgets import QInputDialog, QLineEdit

        text, ok = QInputDialog.getText(
            None,
            "Send to Jarvis",
            "Message:",
            QLineEdit.EchoMode.Normal,
            "",
        )
        if ok and text.strip():
            self._on_quick_send(text.strip())

    def _on_quit(self):
        """Shut down the tray app cleanly."""
        logger.info("Shutting down N-Xyme MIND tray…")
        if self.timer:
            self.timer.stop()
        if self.tray:
            self.tray.hide()
        if self.app:
            self.app.quit()

    # ── Tray Icon Double-Click ───────────────────────────────────────────

    def _on_activated(self, reason):
        """Handle tray icon activation."""
        from PyQt6.QtWidgets import QSystemTrayIcon

        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._on_toggle_dictation()
        elif reason == QSystemTrayIcon.ActivationReason.MiddleClick:
            # Middle-click = show quick status popup
            if self.tray:
                self.tray.showMessage(
                    "N-Xyme MIND — Quick Status",
                    self.snapshot.status_summary,
                    self.tray.MessageIcon.Information,
                    3000,
                )

    # ── Start / Run ──────────────────────────────────────────────────────

    def start(self) -> bool:
        """Initialize and start the system tray application.

        Returns True on success, False if tray is unavailable.
        """
        try:
            from PyQt6.QtWidgets import QApplication, QSystemTrayIcon
            from PyQt6.QtCore import QTimer
            from PyQt6.QtGui import QAction, QIcon
        except ImportError as e:
            logger.error("PyQt6 not installed: %s", e)
            return False

        try:
            self.app = QApplication.instance() or QApplication(sys.argv)
            self.app.setQuitOnLastWindowClosed(False)

            if not QSystemTrayIcon.isSystemTrayAvailable():
                logger.error("System tray not available on this desktop")
                return False

            # Build menu
            menu = self._build_menu()

            # Create tray icon
            self.tray = QSystemTrayIcon()
            self.tray.setContextMenu(menu)
            self.tray.activated.connect(self._on_activated)

            # Set initial icon
            self.tray.setIcon(self._get_icon(DictateState.IDLE))
            self.tray.setToolTip("N-Xyme MIND — starting…")
            self.tray.show()

            # Initial poll
            self._poll()

            # Start polling timer
            self.timer = QTimer()
            self.timer.timeout.connect(self._poll)
            self.timer.start(POLL_INTERVAL_MS)

            logger.info("N-Xyme MIND Tray started — polling every %d ms", POLL_INTERVAL_MS)
            return True

        except Exception as e:
            logger.error("Tray init failed: %s", e, exc_info=True)
            return False

    def run(self):
        """Execute the Qt application event loop."""
        if self.app:
            return self.app.exec()
        return 1

    def stop(self):
        """Graceful stop."""
        self._on_quit()


# ── CLI Entry Point ───────────────────────────────────────────────────────


def main():
    """Parse args and run the tray application."""
    import argparse

    parser = argparse.ArgumentParser(description="N-Xyme MIND System Tray")
    parser.add_argument("--daemon", action="store_true", help="Fork to background")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    if args.daemon:
        pid = os.fork()
        if pid > 0:
            # Parent exits
            sys.exit(0)

        # Child continues
        os.setsid()
        # Close stdin/stdout/stderr in daemon mode
        sys.stdin.close()
        sys.stdout.close()
        sys.stderr.close()

    logger.info("=== N-Xyme MIND Tray starting ===")
    logger.info(f"FIFO: {FIFO_PATH}")
    logger.info(f"State file: {STATE_FILE}")
    logger.info(f"Sessions: {SESSIONS_FILE}")

    app = NXTrayApp()
    if app.start():
        exit_code = app.run()
        logger.info("Tray exited with code %d", exit_code)
        sys.exit(exit_code)
    else:
        logger.error("Failed to start tray application")
        sys.exit(1)


if __name__ == "__main__":
    main()
