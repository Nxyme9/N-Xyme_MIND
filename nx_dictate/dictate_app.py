# N-Xyme Dictate - Main Application
# Uses existing nx_engine whisper integration

from __future__ import annotations

import logging
import threading
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("nxyme_dictate.dictate")


class DictationApp:
    """Main dictation application using nx_engine whisper."""

    def __init__(self):
        # Components
        self._engine = None
        self._audio = None
        self._hotkey = None
        self._state = None

        self._on_state_change = None
        self._on_text = None
        self._on_settings = None

        # Audio storage
        self._current_audio = []

        # Thread safety
        self._lock = threading.Lock()
        self._transcription_thread = None

    @property
    def state(self):
        return self._state.state if self._state else None

    @property
    def engine_name(self) -> str:
        return self._engine.model_name if self._engine else "none"

    def initialize(self) -> bool:
        """Initialize all components."""
        logger.info("Initializing N-Xyme Dictate...")

        # Import here to avoid circular dependency
        from .core.engine import (
            get_engine,
            auto_select_model,
            get_gpu_vram_gb,
            DictationConfig,
        )
        from .core.audio import AudioPipeline, AudioConfig
        from .core.hotkey import create_default_hotkey
        from .core.state import StateMachine, DictationState

        # Initialize state
        self._state = StateMachine()

        # Initialize whisper engine via nx_engine
        vram = get_gpu_vram_gb()
        model = auto_select_model(vram)
        logger.info(f"Using model: {model} ({vram:.1f}GB VRAM)")

        config = DictationConfig(
            model=model,
            device="auto",
        )

        self._engine = get_engine(config)
        if not self._engine.load():
            logger.error("Failed to load whisper engine")
            return False

        # Initialize hotkey
        self._hotkey = create_default_hotkey(
            on_press=self._on_hotkey_press,
            on_release=self._on_hotkey_release,
        )

        # Setup state callbacks
        self._state.set_state_change_callback(self._handle_state_change)

        logger.info(f"N-Xyme Dictate ready: {model}")
        return True

    def _on_hotkey_press(self) -> None:
        """Handle hotkey press."""
        if self._state and self._state.is_ready:
            self._start_recording()

    def _on_hotkey_release(self) -> None:
        """Handle hotkey release."""
        if self._state and self._state.is_recording:
            self._stop_recording()

    def toggle_recording(self) -> bool:
        """Toggle recording with state validation. Returns True if successful."""
        if not self._state:
            logger.warning("State not initialized")
            return False
        if self._state.is_recording:
            return self._stop_recording()
        elif self._state.is_ready:
            return self._start_recording()
        elif self._state.is_processing:
            logger.warning("Cannot toggle: currently processing transcription")
            return False
        elif self._state.has_error:
            logger.warning("Error state detected, resetting")
            if not self._state.reset():
                logger.error("Failed to reset from error state")
                return False
            return self._start_recording()
        else:
            logger.warning(f"Cannot toggle from unknown state: {self._state.state}")
            return False

    def _start_recording(self) -> bool:
        """Start audio recording. Returns True if successful."""
        from .core.audio import AudioPipeline, AudioConfig

        # Validate state before attempting transition
        if not self._state or not self._state.is_ready:
            logger.warning(f"Cannot start recording from state: {self._state.state if self._state else 'None'}")
            return False

        if self._audio:
            self._audio.stop()

        config = AudioConfig()
        self._audio = AudioPipeline(config)
        self._audio.start()
        self._current_audio = []

        if not self._state.start_recording():
            logger.error("Failed to transition to recording state")
            return False

        logger.info("Recording started")
        return True

    def _stop_recording(self) -> bool:
        """Stop recording and transcribe. Returns True if successful."""
        if not self._audio:
            return False

        # Validate state before attempting transition
        if not self._state or not self._state.is_recording:
            logger.warning(f"Cannot stop recording from state: {self._state.state if self._state else 'None'}")
            return False

        audio_data, _ = self._audio.stop()
        if audio_data is None or len(audio_data) == 0:
            logger.warning("No audio captured")
            if self._state and not self._state.reset():
                logger.error("Failed to reset state after no audio")
            return False

        self._current_audio.append(audio_data)

        if not self._state.stop_recording():
            logger.error("Failed to transition to processing state")
            return False

        with self._lock:
            if self._transcription_thread is not None:
                logger.warning("Transcription already in progress")
            self._transcription_thread = threading.Thread(
                target=self._do_transcribe,
                args=(audio_data,),
                daemon=True,
            )
            self._transcription_thread.start()
        return True

    def _do_transcribe(self, audio) -> None:
        """Perform transcription."""
        if not self._engine:
            if self._state:
                self._state.error_transcription()
            return

        try:
            from .audio_processing import preprocess_audio
            audio = preprocess_audio(audio)
            
            text = self._engine.transcribe(audio) or ""
            if not text:
                logger.warning("Transcription returned empty text")
                if self._state:
                    self._state.complete_transcription()
                return
            logger.info(f"Transcribed: {text[:50]}...")

            if text and not text.startswith("["):
                from .commands import create_command_recognizer
                from .tts import get_audio_feedback
                from .injection import copy_and_paste

                cmd_recognizer = create_command_recognizer()
                processed_text, applied = cmd_recognizer.process(text)
                if applied:
                    logger.info(f"Applied voice commands: {applied}")

                try:
                    paste_success = copy_and_paste(processed_text)
                    if paste_success:
                        logger.info("Text injected via keyboard")
                    else:
                        logger.warning("Injection failed, text on clipboard")
                except Exception as e:
                    logger.warning(f"Injection error: {e}")

                if self._on_text:
                    self._on_text(processed_text)

                tts = get_audio_feedback()
                tts.speak("done")

            if self._state:
                self._state.complete_transcription()

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            if self._state:
                self._state.error_transcription()

    def _handle_state_change(self, state) -> None:
        """Handle state change."""
        state_str = state.value if hasattr(state, 'value') else str(state)
        if self._on_state_change:
            self._on_state_change(state_str)

    def set_state_callback(self, callback: callable) -> None:
        self._on_state_change = callback

    def set_text_callback(self, callback: callable) -> None:
        self._on_text = callback

    def set_settings_callback(self, callback: callable) -> None:
        self._on_settings = callback

    def show_settings(self) -> None:
        if self._on_settings:
            self._on_settings()

    def on_settings_button(self):
        self.show_settings()

    def shutdown(self) -> None:
        """Clean shutdown."""
        logger.info("Shutting down...")

        with self._lock:
            if self._transcription_thread is not None:
                logger.warning("Waiting for transcription to complete...")
                self._transcription_thread.join(timeout=10)
                if self._transcription_thread.is_alive():
                    logger.warning("Transcription timeout, forcing shutdown")

        if self._audio:
            self._audio.stop()

        if self._hotkey:
            self._hotkey.stop()

        if self._engine:
            self._engine.unload()

        logger.info("Shutdown complete")


def main():
    """Entry point."""
    app = DictationApp()

    if not app.initialize():
        logger.error("Initialization failed")
        return

    try:
        logger.info("N-Xyme Dictate running... (press hotkey to transcribe)")

        # Keep running
        import time

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Interrupted")

    finally:
        app.shutdown()


if __name__ == "__main__":
    main()
