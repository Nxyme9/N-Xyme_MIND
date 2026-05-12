from __future__ import annotations
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("nxyme_dictate.metrics")


@dataclass
class TranscriptionMetrics:
    wer: float = 0.0
    reference_words: int = 0
    hypothesis_words: int = 0
    errors: int = 0
    latency_ms: float = 0.0
    rtf: float = 0.0
    timestamp: float = field(default_factory=time.time)


def levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def calculate_wer(reference: str, hypothesis: str) -> float:
    ref_words = reference.lower().split()
    hyp_words = hypothesis.lower().split()

    if not ref_words:
        return 0.0 if not hyp_words else 1.0

    ref_joined = " ".join(ref_words)
    hyp_joined = " ".join(hyp_words)

    distance = levenshtein_distance(ref_joined, hyp_joined)
    wer = distance / len(ref_words)

    return min(wer, 1.0)


def calculate_rtf(process_time: float, audio_duration: float) -> float:
    if audio_duration <= 0:
        return 0.0
    return process_time / audio_duration


class MetricsCollector:
    def __init__(self):
        self._history: list[TranscriptionMetrics] = []
        self._session_start = time.time()
        self._transcription_count = 0

    def record_transcription(
        self,
        reference: Optional[str] = None,
        hypothesis: str = "",
        latency_ms: float = 0.0,
        audio_duration: float = 0.0,
    ) -> TranscriptionMetrics:
        metrics = TranscriptionMetrics(
            latency_ms=latency_ms,
            rtf=calculate_rtf(latency_ms / 1000.0, audio_duration),
            hypothesis_words=len(hypothesis.split()),
            timestamp=time.time(),
        )

        if reference is not None:
            metrics.wer = calculate_wer(reference, hypothesis)
            metrics.reference_words = len(reference.split())
            metrics.errors = int(metrics.wer * metrics.reference_words)

        self._history.append(metrics)
        self._transcription_count += 1

        return metrics

    def get_average_wer(self) -> float:
        wer_values = [m.wer for m in self._history if m.wer > 0]
        return sum(wer_values) / len(wer_values) if wer_values else 0.0

    def get_average_latency(self) -> float:
        latencies = [m.latency_ms for m in self._history if m.latency_ms > 0]
        return sum(latencies) / len(latencies) if latencies else 0.0

    def get_average_rtf(self) -> float:
        rtfs = [m.rtf for m in self._history if m.rtf > 0]
        return sum(rtfs) / len(rtfs) if rtfs else 0.0

    def get_summary(self) -> dict:
        total_transcriptions = len(self._history)
        total_words = sum(m.hypothesis_words for m in self._history)
        session_duration = time.time() - self._session_start

        return {
            "total_transcriptions": total_transcriptions,
            "total_words": total_words,
            "session_duration_sec": round(session_duration, 2),
            "average_wer": round(self.get_average_wer() * 100, 2),
            "average_latency_ms": round(self.get_average_latency(), 2),
            "average_rtf": round(self.get_average_rtf(), 3),
            "transcriptions_per_minute": round(
                (total_transcriptions / session_duration * 60)
                if session_duration > 0
                else 0,
                1,
            ),
        }

    def log_summary(self):
        summary = self.get_summary()
        logger.info(f"Metrics Summary: {summary}")

    def get_history(self) -> list[TranscriptionMetrics]:
        return self._history.copy()
