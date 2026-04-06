"""Base Store interface for memory system."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class Store(ABC):
    """Abstract base class for memory stores."""

    @abstractmethod
    def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
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
    def stats(self) -> Dict[str, Any]:
        """Get statistics about the store."""
        pass
