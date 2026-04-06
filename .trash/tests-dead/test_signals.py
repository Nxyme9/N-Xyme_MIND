#!/usr/bin/env python3
"""Unit tests for signals module."""

import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from src.tools.learning.signals import (
    SignalDetector,
    Signal,
    SignalCategory,
    SignalType,
    get_signal_config,
)


class TestSignalCategory:
    """Tests for SignalCategory enum."""

    def test_all_categories_exist(self):
        """Verify all expected categories exist."""
        assert SignalCategory.INTERACTION.value == "interaction"
        assert SignalCategory.EXECUTION.value == "execution"
        assert SignalCategory.ENVIRONMENT.value == "environment"


class TestSignalType:
    """Tests for SignalType enum."""

    def test_all_types_exist(self):
        """Verify all expected signal types exist."""
        assert SignalType.MISALIGNMENT.value == "misalignment"
        assert SignalType.STAGNATION.value == "stagnation"
        assert SignalType.DISENGAGEMENT.value == "disengagement"
        assert SignalType.SATISFACTION.value == "satisfaction"
        assert SignalType.FAILURE.value == "failure"
        assert SignalType.LOOP.value == "loop"
        assert SignalType.EXHAUSTION.value == "exhaustion"


class TestSignal:
    """Tests for Signal dataclass."""

    def test_creation(self):
        """Test creating a signal."""
        signal = Signal(
            category=SignalCategory.INTERACTION,
            type=SignalType.SATISFACTION,
            confidence=0.9,
        )

        assert signal.category == SignalCategory.INTERACTION
        assert signal.type == SignalType.SATISFACTION
        assert signal.confidence == 0.9

    def test_confidence_validation(self):
        """Test that confidence must be 0-1."""
        with pytest.raises(ValueError, match="Confidence must be 0-1"):
            Signal(
                category=SignalCategory.INTERACTION,
                type=SignalType.SATISFACTION,
                confidence=1.5,
            )


class TestSignalDetector:
    """Tests for SignalDetector class."""

    @pytest.fixture
    def detector(self):
        """Create signal detector."""
        return SignalDetector()

    def test_detect_disengagement_short_query(self, detector):
        """Test detection of disengagement with short query."""
        signals = detector.detect_interaction_signals(
            query="ab",
            results=[],
            response="",
        )

        disengagement = [s for s in signals if s.type == SignalType.DISENGAGEMENT]
        assert len(disengagement) == 1

    def test_detect_misalignment_long_query_short_response(self, detector):
        """Test detection of misalignment."""
        signals = detector.detect_interaction_signals(
            query="This is a very long query that has many words and details",
            results=[{"type": "result"}],
            response="OK",
        )

        misalignment = [s for s in signals if s.type == SignalType.MISALIGNMENT]
        assert len(misalignment) == 1

    def test_detect_misalignment_no_results(self, detector):
        """Test detection of misalignment with no results."""
        signals = detector.detect_interaction_signals(
            query="test query",
            results=[],
            response="No results found",
        )

        misalignment = [s for s in signals if s.type == SignalType.MISALIGNMENT]
        assert len(misalignment) == 1

    def test_detect_stagnation(self, detector):
        """Test detection of stagnation."""
        results = [{"type": "file"} for _ in range(5)]

        signals = detector.detect_interaction_signals(
            query="test query",
            results=results,
            response="Many results here with a longer response",
        )

        stagnation = [s for s in signals if s.type == SignalType.STAGNATION]
        assert len(stagnation) == 1

    def test_detect_satisfaction(self, detector):
        """Test detection of satisfaction."""
        signals = detector.detect_interaction_signals(
            query="test",
            results=[{"type": "result"}],
            response="This is a very detailed response with lots of useful information that should be long enough to trigger the satisfaction signal detection mechanism",
        )

        satisfaction = [s for s in signals if s.type == SignalType.SATISFACTION]
        assert len(satisfaction) == 1

    def test_detect_execution_failure(self, detector):
        """Test detection of execution failure."""
        signals = detector.detect_execution_signals(
            tool_calls=[],
            errors=["Error 1", "Error 2"],
        )

        failures = [s for s in signals if s.type == SignalType.FAILURE]
        assert len(failures) == 1

    def test_detect_execution_loop(self, detector):
        """Test detection of execution loop."""
        tool_calls = [
            {"name": "tool1"},
            {"name": "tool2"},
            {"name": "tool1"},
            {"name": "tool2"},
            {"name": "tool1"},
        ]

        signals = detector.detect_execution_signals(
            tool_calls=tool_calls,
            errors=[],
        )

        loops = [s for s in signals if s.type == SignalType.LOOP]
        assert len(loops) == 1

    def test_detect_environment_exhaustion_rate_limit(self, detector):
        """Test detection of rate limit exhaustion."""
        rate_limits = [{"remaining": 5, "limit": 100}]

        signals = detector.detect_environment_signals(
            rate_limits=rate_limits,
            resources={},
        )

        exhaustion = [s for s in signals if s.type == SignalType.EXHAUSTION]
        assert len(exhaustion) == 1

    def test_detect_environment_exhaustion_cpu(self, detector):
        """Test detection of CPU exhaustion."""
        signals = detector.detect_environment_signals(
            rate_limits=[],
            resources={"cpu_percent": 95},
        )

        exhaustion = [s for s in signals if s.type == SignalType.EXHAUSTION]
        assert len(exhaustion) == 1

    def test_detect_environment_exhaustion_memory(self, detector):
        """Test detection of memory exhaustion."""
        signals = detector.detect_environment_signals(
            rate_limits=[],
            resources={"memory_percent": 92},
        )

        exhaustion = [s for s in signals if s.type == SignalType.EXHAUSTION]
        assert len(exhaustion) == 1

    def test_compute_signal_score_empty(self, detector):
        """Test score calculation with no signals."""
        score = detector.compute_signal_score([])
        assert score == 0.0

    def test_compute_signal_score_single(self, detector):
        """Test score calculation with single signal."""
        signal = Signal(
            category=SignalCategory.INTERACTION,
            type=SignalType.SATISFACTION,
            confidence=0.9,
        )
        score = detector.compute_signal_score([signal])

        assert 0.0 <= score <= 1.0

    def test_compute_signal_score_multiple(self, detector):
        """Test score calculation with multiple signals."""
        signals = [
            Signal(
                category=SignalCategory.INTERACTION,
                type=SignalType.SATISFACTION,
                confidence=0.9,
            ),
            Signal(
                category=SignalCategory.EXECUTION,
                type=SignalType.FAILURE,
                confidence=0.7,
            ),
        ]
        score = detector.compute_signal_score(signals)

        assert 0.0 <= score <= 1.0


class TestGetSignalConfig:
    """Tests for get_signal_config function."""

    def test_returns_valid_config(self):
        """Test that config returns expected structure."""
        config = get_signal_config()

        assert "categories" in config
        assert "interaction" in config["categories"]
        assert "execution" in config["categories"]
        assert "environment" in config["categories"]

    def test_interaction_signals(self):
        """Test interaction signals in config."""
        config = get_signal_config()
        signals = config["categories"]["interaction"]["signals"]

        assert "misalignment" in signals
        assert "stagnation" in signals
        assert "disengagement" in signals
        assert "satisfaction" in signals

    def test_execution_signals(self):
        """Test execution signals in config."""
        config = get_signal_config()
        signals = config["categories"]["execution"]["signals"]

        assert "failure" in signals
        assert "loop" in signals
