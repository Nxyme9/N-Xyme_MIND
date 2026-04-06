"""TEMPR Retrieval Engine — Multi-strategy retrieval with RRF fusion.

Implements Hindsight's TEMPR pattern:
- Semantic retrieval (vector similarity)
- Keyword retrieval (FTS5 BM25)
- RRF fusion for result merging

All retrievers run in parallel, results fused via Reciprocal Rank Fusion.
"""

from .semantic import SemanticRetriever
from .keyword import KeywordRetriever
from .fusion import rrf_fusion, TEMPRRetriever

__all__ = [
    "SemanticRetriever",
    "KeywordRetriever",
    "rrf_fusion",
    "TEMPRRetriever",
]
