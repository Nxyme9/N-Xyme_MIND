"""Connection Pool — Reusable HTTP connections for providers."""

import threading
import urllib.request
import urllib.error
from typing import Dict, Optional


class ConnectionPool:
    """Simple connection pool for HTTP requests."""

    def __init__(self, max_connections: int = 100):
        self.max_connections = max_connections
        self._connections: Dict[str, urllib.request.OpenerDirector] = {}
        self._lock = threading.Lock()

    def get_opener(self, api_key: str = "") -> urllib.request.OpenerDirector:
        """Get or create an opener with the given API key."""
        key = api_key[:20] if api_key else "anonymous"
        with self._lock:
            if key not in self._connections:
                opener = urllib.request.build_opener()
                if api_key:
                    opener.addheaders = [('Authorization', f'Bearer {api_key}')]
                self._connections[key] = opener
            return self._connections[key]

    def close_all(self) -> None:
        """Close all connections."""
        with self._lock:
            self._connections.clear()

    @property
    def size(self) -> int:
        return len(self._connections)


# Global instance
connection_pool = ConnectionPool()
