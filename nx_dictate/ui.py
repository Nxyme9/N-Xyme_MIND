# N-Xyme Dictate - Enhanced UI Module
# PyQt6-based ADHD-friendly interface with bells and whistles

from __future__ import annotations

import logging
import os
import time
from typing import Optional, Callable, List

logger = logging.getLogger("nxyme_dictate.ui")

PYQT6_AVAILABLE = False
try:
    from PyQt6.QtWidgets import (
        QApplication,
        QSystemTrayIcon,
        QMenu,
        QDialog,
        QVBoxLayout,
        QLabel,
        QPushButton,
        QComboBox,
        QGroupBox,
        QCheckBox,
        QSlider,
        QHBoxLayout,
        QWidget,
        QSpinBox,
        QProgressBar,
    )
    from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer, QSize
    from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QFont, QPen, QLinearGradient

    SOUND_AVAILABLE = False
    try:
        from PyQt6.QtMultimedia import QSoundEffect
        SOUND_AVAILABLE = True
    except ImportError:
        pass

    PYQT6_AVAILABLE = True
except ImportError as e:
    logger.warning(f"PyQt6 not available: {e}")

if PYQT6_AVAILABLE:

    class SignalEmitter(QObject):
        state_changed = pyqtSignal(str)
        text_received = pyqtSignal(str)
        error_occurred = pyqtSignal(str)
        audio_level = pyqtSignal(float)
        transcription_complete = pyqtSignal(str, int)

    class TrayIconManager:
        STATE_IDLE = "idle"
        STATE_RECORDING = "recording"
        STATE_PROCESSING = "processing"
        STATE_WARNING = "warning"
        STATE_ERROR = "error"

        def __init__(self):
            self._icon: Optional[QSystemTrayIcon] = None
            self._state = self.STATE_IDLE
            self._callbacks = {}
            self._emitter = SignalEmitter()
            self._last_typed_text = ""
            self._session_stats = {"sessions": 0, "words": 0, "chars": 0}
            self._transcription_history: List[str] = []
            self._max_history = 5
            self._audio_level = 0.0
            self._animation_timer: Optional[QTimer] = None
            self._pulse_state = 0
            self._sound_enabled = True

        def setup(self, app: QApplication, on_toggle: Callable, on_quit: Callable) -> bool:
            self._icon = QSystemTrayIcon()
            icon_paths = [
                "/usr/share/icons/hicolor/48x48/apps/audio-x-generic.png",
                "/usr/share/icons/breeze/actions/audio-volume-high.png",
                "/usr/share/icons/Adwaita/48x48/apps/audio-x-generic.png",
            ]
            loaded = False
            for path in icon_paths:
                if os.path.exists(path):
                    self._icon.setIcon(QIcon(path))
                    loaded = True
                    break
            if not loaded:
                self._icon.setIcon(self._create_icon(self.STATE_IDLE))

            self._icon.setToolTip("N-Xyme Dictate - Ready")
            menu = self._build_menu(on_toggle, on_quit)
            self._icon.setContextMenu(menu)
            self._icon.activated.connect(self._on_icon_activated)
            self._icon.setVisible(True)
            self._icon.show()
            self._start_pulse_animation()
            logger.info(f"Tray icon initialized: visible={self._icon.isVisible()}")
            return True

        def _build_menu(self, on_toggle: Callable, on_quit: Callable) -> QMenu:
            menu = QMenu()
            header = QAction("🎤 N-Xyme Dictate")
            header.setEnabled(False)
            header.setFont(QFont("Sans", 10, QFont.Weight.Bold))
            menu.addAction(header)
            menu.addSeparator()

            self._status_action = QAction("Status: Ready")
            self._status_action.setEnabled(False)
            menu.addAction(self._status_action)

            self._audio_level_action = QAction("Audio: ▁▂▃▅▇")
            self._audio_level_action.setEnabled(False)
            menu.addAction(self._audio_level_action)

            self._last_text_action = QAction("Last: None")
            self._last_text_action.setEnabled(False)
            menu.addAction(self._last_text_action)

            menu.addSeparator()

            self._toggle_action = QAction("▶ Start Recording")
            self._toggle_action.triggered.connect(on_toggle)
            menu.addAction(self._toggle_action)

            menu.addSeparator()

            device_menu = QMenu("🎧 Audio Device")
            menu.addMenu(device_menu)
            self._selected_device = 11
            self._device_status = QAction("Current: Default")
            self._device_status.setEnabled(False)
            menu.addAction(self._device_status)

            try:
                import sounddevice as sd
                devices = sd.query_devices()
                for i, d in enumerate(devices):
                    if d.get("max_input_channels", 0) > 0:
                        name = d["name"][:35]
                        action = QAction(f"{name}")
                        action.setData(i)
                        action.setCheckable(True)
                        action.setChecked(i == self._selected_device)
                        action.triggered.connect(lambda checked, dev=i: self._on_device_selected(dev))
                        device_menu.addAction(action)
            except Exception:
                pass

            menu.addSeparator()

            quick_toggles = QMenu("⚡ Quick Toggles")
            menu.addMenu(quick_toggles)

            self._live_mode_action = QAction("Live Typing Mode")
            self._live_mode_action.setCheckable(True)
            self._live_mode_action.setChecked(True)
            quick_toggles.addAction(self._live_mode_action)

            self._fast_mode_action = QAction("Fast Mode (No Noise Suppression)")
            self._fast_mode_action.setCheckable(True)
            self._fast_mode_action.setChecked(False)
            quick_toggles.addAction(self._fast_mode_action)

            self._realtime_action = QAction("Real-time Transcription")
            self._realtime_action.setCheckable(True)
            self._realtime_action.setChecked(False)
            quick_toggles.addAction(self._realtime_action)

            self._injection_action = QAction("Auto-inject Text")
            self._injection_action.setCheckable(True)
            self._injection_action.setChecked(True)
            quick_toggles.addAction(self._injection_action)

            menu.addSeparator()

            self._sound_action = QAction("🔔 Sound Feedback")
            self._sound_action.setCheckable(True)
            self._sound_action.setChecked(True)
            menu.addAction(self._sound_action)

            self._notifications_action = QAction("📨 Show Notifications")
            self._notifications_action.setCheckable(True)
            self._notifications_action.setChecked(True)
            menu.addAction(self._notifications_action)

            menu.addSeparator()

            stats_menu = QMenu("📊 Statistics")
            menu.addMenu(stats_menu)
            self._sessions_action = QAction("Sessions: 0")
            self._sessions_action.setEnabled(False)
            stats_menu.addAction(self._sessions_action)

            self._words_action = QAction("Words: 0")
            self._words_action.setEnabled(False)
            stats_menu.addAction(self._words_action)

            self._chars_action = QAction("Characters: 0")
            self._chars_action.setEnabled(False)
            stats_menu.addAction(self._chars_action)

            self._avg_latency_action = QAction("Avg Latency: 0ms")
            self._avg_latency_action.setEnabled(False)
            stats_menu.addAction(self._avg_latency_action)

            history_menu = QMenu("📜 Recent Transcriptions")
            menu.addMenu(history_menu)
            self._history_actions: List[QAction] = []
            for i in range(self._max_history):
                action = QAction(f"{i+1}. (empty)")
                action.setEnabled(False)
                action.setVisible(False)
                history_menu.addAction(action)
                self._history_actions.append(action)

            menu.addSeparator()

            self._settings_action = QAction("⚙ Settings")
            self._settings_action.triggered.connect(self._show_settings)
            menu.addAction(self._settings_action)

            self._language_action = QAction("🌐 Language: English")
            self._language_action.setCheckable(True)
            menu.addAction(self._language_action)

            menu.addSeparator()

            shortcuts = QMenu("⌨ Keyboard Shortcuts")
            menu.addMenu(shortcuts)
            shortcuts.addAction(QAction("Start/Stop: F6 (default)", None))
            shortcuts.addAction(QAction("Toggle: Mouse Back btn", None))
            shortcuts.addAction(QAction("Settings: Double-click tray", None))

            menu.addSeparator()

            quit_action = QAction("✖ Quit")
            quit_action.triggered.connect(on_quit)
            menu.addAction(quit_action)
            self._quit_action = quit_action

            return menu

        def _start_pulse_animation(self):
            self._animation_timer = QTimer()
            self._animation_timer.timeout.connect(self._update_pulse)
            self._animation_timer.start(100)

        def _update_pulse(self):
            if self._state == self.STATE_RECORDING:
                self._pulse_state = (self._pulse_state + 1) % 10
                if self._icon:
                    self._icon.setIcon(self._create_icon(self._state, self._pulse_state))

        def _on_icon_activated(self, reason):
            if reason == QSystemTrayIcon.ActivationReason.Trigger:
                if self._callbacks.get("toggle"):
                    self._callbacks["toggle"]()
            elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
                if self._callbacks.get("show_settings"):
                    self._callbacks["show_settings"]()

        def _on_device_selected(self, device_index: int):
            self._selected_device = device_index
            try:
                import sounddevice as sd
                d = sd.query_devices(device_index)
                name = d["name"][:30]
                self._device_status.setText(f"Current: {name}")
            except Exception:
                pass
            if self._callbacks.get("device_changed"):
                self._callbacks["device_changed"](device_index)

        def get_selected_device(self) -> int:
            return self._selected_device

        def set_callback(self, name: str, callback: Callable):
            self._callbacks[name] = callback

        def _show_settings(self):
            if self._callbacks.get("show_settings"):
                self._callbacks["show_settings"]()

        def update_state(self, state: str):
            self._state = state
            if self._icon:
                self._icon.setIcon(self._create_icon(state))
                
                # ADHD-friendly: Enhanced tooltips with clear instructions
                tooltips = {
                    self.STATE_IDLE: "🟢 N-Xyme Dictate - Ready\n• Press F6 or click to start\n• Speak naturally, I'll type it out!",
                    self.STATE_RECORDING: "🔴 RECORDING - Speak now!\n• I can hear you...\n• Click or press F6 to stop",
                    self.STATE_PROCESSING: "🔵 Processing your words...\n• Almost done!\n• Converting speech to text...",
                    self.STATE_WARNING: "⚠️ Low confidence\n• Speak more clearly\n• Check microphone",
                    self.STATE_ERROR: "❌ Oops! Something went wrong\n• Click for error details\n• Check microphone setup",
                }
                self._icon.setToolTip(tooltips.get(state, "N-Xyme Dictate"))
                
                # ADHD-friendly: Show notification bubbles for state changes
                notification_messages = {
                    self.STATE_RECORDING: ("🎤 Recording Started", "Speak now! I'm listening..."),
                    self.STATE_PROCESSING: ("⏳ Processing", "Converting speech to text..."),
                    self.STATE_IDLE: ("✅ Ready", "Dictation stopped. Tap F6 to start again!"),
                }
                if state in notification_messages and self._icon.supportsMessages():
                    title, msg = notification_messages[state]
                    self._icon.showMessage(title, msg, QSystemTrayIcon.MessageIcon.Information, 2000)
                
                if self._sound_enabled:
                    self._play_state_sound(state)

                if state == self.STATE_RECORDING:
                    self._toggle_action.setText("⏹ Stop Recording")
                elif state == self.STATE_PROCESSING:
                    self._toggle_action.setText("⏳ Processing...")
                else:
                    self._toggle_action.setText("▶ Start Dictation")

                status_texts = {
                    self.STATE_IDLE: "Status: Ready",
                    self.STATE_RECORDING: "Status: 🎤 Recording",
                    self.STATE_PROCESSING: "Status: ⚙ Processing",
                    self.STATE_WARNING: "Status: ⚠️ Warning",
                    self.STATE_ERROR: "Status: ❌ Error",
                }
                self._status_action.setText(status_texts.get(state, "Status: Unknown"))

        def _create_icon(self, state: str, pulse: int = 0) -> QIcon:
            size = 64
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)

            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            state_colors = {
                self.STATE_IDLE: (100, 100, 100),
                self.STATE_RECORDING: (220, 50, 50),
                self.STATE_PROCESSING: (50, 120, 220),
                self.STATE_WARNING: (220, 180, 50),
                self.STATE_ERROR: (220, 80, 50),
            }

            r, g, b = state_colors.get(state, (100, 100, 100))

            if state == self.STATE_RECORDING and pulse > 0:
                intensity = 0.5 + (pulse / 20.0)
                r = min(255, int(r * intensity))
                g = min(255, int(g * intensity))
                b = min(255, int(b * intensity))

            color = QColor(r, g, b)

            gradient = QLinearGradient(0, 0, size, size)
            gradient.setColorAt(0, color.lighter(120))
            gradient.setColorAt(1, color.darker(120))
            painter.setBrush(gradient)
            painter.setPen(Qt.PenStyle.NoPen)

            margin = 6
            painter.drawEllipse(margin, margin, size - 2 * margin, size - 2 * margin)

            if state == self.STATE_RECORDING:
                pen = QPen(QColor(255, 255, 255, 100))
                pen.setWidth(2)
                painter.setPen(pen)
                wave_x = 16
                for i in range(5):
                    bar_height = int(8 + (i * 4) % 16)
                    y = int(32 - bar_height // 2)
                    painter.drawLine(wave_x + i * 8, y, wave_x + i * 8, y + bar_height)

            if state == self.STATE_PROCESSING:
                pen = QPen(QColor(255, 255, 255, 150))
                pen.setWidth(3)
                painter.setPen(pen)
                cx, cy = size // 2, size // 2
                for i in range(8):
                    angle = (i * 45 + int(time.time() * 100) % 360) * 3.14159 / 180
                    x1 = int(cx + 8 * (1 if i % 2 == 0 else 0.5) * (-1 if i >= 4 else 1) * (1 if i < 4 else -1))
                    y1 = int(cy + 8 * (1 if i % 2 == 0 else 0.5) * (1 if 2 <= i <= 5 else -1) * (1 if i < 4 else -1))
                    x2 = int(cx + 20 * (1 if i % 2 == 0 else 0.7) * (-1 if i >= 4 else 1) * (1 if i < 4 else -1) * 0.7 + 12 * (1 if i % 2 == 0 else 0.6) * (1 if i % 4 < 2 else -1) * (1 if i < 2 or i >= 6 else -1))
                    y2 = int(cy + 20 * (1 if i % 2 == 0 else 0.7) * (1 if 2 <= i <= 5 else -1) * (1 if i < 4 else -1))
                    painter.drawLine(x1, y1, x2, y2)

            mic_color = QColor(255, 255, 255)
            painter.setBrush(mic_color)
            painter.setPen(Qt.PenStyle.NoPen)
            mic_x = size // 2 - 6
            mic_y = size // 2 - 10
            painter.drawEllipse(mic_x + 4, mic_y, 4, 6)
            painter.drawRect(mic_x, mic_y + 4, 12, 10)
            painter.drawLine(int(mic_x + 6), int(mic_y + 14), int(mic_x + 6), int(mic_y + 20))
            painter.drawLine(int(mic_x + 2), int(mic_y + 18), int(mic_x + 10), int(mic_y + 18))

            painter.end()
            return QIcon(pixmap)

        def _play_state_sound(self, state: str):
            try:
                import subprocess
                sound_map = {
                    self.STATE_RECORDING: ["paplay", "/usr/share/sounds/freedesktop/stereo/media-record.ogg"],
                    self.STATE_PROCESSING: ["paplay", "/usr/share/sounds/freedesktop/stereo/service-login.ogg"],
                    self.STATE_IDLE: ["paplay", "/usr/share/sounds/freedesktop/stereo/service-logout.ogg"],
                }
                if state in sound_map:
                    subprocess.run(sound_map[state], capture_output=True, timeout=1)
            except Exception:
                pass

        def update_audio_level(self, level: float):
            self._audio_level = level
            bars = "▁▂▃▅▇"
            num_bars = int((level / 100.0) * 5)
            bar_str = bars[:num_bars] + " " * (5 - num_bars)
            self._audio_level_action.setText(f"Audio: {bar_str}")

        def show_message(self, title: str, message: str, icon=QSystemTrayIcon.MessageIcon.Information):
            if self._icon and self._notifications_action.isChecked():
                self._icon.showMessage(title, message, icon, 3000)

        def notify_text(self, text: str, latency_ms: int = 0):
            display_text = text[:45] + "..." if len(text) > 45 else text
            self._last_text_action.setText(f"Last: {display_text}")

            self._transcription_history.insert(0, text)
            if len(self._transcription_history) > self._max_history:
                self._transcription_history.pop()

            for i, action in enumerate(self._history_actions):
                if i < len(self._transcription_history):
                    hist_text = self._transcription_history[i][:30]
                    action.setText(f"{i+1}. {hist_text}...")
                    action.setVisible(True)
                else:
                    action.setVisible(False)

            word_count = len(text.split())
            char_count = len(text)
            self._session_stats["sessions"] += 1
            self._session_stats["words"] += word_count
            self._session_stats["chars"] += char_count

            self._sessions_action.setText(f"Sessions: {self._session_stats['sessions']}")
            self._words_action.setText(f"Words: {self._session_stats['words']}")
            self._chars_action.setText(f"Characters: {self._session_stats['chars']}")
            if latency_ms > 0:
                self._avg_latency_action.setText(f"Avg Latency: {latency_ms}ms")

            if self._notifications_action.isChecked():
                self.show_message("✅ Transcribed", f"{word_count} words in {latency_ms}ms")

        def set_stats(self, sessions: int, words: int, chars: int, latency_ms: int = 0):
            self._session_stats = {"sessions": sessions, "words": words, "chars": chars}
            self._sessions_action.setText(f"Sessions: {sessions}")
            self._words_action.setText(f"Words: {words}")
            self._chars_action.setText(f"Characters: {chars}")
            if latency_ms > 0:
                self._avg_latency_action.setText(f"Avg Latency: {latency_ms}ms")

    class SettingsDialog(QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("⚡ N-Xyme Dictate Settings")
            self.setModal(False)
            self.setMinimumSize(700, 750)
            self._setup_ui()

        def _setup_ui(self):
            from PyQt6.QtWidgets import QTabWidget
            
            layout = QVBoxLayout()
            
            title = QLabel("⚡ N-Xyme Dictate Settings")
            title.setFont(QFont("Sans", 14, QFont.Weight.Bold))
            layout.addWidget(title)
            
            tabs = QTabWidget()
            tabs.setDocumentMode(True)
            
            general_tab = self._create_general_tab()
            audio_tab = self._create_audio_tab()
            model_tab = self._create_model_tab()
            output_tab = self._create_output_tab()
            advanced_tab = self._create_advanced_tab()
            
            tabs.addTab(general_tab, "🎤 General")
            tabs.addTab(audio_tab, "🔊 Audio")
            tabs.addTab(model_tab, "🤖 Model")
            tabs.addTab(output_tab, "📝 Output")
            tabs.addTab(advanced_tab, "⚡ Advanced")
            
            layout.addWidget(tabs)
            
            close_btn = QPushButton("Save & Close")
            close_btn.clicked.connect(self.save_and_close)
            layout.addWidget(close_btn)
            self.setLayout(layout)
        
        def _create_general_tab(self):
            widget = QWidget()
            layout = QVBoxLayout()
            
            hotkey_group = QGroupBox("⌨️ Global Hotkey")
            hotkey_layout = QVBoxLayout()
            self.hotkey_combo = QComboBox()
            self.hotkey_combo.addItems(["F6 (default)", "F5", "F7", "Ctrl+Shift+D", "Mouse Back", "Ctrl+Alt+V"])
            hotkey_layout.addWidget(QLabel("Push-to-talk key:"))
            hotkey_layout.addWidget(self.hotkey_combo)
            self.toggle_mode = QCheckBox("Toggle mode (press to start/stop)")
            self.toggle_mode.setChecked(True)
            hotkey_layout.addWidget(self.toggle_mode)
            hotkey_group.setLayout(hotkey_layout)
            layout.addWidget(hotkey_group)
            
            language_group = QGroupBox("🌐 Language")
            lang_layout = QVBoxLayout()
            self.lang_combo = QComboBox()
            self.lang_combo.addItems([
                "English (en)", "Spanish (es)", "French (fr)", "German (de)", 
                "Italian (it)", "Portuguese (pt)", "Russian (ru)", "Chinese (zh)",
                "Japanese (ja)", "Korean (ko)", "Auto-detect"
            ])
            self.lang_combo.setCurrentIndex(10)
            lang_layout.addWidget(self.lang_combo)
            language_group.setLayout(lang_layout)
            layout.addWidget(language_group)
            
            startup_group = QGroupBox("🚀 Startup")
            startup_layout = QVBoxLayout()
            self.auto_start = QCheckBox("Start with system")
            self.auto_start.setChecked(False)
            startup_layout.addWidget(self.auto_start)
            self.start_minimized = QCheckBox("Start minimized to tray")
            self.start_minimized.setChecked(True)
            startup_layout.addWidget(self.start_minimized)
            self.auto_listen = QCheckBox("Auto-listen on startup")
            self.auto_listen.setChecked(False)
            startup_layout.addWidget(self.auto_listen)
            startup_group.setLayout(startup_layout)
            layout.addWidget(startup_group)
            
            layout.addStretch()
            widget.setLayout(layout)
            return widget
        
        def _create_audio_tab(self):
            widget = QWidget()
            layout = QVBoxLayout()
            
            device_group = QGroupBox("🎤 Input Device")
            device_layout = QVBoxLayout()
            self.device_combo = QComboBox()
            self.device_combo.addItems(["Default", "Built-in Microphone", "USB Microphone", "Bluetooth"])
            device_layout.addWidget(QLabel("Audio input:"))
            device_layout.addWidget(self.device_combo)
            device_group.setLayout(device_layout)
            layout.addWidget(device_group)
            
            processing_group = QGroupBox("🔧 Audio Processing")
            proc_layout = QVBoxLayout()
            self.noise_check = QCheckBox("Noise suppression (RNNoise)")
            self.noise_check.setChecked(True)
            proc_layout.addWidget(self.noise_check)
            self.vad_check = QCheckBox("Voice activity detection (VAD)")
            self.vad_check.setChecked(True)
            proc_layout.addWidget(self.vad_check)
            proc_layout.addWidget(QLabel("Silence threshold (seconds):"))
            self.silence_spin = QSpinBox()
            self.silence_spin.setMinimum(1)
            self.silence_spin.setMaximum(10)
            self.silence_spin.setValue(3)
            proc_layout.addWidget(self.silence_spin)
            self.sample_rate = QComboBox()
            self.sample_rate.addItems(["16000 Hz", "22050 Hz", "44100 Hz", "48000 Hz"])
            self.sample_rate.setCurrentIndex(0)
            proc_layout.addWidget(QLabel("Sample rate:"))
            proc_layout.addWidget(self.sample_rate)
            self.channels = QComboBox()
            self.channels.addItems(["Mono (1 channel)", "Stereo (2 channels)"])
            self.channels.setCurrentIndex(0)
            proc_layout.addWidget(QLabel("Channels:"))
            proc_layout.addWidget(self.channels)
            processing_group.setLayout(proc_layout)
            layout.addWidget(processing_group)
            
            feedback_group = QGroupBox("🔔 Audio Feedback")
            fb_layout = QVBoxLayout()
            self.sound_start = QCheckBox("Sound on recording start")
            self.sound_start.setChecked(True)
            fb_layout.addWidget(self.sound_start)
            self.sound_stop = QCheckBox("Sound on recording stop")
            self.sound_stop.setChecked(True)
            fb_layout.addWidget(self.sound_stop)
            self.sound_complete = QCheckBox("Sound on transcription complete")
            self.sound_complete.setChecked(True)
            fb_layout.addWidget(self.sound_complete)
            fb_layout.addWidget(QLabel("Volume:"))
            self.volume_slider = QSlider(Qt.Orientation.Horizontal)
            self.volume_slider.setMinimum(0)
            self.volume_slider.setMaximum(100)
            self.volume_slider.setValue(70)
            fb_layout.addWidget(self.volume_slider)
            feedback_group.setLayout(fb_layout)
            layout.addWidget(feedback_group)
            
            layout.addStretch()
            widget.setLayout(layout)
            return widget
        
        def _create_model_tab(self):
            widget = QWidget()
            layout = QVBoxLayout()
            
            model_group = QGroupBox("🤖 Whisper Model")
            model_layout = QVBoxLayout()
            self.model_combo = QComboBox()
            self.model_combo.addItems([
                "tiny (39M params - fastest)",
                "base (74M params - balanced)",
                "small (244M params - good accuracy)",
                "medium (769M params - high accuracy)",
                "large-v3-turbo (809M params - best)",
                "large-v3 (2953M params - maximum)",
            ])
            self.model_combo.setCurrentIndex(4)
            model_layout.addWidget(QLabel("Model size:"))
            model_layout.addWidget(self.model_combo)
            self.gpu_check = QCheckBox("Use GPU acceleration (CUDA)")
            self.gpu_check.setChecked(True)
            model_layout.addWidget(self.gpu_check)
            self.compute_type = QComboBox()
            self.compute_type.addItems(["float16 (fastest)", "int8 (balanced)", "int8_float16 (safe)"])
            self.compute_type.setCurrentIndex(0)
            model_layout.addWidget(QLabel("Compute type:"))
            model_layout.addWidget(self.compute_type)
            model_group.setLayout(model_layout)
            layout.addWidget(model_group)
            
            threads_group = QGroupBox("⚡ Performance")
            threads_layout = QVBoxLayout()
            self.threads_spin = QSpinBox()
            self.threads_spin.setMinimum(1)
            self.threads_spin.setMaximum(32)
            self.threads_spin.setValue(4)
            threads_layout.addWidget(QLabel("CPU threads:"))
            threads_layout.addWidget(self.threads_spin)
            self.gpu_layers = QSpinBox()
            self.gpu_layers.setMinimum(0)
            self.gpu_layers.setMaximum(99)
            self.gpu_layers.setValue(99)
            threads_layout.addWidget(QLabel("GPU layers (0=auto):"))
            threads_layout.addWidget(self.gpu_layers)
            self.batch_size = QSpinBox()
            self.batch_size.setMinimum(1)
            self.batch_size.setMaximum(64)
            self.batch_size.setValue(8)
            threads_layout.addWidget(QLabel("Batch size:"))
            threads_layout.addWidget(self.batch_size)
            threads_group.setLayout(threads_layout)
            layout.addWidget(threads_group)
            
            layout.addStretch()
            widget.setLayout(layout)
            return widget
        
        def _create_output_tab(self):
            widget = QWidget()
            layout = QVBoxLayout()
            
            output_method_group = QGroupBox("📤 Output Method")
            out_method_layout = QVBoxLayout()
            self.inject_check = QCheckBox("Auto-inject to active window (type text)")
            self.inject_check.setChecked(True)
            out_method_layout.addWidget(self.inject_check)
            self.clipboard_check = QCheckBox("Copy to clipboard")
            self.clipboard_check.setChecked(True)
            out_method_layout.addWidget(self.clipboard_check)
            self.webhook_check = QCheckBox("Send to webhook")
            self.webhook_check.setChecked(False)
            out_method_layout.addWidget(self.webhook_check)
            self.webhook_url = QComboBox()
            self.webhook_url.setEditable(True)
            self.webhook_url.addItems(["http://localhost:8080/webhook", "https://api.example.com/voice"])
            out_method_layout.addWidget(QLabel("Webhook URL:"))
            out_method_layout.addWidget(self.webhook_url)
            output_method_group.setLayout(out_method_layout)
            layout.addWidget(output_method_group)
            
            text_enhance_group = QGroupBox("✨ Text Enhancement")
            text_layout = QVBoxLayout()
            self.capitalize_check = QCheckBox("Auto-capitalize first letter of sentences")
            self.capitalize_check.setChecked(True)
            text_layout.addWidget(self.capitalize_check)
            self.punctuate_check = QCheckBox("Auto-add punctuation")
            self.punctuate_check.setChecked(True)
            text_layout.addWidget(self.punctuate_check)
            self.numbers_check = QCheckBox("Convert spelled numbers (two → 2)")
            self.numbers_check.setChecked(True)
            text_layout.addWidget(self.numbers_check)
            self.filler_check = QCheckBox("Remove filler words (um, uh, like)")
            self.filler_check.setChecked(False)
            text_layout.addWidget(self.filler_check)
            text_enhance_group.setLayout(text_layout)
            layout.addWidget(text_enhance_group)
            
            format_group = QGroupBox("📋 Formatting")
            fmt_layout = QVBoxLayout()
            self.newline_check = QCheckBox("Convert double spaces to newlines")
            self.newline_check.setChecked(True)
            fmt_layout.addWidget(self.newline_check)
            self.unicode_check = QCheckBox("Clean unicode characters")
            self.unicode_check.setChecked(True)
            fmt_layout.addWidget(self.unicode_check)
            self.strip_check = QCheckBox("Strip extra whitespace")
            self.strip_check.setChecked(True)
            fmt_layout.addWidget(self.strip_check)
            format_group.setLayout(fmt_layout)
            layout.addWidget(format_group)
            
            layout.addStretch()
            widget.setLayout(layout)
            return widget
        
        def _create_advanced_tab(self):
            widget = QWidget()
            layout = QVBoxLayout()
            
            realtime_group = QGroupBox("⚡ Real-time")
            realtime_layout = QVBoxLayout()
            self.realtime_check = QCheckBox("Enable real-time transcription")
            self.realtime_check.setChecked(False)
            realtime_layout.addWidget(self.realtime_check)
            self.live_typing_check = QCheckBox("Live typing (type while speaking)")
            self.live_typing_check.setChecked(False)
            realtime_layout.addWidget(self.live_typing_check)
            self.min_length = QSpinBox()
            self.min_length.setMinimum(1)
            self.min_length.setMaximum(50)
            self.min_length.setValue(5)
            realtime_layout.addWidget(QLabel("Min chars before typing:"))
            realtime_layout.addWidget(self.min_length)
            realtime_group.setLayout(realtime_layout)
            layout.addWidget(realtime_group)
            
            api_group = QGroupBox("🌐 API Server")
            api_layout = QVBoxLayout()
            self.api_enable = QCheckBox("Enable HTTP API server")
            self.api_enable.setChecked(True)
            api_layout.addWidget(self.api_enable)
            self.api_host = QComboBox()
            self.api_host.setEditable(True)
            self.api_host.addItems(["127.0.0.1", "0.0.0.0", "localhost"])
            self.api_host.setCurrentIndex(0)
            api_layout.addWidget(QLabel("API Host:"))
            api_layout.addWidget(self.api_host)
            self.api_port = QSpinBox()
            self.api_port.setMinimum(1024)
            self.api_port.setMaximum(65535)
            self.api_port.setValue(8765)
            api_layout.addWidget(QLabel("API Port:"))
            api_layout.addWidget(self.api_port)
            self.api_auth = QCheckBox("Require API key")
            self.api_auth.setChecked(False)
            api_layout.addWidget(self.api_auth)
            api_group.setLayout(api_layout)
            layout.addWidget(api_group)
            
            notify_group = QGroupBox("🔔 Notifications")
            notify_layout = QVBoxLayout()
            self.notify_check = QCheckBox("Show tray notifications")
            self.notify_check.setChecked(True)
            notify_layout.addWidget(self.notify_check)
            self.notify_errors = QCheckBox("Notify on errors")
            self.notify_errors.setChecked(True)
            notify_layout.addWidget(self.notify_errors)
            self.notify_complete = QCheckBox("Notify on transcription complete")
            self.notify_complete.setChecked(False)
            notify_layout.addWidget(self.notify_complete)
            notify_group.setLayout(notify_layout)
            layout.addWidget(notify_group)
            
            history_group = QGroupBox("📜 History")
            hist_layout = QVBoxLayout()
            self.history_enabled = QCheckBox("Keep transcription history")
            self.history_enabled.setChecked(True)
            hist_layout.addWidget(self.history_enabled)
            self.history_max = QSpinBox()
            self.history_max.setMinimum(10)
            self.history_max.setMaximum(1000)
            self.history_max.setValue(100)
            hist_layout.addWidget(QLabel("Max history entries:"))
            hist_layout.addWidget(self.history_max)
            hist_layout.addWidget(QLabel("History file: ~/.config/nxyme-dictate/history.json"))
            history_group.setLayout(hist_layout)
            layout.addWidget(history_group)
            
            layout.addStretch()
            widget.setLayout(layout)
            return widget
        


    class DictationUI:
        def __init__(self):
            self._app: Optional[QApplication] = None
            self._tray: Optional[TrayIconManager] = None
            self._settings: Optional[SettingsDialog] = None
            self._emitter = SignalEmitter()

        def initialize(self, on_toggle: Callable, on_quit: Callable) -> bool:
            import sys
            self._app = QApplication.instance()
            if self._app is None:
                self._app = QApplication(sys.argv)
                self._app.setQuitOnLastWindowClosed(False)
                self._app.setDesktopFileName("nxyme-dictate")

            self._tray = TrayIconManager()
            if not self._tray.setup(self._app, on_toggle, on_quit):
                return False

            self._tray.set_callback("show_settings", self.show_settings)

            self._emitter.state_changed.connect(self._tray.update_state)
            self._emitter.text_received.connect(lambda t: self._tray.notify_text(t))

            self._settings = SettingsDialog()
            logger.info("Enhanced UI initialized")
            return True

        def update_state(self, state: str):
            self._emitter.state_changed.emit(state)

        def notify_text(self, text: str, latency_ms: int = 0):
            self._tray.notify_text(text, latency_ms)

        def notify(self, message: str):
            self._tray.show_message("⚠️ N-Xyme Dictate", message, QSystemTrayIcon.MessageIcon.Warning)

        def update_audio_level(self, level: float):
            self._tray.update_audio_level(level)

        def set_stats(self, sessions: int, words: int, chars: int, latency_ms: int = 0):
            self._tray.set_stats(sessions, words, chars, latency_ms)

        def show_settings(self):
            if self._settings:
                self._settings.show()
                self._settings.raise_()
                self._settings.activateWindow()

        def run(self):
            if self._app:
                self._app.exec()

        def quit(self):
            if self._app:
                self._app.quit()

else:
    TrayIconManager = None
    SettingsDialog = None
    DictationUI = None
    SignalEmitter = None


def create_ui(on_toggle: Callable, on_quit: Callable) -> Optional[object]:
    if not PYQT6_AVAILABLE:
        logger.warning("Cannot create UI - PyQt6 not available")
        return None

    ui = DictationUI()
    if ui.initialize(on_toggle, on_quit):
        return ui
    return None