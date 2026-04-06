"""Context Window Management — Intelligent context handling.

Implements:
- Sliding window with priority retention
- Context compression for long conversations
- Chunked context for large codebases
- Integration with token_estimator and context_compact
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ContextChunk:
    """A chunk of context with priority and metadata."""

    content: str
    priority: int  # 1-10, higher = more important
    source: str  # Where this chunk came from
    tokens: int = 0
    is_compressed: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class ContextManager:
    """Manages context window intelligently."""

    def __init__(self, max_tokens: int = 32768):
        """Initialize context manager.

        Args:
            max_tokens: Maximum context window size.
        """
        self.max_tokens = max_tokens
        self.chunks: list[ContextChunk] = []
        self._total_tokens = 0

    def add_chunk(
        self,
        content: str,
        priority: int = 5,
        source: str = "unknown",
        tokens: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> ContextChunk:
        """Add a context chunk.

        Args:
            content: Chunk content.
            priority: Priority level (1-10).
            source: Source identifier.
            tokens: Token count (0 = estimate).
            metadata: Additional metadata.

        Returns:
            Created ContextChunk.
        """
        if tokens == 0:
            tokens = len(content) // 4  # Rough estimate

        chunk = ContextChunk(
            content=content,
            priority=priority,
            source=source,
            tokens=tokens,
            metadata=metadata or {},
        )
        self.chunks.append(chunk)
        self._total_tokens += tokens

        # Auto-compress if exceeding limit
        if self._total_tokens > self.max_tokens:
            self._compress()

        return chunk

    def get_context(self, max_tokens: int | None = None) -> str:
        """Get optimized context string.

        Args:
            max_tokens: Maximum tokens to return (None = use manager limit).

        Returns:
            Optimized context string.
        """
        limit = max_tokens or self.max_tokens
        current_tokens = 0
        parts = []

        # Sort by priority (highest first)
        sorted_chunks = sorted(self.chunks, key=lambda c: c.priority, reverse=True)

        for chunk in sorted_chunks:
            if current_tokens + chunk.tokens > limit:
                # Try to compress this chunk
                if not chunk.is_compressed and chunk.tokens > 100:
                    compressed = self._compress_content(
                        chunk.content, limit - current_tokens
                    )
                    if compressed:
                        parts.append(compressed)
                        current_tokens += len(compressed) // 4
                continue

            parts.append(chunk.content)
            current_tokens += chunk.tokens

        return "\n\n".join(parts)

    def compress_chunk(self, index: int, target_tokens: int) -> bool:
        """Compress a specific chunk.

        Args:
            index: Chunk index.
            target_tokens: Target token count.

        Returns:
            True if compression succeeded.
        """
        if index < 0 or index >= len(self.chunks):
            return False

        chunk = self.chunks[index]
        if chunk.is_compressed:
            return False

        compressed = self._compress_content(chunk.content, target_tokens)
        if compressed:
            old_tokens = chunk.tokens
            chunk.content = compressed
            chunk.tokens = len(compressed) // 4
            chunk.is_compressed = True
            self._total_tokens -= old_tokens - chunk.tokens
            return True

        return False

    def remove_low_priority(self, min_priority: int = 3) -> int:
        """Remove chunks below minimum priority.

        Args:
            min_priority: Minimum priority to keep.

        Returns:
            Number of chunks removed.
        """
        original_count = len(self.chunks)
        removed_tokens = 0

        for chunk in self.chunks:
            if chunk.priority < min_priority:
                removed_tokens += chunk.tokens

        self.chunks = [c for c in self.chunks if c.priority >= min_priority]
        self._total_tokens -= removed_tokens

        return original_count - len(self.chunks)

    def clear(self) -> None:
        """Clear all chunks."""
        self.chunks.clear()
        self._total_tokens = 0

    def get_stats(self) -> dict[str, Any]:
        """Get context manager statistics."""
        by_priority: dict[int, int] = {}
        by_source: dict[str, int] = {}

        for chunk in self.chunks:
            by_priority[chunk.priority] = by_priority.get(chunk.priority, 0) + 1
            by_source[chunk.source] = by_source.get(chunk.source, 0) + chunk.tokens

        return {
            "total_chunks": len(self.chunks),
            "total_tokens": self._total_tokens,
            "max_tokens": self.max_tokens,
            "usage_pct": round(self._total_tokens / max(1, self.max_tokens) * 100, 1),
            "by_priority": by_priority,
            "by_source": by_source,
        }

    def _compress(self) -> None:
        """Auto-compress context to fit within limits."""
        # Remove lowest priority chunks first
        self.chunks.sort(key=lambda c: c.priority)

        while self._total_tokens > self.max_tokens and self.chunks:
            chunk = self.chunks.pop(0)
            self._total_tokens -= chunk.tokens

    def _compress_content(self, content: str, target_tokens: int) -> str | None:
        """Compress content to target token count.

        In production, this would use an LLM to summarize.
        For now, uses simple extraction.

        Args:
            content: Content to compress.
            target_tokens: Target token count.

        Returns:
            Compressed content or None if can't compress.
        """
        target_chars = target_tokens * 4
        if len(content) <= target_chars:
            return content

        # Keep first and last portions
        first_portion = content[: target_chars // 2]
        last_portion = content[-target_chars // 2 :]

        return f"{first_portion}\n\n... [compressed] ...\n\n{last_portion}"


# Global singleton
_context_manager = ContextManager()


def add_context_chunk(
    content: str,
    priority: int = 5,
    source: str = "unknown",
    tokens: int = 0,
    metadata: dict[str, Any] | None = None,
) -> ContextChunk:
    """Convenience function to add a context chunk."""
    return _context_manager.add_chunk(content, priority, source, tokens, metadata)


def get_context(max_tokens: int | None = None) -> str:
    """Convenience function to get context."""
    return _context_manager.get_context(max_tokens)
