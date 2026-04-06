"""Memory Registry — Manages memory sources with health checks."""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from .connectors import (
    CONNECTORS,
    MemoryConnector,
    HealthStatus,
    MemoryResult,
    AthenaConnector,
    MemoryMCPConnector,
    SessionConnector,
    SQLiteConnector,
    MemoryDBConnector,
)


logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


@dataclass
class MemorySource:
    """A registered memory source."""

    name: str
    connector: MemoryConnector
    enabled: bool = True
    priority: int = 0


class MemoryRegistry:
    """Registry for managing memory sources."""

    def __init__(self):
        self._sources: Dict[str, MemorySource] = {}
        self._initialize_sources()

    def _initialize_sources(self):
        """Initialize default memory sources."""
        # Core connectors (always available)
        self.register(AthenaConnector())
        self.register(SessionConnector())
        self.register(MemoryDBConnector())

        # File content connector (for indexed drive files)
        try:
            from .file_content_connector import FileContentConnector
            self.register(FileContentConnector())
        except Exception as e:
            logger.info(f"File content connector not available: {e}")

        # Optional connectors (wrapped in try/except for graceful fallback)
        # Memory MCP - requires graph file
        try:
            self.register(MemoryMCPConnector())
        except Exception as e:
            logger.info(f"Memory MCP not available: {e}")

        # SQLite sources - lazy check for file existence
        sqlite_base = os.environ.get("NX_MIND_DATA_DIR", str(PROJECT_ROOT / "data"))
        sqlite_sources = [
            ("mind_sqlite", f"{sqlite_base}/mind.db"),
            ("jarvis_sqlite", f"{sqlite_base}/jarvis.db"),
            ("jarvis_events", f"{sqlite_base}/jarvis_events.db"),
            ("nxm_sqlite", f"{sqlite_base}/nxm.db"),
        ]
        for name, db_path in sqlite_sources:
            if os.path.exists(db_path):
                try:
                    self.register(SQLiteConnector(name, db_path))
                except Exception as e:
                    logger.warning(f"Failed to register {name}: {e}")

    def register(self, connector: MemoryConnector, priority: int = 0):
        """Register a memory source."""
        source = MemorySource(
            name=connector.name,
            connector=connector,
            enabled=connector.enabled,
            priority=priority,
        )
        self._sources[connector.name] = source

    def unregister(self, name: str):
        """Unregister a memory source."""
        if name in self._sources:
            del self._sources[name]
            logger.info(f"Unregistered memory source: {name}")

    def get(self, name: str) -> Optional[MemoryConnector]:
        """Get a connector by name."""
        source = self._sources.get(name)
        return source.connector if source else None

    def list_sources(self) -> List[str]:
        """List all registered source names."""
        return list(self._sources.keys())

    def get_enabled_sources(self) -> List[MemorySource]:
        """Get all enabled sources sorted by priority."""
        return sorted(
            [s for s in self._sources.values() if s.enabled],
            key=lambda s: s.priority,
            reverse=True,
        )

    def health_check_all(self) -> List[HealthStatus]:
        """Run health check on all sources."""
        results = []
        for source in self._sources.values():
            try:
                status = source.connector.health_check()
                results.append(status)
            except Exception as e:
                results.append(
                    HealthStatus(
                        source=source.name,
                        healthy=False,
                        latency_ms=0,
                        error=str(e),
                    )
                )
        return results

    def close_all(self):
        """Close all connectors."""
        for source in self._sources.values():
            try:
                source.connector.close()
            except Exception as e:
                logger.warning(f"Error closing {source.name}: {e}")


# Global registry instance
_registry: Optional[MemoryRegistry] = None


def get_registry() -> MemoryRegistry:
    """Get the global memory registry."""
    global _registry
    if _registry is None:
        _registry = MemoryRegistry()
    return _registry


def health_check_all() -> List[HealthStatus]:
    """Convenience function to check all sources."""
    return get_registry().health_check_all()


def get_enabled_connectors() -> List[MemoryConnector]:
    """Get list of enabled connectors."""
    return [s.connector for s in get_registry().get_enabled_sources()]
