"""
Memory Injector — Pre-Agent Context Injection (Phase 1.4).

Injects contextual memory BEFORE agent dispatch to improve agent performance.
Searches memory for relevant context, ranks by importance, and compresses to
fit token budget.

Importance Scoring:
    success * 1.0 + recency * 0.5 + similarity * 0.3

Usage:
    from packages.orchestration.memory_injector import PreAgentMemoryInjector

    injector = PreAgentMemoryInjector()
    context = injector.inject(agent="hephaestus", task="implement JWT auth")
    print(context)  # Formatted context block for injection
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

ALLOWED_AGENTS = frozenset(
    {
        "hephaestus",
        "explore",
        "oracle",
        "librarian",
        "metis",
        "momus",
        "sisyphus",
        "sisyphus-junior",
        "atlas",
        "catalyst",
    }
)


def _sanitize_search_input(value: str, max_length: int = 500) -> str:
    if not isinstance(value, str):
        return ""
    sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value)
    sanitized = sanitized[:max_length]
    return sanitized.strip()


def _validate_agent(agent: str) -> str:
    agent = _sanitize_search_input(agent, max_length=30)
    return agent if agent in ALLOWED_AGENTS else "unknown"


# ============================================================================
# Configuration
# ============================================================================
# Configuration
# ============================================================================

# Token budget for injected context (enforced)
MAX_TOKENS = 500

# Approximate tokens per character (conservative for multilingual)
TOKENS_PER_CHAR = 0.25

# Persistence path for LRU cache
CACHE_STATE_FILE = os.environ.get("CACHE_STATE_FILE", "/tmp/nxyme_memory_cache.json")
CACHE_MAX_SIZE = 100


# ============================================================================
# Result Dataclass
# ============================================================================


@dataclass
class MemoryInjectionResult:
    """Result of memory injection operation."""

    context_block: str
    memories_injected: int
    tokens_used: int
    within_budget: bool

    def __post_init__(self) -> None:
        """Validate budget compliance."""
        self.within_budget = self.tokens_used <= MAX_TOKENS


# ============================================================================
# PreAgentMemoryInjector
# ============================================================================


class PreAgentMemoryInjector:
    """Injects contextual memory BEFORE agent dispatch.

    Implements Phase 1.4 of the revised masterplan:
    - Search memory for relevant context to current task
    - Rank by importance (success * 1.0 + recency * 0.5 + similarity * 0.3)
    - Compress to fit token budget (500 tokens max)
    - Return formatted context block for injection into agent prompts

    Attributes:
        MAX_TOKENS: Maximum tokens allowed for injected context.
    """

    MAX_TOKENS = MAX_TOKENS

    # Simple in-memory cache for repeated tasks (LRU behavior)
    _cache: Dict[str, str] = {}
    _cache_max_size = CACHE_MAX_SIZE

    # Cache persistence
    _cache_loaded = False

    # Pre-warmed queries for faster cold starts
    _warm_cache: Dict[str, List[Dict[str, Any]]] = {}
    _warm_cache_loaded = False

    def __init__(self, max_tokens: int = MAX_TOKENS) -> None:
        """Initialize injector with optional token budget override.

        Args:
            max_tokens: Maximum tokens for injected context (default: 500).
        """
        self.max_tokens = max_tokens

        # Load persisted cache first
        self._load_cache()

        # Auto-warm on first instantiation
        if not PreAgentMemoryInjector._warm_cache_loaded:
            self._async_warmup()

    def _async_warmup(self) -> None:
        """Pre-load common query results in background thread."""
        import threading

        def _do_warmup():
            # Common dev tasks that likely get repeated
            common_queries = [
                "implement auth",
                "fix bug",
                "add feature",
                "refactor code",
                "write test",
                "api endpoint",
                "database query",
                "create component",
                "add validation",
            ]
            for query in common_queries:
                try:
                    results = self._search_memory(query, limit=5)
                    PreAgentMemoryInjector._warm_cache[query] = results
                except Exception:
                    pass
            PreAgentMemoryInjector._warm_cache_loaded = True
            logger.info(f"Warm cache pre-loaded {len(common_queries)} queries")

        # Run warmup in background
        threading.Thread(target=_do_warmup, daemon=True).start()
        logger.debug("Started background warmup")

    def inject(self, agent: str, task: str) -> str:
        agent = _validate_agent(agent)
        task = _sanitize_search_input(task)

        cache_key = f"{agent}:{task}"
        if cache_key in PreAgentMemoryInjector._cache:
            return PreAgentMemoryInjector._cache[cache_key]

        # Check warm cache for partial match (task contains warm query)
        for warm_query, warm_results in PreAgentMemoryInjector._warm_cache.items():
            if warm_query in task and warm_results:
                # Use warm cache results, just rank and format
                ranked = self._rank_by_importance(warm_results)
                result = self._compress_to_budget(ranked)
                formatted = self._format_context_block(agent, task, result)
                PreAgentMemoryInjector._cache[cache_key] = formatted
                self._evict_cache_if_needed()
                self._save_cache()
                return formatted

        # Step 1: Search memory for relevant context
        memories = self._search_memory(task)

        if not memories:
            logger.debug(f"No memories found for task: {task[:50]}...")
            # Cache empty results too
            PreAgentMemoryInjector._cache[cache_key] = ""
            self._evict_cache_if_needed()
            self._save_cache()
            return ""

        # Step 2: Rank by importance
        ranked = self._rank_by_importance(memories)

        # Step 3: Compress to token budget
        result = self._compress_to_budget(ranked)

        # Step 4: Format context block
        formatted = self._format_context_block(agent, task, result)

        # Cache result
        PreAgentMemoryInjector._cache[cache_key] = formatted
        self._evict_cache_if_needed()
        self._save_cache()

        return formatted

    def _evict_cache_if_needed(self) -> None:
        """Evict oldest entries if cache exceeds max size."""
        if len(PreAgentMemoryInjector._cache) > PreAgentMemoryInjector._cache_max_size:
            # Remove oldest 20%
            keys_to_remove = list(PreAgentMemoryInjector._cache.keys())[:20]
            for key in keys_to_remove:
                del PreAgentMemoryInjector._cache[key]
            logger.debug(f"Cache evicted {len(keys_to_remove)} entries")

    # ============================================================================
    # Persistence (ROI #5)
    # ============================================================================

    def _load_cache(self) -> bool:
        """Load cache from persistent file. Returns True if successful."""
        if PreAgentMemoryInjector._cache_loaded:
            return True
        if not os.path.exists(CACHE_STATE_FILE):
            return False
        try:
            with open(CACHE_STATE_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    PreAgentMemoryInjector._cache = data
            PreAgentMemoryInjector._cache_loaded = True
            logger.info(
                f"Memory cache loaded ({len(PreAgentMemoryInjector._cache)} entries)"
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to load memory cache: {e}")
            return False

    def _save_cache(self) -> None:
        """Save cache to persistent file."""
        try:
            with open(CACHE_STATE_FILE, "w") as f:
                json.dump(PreAgentMemoryInjector._cache, f)
            logger.debug(
                f"Memory cache saved ({len(PreAgentMemoryInjector._cache)} entries)"
            )
        except Exception as e:
            logger.warning(f"Failed to save memory cache: {e}")

    def _search_memory(self, task: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search memory for relevant context to task.

        Args:
            task: Task description to search for.
            limit: Maximum results to return.

        Returns:
            List of memory dictionaries.
        """
        try:
            from packages.brain_mcp.namespaces.memory import memory_search_memories

            result = memory_search_memories(
                query=task,
                limit=limit,
                strict=False,
                rerank=False,
            )

            if isinstance(result, dict) and "error" in result:
                logger.warning(f"Memory search error: {result.get('error')}")
                return []

            results = result.get("results", []) if isinstance(result, dict) else []
            return results

        except ImportError as e:
            logger.warning(f"Memory tools not available: {e}")
            return []
        except Exception as e:
            logger.error(f"Memory search failed: {e}")
            return []

    def _rank_by_importance(
        self, memories: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Rank memories by importance scoring.

        Formula: success * 1.0 + recency * 0.5 + similarity * 0.3

        Args:
            memories: List of memory dictionaries.

        Returns:
            Sorted list by importance descending.
        """
        ranked = []

        for mem in memories:
            # Extract metadata
            metadata = mem.get("metadata", {})

            # Calculate importance components
            success = metadata.get("success", False)
            recency = metadata.get("recency_score", 0.5)
            similarity = metadata.get("similarity_score", 0.5)

            # Formula: success * 1.0 + recency * 0.5 + similarity * 0.3
            importance = (
                (1.0 if success else 0.0) * 1.0 + recency * 0.5 + similarity * 0.3
            )

            ranked.append(
                {
                    "id": mem.get("id"),
                    "content": mem.get("content", ""),
                    "importance": importance,
                    "timestamp": mem.get("created_at"),
                    "metadata": metadata,
                }
            )

        # Sort by importance descending
        ranked.sort(key=lambda x: x["importance"], reverse=True)

        return ranked

    def _compress_to_budget(
        self, memories: List[Dict[str, Any]]
    ) -> MemoryInjectionResult:
        """Compress memories to fit token budget.

        Args:
            memories: Ranked list of memories.

        Returns:
            MemoryInjectionResult with compressed context.
        """
        # Build context from memories
        context_parts: List[str] = []
        total_chars = 0

        for mem in memories:
            content = mem.get("content", "")
            if not content:
                continue

            # Check if adding this would exceed budget
            new_chars = total_chars + len(content) + 50  # +50 for formatting
            estimated_tokens = int(new_chars * TOKENS_PER_CHAR)

            if estimated_tokens > self.max_tokens:
                # Try to fit remaining memories more tightly
                remaining = self.max_tokens - total_chars
                if remaining < 100:
                    break

                # Truncate to fit
                max_chars = int(remaining / TOKENS_PER_CHAR) - 50
                if max_chars > 50:
                    content = content[:max_chars] + "..."
                    new_chars = total_chars + len(content)
                    estimated_tokens = int(new_chars * TOKENS_PER_CHAR)
                else:
                    break

            context_parts.append(content)
            total_chars = new_chars

            if estimated_tokens > self.max_tokens:
                break

        context = "\n\n".join(context_parts)
        tokens_used = int(total_chars * TOKENS_PER_CHAR)

        return MemoryInjectionResult(
            context_block=context,
            memories_injected=len(context_parts),
            tokens_used=tokens_used,
            within_budget=tokens_used <= self.max_tokens,
        )

    def _format_context_block(
        self, agent: str, task: str, result: MemoryInjectionResult
    ) -> str:
        """Format context block for injection.

        Args:
            agent: Target agent name.
            task: Task description.
            result: MemoryInjectionResult.

        Returns:
            Formatted context block string.
        """
        if not result.context_block:
            return ""

        # Build header
        lines = [
            "<!-- PREVIOUS CONTEXT -->",
            f"Agent: {agent}",
            f"Task: {task}",
            f"Memories: {result.memories_injected} | Tokens: {result.tokens_used}/{self.max_tokens}",
            "",
            result.context_block,
        ]

        return "\n".join(lines)

    def inject_for_tool_call(
        self,
        agent: str,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> str:
        agent = _validate_agent(agent)
        tool_name = _sanitize_search_input(tool_name, max_length=100)
        query = f"{tool_name}"
        if arguments:
            query += f" {' '.join(str(v) for v in arguments.values() if v)}"

        return self.inject(agent=agent, task=query)


# ============================================================================
# Convenience Functions
# ============================================================================


def inject_memory(agent: str, task: str) -> str:
    """Convenience function for memory injection."""
    injector = PreAgentMemoryInjector()
    return injector.inject(agent=agent, task=task)


# ============================================================================
# CLI (for testing)
# ============================================================================


if __name__ == "__main__":
    import sys

    # Basic test
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
    else:
        task = "implement authentication"

    injector = PreAgentMemoryInjector()
    result = injector.inject(agent="hephaestus", task=task)

    print(f"Task: {task}")
    print(f"Context:\n{result}")
