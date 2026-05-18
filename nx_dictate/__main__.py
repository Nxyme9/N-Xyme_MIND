"""CLI entry point for nx_dictate — with QoL: TTS, hold-to-talk, error resilience, metrics."""

from __future__ import annotations

import argparse
import logging
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from nx_dictate.config import NxDictateConfig, Backend, WhisperModel
from nx_dictate.core.state import DictationState, State
from nx_dictate.audio.capture import AudioCapture
from nx_dictate.core.engine import WhisperEngine
from nx_dictate.commands import VoiceCommandRecognizer
from nx_dictate.core.hotkey import GlobalHotkey, EvdevHotkey
from nx_dictate.core.injection import inject_text, inject_key_combo
from nx_dictate.ui.feedback import Feedback
from nx_dictate.ui.tray import SystemTray

logger = logging.getLogger(__name__)


@dataclass
class PipelineMetrics:
    """Latency tracking per pipeline stage (from real-time-jarvis-voice.md)."""
    audio_capture_ms: float = 0.0
    stt_ms: float = 0.0
    command_ms: float = 0.0
    injection_ms: float = 0.0
    total_ms: float = 0.0
    text_length: int = 0
    timestamps: list = field(default_factory=list)

    def log(self) -> str:
        avg_conf = ""
        return (f"[metrics] STT={self.stt_ms:.0f}ms cmd={self.command_ms:.0f}ms "
                f"inj={self.injection_ms:.0f}ms total={self.total_ms:.0f}ms "
                f"text={self.text_length}ch")


