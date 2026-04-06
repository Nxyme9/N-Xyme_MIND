"""Context Compaction — Intelligent context window management.

Ported from ant-source-code-main/services/compact/
Implements intelligent context window management with:
- Conversation summarization when approaching limits
- Priority-based context pruning (keep important, discard filler)
- Sliding window with priority retention
- Context compression for long conversations

Pattern: Monitors context window usage and automatically compacts
conversations when approaching limits, preserving critical information.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Compaction thresholds
COMPACT_WARNING_THRESHOLD = 0.7  # Warn at 70% context usage
COMPACT_ACTION_THRESHOLD = 0.85  # Compact at 85% context usage
COMPACT_CRITICAL_THRESHOLD = 0.95  # Emergency compact at 95%

# Priority levels for context retention
PRIORITY_CRITICAL = 10  # System prompts, key decisions
PRIORITY_HIGH = 8  # User corrections, important context
PRIORITY_MEDIUM = 5  # Regular conversation
PRIORITY_LOW = 3  # Filler, summaries, tool outputs
PRIORITY_DISCARDABLE = 1  # Temporary context, can be discarded


@dataclass
class ContextSegment:
    """A segment of context with priority and metadata."""

    id: str
    role: str
    content: str
    priority: int
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    tokens: int = 0
    is_compacted: bool = False
    compacted_summary: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class CompactionResult:
    """Result of context compaction."""

    original_tokens: int
    compacted_tokens: int
    reduction_pct: float
    segments_compacted: int
    segments_discarded: int
    summary: str


class ContextCompactor:
    """Intelligent context window management."""

    def __init__(self, context_window: int = 32768):
        """Initialize compactor.

        Args:
            context_window: Maximum context window size in tokens.
        """
        self.context_window = context_window
        self.segments: list[ContextSegment] = []
        self._segment_counter = 0

    def add_segment(
        self,
        role: str,
        content: str,
        priority: int = PRIORITY_MEDIUM,
        tags: list[str] | None = None,
    ) -> ContextSegment:
        """Add a context segment.

        Args:
            role: Message role (system, user, assistant, tool).
            content: Message content.
            priority: Priority level (1-10).
            tags: Optional tags for filtering.

        Returns:
            Created ContextSegment.
        """
        self._segment_counter += 1
        segment = ContextSegment(
            id=f"seg_{self._segment_counter}",
            role=role,
            content=content,
            priority=priority,
            tags=tags or [],
        )
        self.segments.append(segment)
        return segment

    def get_total_tokens(self) -> int:
        """Get total tokens in all segments."""
        return sum(s.tokens for s in self.segments)

    def get_context_usage_pct(self) -> float:
        """Get current context usage percentage."""
        total = self.get_total_tokens()
        return (total / self.context_window * 100) if self.context_window > 0 else 0

    def needs_compaction(self, threshold: float = COMPACT_ACTION_THRESHOLD) -> bool:
        """Check if context needs compaction.

        Args:
            threshold: Usage percentage threshold.

        Returns:
            True if compaction is needed.
        """
        return self.get_context_usage_pct() >= (threshold * 100)

    def compact(
        self,
        target_tokens: int | None = None,
        target_pct: float = 0.7,
    ) -> CompactionResult:
        """Compact context to fit within limits.

        Args:
            target_tokens: Target token count (None = auto-calculate).
            target_pct: Target context usage percentage.

        Returns:
            CompactionResult with compaction stats.
        """
        if target_tokens is None:
            target_tokens = int(self.context_window * target_pct)

        original_tokens = self.get_total_tokens()
        if original_tokens <= target_tokens:
            return CompactionResult(
                original_tokens=original_tokens,
                compacted_tokens=original_tokens,
                reduction_pct=0.0,
                segments_compacted=0,
                segments_discarded=0,
                summary="No compaction needed",
            )

        # Sort segments by priority (lowest first)
        sorted_segments = sorted(self.segments, key=lambda s: s.priority)

        compacted_count = 0
        discarded_count = 0
        current_tokens = original_tokens

        for segment in sorted_segments:
            if current_tokens <= target_tokens:
                break

            if segment.is_compacted:
                continue

            # Try to compact the segment
            if segment.priority <= PRIORITY_LOW:
                # Low priority: summarize or discard
                if segment.tokens > 500:
                    # Summarize long segments
                    segment.compacted_summary = self._summarize_segment(segment.content)
                    segment.is_compacted = True
                    old_tokens = segment.tokens
                    segment.tokens = len(segment.compacted_summary) // 4  # Estimate
                    current_tokens -= old_tokens - segment.tokens
                    compacted_count += 1
                else:
                    # Discard short low-priority segments
                    current_tokens -= segment.tokens
                    segment.tokens = 0
                    discarded_count += 1
            elif segment.priority <= PRIORITY_MEDIUM:
                # Medium priority: summarize if very long
                if segment.tokens > 1000:
                    segment.compacted_summary = self._summarize_segment(segment.content)
                    segment.is_compacted = True
                    old_tokens = segment.tokens
                    segment.tokens = len(segment.compacted_summary) // 4
                    current_tokens -= old_tokens - segment.tokens
                    compacted_count += 1

        reduction_pct = (
            ((original_tokens - current_tokens) / original_tokens * 100)
            if original_tokens > 0
            else 0
        )

        return CompactionResult(
            original_tokens=original_tokens,
            compacted_tokens=current_tokens,
            reduction_pct=round(reduction_pct, 2),
            segments_compacted=compacted_count,
            segments_discarded=discarded_count,
            summary=f"Compacted {compacted_count} segments, discarded {discarded_count}. Reduced by {reduction_pct:.1f}%",
        )

    def _summarize_segment(self, content: str, max_length: int = 200) -> str:
        """Summarize a segment (placeholder - would use LLM in production).

        Args:
            content: Segment content to summarize.
            max_length: Maximum summary length.

        Returns:
            Summarized content.
        """
        # Simple extraction: keep first sentence and key phrases
        sentences = content.split(". ")
        if len(sentences) <= 2:
            return (
                content[:max_length] + "..." if len(content) > max_length else content
            )

        # Keep first sentence and last sentence
        summary = sentences[0]
        if len(sentences) > 1:
            summary += ". " + sentences[-1]

        if len(summary) > max_length:
            summary = summary[:max_length] + "..."

        return summary

    def get_compacted_context(self) -> list[dict[str, Any]]:
        """Get context as list of message dicts, using summaries where available.

        Returns:
            List of message dicts suitable for API calls.
        """
        messages = []
        for segment in self.segments:
            if segment.tokens == 0:
                continue  # Discarded

            content = (
                segment.compacted_summary if segment.is_compacted else segment.content
            )
            messages.append(
                {
                    "role": segment.role,
                    "content": content,
                }
            )

        return messages

    def get_priority_summary(self) -> dict[str, Any]:
        """Get summary of context by priority level.

        Returns:
            Dict with priority breakdown.
        """
        by_priority: dict[int, dict[str, Any]] = {}
        for segment in self.segments:
            if segment.priority not in by_priority:
                by_priority[segment.priority] = {
                    "count": 0,
                    "tokens": 0,
                    "compacted": 0,
                }
            by_priority[segment.priority]["count"] += 1
            by_priority[segment.priority]["tokens"] += segment.tokens
            if segment.is_compacted:
                by_priority[segment.priority]["compacted"] += 1

        return {
            "total_segments": len(self.segments),
            "total_tokens": self.get_total_tokens(),
            "context_usage_pct": self.get_context_usage_pct(),
            "by_priority": by_priority,
        }

    def clear(self) -> None:
        """Clear all segments."""
        self.segments.clear()
        self._segment_counter = 0

    def remove_low_priority(self, min_priority: int = PRIORITY_MEDIUM) -> int:
        """Remove segments below minimum priority.

        Args:
            min_priority: Minimum priority to keep.

        Returns:
            Number of segments removed.
        """
        original_count = len(self.segments)
        self.segments = [s for s in self.segments if s.priority >= min_priority]
        return original_count - len(self.segments)


# Global singleton
_compactor = ContextCompactor()


def add_context_segment(
    role: str,
    content: str,
    priority: int = PRIORITY_MEDIUM,
    tags: list[str] | None = None,
) -> ContextSegment:
    """Convenience function to add context segment."""
    return _compactor.add_segment(role, content, priority, tags)


def needs_compaction(threshold: float = COMPACT_ACTION_THRESHOLD) -> bool:
    """Convenience function to check if compaction is needed."""
    return _compactor.needs_compaction(threshold)


def compact_context(
    target_tokens: int | None = None,
    target_pct: float = 0.7,
) -> CompactionResult:
    """Convenience function to compact context."""
    return _compactor.compact(target_tokens, target_pct)


def get_compacted_context() -> list[dict[str, Any]]:
    """Convenience function to get compacted context."""
    return _compactor.get_compacted_context()
