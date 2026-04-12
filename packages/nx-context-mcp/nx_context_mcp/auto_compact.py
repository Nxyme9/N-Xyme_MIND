"""Auto-Compact — Automatic conversation summarization when approaching context limit.

Ported from ant-source-code-main/services/compact/autoCompact.ts and compact.ts
Implements:
- Model-aware context window detection (default 200k, supports 1M for advanced models)
- Auto-trigger calculation at context_window - 13,000 token buffer
- Circuit breaker pattern (max 3 consecutive failures)
- Compaction with boundary markers, partial compaction support
- Preservation of file attachments and MCP tools info

Pattern: Monitors conversation tokens and automatically summarizes when
approaching context limit to prevent prompt_too_long errors.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# Constants from TypeScript reference
DEFAULT_CONTEXT_WINDOW = 200_000  # Default 200k tokens
HIGH_CONTEXT_WINDOW = 1_000_000  # 1M for advanced models
AUTOCOMPACT_BUFFER_TOKENS = 13_000
WARNING_THRESHOLD_BUFFER_TOKENS = 20_000
ERROR_THRESHOLD_BUFFER_TOKENS = 20_000
MANUAL_COMPACT_BUFFER_TOKENS = 3_000

# Reserve tokens for output during compaction (based on p99.99 of compact output)
MAX_OUTPUT_TOKENS_FOR_SUMMARY = 20_000

# Circuit breaker: stop after N consecutive failures
MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3


class ModelCapability(Enum):
    """Model capability tiers."""

    STANDARD = "standard"  # 200k context
    EXTENDED = "extended"  # 500k context
    HIGH = "high"  # 1M+ context


# Model context windows (tokens)
MODEL_CONTEXT_WINDOWS: dict[str, int] = {
    # Anthropic models
    "claude-3-opus": 200_000,
    "claude-3-sonnet": 200_000,
    "claude-3-5-sonnet": 200_000,
    "claude-3-5-haiku": 200_000,
    "claude-4-opus": 200_000,
    "claude-4-sonnet": 200_000,
    # Anthropic extended
    "claude-3-5-sonnet-20241022": 500_000,
    "claude-3-5-sonnet-20241022-extended": 500_000,
    "claude-sonnet-4-20250514": 500_000,
    # OpenAI models
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-4-turbo": 128_000,
    "gpt-4": 8192,
    "o1": 200_000,
    "o1-mini": 128_000,
    "o1-preview": 128_000,
    "o3": 200_000,
    "o3-mini": 200_000,
    # OpenCode models
    "opencode/qwen3.6-plus-free": 32_768,
    "opencode/qwen3.6-coder-free": 32_768,
    "opencode/minimax-m2.5-free": 32_768,
    # Ollama models
    "llama-3.2-3b": 131_072,
    "llama-3.2-8b": 131_072,
    "llama-3.3-70b": 128_000,
    "mistral-7b": 32_768,
    "phi-3-mini": 128_000,
    "qwen2.5-7b": 32_768,
    "qwen2.5-14b": 32_768,
    "qwen2.5-72b": 32_768,
}

# Model max output tokens
MODEL_MAX_OUTPUT_TOKENS: dict[str, int] = {
    "claude-3-opus": 4096,
    "claude-3-sonnet": 4096,
    "claude-3-5-sonnet": 4096,
    "claude-3-5-haiku": 4096,
    "claude-4-opus": 4096,
    "claude-4-sonnet": 4096,
    "gpt-4o": 4096,
    "gpt-4o-mini": 4096,
    "o1": 100_000,
    "o1-mini": 65_536,
    "o3": 100_000,
    "opencode/qwen3.6-plus-free": 4096,
    "opencode/qwen3.6-coder-free": 4096,
    "opencode/minimax-m2.5-free": 4096,
}


@dataclass
class AutoCompactTrackingState:
    """Tracks auto-compact state across conversation turns."""

    compacted: bool = False
    turn_counter: int = 0
    turn_id: str = ""  # Unique ID per turn
    consecutive_failures: int = 0  # Circuit breaker counter


@dataclass
class TokenWarningState:
    """Token usage warning state."""

    percent_left: float
    is_above_warning_threshold: bool
    is_above_error_threshold: bool
    is_above_auto_compact_threshold: bool
    is_at_blocking_limit: bool


@dataclass
class CompactionResult:
    """Result of context compaction."""

    boundary_marker: dict[str, Any]
    summary_messages: list[dict[str, Any]]
    attachments: list[dict[str, Any]] = field(default_factory=list)
    hook_results: list[dict[str, Any]] = field(default_factory=list)
    messages_to_keep: list[dict[str, Any]] | None = None
    user_display_message: str | None = None
    pre_compact_token_count: int = 0
    post_compact_token_count: int = 0
    true_post_compact_token_count: int = 0
    compaction_usage: dict[str, int] | None = None


@dataclass
class RecompactionInfo:
    """Info about recompaction chain."""

    is_recompaction_in_chain: bool
    turns_since_previous_compact: int
    previous_compact_turn_id: str | None = None
    auto_compact_threshold: int = 0
    query_source: str | None = None


# ============================================================================
# Context Window Detection
# ============================================================================


def get_context_window_for_model(model: str | None) -> int:
    """Get context window size for a model.

    Args:
        model: Model name (None for default)

    Returns:
        Context window size in tokens
    """
    if model is None:
        return DEFAULT_CONTEXT_WINDOW
    # Check exact match
    if model in MODEL_CONTEXT_WINDOWS:
        return MODEL_CONTEXT_WINDOWS[model]

    # Check prefix match for variants
    for known_model, window in MODEL_CONTEXT_WINDOWS.items():
        if model.startswith(known_model) or known_model.startswith(model):
            return window

    # Check environment override
    env_override = os.environ.get("NX_CONTEXT_WINDOW_OVERRIDE")
    if env_override:
        try:
            return int(env_override)
        except ValueError:
            pass

    # Default fallback
    return DEFAULT_CONTEXT_WINDOW


def get_model_capability(model: str) -> ModelCapability:
    """Get model capability tier.

    Args:
        model: Model name

    Returns:
        ModelCapability tier
    """
    window = get_context_window_for_model(model)
    if window >= HIGH_CONTEXT_WINDOW:
        return ModelCapability.HIGH
    elif window >= 500_000:
        return ModelCapability.EXTENDED
    else:
        return ModelCapability.STANDARD


def get_max_output_tokens_for_model(model: str) -> int:
    """Get max output tokens for model.

    Args:
        model: Model name

    Returns:
        Max output tokens
    """
    if model in MODEL_MAX_OUTPUT_TOKENS:
        return MODEL_MAX_OUTPUT_TOKENS[model]

    # Check prefix match
    for known_model, max_tokens in MODEL_MAX_OUTPUT_TOKENS.items():
        if model.startswith(known_model):
            return max_tokens

    # Default
    return 4096


def get_effective_context_window_size(model: str) -> int:
    """Get effective context window (minus reserved output tokens).

    Args:
        model: Model name

    Returns:
        Effective context window for auto-compact trigger
    """
    reserved = min(
        get_max_output_tokens_for_model(model),
        MAX_OUTPUT_TOKENS_FOR_SUMMARY,
    )
    context_window = get_context_window_for_model(model)

    # Allow override via env
    auto_compact_window = os.environ.get("NX_AUTO_COMPACT_WINDOW")
    if auto_compact_window:
        try:
            parsed = int(auto_compact_window)
            if parsed > 0:
                context_window = min(context_window, parsed)
        except ValueError:
            pass

    return context_window - reserved


# ============================================================================
# Auto-Compact Trigger Calculation
# ============================================================================


def get_auto_compact_threshold(model: str) -> int:
    """Get the token count at which auto-compact triggers.

    Args:
        model: Model name

    Returns:
        Token threshold for auto-compact trigger
    """
    effective_window = get_effective_context_window_size(model)
    threshold = effective_window - AUTOCOMPACT_BUFFER_TOKENS

    # Allow testing override
    env_pct = os.environ.get("NX_AUTOCOMPACT_PCT_OVERRIDE")
    if env_pct:
        try:
            parsed = float(env_pct)
            if 0 < parsed <= 100:
                pct_threshold = int(effective_window * (parsed / 100))
                return min(pct_threshold, threshold)
        except ValueError:
            pass

    return threshold


def calculate_token_warning_state(
    token_usage: int,
    model: str,
    auto_compact_enabled: bool = True,
) -> TokenWarningState:
    """Calculate token warning state for a model.

    Args:
        token_usage: Current token count
        model: Model name
        auto_compact_enabled: Whether auto-compact is enabled

    Returns:
        TokenWarningState with thresholds
    """
    auto_compact_threshold = get_auto_compact_threshold(model)
    effective_window = get_effective_context_window_size(model)

    if auto_compact_enabled:
        threshold = auto_compact_threshold
    else:
        threshold = effective_window

    percent_left = max(0, round(((threshold - token_usage) / threshold) * 100))

    warning_threshold = threshold - WARNING_THRESHOLD_BUFFER_TOKENS
    error_threshold = threshold - ERROR_THRESHOLD_BUFFER_TOKENS

    is_above_warning = token_usage >= warning_threshold
    is_above_error = token_usage >= error_threshold
    is_above_auto_compact = (
        auto_compact_enabled and token_usage >= auto_compact_threshold
    )

    # Calculate blocking limit
    default_blocking_limit = effective_window - MANUAL_COMPACT_BUFFER_TOKENS
    blocking_override = os.environ.get("NX_BLOCKING_LIMIT_OVERRIDE")
    try:
        blocking_limit = (
            int(blocking_override) if blocking_override else default_blocking_limit
        )
    except ValueError:
        blocking_limit = default_blocking_limit

    is_at_blocking = token_usage >= blocking_limit

    return TokenWarningState(
        percent_left=percent_left,
        is_above_warning_threshold=is_above_warning,
        is_above_error_threshold=is_above_error,
        is_above_auto_compact_threshold=is_above_auto_compact,
        is_at_blocking_limit=is_at_blocking,
    )


def should_auto_compact(
    messages: list[dict[str, Any]],
    model: str,
    snip_tokens_freed: int = 0,
) -> bool:
    """Check if auto-compact should trigger.

    Args:
        messages: Conversation messages
        model: Model name
        snip_tokens_freed: Tokens freed by snip operation

    Returns:
        True if auto-compact should run
    """
    # Check if auto-compact is disabled
    if os.environ.get("DISABLE_COMPACT", "").lower() in ("1", "true", "yes"):
        return False
    if os.environ.get("DISABLE_AUTO_COMPACT", "").lower() in ("1", "true", "yes"):
        return False

    # Count tokens
    token_count = estimate_conversation_tokens(messages) - snip_tokens_freed

    # Check against threshold
    warning_state = calculate_token_warning_state(token_count, model)
    return warning_state.is_above_auto_compact_threshold


def estimate_conversation_tokens(messages: list[dict[str, Any]]) -> int:
    """Estimate total tokens in conversation.

    Uses character-based estimation with code/prose detection.

    Args:
        messages: List of message dicts with 'role' and 'content'

    Returns:
        Estimated token count
    """
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if not content:
            continue

        # Detect code vs prose
        is_code = _is_code_content(content)
        chars_per_token = 3.5 if is_code else 4.5

        # Estimate tokens
        tokens = max(1, int(len(content) / chars_per_token))
        total += tokens

    return total


def _is_code_content(content: str) -> bool:
    """Detect if content is code."""
    code_indicators = [
        "def ",
        "class ",
        "import ",
        "from ",
        "function ",
        "const ",
        "let ",
        "var ",
        "if ",
        "else ",
        "for ",
        "while ",
        "return ",
        "async ",
        "await ",
        "=>",
        "->",
        "pub fn",
        "fn ",
        "impl ",
    ]
    return sum(1 for ind in code_indicators if ind in content) > 3


# ============================================================================
# Circuit Breaker
# ============================================================================


class CircuitBreaker:
    """Circuit breaker for auto-compact failures.

    Prevents API hammering after consecutive failures.
    """

    def __init__(self, max_failures: int = MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES):
        """Initialize circuit breaker.

        Args:
            max_failures: Max consecutive failures before stopping
        """
        self.max_failures = max_failures
        self.failures = 0

    def record_success(self) -> None:
        """Record successful compaction - reset failure count."""
        self.failures = 0

    def record_failure(self) -> None:
        """Record failed compaction attempt."""
        self.failures += 1
        if self.failures >= self.max_failures:
            logger.warning(
                f"Circuit breaker tripped after {self.failures} consecutive failures"
            )

    def should_allow_attempt(self) -> bool:
        """Check if another compaction attempt is allowed.

        Returns:
            True if circuit allows attempt
        """
        return self.failures < self.max_failures

    def get_state(self) -> dict[str, Any]:
        """Get circuit breaker state.

        Returns:
            Dict with state info
        """
        return {
            "failures": self.failures,
            "max_failures": self.max_failures,
            "is_tripped": self.failures >= self.max_failures,
        }


# ============================================================================
# Compaction Implementation
# ============================================================================


def create_compact_boundary_marker(
    trigger: str,  # 'auto' or 'manual'
    pre_compact_token_count: int,
    last_message_uuid: str | None = None,
    user_feedback: str | None = None,
    messages_summarized: int | None = None,
) -> dict[str, Any]:
    """Create a compact boundary marker message.

    Args:
        trigger: What triggered compaction ('auto' or 'manual')
        pre_compact_token_count: Token count before compaction
        last_message_uuid: UUID of last message before boundary
        user_feedback: User feedback for partial compact
        messages_summarized: Number of messages summarized

    Returns:
        Boundary marker dict
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    return {
        "type": "system",
        "role": "system",
        "content": f"[Earlier conversation compact: {pre_compact_token_count} tokens summarized]",
        "timestamp": timestamp,
        "is_compact_boundary": True,
        "compact_metadata": {
            "trigger": trigger,
            "pre_compact_token_count": pre_compact_token_count,
            "last_message_uuid": last_message_uuid,
            "user_feedback": user_feedback,
            "messages_summarized": messages_summarized,
            "version": "1.0",
        },
    }


