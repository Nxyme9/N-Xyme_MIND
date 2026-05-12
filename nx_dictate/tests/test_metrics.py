from __future__ import annotations
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metrics import (
    calculate_wer,
    calculate_rtf,
    levenshtein_distance,
    MetricsCollector,
    TranscriptionMetrics,
)


class TestLevenshtein:
    def test_empty_strings(self):
        assert levenshtein_distance("", "") == 0

    def test_identical_strings(self):
        assert levenshtein_distance("hello", "hello") == 0

    def test_single_insertion(self):
        assert levenshtein_distance("hello", "hallo") == 1

    def test_single_deletion(self):
        assert levenshtein_distance("hello", "hell") == 1

    def test_single_substitution(self):
        assert levenshtein_distance("hello", "hallo") == 1


class TestWER:
    def test_identical_transcription(self):
        assert calculate_wer("hello world", "hello world") == 0.0

    def test_one_word_error(self):
        wer = calculate_wer("hello world", "hello word")
        assert wer > 0 and wer <= 1.0

    def test_empty_reference(self):
        assert calculate_wer("", "hello") == 1.0

    def test_empty_hypothesis(self):
        assert calculate_wer("hello", "") == 1.0

    def test_both_empty(self):
        assert calculate_wer("", "") == 0.0


class TestRTF:
    def test_rtf_equal(self):
        assert calculate_rtf(1.0, 1.0) == 1.0

    def test_rtf_faster_than_realtime(self):
        assert calculate_rtf(0.5, 1.0) == 0.5

    def test_rtf_slower_than_realtime(self):
        assert calculate_rtf(2.0, 1.0) == 2.0

    def test_zero_duration(self):
        assert calculate_rtf(1.0, 0.0) == 0.0


class TestMetricsCollector:
    def test_record_without_reference(self):
        collector = MetricsCollector()
        metrics = collector.record_transcription(
            hypothesis="hello world",
            latency_ms=100.0,
            audio_duration=0.5,
        )
        assert metrics.hypothesis_words == 2
        assert metrics.latency_ms == 100.0
        assert metrics.wer == 0.0

    def test_record_with_reference(self):
        collector = MetricsCollector()
        metrics = collector.record_transcription(
            reference="hello world",
            hypothesis="hello world",
            latency_ms=100.0,
            audio_duration=0.5,
        )
        assert metrics.wer == 0.0
        assert metrics.reference_words == 2

    def test_average_wer(self):
        collector = MetricsCollector()
        collector.record_transcription(
            reference="hello", hypothesis="hello", latency_ms=100.0
        )
        collector.record_transcription(
            reference="world", hypothesis="word", latency_ms=100.0
        )
        avg_wer = collector.get_average_wer()
        assert avg_wer >= 0

    def test_average_latency(self):
        collector = MetricsCollector()
        collector.record_transcription(hypothesis="test", latency_ms=100.0)
        collector.record_transcription(hypothesis="test", latency_ms=200.0)
        avg_latency = collector.get_average_latency()
        assert avg_latency == 150.0

    def test_summary(self):
        collector = MetricsCollector()
        collector.record_transcription(
            hypothesis="hello world", latency_ms=100.0, audio_duration=0.5
        )
        summary = collector.get_summary()
        assert "total_transcriptions" in summary
        assert "average_latency_ms" in summary
        assert "average_rtf" in summary

    def test_history(self):
        collector = MetricsCollector()
        collector.record_transcription(hypothesis="test1", latency_ms=50.0)
        collector.record_transcription(hypothesis="test2", latency_ms=100.0)
        history = collector.get_history()
        assert len(history) == 2


class TestTranscriptionMetrics:
    def test_default_values(self):
        metrics = TranscriptionMetrics()
        assert metrics.wer == 0.0
        assert metrics.reference_words == 0
        assert metrics.latency_ms == 0.0
        assert metrics.rtf == 0.0
