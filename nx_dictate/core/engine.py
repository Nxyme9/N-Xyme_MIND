"""Whisper transcription engine — with VAD filter, confidence scoring, language detection."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

from nx_dictate.config import WhisperConfig

logger = logging.getLogger(__name__)


@dataclass
class Segment:
    """A transcription segment with confidence."""

    start: float
    end: float
    text: str
    confidence: float = 0.0


@dataclass
class TranscriptionResult:
    """Structured transcription result."""

    text: str
    segments: list[Segment] = field(default_factory=list)
    language: str = "en"
    duration: float = 0.0


class WhisperEngine:
    def __init__(self, config: WhisperConfig, model_dir: Optional[Path] = None) -> None:
        self.config = config
        self.model_dir = model_dir
        self._model = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @staticmethod
    def get_device() -> str:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        return "cpu"

    def load(self) -> None:
        import faster_whisper

        device = self.config.device
        if device == "cuda":
            try:
                import torch
                if not torch.cuda.is_available():
                    device = "cpu"
                    logger.warning("CUDA not available, falling back to CPU")
            except ImportError:
                device = "cpu"
                logger.warning("torch not available, falling back to CPU")

        compute_type = self.config.compute_type
        if device == "cpu" and compute_type == "float16":
            compute_type = "int8"

        self._model = faster_whisper.WhisperModel(
            model_size_or_path=self.config.model.value,
            device=device,
            compute_type=compute_type,
            download_root=str(self.model_dir) if self.model_dir else None,
        )
        logger.info("Whisper model loaded on %s", device)

    def unload(self) -> None:
        self._model = None
        import gc
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass
        logger.info("Whisper model unloaded")

    def _normalize(self, audio: np.ndarray) -> np.ndarray:
        peak = np.abs(audio).max()
        if peak > 0:
            audio = audio / peak
        return audio

    def _trim_silence(self, audio: np.ndarray, threshold: float = 0.01) -> np.ndarray:
        indices = np.where(np.abs(audio) > threshold)[0]
        if len(indices) == 0:
            return audio
        return audio[indices[0]: indices[-1] + 1]

    def transcribe(self, audio: np.ndarray) -> str:
        """Quick transcribe, returns plain text."""
        return self.transcribe_detailed(audio).text

    def transcribe_streaming(self, audio: np.ndarray) -> list[str]:
        """Streaming transcription — yields progressive text as it stabilizes.
        Processes audio in overlapping 2s chunks so words appear as you speak.
        """
        if self._model is None:
            raise RuntimeError("Model not loaded")
        audio = self._normalize(audio)
        if len(audio) < 16000:
            return []

        chunk_s = 2.0       # 2-second chunks
        overlap_s = 0.5     # 0.5s overlap between chunks
        chunk_n = int(chunk_s * 16000)
        overlap_n = int(overlap_s * 16000)
        step = chunk_n - overlap_n

        results = []
        prev_text = ""
        for start in range(0, len(audio) - chunk_n + 1, step):
            chunk = audio[start:start + chunk_n]
            segs, _ = self._model.transcribe(chunk, beam_size=1, temperature=0.0, vad_filter=False)
            text = " ".join(s.text.strip() for s in segs)
            if text and text != prev_text:
                results.append(text)
                prev_text = text

        return results if results else [self.transcribe(audio)]

    def transcribe_detailed(self, audio: np.ndarray) -> TranscriptionResult:
        """Transcribe with structured result — uses VAD filter, confidence, language detection."""
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        import time
        audio = self._normalize(audio)
        audio = self._trim_silence(audio)

        if len(audio) < 16000 * 0.3:  # Less than 300ms
            return TranscriptionResult(text="", duration=0.0)

        start_time = time.time()

        # Build VAD params (from old dictate.py)
        vad_params = {
            "min_silence_duration_ms": self.config.vad_min_silence_duration_ms,
            "speech_pad_ms": self.config.vad_speech_pad_ms,
        }

        # Build initial_prompt from vocabulary for better term recognition
        initial_prompt = self.config.initial_prompt

        segments_gen, info = self._model.transcribe(
            audio,
            language=self.config.language,
            beam_size=self.config.beam_size,
            temperature=self.config.temperature,
            vad_filter=self.config.vad_filter,
            vad_parameters=vad_params,
            initial_prompt=initial_prompt,
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

        # Log per-segment confidence for debugging
        if segments:
            avg_conf = sum(s.confidence for s in segments) / len(segments)
            logger.debug("Transcription: %.1fs, %.1f conf, %d segs",
                         duration, avg_conf, len(segments))

        return TranscriptionResult(
            text=" ".join(full_text),
            segments=segments,
            language=info.language,
            duration=duration,
        )

    def detect_language(self, audio: np.ndarray) -> Optional[str]:
        """Detect language of audio without full transcription."""
        if self._model is None:
            return None
        try:
            _, info = self._model.transcribe(audio, beam_size=1)
            return info.language
        except Exception:
            return None

    def transcribe_file(self, audio_path: str) -> TranscriptionResult:
        """Transcribe an audio file."""
        import soundfile as sf
        audio, sr = sf.read(audio_path)
        if sr != 16000:
            import scipy.signal
            audio = scipy.signal.resample(audio, int(len(audio) * 16000 / sr))
        return self.transcribe_detailed(audio.astype(np.float32))
