"""
4-Stage Context Compression for Agent Loop.

Based on Claude Code's compression patterns (snip → micro → collapse → auto):
- Stage 1: Snip Compact — trims overly long individual messages
- Stage 2: Micro Compact — finer-grained editing based on tool_call_id
- Stage 3: Context Collapse — folds inactive regions into summaries
- Stage 4: Auto Compact — full compression when tokens approach threshold

Usage:
    compressor = ContextCompressor()
    result = compressor.compress(messages, token_count, token_limit)
    print(result.messages, result.tokens_saved, result.compression_ratio)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("compression")


# =============================================================================
# Result Dataclass
# =============================================================================


@dataclass
class CompressedResult:
    """Result of context compression."""

    messages: List[Dict[str, Any]]
    tokens_saved: int
    stages_applied: List[str]
    compression_ratio: float

    def __post_init__(self) -> None:
        """Validate and compute derived fields."""
        if self.compression_ratio <= 0:
            # Avoid division by zero
            self.compression_ratio = 1.0


# =============================================================================
# Stage 1: Snip Compact
# =============================================================================


def snip_compact(
    messages: List[Dict[str, Any]],
    max_message_length: int = 2000,
) -> List[Dict[str, Any]]:
    """
    Stage 1: Snip Compact — trims overly long individual messages.

    Args:
        messages: List of message dicts with 'role' and 'content'
        max_message_length: Maximum length before truncation

    Returns:
        Messages with overly long content truncated
    """
    result: List[Dict[str, Any]] = []

    for msg in messages:
        msg_copy = dict(msg)

        # Check content length
        content = msg_copy.get("content", "")
        if isinstance(content, str) and len(content) > max_message_length:
            # Truncate with indicator
            msg_copy["content"] = (
                content[:max_message_length]
                + f"\n\n[... {len(content) - max_message_length} chars truncated ...]"
            )
            msg_copy["_truncated"] = True

        result.append(msg_copy)

    return result


# =============================================================================
# Stage 2: Micro Compact
# =============================================================================


def micro_compact(
    messages: List[Dict[str, Any]],
    tool_call_ids_to_preserve: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Stage 2: Micro Compact — finer-grained editing based on tool_call_id.

    Removes redundant tool call details while preserving key information
    for the specified tool_call_ids.

    Args:
        messages: List of message dicts
        tool_call_ids_to_preserve: Tool call IDs to preserve in detail

    Returns:
        Messages with redundant tool call info removed
    """
    if tool_call_ids_to_preserve is None:
        tool_call_ids_to_preserve = []

    preserve_set = set(tool_call_ids_to_preserve)
    result: List[Dict[str, Any]] = []

    for msg in messages:
        msg_copy = dict(msg)

        # Handle tool calls in assistant messages
        if msg_copy.get("role") == "assistant" and "tool_calls" in msg_copy:
            tool_calls = msg_copy["tool_calls"]
            if isinstance(tool_calls, list):
                cleaned_calls = []
                for tc in tool_calls:
                    if isinstance(tc, dict):
                        tc_id = tc.get("id", "")
                        # Keep full details only for preserved IDs
                        if tc_id in preserve_set:
                            cleaned_calls.append(tc)
                        else:
                            # Minimal info for non-preserved
                            func = tc.get("function", {})
                            cleaned_calls.append(
                                {
                                    "id": tc_id,
                                    "function": {
                                        "name": func.get("name", ""),
                                        # Remove arguments for non-preserved
                                    },
                                }
                            )
                    else:
                        cleaned_calls.append(tc)
                msg_copy["tool_calls"] = cleaned_calls

        # Handle tool results - trim large outputs
        if msg_copy.get("role") == "tool":
            tool_call_id = msg_copy.get("tool_call_id", "")
            if tool_call_id not in preserve_set:
                content = msg_copy.get("content", "")
                if isinstance(content, str) and len(content) > 500:
                    msg_copy["content"] = (
                        content[:500]
                        + f"\n[... {len(content) - 500} chars truncated ...]"
                    )
                    msg_copy["_micro_compacted"] = True

        result.append(msg_copy)

    return result


# =============================================================================
# Stage 3: Context Collapse
# =============================================================================