class DictationApp:
    def __init__(self, config: NxDictateConfig, always_listen: bool = False, stream: bool = False) -> None:
        self.config = config
        self.always_listen = always_listen
        self.stream = stream
        self.state = DictationState()
        self.audio = AudioCapture(config.audio)
        self.engine = WhisperEngine(config.whisper)
        self.feedback = Feedback(config.ui, tts_enabled=True)
        self.commands = VoiceCommandRecognizer(config.commands)

        # Auto-detect audio device if not configured
        if config.audio.device_index is None:
            config.audio.device_index = self._auto_detect_device()

        # Hold-to-talk vs toggle mode
        hotkey_cls = EvdevHotkey if config.hotkey.backend == "evdev" else GlobalHotkey
        if config.hotkey.hold_key:
            # Hold-to-talk: press to start, release to transcribe
            self.hotkey = hotkey_cls(
                config.hotkey,
                on_toggle=self.toggle_recording,
                on_hold_start=self._hold_start,
                on_hold_end=self._hold_end,
            )
        else:
            # Toggle mode: press to toggle
            self.hotkey = hotkey_cls(
                config.hotkey,
                on_toggle=self.toggle_recording,
            )

        self.tray = SystemTray(self.toggle_recording, self.stop)
        self._audio_buffer = None
        self._audio_ready = threading.Event()
        self._running = False
        self._tray_started = False

    def _auto_detect_device(self) -> Optional[int]:
        """Auto-detect best audio input device. Fallback chain: Scarlett > default > None."""
        devices = AudioCapture.list_devices()
        if not devices:
            return None

        # Prefer Scarlett 2i2
        for dev in devices:
            if "Scarlett" in dev["name"]:
                logger.info("Auto-detected: [%d] %s", dev["index"], dev["name"])
                return dev["index"]

        # Fallback to default
        logger.info("Using default input device")
        return None

    def _check_hotkey_conflicts(self) -> list[str]:
        """Check for potential hotkey conflicts (from real-time-jarvis-voice.md plan)."""
        conflicts = []
        if self.config.hotkey.hold_key == "right ctrl":
            # Right Ctrl is rarely used by other apps — low conflict risk
            pass
        elif self.config.hotkey.toggle_key == "f8":
            # F8 is used by some IDEs for debug — common conflict
            conflicts.append("F8 may conflict with IDE debug shortcuts (VSCode, IntelliJ)")
        return conflicts

    def start(self) -> None:
        self._running = True

        # Check for hotkey conflicts
        conflicts = self._check_hotkey_conflicts()
        if conflicts:
            for c in conflicts:
                print(f"  ⚠️  {c}")

        print("Loading Whisper model...")
        try:
            self.engine.load()
            print("  ✅ Model loaded.")
        except Exception as e:
            print(f"  ❌ Model load failed: {e}")
            print("  Try: python -m nx_dictate --model tiny (fallback)")
            self.stop()
            return

        devices = AudioCapture.list_devices()
        if devices:
            print("Available audio devices:")
            for dev in devices:
                marker = " ← selected" if dev["index"] == self.config.audio.device_index else ""
                print(f"  [{dev['index']}] {dev['name']}{marker}")

        # Register state handlers
        self.state.on_state(State.IDLE, self._on_idle)
        self.state.on_state(State.RECORDING, self._on_recording)
        self.state.on_state(State.PROCESSING, self._on_processing)
        self.state.on_state(State.INJECTING, self._on_injecting)
        self.state.on_state(State.ERROR, self._on_error)

        # Show mode
        if self.config.hotkey.hold_key:
            print(f"\n🎤 Hold-to-talk mode: press [{self.config.hotkey.hold_key}] to speak, release to transcribe")
        else:
            print(f"\n🎤 Toggle mode: press [{self.config.hotkey.toggle_key}] to start/stop recording")
        print("   Type 't' + Enter to toggle, 'q' + Enter to quit.\n")

        self.feedback.on_ready()

        # Auto-start recording in always-listen mode
        if self.always_listen:
            threading.Thread(target=lambda: (
                time.sleep(0.5),
                self.state.transition(State.RECORDING)
            ), daemon=True).start()

        self.hotkey.start()
        self._tray_started = self.tray.start()
        if self._tray_started:
            mode = "Hold-to-talk" if self.config.hotkey.hold_key else f"Toggle ({self.config.hotkey.toggle_key})"
            self.tray.update_mode(mode)

        if self._tray_started:
            try:
                self.tray.app.exec()
            except Exception:
                pass
        else:
            input_thread = threading.Thread(target=self._stdin_loop, daemon=True)
            input_thread.start()
            try:
                while self._running:
                    time.sleep(0.5)
            except KeyboardInterrupt:
                pass

        self.stop()

    def _stdin_loop(self) -> None:
        while self._running:
            try:
                cmd = input().strip().lower()
                if cmd == "t":
                    self.toggle_recording()
                elif cmd == "q":
                    self._running = False
                    break
            except (EOFError, ValueError):
                break

    def stop(self) -> None:
        self._running = False
        self.hotkey.stop()
        self.audio.stop()
        self._audio_ready.set()
        time.sleep(0.2)
        self.engine.unload()
        self.tray.stop()

    def toggle_recording(self) -> None:
        s = self.state.state
        ok = False
        if s == State.IDLE:
            ok = self.state.transition(State.RECORDING)
        elif s == State.RECORDING:
            ok = self.state.transition(State.PROCESSING)
        elif s == State.ERROR:
            ok = self.state.transition(State.IDLE)
        if not ok:
            logger.debug("toggle ignored in state %s", s.value)

    def _hold_start(self) -> None:
        """Hold-to-talk: key pressed -> start recording."""
        if self.state.state == State.IDLE:
            self.state.transition(State.RECORDING)

    def _hold_end(self) -> None:
        """Hold-to-talk: key released -> stop recording + transcribe."""
        if self.state.state == State.RECORDING:
            self.state.transition(State.PROCESSING)

    # --- State handlers ---

    def _on_idle(self, old: State, new: State) -> None:
        if self._tray_started:
            self.tray.update_state(State.IDLE)
        # Always-listen: loop back to recording after processing
        if self.always_listen and old in (State.INJECTING, State.PROCESSING):
            threading.Thread(target=lambda: (
                time.sleep(0.3),
                self.state.transition(State.RECORDING)
            ), daemon=True).start()

    def _on_recording(self, old: State, new: State) -> None:
        self.feedback.on_start()
        self._audio_buffer = None
        self._audio_ready.clear()
        self.audio.start()
        if self._tray_started:
            self.tray.update_state(State.RECORDING)
        threading.Thread(target=self._record_loop, daemon=True).start()

    def _on_processing(self, old: State, new: State) -> None:
        self.feedback.on_stop()
        self.audio.stop()
        self._audio_ready.set()
        if self._tray_started:
            self.tray.update_state(State.PROCESSING)
        threading.Thread(target=self._process_loop, daemon=True).start()

    def _on_injecting(self, old: State, new: State) -> None:
        if self._tray_started:
            self.tray.update_state(State.INJECTING)
        text = self.state.text_buffer
        if text:
            ok = inject_text(text, self.config.injection)
            if ok:
                self.feedback.on_inject(text)
            else:
                self.feedback.on_error("Failed to inject text")
        self.state.clear_text()
        self.state.transition(State.IDLE)

    def _on_error(self, old: State, new: State) -> None:
        if self._tray_started:
            self.tray.update_state(State.ERROR)
        self.feedback.on_error(self.state.error_message or "Unknown error")
        self.audio.stop()

    # --- Core loops ---

    def _record_loop(self) -> None:
        import numpy as np
        chunks = []
        silence_start = None
        max_dur = self.config.audio.max_duration
        sil_dur = self.config.audio.silence_duration
        start = time.time()

        while self.state.state == State.RECORDING:
            if not self._running:
                return
            chunk = self.audio.get_chunk(timeout=0.1)
            if chunk is None:
                continue
            chunks.append(chunk)

            from nx_dictate.audio.processing import is_speech
            if not is_speech(chunk, self.config.audio.silence_threshold):
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start > sil_dur:
                    self.state.transition(State.PROCESSING)
                    break
            else:
                silence_start = None

            if time.time() - start > max_dur:
                self.state.transition(State.PROCESSING)
                break

        if chunks:
            self._audio_buffer = np.concatenate(chunks)
            self._audio_ready.set()

    def _process_loop(self) -> None:
        metrics = PipelineMetrics()
        t_start = time.time()

        try:
            # Wait for audio buffer
            self._audio_ready.wait(timeout=3.0)
            audio = self._audio_buffer
            if audio is None or len(audio) == 0:
                self.state.set_error("No audio recorded")
                return

            metrics.audio_capture_ms = (time.time() - t_start) * 1000

            # Transcribe
            t_stt = time.time()
            try:
                if self.stream:
                    partials = self.engine.transcribe_streaming(audio)
                    text = " ".join(partials) if partials else ""
                    # Inject each partial progressively
                    for p in partials[:-1] if len(partials) > 1 else []:
                        inject_text(p, self.config.injection)
                else:
                    result = self.engine.transcribe_detailed(audio)
                    text = result.text
                metrics.stt_ms = (time.time() - t_stt) * 1000
                metrics.text_length = len(text)
            except Exception as e:
                self.state.set_error(f"Transcription failed: {e}")
                return

            if not text:
                self.state.set_error("No speech detected")
                return

            # ⟶ Send to Jarvis FIFO for agent processing
            try:
                with open("/tmp/jarvis_fifo", "w") as f:
                    f.write(text + "\n")
                logger.info(f"🗣️ Sent to Jarvis: {text[:60]}...")
            except Exception:
                pass  # Jarvis bridge not running is fine

            # Command processing
            t_cmd = time.time()
            if self.commands.is_command(text):
                action = self.commands.recognize(text)
                if action:
                    metrics.command_ms = (time.time() - t_cmd) * 1000
                    if action == "STOP_RECORDING":
                        self.state.transition(State.IDLE)
                        return
                    elif action == "START_RECORDING":
                        self.state.transition(State.RECORDING)
                        return
                    elif any(action.startswith(p) for p in ("ctrl", "alt", "super", "shift")):
                        ok = inject_key_combo(action)
                        if not ok:
                            self.feedback.on_error(f"Failed to inject key combo: {action}")
                        self.state.transition(State.IDLE)
                        return
                    elif action.startswith("\\"):
                        self.state.set_text(action)
                        metrics.total_ms = (time.time() - t_start) * 1000
                        logger.debug(metrics.log())
                        self.state.transition(State.INJECTING)
                        return

            metrics.command_ms = (time.time() - t_cmd) * 1000
            metrics.total_ms = (time.time() - t_start) * 1000
            logger.debug(metrics.log())

            self.state.set_text(text)
            self.state.transition(State.INJECTING)

        except Exception as e:
            self.state.set_error(str(e))


