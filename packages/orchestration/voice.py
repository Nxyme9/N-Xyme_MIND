"""
Voice/STT — Speech-to-text input module.

Ported from: services/voiceStreamSTT.ts (Claude Code)
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class VoiceState(str, Enum):
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"
    TRANSCRIBING = "transcribing"
    ERROR = "error"


@dataclass
class TranscriptResult:
    """Speech transcription result."""
    text: str
    is_final: bool
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.time)
    duration_ms: int = 0


@dataclass
class VoiceConfig:
    """Voice input configuration."""
    sample_rate: int = 16000
    channels: int = 1
    codec: str = "pcm_s16le"
    endpoint: str = "wss://api.anthropic.com/api/ws/speech_to_text/voice_stream"
    language: str = "en-US"
    timeout: float = 30.0
    keepalive_interval: float = 8.0


class AudioSource(ABC):
    """Audio source interface."""

    @abstractmethod
    def start(self) -> bool:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass

    @abstractmethod
    def read(self, size: int) -> Optional[bytes]:
        pass

    @abstractmethod
    def is_active(self) -> bool:
        pass


class MicrophoneSource(AudioSource):
    """Microphone audio source using pyaudio or sounddevice."""

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self._stream = None
        self._active = False
        self._audio = None

    def start(self) -> bool:
        """Start microphone capture."""
        try:
            import sounddevice as sd
            self._audio = sd
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                blocksize=1024,
                callback=self._callback,
            )
            self._stream.start()
            self._active = True
            logger.info("Microphone started")
            return True
        except ImportError:
            logger.warning("sounddevice not available, trying pyaudio")
            return self._start_pyaudio()

    def _start_pyaudio(self) -> bool:
        """Start with pyaudio fallback."""
        try:
            import pyaudio
            self._audio = pyaudio.PyAudio()
            self._stream = self._audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=1024,
            )
            self._active = True
            logger.info("PyAudio microphone started")
            return True
        except ImportError:
            logger.error("No audio library available")
            return False

    def _callback(self, indata, frames, time_info, status):
        pass

    def stop(self) -> None:
        """Stop microphone capture."""
        self._active = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def read(self, size: int) -> Optional[bytes]:
        """Read audio data."""
        if not self._active or not self._stream:
            return None

        try:
            if hasattr(self._stream, "read"):
                return self._stream.read(size, exception_on_overflow=False)
        except Exception as e:
            logger.error(f"Audio read error: {e}")
        return None

    def is_active(self) -> bool:
        return self._active


class FileSource(AudioSource):
    """File-based audio source for testing."""

    def __init__(self, path: Path):
        self.path = path
        self._file = None
        self._active = False

    def start(self) -> bool:
        try:
            self._file = open(self.path, "rb")
            self._active = True
            return True
        except Exception as e:
            logger.error(f"File open error: {e}")
            return False

    def stop(self) -> None:
        self._active = False
        if self._file:
            self._file.close()
            self._file = None

    def read(self, size: int) -> Optional[bytes]:
        if not self._active or not self._file:
            return None
        return self._file.read(size)

    def is_active(self) -> bool:
        return self._active


class VoiceCallbacks:
    """Voice input callbacks."""

    def __init__(
        self,
        on_transcript: Optional[Callable[[str, bool], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        on_ready: Optional[Callable[[], None]] = None,
        on_close: Optional[Callable[[], None]] = None,
    ):
        self.on_transcript = on_transcript
        self.on_error = on_error
        self.on_ready = on_ready
        self.on_close = on_close


class VoiceStream:
    """Voice stream handler for STT."""

    def __init__(
        self,
        config: Optional[VoiceConfig] = None,
        callbacks: Optional[VoiceCallbacks] = None,
    ):
        self.config = config or VoiceConfig()
        self.callbacks = callbacks or VoiceCallbacks()
        self.state = VoiceState.IDLE
        self._source: Optional[AudioSource] = None
        self._ws = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def connect(self) -> bool:
        """Connect to voice stream endpoint."""
        try:
            import websockets

            self._ws = websockets.connect(
                self.config.endpoint,
                extra_headers=self._get_headers(),
            )
            self.state = VoiceState.IDLE

            if self.callbacks.on_ready:
                self.callbacks.on_ready()

            return True
        except ImportError:
            logger.warning("websockets not available")
            return False
        except Exception as e:
            logger.error(f"Voice connect error: {e}")
            if self.callbacks.on_error:
                self.callbacks.on_error(str(e))
            return False

    def _get_headers(self) -> dict:
        """Get authentication headers."""
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
        }

    def _get_token(self) -> str:
        """Get OAuth token (placeholder)."""
        return ""

    def start(self, source: Optional[AudioSource] = None) -> bool:
        """Start voice capture and streaming."""
        self._source = source or MicrophoneSource(
            self.config.sample_rate,
            self.config.channels,
        )

        if not self._source.start():
            self.state = VoiceState.ERROR
            return False

        if not self.connect():
            self._source.stop()
            self.state = VoiceState.ERROR
            return False

        self._running = True
        self.state = VoiceState.RECORDING
        self._thread = threading.Thread(target=self._stream_loop, daemon=True)
        self._thread.start()

        return True

    def _stream_loop(self) -> None:
        """Main streaming loop."""
        while self._running:
            if not self._source or not self._source.is_active():
                break

            audio_data = self._source.read(1024)
            if audio_data and self._ws:
                try:
                    self._ws.send(audio_data)
                except Exception as e:
                    logger.error(f"Stream send error: {e}")
                    break

            time.sleep(0.01)

        self._cleanup()

    def stop(self) -> None:
        """Stop voice capture."""
        self._running = False

        if self._ws:
            try:
                self._ws.send('{"type":"CloseStream"}')
            except Exception:
                pass

        if self._source:
            self._source.stop()

        self.state = VoiceState.IDLE

    def _cleanup(self) -> None:
        """Clean up resources."""
        if self._source:
            self._source.stop()
            self._source = None

        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None

        if self.callbacks.on_close:
            self.callbacks.on_close()

    def is_active(self) -> bool:
        return self._running and self.state == VoiceState.RECORDING


class VoiceInput:
    """High-level voice input handler."""

    def __init__(self, config: Optional[VoiceConfig] = None):
        self.config = config or VoiceConfig()
        self.stream: Optional[VoiceStream] = None
        self._transcripts: list[TranscriptResult] = []

    def start(
        self,
        on_transcript: Optional[Callable[[str, bool], None]] = None,
    ) -> bool:
        """Start voice input."""
        callbacks = VoiceCallbacks(
            on_transcript=on_transcript or self._default_transcript,
            on_error=self._default_error,
        )
        self.stream = VoiceStream(self.config, callbacks)
        return self.stream.start()

    def stop(self) -> None:
        """Stop voice input."""
        if self.stream:
            self.stream.stop()

    def _default_transcript(self, text: str, is_final: bool) -> None:
        result = TranscriptResult(text=text, is_final=is_final)
        self._transcripts.append(result)

    def _default_error(self, error: str) -> None:
        logger.error(f"Voice error: {error}")

    def get_transcripts(self) -> list[TranscriptResult]:
        """Get all transcripts."""
        return self._transcripts

    def clear_transcripts(self) -> None:
        """Clear transcripts."""
        self._transcripts.clear()


def start_voice_input(
    on_transcript: Optional[Callable[[str, bool], None]] = None,
) -> Optional[VoiceInput]:
    """Start voice input (convenience function)."""
    voice = VoiceInput()
    if voice.start(on_transcript):
        return voice
    return None


__all__ = [
    "VoiceState",
    "TranscriptResult",
    "VoiceConfig",
    "AudioSource",
    "MicrophoneSource",
    "FileSource",
    "VoiceCallbacks",
    "VoiceStream",
    "VoiceInput",
    "start_voice_input",
]
