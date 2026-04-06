#!/usr/bin/env python3
"""
File RRF — Reciprocal Rank Fusion for file + memory search.

Implements RRF to combine file search results with memory search results,
returning a unified ranked list with deduplication by content similarity.

RRF Formula: score = 1 / (k + rank) per Cormack et al. SIGIR 2009

Usage:
    from src.memory.file_rrf import rank_files_and_memories, fuse_results

    files = [{'content': 'test file', 'score': 0.9, 'source': 'file', 'metadata': {}, 'type': 'file'}]
    memories = [{'content': 'test memory', 'score': 0.8, 'source': 'memory', 'metadata': {}, 'type': 'memory'}]
    result = rank_files_and_memories(files, memories)
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# RRF Score Calculation
# ---------------------------------------------------------------------------


def get_rrf_score(rank: int, k: int = 60) -> float:
    """
    Calculate RRF score for a given rank.

    RRF formula: score = 1 / (k + rank)

    Args:
        rank: Position in ranked list (0-indexed)
        k: Constant (default 60, per Cormack et al.)

    Returns:
        RRF score for this rank
    """
    return 1.0 / (k + rank + 1)  # +1 because rank is 0-indexed


# ---------------------------------------------------------------------------
# Result Normalization
# ---------------------------------------------------------------------------


def normalize_result(result: dict, default_type: str = "unknown") -> dict:
    """
    Normalize a result dict to include required fields.

    Args:
        result: Raw result dict from file or memory search
        default_type: Default type if not specified

    Returns:
        Normalized result dict with all required fields
    """
    return {
        "content": result.get("content", ""),
        "score": result.get("score", 0.0),
        "source": result.get("source", "unknown"),
        "metadata": result.get("metadata", {}),
        "type": result.get("type", default_type),
    }


# ---------------------------------------------------------------------------
# RRF Fusion
# ---------------------------------------------------------------------------


def fuse_results(
    file_results: List[dict],
    memory_results: List[dict],
    k: int = 60,
) -> List[dict]:
    """
    Fuse file and memory results using Reciprocal Rank Fusion.

    Combines ranked lists from file search and memory search using RRF,
    then sorts by descending RRF score.

    Args:
        file_results: List of file search result dicts
                     Each dict should have: content, score, source, metadata, type
        memory_results: List of memory search result dicts
                       Each dict should have: content, score, source, metadata, type
        k: RRF constant (default 60)

    Returns:
        Fused list of result dicts sorted by RRF score descending
        Each dict includes: content, score, source, metadata, type, rrf_score
    """
    # Normalize results
    normalized_files = [normalize_result(r, "file") for r in file_results]
    normalized_memories = [normalize_result(r, "memory") for r in memory_results]

    # Build ranked lists for RRF
    file_ranked = [(i, r) for i, r in enumerate(normalized_files)]
    memory_ranked = [(i, r) for i, r in enumerate(normalized_memories)]

    # Calculate RRF scores for each result
    rrf_scores: Dict[int, float] = {}
    result_by_index: Dict[int, dict] = {}

    # Process file results
    for rank, result in file_ranked:
        rrf = get_rrf_score(rank, k)
        key = hash((result["type"], result["content"][:100].lower()))
        if key not in rrf_scores:
            rrf_scores[key] = 0.0
            result_by_index[key] = result
        rrf_scores[key] += rrf

    # Process memory results
    for rank, result in memory_ranked:
        rrf = get_rrf_score(rank, k)
        key = hash((result["type"], result["content"][:100].lower()))
        if key not in rrf_scores:
            rrf_scores[key] = 0.0
            result_by_index[key] = result
        rrf_scores[key] += rrf

    # Build fused results with RRF scores
    fused = []
    for key, rrf_score in rrf_scores.items():
        result = result_by_index[key].copy()
        result["rrf_score"] = rrf_score
        fused.append(result)

    # Sort by RRF score descending
    fused.sort(key=lambda r: r["rrf_score"], reverse=True)

    return fused


# ---------------------------------------------------------------------------
# Content Deduplication
# ---------------------------------------------------------------------------


def _content_similarity(a: str, b: str) -> float:
    """
    Calculate content similarity for deduplication.

    Uses simple substring matching - returns 1.0 if one is substring of other,
    or uses word overlap for longer content.

    Args:
        a: First content string
        b: Second content string

    Returns:
        Similarity score 0-1
    """
    if not a or not b:
        return 0.0

    # Direct match
    if a.lower() == b.lower():
        return 1.0

    # Substring match
    if a.lower() in b.lower() or b.lower() in a.lower():
        return 0.9

    # Word overlap
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())

    if not words_a or not words_b:
        return 0.0

    overlap = len(words_a & words_b) / len(words_a | words_b)
    return overlap


def deduplicate_by_content(results: List[dict]) -> List[dict]:
    """
    Deduplicate results by content similarity.

    If same content appears in multiple results (e.g., both file and memory),
    keep the one with higher RRF score.

    Args:
        results: List of result dicts with content and rrf_score

    Returns:
        Deduplicated list sorted by RRF score
    """
    if not results:
        return []

    # Sort by RRF score first (we want to keep highest score)
    sorted_results = sorted(results, key=lambda r: r.get("rrf_score", 0), reverse=True)

    kept = []
    seen_content: List[str] = []

    for result in sorted_results:
        content = result.get("content", "")

        # Check similarity with already kept results
        is_duplicate = False
        for seen in seen_content:
            if _content_similarity(content, seen) > 0.8:  # 80% similarity threshold
                is_duplicate = True
                break

        if not is_duplicate:
            kept.append(result)
            seen_content.append(content)

    return kept


# ---------------------------------------------------------------------------
# Main Ranking Function
# ---------------------------------------------------------------------------


def rank_files_and_memories(
    file_results: List[dict],
    memory_results: List[dict],
    k: int = 60,
    deduplicate: bool = True,
) -> List[dict]:
    """
    Main function to rank file and memory results together.

    Combines file search results with memory search results using RRF,
    applies deduplication, and returns unified ranked list.

    Args:
        file_results: List of file search result dicts
        memory_results: List of memory search result dicts
        k: RRF constant (default 60)
        deduplicate: Whether to deduplicate by content similarity (default True)

    Returns:
        Unified ranked list of results (files + memories)
        Each dict has: content, score, source, metadata, type, rrf_score

    Example:
        >>> files = [{'content': 'test file', 'score': 0.9, 'source': 'test'}]
        >>> memories = [{'content': 'test memory', 'score': 0.8, 'source': 'test'}]
        >>> results = rank_files_and_memories(files, memories)
        >>> print(f"Fused: {len(results)} results")
    """
    # Edge cases
    if not file_results and not memory_results:
        return []

    if not file_results:
        # Return memory results with default RRF scores
        return deduplicate_by_content(memory_results) if deduplicate else memory_results

    if not memory_results:
        # Return file results with default RRF scores
        return deduplicate_by_content(file_results) if deduplicate else file_results

    # Fuse using RRF
    fused = fuse_results(file_results, memory_results, k)

    # Deduplicate if enabled
    if deduplicate:
        return deduplicate_by_content(fused)

    return fused


# ---------------------------------------------------------------------------
# Package Exports
# ---------------------------------------------------------------------------

__all__ = [
    "get_rrf_score",
    "fuse_results",
    "rank_files_and_memories",
    "deduplicate_by_content",
]


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Test the module
    files = [
        {
            "content": "test file content",
            "score": 0.9,
            "source": "filesystem",
            "metadata": {"path": "/test.py"},
            "type": "file",
        },
    ]
    memories = [
        {
            "content": "test memory content",
            "score": 0.8,
            "source": "memory",
            "metadata": {"id": "123"},
            "type": "memory",
        },
    ]

    result = rank_files_and_memories(files, memories)
    print(f"Fused: {len(result)} results")
    for r in result:
        print(
            f"  - {r['type']}: {r['content'][:30]}... (rrf_score: {r.get('rrf_score', 0):.4f})"
        )
