"""
athena.core.models
==================

Shared data structures and Pydantic models.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SearchResult:
    """
    Standardized search result object.
    Used by: Smart Search, Reranker, Context Window.
    """

    id: str
    content: str
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0  # Raw score from source (cos-sim or keyword match)
    rrf_score: float = 0.0  # Fused Reciprocal Rank score
    signals: dict[str, Any] = field(default_factory=dict)  # Debug info

    def to_dict(self) -> dict[str, Any]:
        d = {
            "id": self.id,
            "content": self.content[:100] + "...",
            "rrf_score": self.rrf_score,
            "signals": self.signals,
        }
        if self.metadata.get("path"):
            d["path"] = self.metadata["path"]
        return d