def create_summary_message(
    summary: str,
    is_visible_in_transcript_only: bool = False,
) -> dict[str, Any]:
    """Create a user message with conversation summary.

    Args:
        summary: Summarized conversation content
        is_visible_in_transcript_only: Whether to show in transcript

    Returns:
        Summary message dict
    """
    return {
        "type": "user",
        "role": "user",
        "content": f"[Summary of earlier conversation]\n\n{summary}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "is_compact_summary": True,
        "is_visible_in_transcript_only": is_visible_in_transcript_only,
    }


def strip_images_from_messages(
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Strip image blocks from user messages before compaction.

    Images are not needed for summary generation and can cause
    the compaction API call itself to hit prompt-too-long.

    Args:
        messages: Original messages

    Returns:
        Messages with images replaced by markers
    """
    result = []
    for msg in messages:
        if msg.get("role") != "user":
            result.append(msg)
            continue

        content = msg.get("content")
        if isinstance(content, list):
            # Handle content blocks
            new_content = []
            for block in content:
                if isinstance(block, dict):
                    block_type = block.get("type")
                    if block_type == "image":
                        new_content.append({"type": "text", "text": "[image]"})
                    elif block_type == "document":
                        new_content.append({"type": "text", "text": "[document]"})
                    else:
                        new_content.append(block)
                else:
                    new_content.append(block)
            result.append({**msg, "content": new_content})
        else:
            result.append(msg)

    return result


def build_post_compact_messages(result: CompactionResult) -> list[dict[str, Any]]:
    """Build the final message list after compaction.

    Order: boundary_marker, summary_messages, messages_to_keep,
           attachments, hook_results

    Args:
        result: CompactionResult

    Returns:
        List of messages in correct order
    """
    messages = [
        result.boundary_marker,
        *result.summary_messages,
    ]

    if result.messages_to_keep:
        messages.extend(result.messages_to_keep)

    messages.extend(result.attachments)
    messages.extend(result.hook_results)

    return messages


# ============================================================================
# Partial Compaction Support
# ============================================================================


class PartialCompactDirection(Enum):
    """Direction for partial compaction."""

    PREFIX_PRESERVING = "from"  # Summarize tail, keep head
    SUFFIX_PRESERVING = "up_to"  # Summarize head, keep tail


def partial_compact_messages(
    all_messages: list[dict[str, Any]],
    pivot_index: int,
    direction: PartialCompactDirection = PartialCompactDirection.PREFIX_PRESERVING,
    custom_summary: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Perform partial compaction around a pivot point.

    Args:
        all_messages: All conversation messages
        pivot_index: Index to pivot around
        direction: Which side to summarize
        custom_summary: Optional pre-generated summary

    Returns:
        Tuple of (summarized_messages, kept_messages, boundary_marker)
    """
    if direction == PartialCompactDirection.SUFFIX_PRESERVING:
        # 'up_to': summarize messages before pivot, keep after
        to_summarize = all_messages[:pivot_index]
        to_keep = all_messages[pivot_index:]

        # Filter out progress, boundaries, old summaries from kept
        to_keep = [
            m
            for m in to_keep
            if m.get("type") != "progress"
            and not m.get("is_compact_boundary")
            and not (m.get("role") == "user" and m.get("is_compact_summary"))
        ]
    else:
        # 'from': summarize messages after pivot, keep before
        to_summarize = all_messages[pivot_index:]
        to_keep = all_messages[:pivot_index]
        to_keep = [m for m in to_keep if m.get("type") != "progress"]

    if not to_summarize:
        raise ValueError("Nothing to summarize in the specified direction")

    # Estimate tokens for summary
    pre_compact_tokens = estimate_conversation_tokens(to_summarize)

    # Create boundary with direction info
    last_keep_uuid = to_keep[-1].get("uuid") if to_keep else None
    boundary = create_compact_boundary_marker(
        trigger="manual",
        pre_compact_token_count=pre_compact_tokens,
        last_message_uuid=last_keep_uuid,
        messages_summarized=len(to_summarize),
    )

    # For prefix-preserving, anchor to boundary
    # For suffix-preserving, anchor to last summary message
    if direction == PartialCompactDirection.PREFIX_PRESERVING:
        # Preserve head - anchor to boundary
        boundary["compact_metadata"]["preserved_segment"] = {
            "anchor_uuid": boundary.get("uuid", ""),
            "tail_uuid": to_keep[-1].get("uuid") if to_keep else "",
        }
    else:
        # Preserve tail - will be set after summary creation
        pass

    return to_summarize, to_keep, boundary


# ============================================================================
# MCP Tools Info Preservation
# ============================================================================


def extract_mcp_tools_info(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract MCP tools info from messages for post-compact restoration.

    Args:
        messages: Conversation messages

    Returns:
        List of MCP tool info dicts
    """
    mcp_tools = []

    for msg in messages:
        # Look for MCP tool announcements in attachments or content
        content = msg.get("content", "")
        if isinstance(content, str):
            # Check for MCP tool patterns
            if "MCP" in content or "mcp_tools" in str(msg):
                mcp_tools.append(
                    {
                        "source": msg.get("role"),
                        "content_preview": content[:200]
                        if len(content) > 200
                        else content,
                    }
                )

    return mcp_tools


def preserve_file_attachments(
    messages: list[dict[str, Any]],
    max_files: int = 5,
) -> list[dict[str, Any]]:
    """Extract file attachment info for post-compact restoration.

    Args:
        messages: Messages to extract attachments from
        max_files: Maximum files to preserve

    Returns:
        List of file attachment info
    """
    attachments = []
    file_paths = set()

    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            # Look for file path patterns
            if "File:" in content or "Read:" in content or "path:" in content:
                # Simple extraction - in production would use proper parsing
                lines = content.split("\n")
                for line in lines:
                    if line.strip().startswith("File:") or line.strip().startswith(
                        "Read:"
                    ):
                        path = line.split(":", 1)[1].strip()
                        if (
                            path
                            and path not in file_paths
                            and len(attachments) < max_files
                        ):
                            file_paths.add(path)
                            attachments.append(
                                {
                                    "type": "file",
                                    "path": path,
                                }
                            )

    return attachments


# ============================================================================
# Auto-Compact Execution
# ============================================================================


class AutoCompactor:
    """Auto-compact orchestrator with circuit breaker."""

    def __init__(self, model: str = "claude-3-5-sonnet"):
        """Initialize auto-compactor.

        Args:
            model: Default model to use
        """
        self.model = model
        self.circuit_breaker = CircuitBreaker()
        self.tracking = AutoCompactTrackingState()

    def reset_turn(self) -> None:
        """Reset for new turn."""
        self.tracking.turn_counter += 1
        self.tracking.turn_id = (
            f"turn_{self.tracking.turn_counter}_{datetime.now().timestamp()}"
        )

    def should_compact(
        self,
        messages: list[dict[str, Any]],
        snip_tokens_freed: int = 0,
    ) -> bool:
        """Check if compaction should run.

        Args:
            messages: Conversation messages
            snip_tokens_freed: Tokens freed by snip

        Returns:
            True if should compact
        """
        if not self.circuit_breaker.should_allow_attempt():
            logger.info("Circuit breaker - skipping compaction attempt")
            return False

        return should_auto_compact(messages, self.model, snip_tokens_freed)

    async def compact(
        self,
        messages: list[dict[str, Any]],
        summary_provider: callable = None,  # Async callable to generate summary
    ) -> tuple[bool, CompactionResult | None]:
        """Execute compaction.

        Args:
            messages: Messages to compact
            summary_provider: Async callable that takes messages and returns summary

        Returns:
            Tuple of (was_compacted, result)
        """
        if not self.circuit_breaker.should_allow_attempt():
            return False, None

        pre_compact_tokens = estimate_conversation_tokens(messages)

        try:
            # Generate summary (call external provider)
            if summary_provider:
                # Strip images for compaction API
                clean_messages = strip_images_from_messages(messages)
                summary = await summary_provider(clean_messages)
            else:
                # Placeholder - in production would call LLM
                summary = f"[Summary of {pre_compact_tokens} tokens of conversation]"

            # Create boundary marker
            boundary = create_compact_boundary_marker(
                trigger="auto",
                pre_compact_token_count=pre_compact_tokens,
                last_message_uuid=messages[-1].get("uuid") if messages else None,
            )

            # Create summary message
            summary_msg = create_summary_message(summary)

            # Extract attachments to preserve
            attachments = preserve_file_attachments(messages)
            mcp_tools = extract_mcp_tools_info(messages)

            # Add MCP tools info to attachments
            if mcp_tools:
                attachments.append(
                    {
                        "type": "mcp_tools",
                        "tools": mcp_tools,
                    }
                )

            result = CompactionResult(
                boundary_marker=boundary,
                summary_messages=[summary_msg],
                attachments=attachments,
                pre_compact_token_count=pre_compact_tokens,
                post_compact_token_count=estimate_conversation_tokens(
                    [boundary, summary_msg]
                ),
                true_post_compact_token_count=estimate_conversation_tokens(
                    [boundary, summary_msg] + attachments
                ),
            )

            # Update tracking
            self.tracking.compacted = True
            self.circuit_breaker.record_success()

            return True, result

        except Exception as e:
            logger.error(f"Compaction failed: {e}")
            self.circuit_breaker.record_failure()
            self.tracking.consecutive_failures = self.circuit_breaker.failures

            return False, None

    def get_status(self) -> dict[str, Any]:
        """Get current auto-compact status.

        Returns:
            Status dict
        """
        return {
            "model": self.model,
            "context_window": get_context_window_for_model(self.model),
            "effective_context_window": get_effective_context_window_size(self.model),
            "auto_compact_threshold": get_auto_compact_threshold(self.model),
            "tracking": {
                "compacted": self.tracking.compacted,
                "turn_counter": self.tracking.turn_counter,
                "consecutive_failures": self.tracking.consecutive_failures,
            },
            "circuit_breaker": self.circuit_breaker.get_state(),
        }


# ============================================================================
# Module-level便利関数
# ============================================================================


def is_auto_compact_enabled() -> bool:
    """Check if auto-compact is enabled.

    Returns:
        True if enabled
    """
    if os.environ.get("DISABLE_COMPACT", "").lower() in ("1", "true", "yes"):
        return False
    if os.environ.get("DISABLE_AUTO_COMPACT", "").lower() in ("1", "true", "yes"):
        return False
    return True


def get_default_model() -> str:
    """Get default model for context window calculations.

    Returns:
        Default model name
    """
    return os.environ.get("NX_DEFAULT_MODEL", "claude-3-5-sonnet")
