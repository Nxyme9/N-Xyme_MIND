"""Session Context — Per-session context storage"""

import logging, time
from typing import Any, Dict

logger = logging.getLogger(__name__)


class SessionContext:
    def __init__(self):
        self._contexts: Dict[str, Dict[str, Any]] = {}

    def set(self, session_id: str, key: str, value: Any):
        if session_id not in self._contexts:
            self._contexts[session_id] = {}
        self._contexts[session_id][key] = {"value": value, "timestamp": time.time()}

    def get(self, session_id: str, key: str, default: Any = None) -> Any:
        entry = self._contexts.get(session_id, {}).get(key)
        return entry["value"] if entry else default

    def get_all(self, session_id: str) -> Dict:
        return {k: v["value"] for k, v in self._contexts.get(session_id, {}).items()}

    def clear(self, session_id: str):
        self._contexts.pop(session_id, None)

    def merge(self, session_id: str, data: Dict):
        for key, value in data.items():
            self.set(session_id, key, value)