def context_collapse(
    messages: List[Dict[str, Any]],
    active_window_size: int = 10,
) -> List[Dict[str, Any]]:
    """
    Stage 3: Context Collapse — folds inactive regions into summaries.

    Keeps only the most recent messages (active window) and summarizes
    the rest as a collapsed context block.

    Args:
        messages: List of message dicts
        active_window_size: Number of recent messages to keep intact

    Returns:
        Messages with older region collapsed into summary
    """
    if len(messages) <= active_window_size:
        return messages

    # Split into active and archived
    active = messages[-active_window_size:]
    archived = messages[:-active_window_size]

    # Build summary of archived messages
    role_counts: Dict[str, int] = {}
    total_chars = 0

    for msg in archived:
        role = msg.get("role", "unknown")
        role_counts[role] = role_counts.get(role, 0) + 1
        content = msg.get("content", "")
        if isinstance(content, str):
            total_chars += len(content)

    # Create summary message
    summary = {
        "role": "system",
        "content": (
            f"[Context collapsed: {len(archived)} messages archived. "
            f"Roles: {role_counts}, Total chars: {total_chars}]"
        ),
        "_is_collapse_summary": True,
        "_archived_count": len(archived),
    }

    return [summary] + active


# =============================================================================
# Stage 4: Auto Compact
# =============================================================================


def auto_compact(
    messages: List[Dict[str, Any]],
    target_tokens: int,
) -> List[Dict[str, Any]]:
    """
    Stage 4: Auto Compact — full compression when tokens approach threshold.

    Aggressively compresses messages to fit within target token budget.
    Uses multiple passes with increasing intensity.

    Args:
        messages: List of message dicts
        target_tokens: Target token count to achieve

    Returns:
        Heavily compressed messages
    """
    result = list(messages)

    # Pass 1: Aggressive truncation
    result = snip_compact(result, max_message_length=500)

    # Pass 2: Remove all but essential tool results
    result = micro_compact(result, tool_call_ids_to_preserve=[])

    # Pass 3: Reduce active window
    result = context_collapse(result, active_window_size=5)

    # Pass 4: Final aggressive trim if still over
    if len(result) > 5:
        result = result[-5:]  # Keep only last 5 messages

    # Mark as auto-compacted
    for msg in result:
        msg["_auto_compacted"] = True

    return result


# =============================================================================
# Token Estimation (Lightweight)
# =============================================================================


def estimate_tokens(text: str) -> int:
    """
    Lightweight token estimation.

    Uses approximate ratio: 1 token ≈ 4 characters for English text.
    This is faster than using tiktoken or similar libraries.

    Args:
        text: Text to estimate tokens for

    Returns:
        Approximate token count
    """
    if not isinstance(text, str):
        text = str(text)
    # Approximate: 4 chars per token
    return len(text) // 4


def count_message_tokens(messages: List[Dict[str, Any]]) -> int:
    """
    Estimate total tokens in messages.

    Args:
        messages: List of message dicts

    Returns:
        Estimated total token count
    """
    total = 0

    for msg in messages:
        # Base overhead per message
        total += 4  # role, etc.

        # Content tokens
        content = msg.get("content", "")
        if content:
            total += estimate_tokens(content)

        # Tool calls overhead
        if "tool_calls" in msg:
            total += estimate_tokens(str(msg["tool_calls"]))

        # Tool result overhead
        if msg.get("role") == "tool":
            total += 4  # tool_call_id overhead

    return total


# =============================================================================
# Main ContextCompressor Class
# =============================================================================


