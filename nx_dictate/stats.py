from __future__ import annotations
import time
import threading
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class TranscriptionStats:
    total_transcriptions: int = 0
    total_words: int = 0
    total_duration_ms: int = 0
    total_audio_samples: int = 0
    failed_transcriptions: int = 0
    avg_latency_ms: float = 0.0
    avg_words_per_minute: float = 0.0
    avg_confidence: float = 0.0
    total_confidence_samples: int = 0
    last_transcription: Optional[str] = None
    last_timestamp: Optional[str] = None
    _lock: threading.Lock = field(default_factory=threading.Lock)


class PerformanceMonitor:
    def __init__(self):
        self._stats = TranscriptionStats()
        self._start_time = time.time()
        self._session_start = datetime.now().isoformat()

    def record_transcription(
        self,
        text: str,
        duration_ms: int,
        word_count: int,
        audio_samples: int,
        success: bool = True,
        confidence: float = 0.0,
    ):
        with self._stats._lock:
            if success:
                self._stats.total_transcriptions += 1
                self._stats.total_words += word_count
                self._stats.total_duration_ms += duration_ms
                self._stats.total_audio_samples += audio_samples
                self._stats.last_transcription = text[:100]
                self._stats.last_timestamp = datetime.now().isoformat()

                if confidence > 0:
                    self._stats.total_confidence_samples += 1
                    total_conf = self._stats.avg_confidence * (
                        self._stats.total_confidence_samples - 1
                    )
                    self._stats.avg_confidence = (
                        total_conf + confidence
                    ) / self._stats.total_confidence_samples

                if self._stats.total_transcriptions > 0:
                    self._stats.avg_latency_ms = (
                        self._stats.total_duration_ms / self._stats.total_transcriptions
                    )

                if self._stats.total_duration_ms > 0:
                    minutes = self._stats.total_duration_ms / 60000.0
                    if minutes > 0:
                        self._stats.avg_words_per_minute = self._stats.total_words / minutes
            else:
                self._stats.failed_transcriptions += 1

    def get_stats(self) -> dict:
        with self._stats._lock:
            uptime = time.time() - self._start_time
            return {
                "session_start": self._session_start,
                "uptime_seconds": round(uptime, 1),
                "transcriptions": self._stats.total_transcriptions,
                "failed": self._stats.failed_transcriptions,
                "total_words": self._stats.total_words,
                "avg_latency_ms": round(self._stats.avg_latency_ms, 1),
                "avg_wpm": round(self._stats.avg_words_per_minute, 1),
                "avg_confidence": round(self._stats.avg_confidence * 100, 1),
                "last_transcription": self._stats.last_transcription,
                "last_timestamp": self._stats.last_timestamp,
            }

    def reset(self):
        with self._stats._lock:
            self._stats = TranscriptionStats()
            self._start_time = time.time()


_monitor: Optional[PerformanceMonitor] = None


def get_monitor() -> PerformanceMonitor:
    global _monitor
    if _monitor is None:
        _monitor = PerformanceMonitor()
    return _monitor
