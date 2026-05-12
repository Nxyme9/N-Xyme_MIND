"""Tests for dictate_app.py state handling."""

import pytest
from nx_dictate.dictate_app import DictationApp
from nx_dictate.core.state import StateMachine, DictationState


class TestToggleRecording:
    """Test toggle_recording() with various states."""

    def setup_method(self):
        self.app = DictationApp.__new__(DictationApp)
        self.app._state = StateMachine()
        self.app._audio = None
        self.app._current_audio = []

    def test_toggle_from_ready_starts_recording(self):
        """Toggle from READY state should start recording."""
        result = self.app.toggle_recording()
        assert result is True
        assert self.app._state.state == DictationState.RECORDING

    def test_toggle_from_recording_without_audio_returns_false(self):
        """Toggle from RECORDING without audio object should return False."""
        self.app._state.start_recording()
        result = self.app.toggle_recording()
        assert result is False

    def test_toggle_from_processing_returns_false(self):
        """Toggle from PROCESSING state should return False."""
        self.app._state.start_recording()
        self.app._state.stop_recording()
        assert self.app._state.state == DictationState.PROCESSING
        result = self.app.toggle_recording()
        assert result is False
        assert self.app._state.state == DictationState.PROCESSING

    def test_toggle_from_error_resets_and_starts(self):
        """Toggle from ERROR state should reset then start."""
        self.app._state.start_recording()
        self.app._state.stop_recording()
        self.app._state.error_transcription()
        assert self.app._state.state == DictationState.ERROR
        result = self.app.toggle_recording()
        assert result is True
        assert self.app._state.state == DictationState.RECORDING


class TestStartRecording:
    """Test _start_recording() state validation."""

    def setup_method(self):
        self.app = DictationApp.__new__(DictationApp)
        self.app._state = StateMachine()
        self.app._audio = None
        self.app._current_audio = []

    def test_start_from_ready_succeeds(self):
        """Start from READY should succeed."""
        result = self.app._start_recording()
        assert result is True
        assert self.app._state.state == DictationState.RECORDING

    def test_start_from_recording_returns_false(self):
        """Start from RECORDING should return False."""
        self.app._state.start_recording()
        result = self.app._start_recording()
        assert result is False

    def test_start_from_processing_returns_false(self):
        """Start from PROCESSING should return False."""
        self.app._state.start_recording()
        self.app._state.stop_recording()
        result = self.app._start_recording()
        assert result is False


class TestStopRecording:
    """Test _stop_recording() state validation."""

    def setup_method(self):
        self.app = DictationApp.__new__(DictationApp)
        self.app._state = StateMachine()
        self.app._audio = None
        self.app._current_audio = []

    def test_stop_from_ready_returns_false(self):
        """Stop from READY should return False."""
        result = self.app._stop_recording()
        assert result is False

    def test_stop_from_recording_without_audio_returns_false(self):
        """Stop from RECORDING without audio object should return False."""
        self.app._state.start_recording()
        result = self.app._stop_recording()
        assert result is False