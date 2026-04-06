"""Stall/Halt Detector — Detects and recovers from API stalls."""

import time
import threading
from typing import Dict, Optional
from collections import defaultdict


class StallDetector:
    def __init__(self, stall_threshold_ms: float = 30000.0, max_consecutive_stalls: int = 3):
        self.stall_threshold_ms = stall_threshold_ms
        self.max_consecutive_stalls = max_consecutive_stalls
        self._lock = threading.Lock()
        self._request_times: Dict[str, float] = {}
        self._consecutive_stalls: Dict[str, int] = defaultdict(int)
        self._is_stalled: Dict[str, bool] = defaultdict(bool)

    def start_request(self, request_id: str) -> None:
        """Mark request as started."""
        with self._lock:
            self._request_times[request_id] = time.time()

    def complete_request(self, request_id: str, success: bool) -> bool:
        """Mark request as complete. Returns True if stall detected."""
        with self._lock:
            start = self._request_times.pop(request_id, None)
            if start is None:
                return False
            elapsed_ms = (time.time() - start) * 1000
            if elapsed_ms > self.stall_threshold_ms:
                self._consecutive_stalls[request_id.split(":")[0]] += 1
                if self._consecutive_stalls[request_id.split(":")[0]] >= self.max_consecutive_stalls:
                    self._is_stalled[request_id.split(":")[0]] = True
                return True
            else:
                self._consecutive_stalls[request_id.split(":")[0]] = 0
                self._is_stalled[request_id.split(":")[0]] = False
                return False

    def is_provider_stalled(self, provider: str) -> bool:
        """Check if a provider is currently stalled."""
        with self._lock:
            return self._is_stalled.get(provider, False)

    def get_stalled_providers(self) -> list:
        """Get list of currently stalled providers."""
        with self._lock:
            return [p for p, stalled in self._is_stalled.items() if stalled]

    def reset_provider(self, provider: str) -> None:
        """Manually reset a provider's stall status."""
        with self._lock:
            self._is_stalled[provider] = False
            self._consecutive_stalls[provider] = 0


# Global instance
stall_detector = StallDetector()
