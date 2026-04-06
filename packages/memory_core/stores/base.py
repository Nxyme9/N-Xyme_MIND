"""Base Store interface for memory system.

Provides typed interfaces for:
- Data classes: SearchResult, MemoryRecord
- Abstract stores: VectorStore, RelationalStore, GraphStore, Retriever
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class SearchResult:
    """Single search result with score and metadata."""

    id: str
    content: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str = "semantic"  # "semantic", "keyword", "graph", "hindsight"


@dataclass
class MemoryRecord:
    """A memory record stored in the memory system."""

    id: str
    content: str
    kind: str = "episodic"  # "episodic", "semantic", "reasoning"
    scope: str = "session"  # "session", "cross_session", "global"
    tier: str = "short_term"  # "short_term", "long_term", "dormant", "archived"
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Abstract Base Classes
# ---------------------------------------------------------------------------


class VectorStore(ABC):
    """Abstract base class for vector stores."""

    @abstractmethod
    def add(self, id: str, content: str, vector: list[float]) -> None:
        """Add a vector to the store."""
        pass

    @abstractmethod
    def search(self, query: str, top_k: int) -> list[SearchResult]:
        """Search for similar vectors."""
        pass

    @abstractmethod
    def delete(self, id: str) -> bool:
        """Delete a vector by ID."""
        pass

    @abstractmethod
    def stats(self) -> dict[str, Any]:
        """Get statistics about the store."""
        pass


class RelationalStore(ABC):
    """Abstract base class for relational stores."""

    @abstractmethod
    def store(self, record: MemoryRecord) -> str:
        """Store a memory record and return its ID."""
        pass

    @abstractmethod
    def get(self, id: str) -> MemoryRecord | None:
        """Get a memory record by ID."""
        pass

    @abstractmethod
    def search(self, query: str, limit: int) -> list[MemoryRecord]:
        """Search for memory records."""
        pass

    @abstractmethod
    def delete(self, id: str) -> bool:
        """Delete a memory record by ID."""
        pass

    @abstractmethod
    def stats(self) -> dict[str, Any]:
        """Get statistics about the store."""
        pass


class GraphStore(ABC):
    """Abstract base class for graph stores."""

    @abstractmethod
    def add_node(self, id: str, node_type: str, properties: dict) -> None:
        """Add a node to the graph."""
        pass

    @abstractmethod
    def add_edge(
        self, source: str, target: str, relation: str, properties: dict | None = None
    ) -> None:
        """Add an edge between two nodes."""
        pass

    @abstractmethod
    def get_node(self, id: str) -> dict | None:
        """Get a node by ID."""
        pass

    @abstractmethod
    def traverse(self, start_id: str, relation: str, depth: int) -> list[str]:
        """Traverse the graph from a starting node."""
        pass

    @abstractmethod
    def stats(self) -> dict[str, Any]:
        """Get statistics about the graph store."""
        pass


class Retriever(ABC):
    """Abstract base class for memory retrievers."""

    @abstractmethod
    def search(self, query: str, top_k: int) -> list[SearchResult]:
        """Search for memory records."""
        pass

    @abstractmethod
    def get_capabilities(self) -> list[str]:
        """Get the capabilities of this retriever."""
        pass


# ---------------------------------------------------------------------------
# Legacy Store (kept for compatibility)
# ---------------------------------------------------------------------------


class Store(ABC):
    """Abstract base class for memory stores."""

    @abstractmethod
    def search(self, query: str, **kwargs) -> list[dict[str, Any]]:
        """Search the store for matching items."""
        pass

    @abstractmethod
    def store(self, content: str, **kwargs) -> str:
        """Store content and return an ID."""
        pass

    @abstractmethod
    def delete(self, id: str) -> bool:
        """Delete an item by ID."""
        pass

    @abstractmethod
    def stats(self) -> dict[str, Any]:
        """Get statistics about the store."""
        pass


__all__ = [
    "SearchResult",
    "MemoryRecord",
    "VectorStore",
    "RelationalStore",
    "GraphStore",
    "Retriever",
    "Store",
]
