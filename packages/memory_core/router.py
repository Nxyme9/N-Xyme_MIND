from dataclasses import dataclass, field
from typing import List, Any


@dataclass
class UnifiedMemoryQuery:
    query: str
    max_results_per_source: int = 10
    use_semantic: bool = True
    filters: dict = field(default_factory=dict)


@dataclass
class MemoryResult:
    source: str
    content: Any
    relevance_score: float = 0.0


@dataclass
class SearchResults:
    results: List[MemoryResult]
    total_results: int = 0
    sources_queried: List[str] = field(default_factory=list)
    query_time_ms: float = 0.0


class MemoryRouter:
    def __init__(self):
        pass

    def search(self, query: UnifiedMemoryQuery) -> SearchResults:
        # Stub - returns empty results
        return SearchResults(results=[], total_results=0, sources_queried=["stub"])
