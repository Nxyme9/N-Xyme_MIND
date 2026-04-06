"""
Whisper Transcription — Speech-to-text with timestamps (ported from VIBE)

Uses faster-whisper for local transcription.

Usage:
    service = WhisperTranscription()
    result = service.transcribe("audio.wav")
    print(result.text)
    for segment in result.segments:
        print(f"[{segment.start:.1f}s] {segment.text}")
"""

import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Check faster-whisper
FASTER_WHISPER_AVAILABLE = False
try:
    from faster_whisper import WhisperModel

    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    logger.warning("faster-whisper not installed. Run: pip install faster-whisper")


@dataclass
class Segment:
    """A transcription segment."""

    start: float
    end: float
    text: str
    confidence: float = 0.0


@dataclass
class TranscriptionResult:
    """Transcription result."""

    text: str
    segments: List[Segment] = field(default_factory=list)
    language: str = "en"
    duration: float = 0.0
    model: str = "base"


class WhisperTranscription:
    """Speech-to-text using faster-whisper."""

    MODELS = {
        "tiny": "tiny",  # 39M params, fastest
        "base": "base",  # 74M params, balanced
        "small": "small",  # 244M params, better quality
        "medium": "medium",  # 769M params, good quality
        "large": "large-v3",  # 1550M params, best quality
    }

    def __init__(self, model_name: str = "base", device: str = "auto"):
        self.model_name = model_name
        self.model = None

        if FASTER_WHISPER_AVAILABLE:
            try:
                self.model = WhisperModel(
                    self.MODELS.get(model_name, "base"),
                    device="cuda" if device == "auto" else device,
                    compute_type="float16",
                )
                logger.info(f"WhisperTranscription: Loaded {model_name}")
            except Exception as e:
                logger.error(f"WhisperTranscription: Failed to load: {e}")

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe audio file."""
        if not self.model:
            return TranscriptionResult(text="[Whisper not available]")

        path = Path(audio_path)
        if not path.exists():
            return TranscriptionResult(text=f"[File not found: {audio_path}]")

        try:
            start_time = time.time()

            segments_gen, info = self.model.transcribe(
                str(path),
                language=language,
                beam_size=5,
                vad_filter=True,
            )

            segments = []
            full_text = []

            for segment in segments_gen:
                seg = Segment(
                    start=segment.start,
                    end=segment.end,
                    text=segment.text.strip(),
                    confidence=segment.avg_logprob,
                )
                segments.append(seg)
                full_text.append(seg.text)

            duration = time.time() - start_time

            return TranscriptionResult(
                text=" ".join(full_text),
                segments=segments,
                language=info.language,
                duration=duration,
                model=self.model_name,
            )
        except Exception as e:
            logger.error(f"WhisperTranscription: Transcription failed: {e}")
            return TranscriptionResult(text=f"[Error: {e}]")

    def transcribe_with_timestamps(self, audio_path: str) -> List[Dict]:
        """Transcribe and return timestamped segments."""
        result = self.transcribe(audio_path)
        return [
            {
                "start": s.start,
                "end": s.end,
                "text": s.text,
                "confidence": s.confidence,
            }
            for s in result.segments
        ]

    def detect_language(self, audio_path: str) -> Optional[str]:
        """Detect language of audio."""
        if not self.model:
            return None

        try:
            _, info = self.model.transcribe(audio_path, beam_size=1)
            return info.language
        except Exception:
            return None


def create_whisper_service(model: str = "base") -> WhisperTranscription:
    """Create Whisper transcription service."""
    return WhisperTranscription(model_name=model)
