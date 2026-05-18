"""Feedback system: beeps + desktop notifications + optional TTS voice."""
from __future__ import annotations

import subprocess
import threading
from pathlib import Path
from typing import Optional

from nx_dictate.config import UIConfig


class Feedback:
    """Multi-modal feedback: beep + notify + optional TTS."""

    def __init__(self, config: UIConfig, tts_enabled: bool = True):
        self.config = config
        self.tts_enabled = tts_enabled
        self._tts_available = False

        if tts_enabled:
            try:
                from nx_dictate.ui.speech import say
                self._say = say
                self._tts_available = True
            except ImportError:
                pass

    def notify(self, message: str, urgency: str = "normal"):
        """Desktop notification."""
        if not self.config.notification_enabled:
            return
        threading.Thread(
            target=lambda: subprocess.run(
                ["notify-send", "-u", urgency, "Nx Dictate", message],
                capture_output=True,
            ),
            daemon=True,
        ).start()

    def beep(self, frequency: int = 800, duration_ms: int = 150):
        """Play a beep via paplay or beep."""
        if not self.config.sound_enabled:
            return

        def _play():
            bell = Path(__file__).parent / "bell.oga"
            if bell.exists():
                subprocess.run(["paplay", str(bell)], capture_output=True)
            else:
                subprocess.run(
                    ["paplay", "--volume=0.5", "/usr/share/sounds/freedesktop/stereo/complete.oga"],
                    capture_output=True,
                )

        threading.Thread(target=_play, daemon=True).start()

    def speak(self, phrase_key: str):
        """TTS voice feedback. Falls back to beep if unavailable."""
        if not self._tts_available or not self.tts_enabled:
            return
        try:
            from nx_dictate.ui.speech import PHRASES
            text = PHRASES.get(phrase_key, phrase_key)
            self._say(text)
        except Exception:
            pass

    def on_start(self):
        """Recording started."""
        self.beep(600, 100)
        self.notify("Recording started")
        self.speak("listening")

    def on_stop(self):
        """Recording stopped."""
        self.beep(800, 150)
        self.notify("Recording stopped")
        self.speak("processing")

    def on_inject(self, text: str):
        """Text injected successfully."""
        preview = text[:50] + "..." if len(text) > 50 else text
        self.notify(f"Injected: {preview}")
        self.speak("injected")

    def on_error(self, message: str):
        """Error occurred."""
        self.beep(400, 300)
        self.notify(message, urgency="critical")
        if self._tts_available:
            self._say("Error")

    def on_ready(self):
        """System ready."""
        self.speak("ready")

    def on_send_to_ai(self, routed: str, confidence: float):
        """Dictation routed to AI. Beep only."""
        self.beep(500, 80)
        self.speak("sending")
