# N-Xyme Dictate - State Machine

from __future__ import annotations

import logging
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger("nxyme_dictate.dictate.state")


class DictationState(Enum):
    """Main application states."""

    READY = "ready"
    RECORDING = "recording"
    PROCESSING = "processing"
    ERROR = "error"


class StateEvent(Enum):
    """State transition events."""

    START_RECORDING = "start_recording"
    STOP_RECORDING = "stop_recording"
    TRANSCRIPTION_COMPLETE = "transcription_complete"
    TRANSCRIPTION_ERROR = "transcription_error"
    RESET = "reset"


# State transitions
TRANSITIONS: dict[DictationState, dict[StateEvent, DictationState]] = {
    DictationState.READY: {
        StateEvent.START_RECORDING: DictationState.RECORDING,
    },
    DictationState.RECORDING: {
        StateEvent.STOP_RECORDING: DictationState.PROCESSING,
    },
    DictationState.PROCESSING: {
        StateEvent.TRANSCRIPTION_COMPLETE: DictationState.READY,
        StateEvent.TRANSCRIPTION_ERROR: DictationState.ERROR,
    },
    DictationState.ERROR: {
        StateEvent.RESET: DictationState.READY,
    },
}


class StateMachine:
    """CATALYST-style state machine for dictation."""

    def __init__(self):
        self._state = DictationState.READY
        self._on_state_change: Optional[Callable[[DictationState], None]] = None
        self._history: list[DictationState] = [self._state]

    @property
    def state(self) -> DictationState:
        return self._state

    @property
    def is_recording(self) -> bool:
        return self._state == DictationState.RECORDING

    @property
    def is_processing(self) -> bool:
        return self._state == DictationState.PROCESSING

    @property
    def is_ready(self) -> bool:
        return self._state == DictationState.READY

    @property
    def has_error(self) -> bool:
        return self._state == DictationState.ERROR

    def set_state_change_callback(
        self,
        callback: Callable[[DictationState], None],
    ) -> None:
        self._on_state_change = callback

    def transition(self, event: StateEvent) -> bool:
        current_state = self._state
        next_state = TRANSITIONS.get(current_state, {}).get(event)

        if next_state is None:
            return False

        self._state = next_state
        self._history.append(next_state)

        logger.info(f"State: {current_state.value} -> {next_state.value}")

        if self._on_state_change:
            try:
                self._on_state_change(next_state)
            except Exception as e:
                logger.error(f"State change callback error: {e}")

        return True

    def start_recording(self) -> bool:
        return self.transition(StateEvent.START_RECORDING)

    def stop_recording(self) -> bool:
        return self.transition(StateEvent.STOP_RECORDING)

    def complete_transcription(self) -> bool:
        return self.transition(StateEvent.TRANSCRIPTION_COMPLETE)

    def error_transcription(self) -> bool:
        return self.transition(StateEvent.TRANSCRIPTION_ERROR)

    def reset(self) -> bool:
        result = self.transition(StateEvent.RESET)
        if result:
            self._history = [self._state]
        return result

    def get_state_display(self) -> str:
        return {
            DictationState.READY: "Ready",
            DictationState.RECORDING: "Recording...",
            DictationState.PROCESSING: "Processing...",
            DictationState.ERROR: "Error",
        }.get(self._state, "Unknown")
