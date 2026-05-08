#!/usr/bin/env python3
"""
Tier 2 - LLM Summarization at 80% threshold

Triggers deep summarization when context reaches 80% capacity:
- Uses LLM to create comprehensive summary of conversation
- Preserves key facts, decisions, and action items
- Reduces context while maintaining important information
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Tier2SummarizationState:
    """State for Tier 2 summarization."""

    summary_count: int = 0
    last_summary_tokens: int = 0
    summary_history: list[str] = field(default_factory=list)


class Tier2Summarizer:
    """Tier 2 - LLM-powered summarization at 80% threshold."""

    def __init__(
        self,
        threshold: float = 0.80,
        max_summary_tokens: int = 4096,
        llm_client=None,
    ):
        self.threshold = threshold
        self.max_summary_tokens = max_summary_tokens
        self.llm_client = llm_client
        self.state = Tier2SummarizationState()

    def should_summarize(self, current_tokens: int, max_tokens: int) -> bool:
        """Check if deep summarization needed."""
        ratio = current_tokens / max_tokens if max_tokens > 0 else 0
        return ratio >= self.threshold

    def summarize(
        self,
        messages: list[dict],
        max_tokens: int = 131072,
        preserve_recent: int = 3,
    ) -> list[dict]:
        """Execute Tier 2 summarization.

        Strategy:
        1. Preserve last N messages (recent context)
        2. Summarize all older messages into compressed format
        3. Include key facts, decisions, action items

        Args:
            messages: List of {"role": "...", "content": "..."}
            max_tokens: Maximum context window
            preserve_recent: Number of recent messages to keep

        Returns:
            Summarized message list
        """
        if not messages:
            return messages

        current_tokens = sum(len(m.get("content", "")) // 4 for m in messages)

        if not self.should_summarize(current_tokens, max_tokens):
            return messages

        # Keep recent messages
        recent = messages[-preserve_recent:]
        older = messages[:-preserve_recent]

        if not older:
            return messages

        # Create comprehensive summary
        if self.llm_client:
            summary = self._llm_comprehensive_summarize(older)
        else:
            summary = self._extract_summarize(older)

        # Store in history
        self.state.summary_history.append(summary)
        self.state.summary_count += 1
        self.state.last_summary_tokens = current_tokens

        logger.info(
            f"Tier 2 summarize: {current_tokens} tokens → {len(summary)} char summary"
        )

        # Return summarized context
        summarized = [
            {
                "role": "system",
                "content": f"[Prior conversation summary: {summary}]",
            },
            *recent,
        ]

        return summarized

    def _llm_comprehensive_summarize(self, messages: list[dict]) -> str:
        """LLM-based comprehensive summarization."""
        try:
            # Build conversation text
            conversation = "\n".join(
                f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages
            )

            prompt = f"""Summarize this conversation comprehensively. Include:
1. Key decisions made
2. Important facts or information
3. Action items or tasks
4. Any errors encountered and how they were resolved
5. Technical details relevant to the work

Provide a detailed but concise summary (2-4 paragraphs):

{conversation}

Summary:"""

            response = self.llm_client.chat([{"role": "user", "content": prompt}])

            return response.get("content", "")[: self.max_summary_tokens]
        except Exception as e:
            logger.warning(f"LLM summarize failed: {e}")
            return self._extract_summarize(messages)

    def _extract_summarize(self, messages: list[dict]) -> str:
        """Extractive summarization - key sentences."""
        if not messages:
            return ""

        # Collect key information
        key_points = []
        for msg in messages:
            content = msg.get("content", "")
            # Take first 200 chars from each message
            if len(content) > 100:
                key_points.append(content[:200])
            else:
                key_points.append(content)

        return " | ".join(key_points[:10])  # Max 10 message summaries

    def get_stats(self) -> dict:
        """Get summarization statistics."""
        return {
            "threshold": self.threshold,
            "summary_count": self.state.summary_count,
            "last_summary_tokens": self.state.last_summary_tokens,
            "history_length": len(self.state.summary_history),
        }


# Singleton
_summarizer: Optional[Tier2Summarizer] = None


def get_tier2_summarizer() -> Tier2Summarizer:
    """Get singleton Tier 2 summarizer."""
    global _summarizer
    if _summarizer is None:
        _summarizer = Tier2Summarizer()
    return _summarizer


# Convenience function
def summarize_messages(
    messages: list[dict],
    max_tokens: int = 131072,
    llm_client=None,
) -> list[dict]:
    """Quick Tier 2 summarization function."""
    summarizer = get_tier2_summarizer()
    if llm_client:
        summarizer.llm_client = llm_client
    return summarizer.summarize(messages, max_tokens)


__all__ = [
    "Tier2Summarizer",
    "Tier2SummarizationState",
    "get_tier2_summarizer",
    "summarize_messages",
]
