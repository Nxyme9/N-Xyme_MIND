from __future__ import annotations
import asyncio
import logging
import queue
import threading
import numpy as np
from typing import Optional, Callable, Any
from dataclasses import dataclass

logger = logging.getLogger("nxyme_dictate.realtime")


@dataclass
class PartialResult:
    text: str
    words: list
    confidence: float
    is_final: bool
    timestamp_ms: int


class RealtimeTranscriber:
    def __init__(
        self,
        whisper_client,
        chunk_duration_ms: int = 500,
        on_partial: Optional[Callable[[PartialResult], None]] = None,
        on_final: Optional[Callable[[PartialResult], None]] = None,
    ):
        self._client = whisper_client
        self._chunk_duration_ms = chunk_duration_ms
        self._on_partial = on_partial
        self._on_final = on_final
        self._audio_buffer = []
        self._running = False
        self._lock = threading.Lock()
        self._last_text = ""
        self._confirm_threshold = 2
        self._min_chunks_for_final = 3

    def add_chunk(self, audio_chunk) -> Optional[PartialResult]:
        self._audio_buffer.append(audio_chunk)

        if len(self._audio_buffer) < 2:
            return None

        combined = np.concatenate(self._audio_buffer[-4:])

        try:
            result = self._client.transcribe(
                combined,
                beam_size=1,
                temperature=0.0,
                word_timestamps=True,
            )
        except Exception as e:
            logger.error(f"Realtime transcription error: {e}")
            return None

        if not result:
            return None

        # Handle faster-whisper result (tuple, generator, or Transcript object)
        if isinstance(result, tuple) and len(result) >= 1:
            segments = result[0]
            if hasattr(segments, '__iter__'):
                text = "".join([getattr(s, 'text', str(s)) for s in segments])
            else:
                text = str(result)
        elif hasattr(result, 'text'):
            text = result.text
        elif hasattr(result, '__iter__') and not isinstance(result, str):
            text = "".join([getattr(r, 'text', str(r)) for r in result])
        else:
            text = str(result) if not isinstance(result, str) else result

        is_final = len(self._audio_buffer) >= self._min_chunks_for_final

        words = []
        confidence = 0.9
        if hasattr(result, "words") and result.words:
            words = result.words
            if hasattr(result, "avg_logprob") and result.avg_logprob:
                confidence = min(1.0, max(0.0, (result.avg_logprob + 1.0)))

        if text == self._last_text and not is_final:
            return None
        self._last_text = text

        partial = PartialResult(
            text=text,
            words=words,
            confidence=confidence,
            is_final=is_final,
            timestamp_ms=len(self._audio_buffer) * self._chunk_duration_ms,
        )

        if is_final and self._on_final:
            try:
                self._on_final(partial)
            except Exception as e:
                logger.error(f"Final callback error: {e}")

        if not is_final and self._on_partial:
            try:
                self._on_partial(partial)
            except Exception as e:
                logger.error(f"Partial callback error: {e}")

        return partial

    def reset(self):
        with self._lock:
            self._audio_buffer = []
            self._last_text = ""


def create_realtime_callbacks(
    on_text: Callable[[str, bool], None],
) -> tuple[Callable, Callable]:
    def on_partial(result: PartialResult):
        on_text(result.text, False)

    def on_final(result: PartialResult):
        on_text(result.text, True)

    return on_partial, on_final
