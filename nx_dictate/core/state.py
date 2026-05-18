from __future__ import annotations

from enum import Enum
from threading import Lock
from typing import Callable, Optional


class State(str, Enum):
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"
    INJECTING = "injecting"
    ERROR = "error"


TRANSITIONS: Dict[State, Set[State]] = {
    State.IDLE: {State.RECORDING, State.ERROR},
    State.RECORDING: {State.IDLE, State.PROCESSING, State.ERROR},
    State.PROCESSING: {State.RECORDING, State.INJECTING, State.IDLE, State.ERROR},
    State.INJECTING: {State.IDLE, State.ERROR},
    State.ERROR: {State.IDLE, State.RECORDING},
}


class DictationState:
    def __init__(self) -> None:
        self._state: State = State.IDLE
        self._text_buffer: str = ""
        self._error_message: Optional[str] = None
        self._lock = Lock()
        self._callbacks: dict[State, list[Callable[[State, State], None]]] = {}

    @property
    def state(self) -> State:
        with self._lock:
            return self._state

    @property
    def text_buffer(self) -> str:
        with self._lock:
            return self._text_buffer

    @property
    def error_message(self) -> Optional[str]:
        with self._lock:
            return self._error_message

    def transition(self, new_state: State) -> bool:
        with self._lock:
            if new_state not in TRANSITIONS.get(self._state, set()):
                return False
            old_state = self._state
            self._state = new_state
            if new_state == State.ERROR:
                self._error_message = None
        for cb in self._callbacks.get(new_state, []):
            cb(old_state, new_state)
        return True

    def set_text(self, text: str) -> None:
        with self._lock:
            self._text_buffer = text

    def append_text(self, text: str) -> None:
        with self._lock:
            self._text_buffer += text

    def clear_text(self) -> None:
        with self._lock:
            self._text_buffer = ""

    def set_error(self, message: str) -> None:
        with self._lock:
            self._error_message = message
            self._state = State.ERROR
        for cb in self._callbacks.get(State.ERROR, []):
            cb(self._state, State.ERROR)

    def on_state(self, state: State, callback: Callable[[State, State], None]) -> None:
        with self._lock:
            self._callbacks.setdefault(state, []).append(callback)

    def is_active(self) -> bool:
        with self._lock:
            return self._state not in (State.IDLE, State.ERROR)