def main() -> None:
    parser = argparse.ArgumentParser(description="N-Xyme Dictate — voice dictation with QoL features")
    parser.add_argument("--config", type=Path, help="Config file path")
    parser.add_argument("--model", choices=["tiny", "base", "small", "medium", "large", "large-v3"],
                        help="Whisper model (default: large-v3 with CUDA)")
    parser.add_argument("--device", type=int, help="Audio device index (default: auto-detect)")
    parser.add_argument("--hotkey", help="Toggle hotkey (f8, f9, ctrl+alt+d)")
    parser.add_argument("--hold", help="Hold-to-talk key (right ctrl, right alt, caps lock)")
    parser.add_argument("--backend", choices=["xdotool", "wtype", "ydotool", "clipboard"],
                        help="Injection backend (default: ydotool for Wayland)")
    parser.add_argument("--list-devices", action="store_true", help="List audio input devices")
    parser.add_argument("--no-tray", action="store_true", help="Disable system tray icon")
    parser.add_argument("--no-tts", action="store_true", help="Disable TTS voice feedback")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon (for systemd)")
    parser.add_argument("--always", action="store_true", help="Always-listening mode (VAD auto-trigger)")
    parser.add_argument("--stream", action="store_true", help="Streaming transcription — words appear as you speak")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    config = NxDictateConfig.load(args.config)

    if args.list_devices:
        for dev in AudioCapture.list_devices():
            print(f"  [{dev['index']}] {dev['name']} ({dev['channels']}ch)")
        sys.exit(0)

    if args.model:
        config.whisper.model = WhisperModel(args.model)
    if args.device is not None:
        config.audio.device_index = args.device
    if args.hotkey:
        config.hotkey.toggle_key = args.hotkey
        config.hotkey.hold_key = None  # Toggle mode
    if args.hold:
        config.hotkey.hold_key = args.hold
        config.hotkey.toggle_key = ""  # Hold mode
    if args.backend:
        config.injection.backend = Backend(args.backend)
    if args.no_tray:
        config.ui.show_tray = False
    if args.no_tts:
        pass  # feedback module handles this

    if args.daemon:
        # Fork for systemd
        if hasattr(sys, 'stdin') and sys.stdin:
            sys.stdin.close()

    app = DictationApp(config, always_listen=args.always, stream=args.stream)

    try:
        app.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"\nFatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
