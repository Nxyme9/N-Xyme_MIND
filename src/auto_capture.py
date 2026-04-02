"""Auto Capture — Capture clipboard, voice, screen"""

import logging, time
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class AutoCapture:
    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._history: List[Dict] = []

    def register(self, capture_type: str, handler: Callable):
        self._handlers[capture_type] = handler

    def capture(self, capture_type: str, **kwargs) -> Optional[Dict]:
        handler = self._handlers.get(capture_type)
        if not handler:
            logger.warning(f"AutoCapture: No handler for '{capture_type}'")
            return None
        try:
            result = handler(**kwargs)
            entry = {"type": capture_type, "data": result, "timestamp": time.time()}
            self._history.append(entry)
            if len(self._history) > 1000:
                self._history = self._history[-1000:]
            return entry
        except Exception as e:
            logger.error(f"AutoCapture: Failed: {e}")
            return None

    def get_history(self, capture_type: str = None, limit: int = 50) -> List[Dict]:
        if capture_type:
            return [h for h in self._history if h["type"] == capture_type][-limit:]
        return self._history[-limit:]

    def register_defaults(self):
        try:
            import pyperclip

            self.register("clipboard", lambda: {"text": pyperclip.paste()})
        except ImportError:
            logger.warning("pyperclip not installed")
