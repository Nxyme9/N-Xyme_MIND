#!/usr/bin/env python3
"""
Tier 1 Micro-Compact - MemGPT-style paging at 50% context threshold

Triggers micro-compaction when context reaches 50% capacity:
- Moves least recent tokens to compressed summary
- Preserves recent conversation context
- Fast operation (<100ms)
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class MicroCompactState:
    """State for micro-compaction."""

    original_tokens: list = field(default_factory=list)
    compressed_tokens: list = field(default_factory=list)
    summary: str = ""
    compact_threshold: float = 0.50  # 50% of context
    last_compact_size: int = 0


class MicroCompactor:
    """Tier 1 micro-compactor - lightweight compression at 50% threshold."""

    def __init__(
        self,
        threshold: float = 0.50,
        max_compressed_tokens: int = 2048,
        llm_client=None,
    ):
        self.threshold = threshold
        self.max_compressed_tokens = max_compressed_tokens
        self.llm_client = llm_client
        self.state = MicroCompactState()

    def should_compact(self, current_tokens: int, max_tokens: int) -> bool:
        """Check if compaction needed."""
        ratio = current_tokens / max_tokens if max_tokens > 0 else 0
        return ratio >= self.threshold

    def compact(self, messages: list[dict], max_tokens: int = 131072) -> list[dict]:
        """Execute micro-compaction on messages.

        Strategy:
        1. Keep last N messages (recent context)
        2. Compress older messages into summary
        3. Insert summary as system context

        Args:
            messages: List of {"role": "...", "content": "..."}
            max_tokens: Maximum context window

        Returns:
            Compacted message list
        """
        if not messages:
            return messages

        current_tokens = sum(len(m.get("content", "")) // 4 for m in messages)

        if not self.should_compact(current_tokens, max_tokens):
            return messages

        # Keep last 5 messages as recent context
        recent_count = 5
        recent = messages[-recent_count:]
        older = messages[:-recent_count]

        # Compress older messages
        if older:
            if self.llm_client:
                # Use LLM for smart summarization
                summary = self._llm_summarize(older)
            else:
                # Simple extractive summary
                summary = self._simple_summarize(older)

            # Create compacted messages
            compacted = [
                {"role": "system", "content": f"[Previous context summary: {summary}]"},
                *recent,
            ]

            self.state.last_compact_size = current_tokens
            logger.info(f"Micro-compact: {current_tokens} → {len(compacted)} messages")

            return compacted

        return messages

    def _llm_summarize(self, messages: list[dict]) -> str:
        """LLM-based summarization."""
        try:
            prompt = f"Summarize this conversation concisely:\n\n"
            for m in messages:
                prompt += f"{m.get('role', 'user')}: {m.get('content', '')}\n"
            prompt += "\nProvide a 2-3 sentence summary of key points."

            response = self.llm_client.chat([{"role": "user", "content": prompt}])

            return response.get("content", "")[:500]
        except Exception as e:
            logger.warning(f"LLM summarize failed: {e}")
            return self._simple_summarize(messages)

    def _simple_summarize(self, messages: list[dict]) -> str:
        """Simple extractive summary - first and last message content."""
        if not messages:
            return ""

        first = messages[0].get("content", "")[:200]
        last = messages[-1].get("content", "")[:200]

        return f"Started with: {first} ... Ended with: {last}"

    def get_stats(self) -> dict:
        """Get compaction statistics."""
        return {
            "threshold": self.threshold,
            "last_compact_size": self.state.last_compact_size,
            "compressed_tokens": len(self.state.compressed_tokens),
        }


# Singleton
_compactor: Optional[MicroCompactor] = None


def get_micro_compactor() -> MicroCompactor:
    """Get singleton compactor."""
    global _compactor
    if _compactor is None:
        _compactor = MicroCompactor()
    return _compactor


# Convenience function
def compact_messages(messages: list[dict], max_tokens: int = 131072) -> list[dict]:
    """Quick compact function."""
    return get_micro_compactor().compact(messages, max_tokens)