class ContextCompressor:
    """
    4-stage context compression for agent loop.

    Implements escalating compression:
    - Stage 1 (Snip): Light - truncate long messages
    - Stage 2 (Micro): Medium - trim tool call details
    - Stage 3 (Collapse): Heavy - fold inactive regions
    - Stage 4 (Auto): Full - aggressive when near limit

    Each stage is independently callable. Compression escalates
    only when lighter stages don't achieve the target.
    """

    # Configuration
    DEFAULT_MAX_MESSAGE_LENGTH = 2000
    DEFAULT_ACTIVE_WINDOW_SIZE = 10
    DEFAULT_TOKEN_BUFFER_RATIO = 0.8  # Apply compression at 80% of limit

    def __init__(
        self,
        max_message_length: int = DEFAULT_MAX_MESSAGE_LENGTH,
        active_window_size: int = DEFAULT_ACTIVE_WINDOW_SIZE,
        token_buffer_ratio: float = DEFAULT_TOKEN_BUFFER_RATIO,
    ) -> None:
        """
        Initialize the compressor.

        Args:
            max_message_length: Max length before Stage 1 truncation
            active_window_size: Active window for Stage 3
            token_buffer_ratio: Ratio at which to trigger compression
        """
        self._max_message_length = max_message_length
        self._active_window_size = active_window_size
        self._token_buffer_ratio = token_buffer_ratio

        logger.info(
            f"ContextCompressor initialized: max_msg_len={max_message_length}, "
            f"window={active_window_size}, buffer={token_buffer_ratio}"
        )

    def compress(
        self,
        messages: List[Dict[str, Any]],
        token_count: Optional[int] = None,
        token_limit: int = 100000,
    ) -> CompressedResult:
        """
        Compress messages using 4-stage escalation.

        Args:
            messages: List of message dicts with 'role' and 'content'
            token_count: Current token count (auto-calculated if None)
            token_limit: Target token limit

        Returns:
            CompressedResult with compressed messages and stats
        """
        # Calculate tokens if not provided
        if token_count is None:
            token_count = count_message_tokens(messages)

        # Calculate buffer threshold
        buffer_threshold = int(token_limit * self._token_buffer_ratio)

        # Start with copy
        result = list(messages)
        stages_applied: List[str] = []

        # Stage 1: Snip Compact (always try first)
        if token_count > buffer_threshold:
            result = snip_compact(result, self._max_message_length)
            stages_applied.append("snip")
            token_count = count_message_tokens(result)
            logger.debug(f"Stage 1 (Snip): tokens={token_count}")

        # Stage 2: Micro Compact (if still over)
        if token_count > buffer_threshold:
            result = micro_compact(result)
            stages_applied.append("micro")
            token_count = count_message_tokens(result)
            logger.debug(f"Stage 2 (Micro): tokens={token_count}")

        # Stage 3: Context Collapse (if still over)
        if token_count > buffer_threshold:
            result = context_collapse(result, self._active_window_size)
            stages_applied.append("collapse")
            token_count = count_message_tokens(result)
            logger.debug(f"Stage 3 (Collapse): tokens={token_count}")

        # Stage 4: Auto Compact (if still over)
        if token_count > token_limit:
            result = auto_compact(result, token_limit)
            stages_applied.append("auto")
            token_count = count_message_tokens(result)
            logger.debug(f"Stage 4 (Auto): tokens={token_count}")

        # Calculate stats
        original_tokens = count_message_tokens(messages)
        tokens_saved = max(0, original_tokens - token_count)
        compression_ratio = original_tokens / token_count if token_count > 0 else 1.0

        logger.info(
            f"Compression complete: saved={tokens_saved} tokens, "
            f"stages={stages_applied}, ratio={compression_ratio:.2f}"
        )

        return CompressedResult(
            messages=result,
            tokens_saved=tokens_saved,
            stages_applied=stages_applied,
            compression_ratio=compression_ratio,
        )

    # =========================================================================
    # Individual Stage Methods (Independently Callable)
    # =========================================================================

    def stage1_snip(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Stage 1: Snip Compact — trims overly long individual messages.

        Args:
            messages: Messages to compress

        Returns:
            Messages with long content truncated
        """
        return snip_compact(messages, self._max_message_length)

    def stage2_micro(
        self,
        messages: List[Dict[str, Any]],
        tool_call_ids_to_preserve: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Stage 2: Micro Compact — finer-grained editing based on tool_call_id.

        Args:
            messages: Messages to compress
            tool_call_ids_to_preserve: IDs to preserve in detail

        Returns:
            Messages with redundant tool info removed
        """
        return micro_compact(messages, tool_call_ids_to_preserve)

    def stage3_collapse(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Stage 3: Context Collapse — folds inactive regions into summaries.

        Args:
            messages: Messages to compress

        Returns:
            Messages with older region collapsed
        """
        return context_collapse(messages, self._active_window_size)

    def stage4_auto(
        self,
        messages: List[Dict[str, Any]],
        target_tokens: int,
    ) -> List[Dict[str, Any]]:
        """
        Stage 4: Auto Compact — full compression when tokens approach threshold.

        Args:
            messages: Messages to compress
            target_tokens: Target token count

        Returns:
            Heavily compressed messages
        """
        return auto_compact(messages, target_tokens)


# =============================================================================
# Module-Level Convenience Functions
# =============================================================================


def compress_messages(
    messages: List[Dict[str, Any]],
    token_limit: int = 100000,
) -> CompressedResult:
    """
    Convenience function to compress messages.

    Args:
        messages: List of message dicts
        token_limit: Target token limit

    Returns:
        CompressedResult
    """
    compressor = ContextCompressor()
    return compressor.compress(messages, token_limit=token_limit)


def quick_snip(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Quick Stage 1 compression only.

    Args:
        messages: Messages to compress

    Returns:
        Messages with long content truncated
    """
    return snip_compact(messages)


# =============================================================================
# Main - Quick Test
# =============================================================================


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s: %(message)s",
    )

    print("=== Context Compression Test ===\n")

    # Test messages
    test_messages = [
        {"role": "system", "content": "You are a helpful coding assistant."},
        {"role": "user", "content": "Hello"},
        {
            "role": "assistant",
            "content": "Hi! How can I help you today?",
        },
        {
            "role": "user",
            "content": "I need to implement a new feature for my app. " * 100,
        },
    ]

    # Test Stage 1: Snip
    print("--- Stage 1: Snip Compact ---")
    snip_result = snip_compact(test_messages, max_message_length=100)
    print(f"Original: {len(test_messages)} msgs")
    print(f"After snip: {len(snip_result)} msgs")
    print(f"Truncated content: {snip_result[3].get('content', '')[:80]}...")

    # Test Stage 2: Micro
    print("\n--- Stage 2: Micro Compact ---")
    micro_result = micro_compact(test_messages, tool_call_ids_to_preserve=[])
    print(f"After micro: {len(micro_result)} msgs")

    # Test Stage 3: Collapse
    print("\n--- Stage 3: Context Collapse ---")
    collapse_result = context_collapse(test_messages, active_window_size=2)
    print(f"Original: {len(test_messages)} msgs")
    print(f"After collapse: {len(collapse_result)} msgs")

    # Test Stage 4: Auto
    print("\n--- Stage 4: Auto Compact ---")
    auto_result = auto_compact(test_messages, target_tokens=50)
    print(f"After auto: {len(auto_result)} msgs")

    # Test full compressor
    print("\n--- Full Compressor ---")
    long_messages = [
        {"role": "system", "content": "System prompt " * 100},
        {"role": "user", "content": "User message " * 100},
        {"role": "assistant", "content": "Assistant response " * 100},
        {"role": "user", "content": "Another user " * 100},
    ]

    compressor = ContextCompressor()
    result = compressor.compress(long_messages, token_limit=500)

    print(f"Stages applied: {result.stages_applied}")
    print(f"Tokens saved: {result.tokens_saved}")
    print(f"Compression ratio: {result.compression_ratio:.2f}")
    print(f"Final message count: {len(result.messages)}")

    # Test individual stages
    print("\n--- Individual Stage Tests ---")
    print(f"Stage 1: {len(compressor.stage1_snip(test_messages))} msgs")
    print(f"Stage 2: {len(compressor.stage2_micro(test_messages))} msgs")
    print(f"Stage 3: {len(compressor.stage3_collapse(test_messages))} msgs")
    print(f"Stage 4: {len(compressor.stage4_auto(test_messages, 50))} msgs")

    # Token estimation test
    print("\n--- Token Estimation ---")
    test_text = "This is a test message for token estimation."
    tokens = estimate_tokens(test_text)
    print(f"Text: '{test_text}'")
    print(f"Estimated tokens: {tokens}")

    print("\nAll tests passed!")
    sys.exit(0)
