"""Error Handler — Global error handling with context"""

import logging, traceback
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ErrorHandler:
    def __init__(self):
        self._errors: list = []

    def handle(self, error: Exception, context: Optional[Dict] = None) -> Dict:
        error_info = {
            "type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc(),
            "context": context or {},
        }
        self._errors.append(error_info)
        logger.error(f"ErrorHandler: {error_info['type']}: {error_info['message']}")
        return error_info

    def get_recent(self, limit: int = 20) -> list:
        return self._errors[-limit:]

    def get_by_type(self, error_type: str) -> list:
        return [e for e in self._errors if e["type"] == error_type]

    def clear(self):
        self._errors.clear()
