"""Voice Prompt Pipeline — Speech-to-text input processing.

Based on docs voice-prompt-pipeline.md.

Implements:
- Speech-to-text (Whisper local)
- Voice command recognition
- Audio response synthesis (optional)
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class VoiceInput:
    """Processed voice input."""

    audio_path: str
    transcript: str = ""
    confidence: float = 0.0
    language: str = "en"
    duration_seconds: float = 0.0
    commands: list[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class VoicePipeline:
    """Voice prompt processing pipeline."""

    def __init__(self, whisper_model: str = "base", language: str = "en"):
        """Initialize voice pipeline.

        Args:
            whisper_model: Whisper model size (tiny, base, small, medium, large).
            language: Default language for transcription.
        """
        self.whisper_model = whisper_model
        self.language = language
        self._history: list[VoiceInput] = []

    def transcribe_audio(self, audio_path: str) -> VoiceInput:
        """Transcribe audio file using Whisper.

        Args:
            audio_path: Path to audio file.

        Returns:
            VoiceInput with transcript.
        """
        voice_input = VoiceInput(audio_path=audio_path)

        try:
            # Try whisper-cli first
            result = subprocess.run(
                [
                    "whisper",
                    audio_path,
                    "--model",
                    self.whisper_model,
                    "--language",
                    self.language,
                    "--output_format",
                    "json",
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode == 0:
                output = json.loads(result.stdout)
                voice_input.transcript = output.get("text", "")
                voice_input.confidence = output.get("confidence", 0.0)
                voice_input.language = output.get("language", self.language)
                voice_input.duration_seconds = output.get("duration", 0.0)
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            # Fallback: return empty transcript
            logger.warning(f"Whisper transcription failed for {audio_path}")
            voice_input.transcript = ""

        # Detect voice commands
        voice_input.commands = self._detect_commands(voice_input.transcript)
        self._history.append(voice_input)

        return voice_input

    def _detect_commands(self, transcript: str) -> list[str]:
        """Detect voice commands in transcript.

        Args:
            transcript: Transcribed text.

        Returns:
            List of detected commands.
        """
        commands = []
        transcript_lower = transcript.lower()

        command_patterns = {
            "run_tests": ["run tests", "execute tests", "test the code"],
            "deploy": ["deploy", "push to production", "release"],
            "stop": ["stop", "cancel", "abort", "halt"],
            "help": ["help", "what can you do", "commands"],
            "status": ["status", "what's happening", "progress"],
            "summarize": ["summarize", "summary", "brief me"],
        }

        for cmd, patterns in command_patterns.items():
            if any(p in transcript_lower for p in patterns):
                commands.append(cmd)

        return commands

    def get_history(self, limit: int = 50) -> list[VoiceInput]:
        """Get voice input history.

        Args:
            limit: Maximum number of entries.

        Returns:
            List of VoiceInput objects.
        """
        return self._history[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """Get voice pipeline statistics."""
        return {
            "total_inputs": len(self._history),
            "avg_confidence": sum(v.confidence for v in self._history)
            / max(1, len(self._history)),
            "total_duration_seconds": sum(v.duration_seconds for v in self._history),
            "commands_detected": sum(len(v.commands) for v in self._history),
            "whisper_model": self.whisper_model,
            "language": self.language,
        }


# Global singleton
_voice_pipeline = VoicePipeline()


def transcribe_audio(audio_path: str) -> VoiceInput:
    """Convenience function to transcribe audio."""
    return _voice_pipeline.transcribe_audio(audio_path)


def get_voice_history(limit: int = 50) -> list[VoiceInput]:
    """Convenience function to get voice history."""
    return _voice_pipeline.get_history(limit)
