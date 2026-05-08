"""Token Counting — Accurate token counting based on Anthropic source patterns.

Implements tokenCountWithEstimation using API response + estimation for new messages.
Based on leaked Anthropic source code patterns from ant-source-code-main/utils/tokens.ts

Key features:
1. Uses last API response tokens (most accurate)
2. Estimates for new messages not yet in response
3. Handles parallel tool calls by walking back to first sibling
4. Includes cache_creation + cache_read in total
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

logger = logging.getLogger(__name__)

# Token estimation constants (from tokenEstimation.ts patterns)
CHARS_PER_TOKEN = 4.0  # Average characters per token
TOKENS_PER_MESSAGE_OVERHEAD = 4  # Average overhead per message

# Synthetic message markers (used in testing)
SYNTHETIC_MESSAGES: set[str] = set()
SYNTHETIC_MODEL = "synthetic-model"


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class Usage:
    """API response usage data."""

    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    # For server-side tool loops
    iterations: list[dict[str, int]] | None = None


@dataclass
class TokenBreakdown:
    """Detailed token breakdown for debugging."""

    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    estimated_new_tokens: int
    total: int


@dataclass
class Message:
    """Message structure matching the TypeScript types."""

    type: str  # 'user', 'assistant', 'system', 'tool'
    message: dict[str, Any] = field(default_factory=dict)
    # For assistant messages, message.id is the API response ID
    id: str | None = None


# ============================================================================
# Protocols
# ============================================================================


class TokenEstimator(Protocol):
    """Protocol for token estimation."""

    def estimate(self, text: str) -> int:
        """Estimate tokens for text."""
        ...


class RoughEstimator:
    """Default rough token estimator based on character count."""

    def estimate(self, text: str) -> int:
        """Estimate tokens using character count."""
        if not text:
            return 0
        return max(1, len(text) // CHARS_PER_TOKEN + TOKENS_PER_MESSAGE_OVERHEAD)


# ============================================================================
# API Response Parser
# ============================================================================


class APIResponseParser:
    """Parses API responses to extract usage data."""

    @staticmethod
    def get_usage(message: Message) -> Usage | None:
        """Extract usage from an assistant message.

        Args:
            message: Message to extract usage from

        Returns:
            Usage object if valid, None otherwise
        """
        if message.type != "assistant":
            return None

        msg_data = message.message

        # Check for synthetic messages (skip them)
        content = msg_data.get("content", [])
        if content and isinstance(content[0], dict):
            first_content = content[0]
            if first_content.get("type") == "text":
                text = first_content.get("text", "")
                if text in SYNTHETIC_MESSAGES:
                    return None

        # Check model
        model = msg_data.get("model", "")
        if model == SYNTHETIC_MODEL:
            return None

        # Extract usage
        usage = msg_data.get("usage")
        if not usage:
            return None

        if isinstance(usage, dict):
            return Usage(
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                cache_creation_input_tokens=usage.get("cache_creation_input_tokens", 0),
                cache_read_input_tokens=usage.get("cache_read_input_tokens", 0),
            )

        return None

    @staticmethod
    def get_response_id(message: Message) -> str | None:
        """Get the API response ID for an assistant message.

        Used to identify split assistant records that came from the same API response —
        when parallel tool calls are streamed, each content block becomes a separate
        record, but they all share the same message.id.

        Args:
            message: Message to get ID from

        Returns:
            API response ID if valid, None otherwise
        """
        if message.type != "assistant":
            return None

        msg_data = message.message

        # Check model
        model = msg_data.get("model", "")
        if model == SYNTHETIC_MODEL:
            return None

        # Get the message ID
        return msg_data.get("id")

    @staticmethod
    def get_token_count_from_usage(usage: Usage) -> int:
        """Calculate total context window tokens from usage data.

        Includes input_tokens + cache tokens + output_tokens.

        Args:
            usage: Usage object

        Returns:
            Total token count
        """
        return (
            usage.input_tokens
            + usage.cache_creation_input_tokens
            + usage.cache_read_input_tokens
            + usage.output_tokens
        )

    @staticmethod
    def get_final_context_tokens(usage: Usage) -> int:
        """Get final context window size from usage.iterations[-1].

        Used for task_budget.remaining computation across compaction boundaries.
        Falls back to top-level input + output when iterations is absent.

        Args:
            usage: Usage object

        Returns:
            Final context tokens (input + output, no cache)
        """
        if usage.iterations and len(usage.iterations) > 0:
            last = usage.iterations[-1]
            return last.get("input_tokens", 0) + last.get("output_tokens", 0)

        # No iterations → top-level usage IS the final window
        return usage.input_tokens + usage.output_tokens

    @staticmethod
    def parse_message_content_length(message: Message) -> int:
        """Calculate character content length of an assistant message.

        Used for spinner token estimation (characters / 4 ≈ tokens).
        Counts: text, thinking, redacted_thinking, tool_use input.

        Args:
            message: Assistant message

        Returns:
            Character content length
        """
        if message.type != "assistant":
            return 0

        content_length = 0
        content = message.message.get("content", [])

        for block in content:
            if not isinstance(block, dict):
                continue

            block_type = block.get("type")
            if block_type == "text":
                content_length += len(block.get("text", ""))
            elif block_type == "thinking":
                content_length += len(block.get("thinking", ""))
            elif block_type == "redacted_thinking":
                content_length += len(block.get("data", ""))
            elif block_type == "tool_use":
                import json

                content_length += len(json.dumps(block.get("input", {})))

        return content_length


# ============================================================================
# Message Walker
# ============================================================================


class MessageWalker:
    """Utilities for traversing messages backward and finding parallel siblings."""

    @staticmethod
    def traverse_messages_backward(
        messages: list[Message],
        start_index: int | None = None,
    ) -> list[tuple[int, Message]]:
        """Traverse messages backward from start index.

        Args:
            messages: List of messages
            start_index: Starting index (default: last message)

        Returns:
            List of (index, message) tuples in reverse order
        """
        if start_index is None:
            start_index = len(messages) - 1

        result = []
        for i in range(start_index, -1, -1):
            result.append((i, messages[i]))

        return result

    @staticmethod
    def find_parallel_tool_siblings(
        messages: list[Message],
        target_index: int,
    ) -> list[int]:
        """Find all parallel tool siblings for a message.

        Walks back to find all assistant messages with the same API response ID.
        This handles the case when parallel tool calls are streamed as separate
        records, all sharing the same message.id.

        Args:
            messages: List of messages
            target_index: Index of the message to find siblings for

        Returns:
            List of indices including the target and all its siblings
        """
        if target_index < 0 or target_index >= len(messages):
            return [target_index]

        target_message = messages[target_index]
        response_id = APIResponseParser.get_response_id(target_message)

        if not response_id:
            return [target_index]

        # Walk back to find all siblings with same response ID
        siblings = [target_index]

        for i in range(target_index - 1, -1, -1):
            msg = messages[i]
            msg_response_id = APIResponseParser.get_response_id(msg)

            if msg_response_id == response_id:
                # Same API response - add as sibling
                siblings.append(i)
            elif msg_response_id is not None:
                # Different API response - stop walking
                break
            # msg_response_id is None (user/tool_result/attachment) - keep walking

        return siblings

    @staticmethod
    def find_first_sibling_index(
        messages: list[Message],
        target_index: int,
    ) -> int:
        """Find the index of the first sibling in the parallel group.

        Walks back to the first message with the same API response ID.

        Args:
            messages: List of messages
            target_index: Index to start from

        Returns:
            Index of the first sibling (may be the same as target_index)
        """
        if target_index < 0 or target_index >= len(messages):
            return target_index

        target_message = messages[target_index]
        response_id = APIResponseParser.get_response_id(target_message)

        if not response_id:
            return target_index

        # Walk back to find first sibling
        first_index = target_index
        for i in range(target_index - 1, -1, -1):
            msg = messages[i]
            msg_response_id = APIResponseParser.get_response_id(msg)

            if msg_response_id == response_id:
                first_index = i
            elif msg_response_id is not None:
                break

        return first_index


# ============================================================================
# Token Counter (Main Class)
# ============================================================================


class TokenCounter:
    """Accurate token counting using API response + estimation.

    This is the canonical function for measuring context size when checking
    thresholds (autocompact, session memory init, etc.).
    """

    def __init__(self, estimator: TokenEstimator | None = None):
        """Initialize token counter.

        Args:
            estimator: Optional custom token estimator
        """
        self._estimator = estimator or RoughEstimator()

    def token_count_with_estimation(
        self,
        messages: list[Message],
    ) -> int:
        """Get current context window size in tokens.

        Uses the last API response's token count (input + output + cache)
        plus estimates for any messages added since.

        Implementation note on parallel tool calls: when the model makes multiple
        tool calls in one response, the streaming code emits a SEPARATE assistant
        record per content block (all sharing the same message.id and usage), and
        the query loop interleaves each tool_result immediately after its tool_use.
        So the messages array looks like:
          [..., assistant(id=A), user(result), assistant(id=A), user(result), ...]
        If we stop at the LAST assistant record, we only estimate the one tool_result
        after it and miss all the earlier interleaved tool_results — which will ALL
        be in the next API request. To avoid undercounting, after finding a usage-
        bearing record we walk back to the FIRST sibling with the same message.id
        so every interleaved tool_result is included in the rough estimate.

        Args:
            messages: List of messages

        Returns:
            Total token count (API response + estimation for new messages)
        """
        # Walk backward to find first message with usage
        i = len(messages) - 1
        while i >= 0:
            message = messages[i]
            usage = APIResponseParser.get_usage(message)

            if message and usage:
                # Walk back past any earlier sibling records split from the same
                # API response (same message.id) so interleaved tool_results between
                # them are included in the estimation slice.
                response_id = APIResponseParser.get_response_id(message)
                if response_id:
                    first_sibling_idx = MessageWalker.find_first_sibling_index(
                        messages, i
                    )
                    # Adjust index to first sibling
                    i = first_sibling_idx

                # Calculate: API response tokens + estimation for messages after
                api_tokens = APIResponseParser.get_token_count_from_usage(usage)
                new_messages = messages[i + 1 :]
                estimated_new = self._estimate_messages(new_messages)

                return api_tokens + estimated_new

            i -= 1

        # No usage found - estimate all messages
        return self._estimate_messages(messages)

    def _estimate_messages(self, messages: list[Message]) -> int:
        """Estimate tokens for a list of messages.

        Uses rough estimation based on message content.

        Args:
            messages: List of messages to estimate

        Returns:
            Estimated token count
        """
        total = 0

        for msg in messages:
            if msg.type == "assistant":
                # Use content length estimation
                content_len = APIResponseParser.parse_message_content_length(msg)
                total += max(1, content_len // CHARS_PER_TOKEN)
            elif msg.type == "user":
                # Estimate from message content
                content = msg.message.get("content", "")
                if isinstance(content, list):
                    # Handle content as list of blocks
                    for block in content:
                        if isinstance(block, dict):
                            text = block.get("text", "") or block.get("content", "")
                            total += self._estimator.estimate(text)
                elif isinstance(content, str):
                    total += self._estimator.estimate(content)
            elif msg.type == "tool":
                # Tool results have content
                content = msg.message.get("content", "")
                total += self._estimator.estimate(content)

            # Add message overhead
            total += TOKENS_PER_MESSAGE_OVERHEAD

        return total

    def token_count_from_last_response(self, messages: list[Message]) -> int:
        """Get token count from the last API response only.

        Does NOT estimate new messages - use token_count_with_estimation() instead.

        Args:
            messages: List of messages

        Returns:
            Token count from last API response, or 0 if none found
        """
        for i in range(len(messages) - 1, -1, -1):
            message = messages[i]
            usage = APIResponseParser.get_usage(message)
            if usage:
                return APIResponseParser.get_token_count_from_usage(usage)

        return 0

    def final_context_tokens_from_last_response(
        self,
        messages: list[Message],
    ) -> int:
        """Get final context window tokens from last response's iterations.

        Used for task_budget.remaining computation across compaction boundaries.

        Args:
            messages: List of messages

        Returns:
            Final context tokens, or 0 if none found
        """
        for i in range(len(messages) - 1, -1, -1):
            message = messages[i]
            usage = APIResponseParser.get_usage(message)
            if usage:
                return APIResponseParser.get_final_context_tokens(usage)

        return 0

    def get_current_usage(
        self,
        messages: list[Message],
    ) -> dict[str, int] | None:
        """Get current usage breakdown from last API response.

        Args:
            messages: List of messages

        Returns:
            Dict with input_tokens, output_tokens, cache_creation, cache_read
            or None if no usage found
        """
        for i in range(len(messages) - 1, -1, -1):
            message = messages[i]
            usage = APIResponseParser.get_usage(message)
            if usage:
                return {
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "cache_creation_input_tokens": usage.cache_creation_input_tokens,
                    "cache_read_input_tokens": usage.cache_read_input_tokens,
                }

        return None

    def get_token_breakdown(
        self,
        messages: list[Message],
    ) -> TokenBreakdown | None:
        """Get detailed token breakdown for debugging.

        Args:
            messages: List of messages

        Returns:
            TokenBreakdown with detailed breakdown, or None if no usage
        """
        # Find first sibling index to include all parallel tool results
        i = len(messages) - 1
        first_sibling_idx = i

        while i >= 0:
            message = messages[i]
            usage = APIResponseParser.get_usage(message)

            if message and usage:
                response_id = APIResponseParser.get_response_id(message)
                if response_id:
                    first_sibling_idx = MessageWalker.find_first_sibling_index(
                        messages, i
                    )
                break

            i -= 1

        # Get API tokens
        api_tokens = self.token_count_from_last_response(messages)
        usage_data = self.get_current_usage(messages)

        if not usage_data:
            # No API usage - estimate all
            estimated = self._estimate_messages(messages)
            return TokenBreakdown(
                input_tokens=0,
                output_tokens=0,
                cache_creation_tokens=0,
                cache_read_tokens=0,
                estimated_new_tokens=estimated,
                total=estimated,
            )

        # Estimate new messages after first sibling
        new_messages = (
            messages[first_sibling_idx + 1 :]
            if first_sibling_idx < len(messages) - 1
            else []
        )
        estimated_new = self._estimate_messages(new_messages)

        return TokenBreakdown(
            input_tokens=usage_data["input_tokens"],
            output_tokens=usage_data["output_tokens"],
            cache_creation_tokens=usage_data["cache_creation_input_tokens"],
            cache_read_tokens=usage_data["cache_read_input_tokens"],
            estimated_new_tokens=estimated_new,
            total=api_tokens + estimated_new,
        )


# ============================================================================
# Convenience Functions
# ============================================================================


# Global singleton
_token_counter = TokenCounter()


def token_count_with_estimation(messages: list[Message]) -> int:
    """Convenience function for token counting with estimation.

    Args:
        messages: List of messages

    Returns:
        Total token count
    """
    return _token_counter.token_count_with_estimation(messages)


def token_count_from_last_response(messages: list[Message]) -> int:
    """Convenience function for getting token count from last API response.

    Args:
        messages: List of messages

    Returns:
        Token count from last response
    """
    return _token_counter.token_count_from_last_response(messages)


def final_context_tokens_from_last_response(messages: list[Message]) -> int:
    """Convenience function for getting final context tokens.

    Args:
        messages: List of messages

    Returns:
        Final context tokens
    """
    return _token_counter.final_context_tokens_from_last_response(messages)


def get_current_usage(messages: list[Message]) -> dict[str, int] | None:
    """Convenience function for getting current usage breakdown.

    Args:
        messages: List of messages

    Returns:
        Usage dict or None
    """
    return _token_counter.get_current_usage(messages)


def get_token_breakdown(messages: list[Message]) -> TokenBreakdown | None:
    """Convenience function for getting detailed token breakdown.

    Args:
        messages: List of messages

    Returns:
        TokenBreakdown or None
    """
    return _token_counter.get_token_breakdown(messages)


# Export all classes and functions
__all__ = [
    "APIResponseParser",
    "MessageWalker",
    "TokenCounter",
    "TokenBreakdown",
    "Usage",
    "Message",
    "token_count_with_estimation",
    "token_count_from_last_response",
    "final_context_tokens_from_last_response",
    "get_current_usage",
    "get_token_breakdown",
]
