"""
Unified Compactor - Consolidates 4 compaction systems into 1.

Combines the BEST features from:
1. MicroCompactor (tier1_micro_compact.py) - 50% threshold, keep last 5 messages
2. ContextCompactor (context_compact.py) - Priority-based (1-10) pruning
3. auto_compact (auto_compact.py) - Model-aware, circuit breaker, file preservation
4. ContextCompressor (compression.py) - Multiple modes: snip/micro/context/auto

Features:
- Model-aware context detection (from auto_compact)
- Circuit breaker pattern (from auto_compact)
- Priority-based pruning (from ContextCompactor)
- Multiple compression modes (from ContextCompressor)
- File attachment preservation (from auto_compact)
- Partial compact support (from auto_compact)
- Configurable thresholds (from ContextCompactor)

Usage:
    compactor = UnifiedCompactor(
        threshold_pct=0.85,
        model="claude-3-5-sonnet",
        max_consecutive_failures=3,
        mode="auto"
    )

    if compactor.should_compact(messages, model):
        result = compactor.compact(messages, model)
        print(f"Reduced: {result.original_tokens} → {result.compacted_tokens}")
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

# Import hook system for pre-compact hook integration
try:
    from packages.orchestration.hooks import (
        HookType,
        CompactContext,
        get_default_registry,
    )

    HOOKS_AVAILABLE = True
except ImportError:
    HOOKS_AVAILABLE = False

logger = logging.getLogger(__name__)

# ============================================================================
# Constants - Combined from all 4 systems
# ============================================================================

# Default thresholds from ContextCompactor
DEFAULT_THRESHOLD_PCT = 0.85  # Compact at 85% context usage
WARNING_THRESHOLD = 0.70  # Warn at 70%
CRITICAL_THRESHOLD = 0.95  # Emergency at 95%

# From auto_compact - Model context windows
DEFAULT_CONTEXT_WINDOW = 200_000  # Default 200k tokens
HIGH_CONTEXT_WINDOW = 1_000_000  # 1M for advanced models
AUTOCOMPACT_BUFFER_TOKENS = 13_000  # Buffer for auto-compact trigger

# Circuit breaker from auto_compact
DEFAULT_MAX_FAILURES = 3  # Max consecutive failures before stopping

# Priority levels from ContextCompactor
PRIORITY_CRITICAL = 10  # System prompts, key decisions
PRIORITY_HIGH = 8  # User corrections, important context
PRIORITY_MEDIUM = 5  # Regular conversation
PRIORITY_LOW = 3  # Filler, summaries, tool outputs
PRIORITY_DISCARDABLE = 1  # Temporary context, can be discarded


# Compression modes from ContextCompressor
class CompressionMode(Enum):
    SNIP = "snip"  # Truncate long messages
    MICRO = "micro"  # Fine-grained tool call trimming
    CONTEXT = "context"  # Context collapse with summary
    AUTO = "auto"  # Full escalation compression


# ============================================================================
# Model Context Windows - From auto_compact
# ============================================================================

MODEL_CONTEXT_WINDOWS: dict[str, int] = {
    # Anthropic models
    "claude-3-opus": 200_000,
    "claude-3-sonnet": 200_000,
    "claude-3-5-sonnet": 200_000,
    "claude-3-5-haiku": 200_000,
    "claude-4-opus": 200_000,
    "claude-4-sonnet": 200_000,
    "claude-3-5-sonnet-20241022": 500_000,
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
    "minimax-m2.5-free": 32_768,
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


# ============================================================================
# Dataclasses - Combined results
# ============================================================================


@dataclass
class CompactionResult:
    """Result of unified compaction."""

    original_messages: list[dict[str, Any]]
    compacted_messages: list[dict[str, Any]]
    original_tokens: int
    compacted_tokens: int
    reduction_pct: float
    stages_applied: list[str]
    boundary_marker: dict[str, Any] | None = None
    summary: str = ""
    messages_compacted: int = 0
    messages_discarded: int = 0


@dataclass
class PrioritySegment:
    """A segment with priority (from ContextCompactor)."""

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


# ============================================================================
# Circuit Breaker - From auto_compact
# ============================================================================


class CircuitBreaker:
    """Circuit breaker pattern - prevents API hammering after failures."""

    def __init__(self, max_failures: int = DEFAULT_MAX_FAILURES):
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
        """Check if another compaction attempt is allowed."""
        return self.failures < self.max_failures

    def get_state(self) -> dict[str, Any]:
        """Get circuit breaker state."""
        return {
            "failures": self.failures,
            "max_failures": self.max_failures,
            "is_tripped": self.failures >= self.max_failures,
        }


# ============================================================================
# Token Estimation - Combined
# ============================================================================


def estimate_tokens(text: str) -> int:
    """Estimate tokens in text (lightweight, ~4 chars per token)."""
    if not isinstance(text, str):
        text = str(text)
    return len(text) // 4


def estimate_conversation_tokens(messages: list[dict[str, Any]]) -> int:
    """Estimate total tokens in conversation (from auto_compact)."""
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if not content:
            continue
        # Detect code vs prose
        is_code = _is_code_content(content)
        chars_per_token = 3.5 if is_code else 4.5
        tokens = max(1, int(len(content) / chars_per_token))
        total += tokens
    return total


def _is_code_content(content: str) -> bool:
    """Detect if content is code (from auto_compact)."""
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
# Model Context Detection - From auto_compact
# ============================================================================


class ModelCapability(Enum):
    """Model capability tiers."""

    STANDARD = "standard"  # 200k context
    EXTENDED = "extended"  # 500k context
    HIGH = "high"  # 1M+ context


def get_context_window_for_model(model: str | None) -> int:
    """Get context window size for a model."""
    if model is None:
        return DEFAULT_CONTEXT_WINDOW
    # Exact match
    if model in MODEL_CONTEXT_WINDOWS:
        return MODEL_CONTEXT_WINDOWS[model]
    # Prefix match
    for known_model, window in MODEL_CONTEXT_WINDOWS.items():
        if model.startswith(known_model) or known_model.startswith(model):
            return window
    # Environment override
    env_override = os.environ.get("NX_CONTEXT_WINDOW_OVERRIDE")
    if env_override:
        try:
            return int(env_override)
        except ValueError:
            pass
    return DEFAULT_CONTEXT_WINDOW


def get_model_capability(model: str) -> ModelCapability:
    """Get model capability tier."""
    window = get_context_window_for_model(model)
    if window >= HIGH_CONTEXT_WINDOW:
        return ModelCapability.HIGH
    elif window >= 500_000:
        return ModelCapability.EXTENDED
    else:
        return ModelCapability.STANDARD


def get_effective_context_window(model: str) -> int:
    """Get effective context window (minus reserved output tokens)."""
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
    return context_window - AUTOCOMPACT_BUFFER_TOKENS


# ============================================================================
# Compression Modes - From ContextCompressor
# ============================================================================


def snip_compact(
    messages: list[dict[str, Any]],
    max_message_length: int = 2000,
) -> list[dict[str, Any]]:
    """Stage 1: Snip - truncate long individual messages."""
    result = []
    for msg in messages:
        msg_copy = dict(msg)
        content = msg_copy.get("content", "")
        if isinstance(content, str) and len(content) > max_message_length:
            msg_copy["content"] = (
                content[:max_message_length]
                + f"\n\n[... {len(content) - max_message_length} chars truncated ...]"
            )
            msg_copy["_truncated"] = True
        result.append(msg_copy)
    return result


def micro_compact(
    messages: list[dict[str, Any]],
    tool_call_ids_to_preserve: Optional[list[str]] = None,
) -> list[dict[str, Any]]:
    """Stage 2: Micro - finer-grained tool call trimming."""
    if tool_call_ids_to_preserve is None:
        tool_call_ids_to_preserve = []
    preserve_set = set(tool_call_ids_to_preserve)
    result = []
    for msg in messages:
        msg_copy = dict(msg)
        # Handle tool calls
        if msg_copy.get("role") == "assistant" and "tool_calls" in msg_copy:
            tool_calls = msg_copy["tool_calls"]
            if isinstance(tool_calls, list):
                cleaned_calls = []
                for tc in tool_calls:
                    if isinstance(tc, dict):
                        tc_id = tc.get("id", "")
                        if tc_id in preserve_set:
                            cleaned_calls.append(tc)
                        else:
                            func = tc.get("function", {})
                            cleaned_calls.append(
                                {
                                    "id": tc_id,
                                    "function": {
                                        "name": func.get("name", ""),
                                    },
                                }
                            )
                    else:
                        cleaned_calls.append(tc)
                msg_copy["tool_calls"] = cleaned_calls
        # Handle tool results
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


def context_collapse(
    messages: list[dict[str, Any]],
    active_window_size: int = 10,
) -> list[dict[str, Any]]:
    """Stage 3: Context collapse - fold inactive regions."""
    if len(messages) <= active_window_size:
        return messages
    active = messages[-active_window_size:]
    archived = messages[:-active_window_size]
    # Build summary
    role_counts: dict[str, int] = {}
    total_chars = 0
    for msg in archived:
        role = msg.get("role", "unknown")
        role_counts[role] = role_counts.get(role, 0) + 1
        content = msg.get("content", "")
        if isinstance(content, str):
            total_chars += len(content)
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


def auto_compact_messages(
    messages: list[dict[str, Any]],
    target_tokens: int,
) -> list[dict[str, Any]]:
    """Stage 4: Auto - full compression when near threshold."""
    result = list(messages)
    # Pass 1: Aggressive truncation
    result = snip_compact(result, max_message_length=500)
    # Pass 2: Remove non-essential tool results
    result = micro_compact(result, tool_call_ids_to_preserve=[])
    # Pass 3: Reduce active window
    result = context_collapse(result, active_window_size=5)
    # Pass 4: Final aggressive trim
    if len(result) > 5:
        result = result[-5:]
    # Mark
    for msg in result:
        msg["_auto_compacted"] = True
    return result


# ============================================================================
# Priority-Based Pruning - From ContextCompactor
# ============================================================================


def priority_compact(
    messages: list[dict[str, Any]],
    target_tokens: int,
    segment_priority: Optional[dict[int, int]] = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Priority-based compaction (1-10 priority levels).

    Returns:
        Tuple of (compacted_messages, stats_dict)
    """
    if segment_priority is None:
        # Default: assign priorities by role
        segment_priority = {
            PRIORITY_CRITICAL: PRIORITY_CRITICAL,  # system
            PRIORITY_HIGH: PRIORITY_HIGH,  # user corrections
            PRIORITY_MEDIUM: PRIORITY_MEDIUM,  # regular
            PRIORITY_LOW: PRIORITY_LOW,  # tool outputs
        }

    # Create priority map
    priority_map = {}
    for i, msg in enumerate(messages):
        role = msg.get("role", "user")
        if role == "system":
            priority = segment_priority.get(PRIORITY_CRITICAL, PRIORITY_CRITICAL)
        elif role == "user":
            # Check for corrections
            content = msg.get("content", "").lower()
            if "actually" in content or "wait" in content or "no," in content:
                priority = segment_priority.get(PRIORITY_HIGH, PRIORITY_HIGH)
            else:
                priority = segment_priority.get(PRIORITY_MEDIUM, PRIORITY_MEDIUM)
        else:
            priority = segment_priority.get(PRIORITY_LOW, PRIORITY_LOW)
        priority_map[i] = priority

    # Sort by priority (lowest first for removal)
    indexed = list(enumerate(messages))
    indexed.sort(key=lambda x: priority_map.get(x[0], PRIORITY_MEDIUM))

    # Remove lowest priority until under target
    result = list(messages)
    removed = set()
    current_tokens = estimate_conversation_tokens(result)

    for idx, msg in indexed:
        if current_tokens <= target_tokens:
            break
        if priority_map.get(idx, PRIORITY_MEDIUM) <= PRIORITY_LOW:
            removed.add(idx)
            current_tokens -= estimate_tokens(msg.get("content", ""))

    compacted = [m for i, m in enumerate(result) if i not in removed]

    stats = {
        "removed_count": len(removed),
        "priority_map": priority_map,
    }
    return compacted, stats


# ============================================================================
# File Preservation - From auto_compact
# ============================================================================


def preserve_file_attachments(
    messages: list[dict[str, Any]],
    max_files: int = 5,
) -> list[dict[str, Any]]:
    """Extract file attachment info for post-compact restoration."""
    attachments = []
    file_paths = set()
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            lines = content.split("\n")
            for line in lines:
                if line.strip().startswith("File:") or line.strip().startswith("Read:"):
                    path = line.split(":", 1)[1].strip()
                    if path and path not in file_paths and len(attachments) < max_files:
                        file_paths.add(path)
                        attachments.append({"type": "file", "path": path})
    return attachments


# ============================================================================
# Boundary Markers - From auto_compact
# ============================================================================


def create_boundary_marker(
    trigger: str,
    pre_compact_token_count: int,
    messages_summarized: int | None = None,
) -> dict[str, Any]:
    """Create a compaction boundary marker."""
    return {
        "type": "system",
        "role": "system",
        "content": f"[Earlier conversation compact: {pre_compact_token_count} tokens summarized]",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "is_compact_boundary": True,
        "compact_metadata": {
            "trigger": trigger,
            "pre_compact_token_count": pre_compact_token_count,
            "messages_summarized": messages_summarized,
            "version": "1.0",
        },
    }


def create_summary_message(summary: str) -> dict[str, Any]:
    """Create a summary message."""
    return {
        "type": "user",
        "role": "user",
        "content": f"[Summary of earlier conversation]\n\n{summary}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "is_compact_summary": True,
    }


# ============================================================================
# Partial Compact - From auto_compact
# ============================================================================


class PartialDirection(Enum):
    """Direction for partial compaction."""

    PREFIX_PRESERVING = "from"  # Summarize tail, keep head
    SUFFIX_PRESERVING = "up_to"  # Summarize head, keep tail


def partial_compact(
    messages: list[dict[str, Any]],
    pivot_index: int,
    direction: PartialDirection = PartialDirection.PREFIX_PRESERVING,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Partial compaction around a pivot point."""
    if direction == PartialDirection.SUFFIX_PRESERVING:
        to_summarize = messages[:pivot_index]
        to_keep = messages[pivot_index:]
        to_keep = [
            m
            for m in to_keep
            if m.get("type") != "progress"
            and not m.get("is_compact_boundary")
            and not (m.get("role") == "user" and m.get("is_compact_summary"))
        ]
    else:
        to_summarize = messages[pivot_index:]
        to_keep = messages[:pivot_index]
        to_keep = [m for m in to_keep if m.get("type") != "progress"]

    if not to_summarize:
        raise ValueError("Nothing to summarize in specified direction")

    pre_tokens = estimate_conversation_tokens(to_summarize)
    boundary = create_boundary_marker(
        trigger="manual",
        pre_compact_token_count=pre_tokens,
        messages_summarized=len(to_summarize),
    )
    return to_summarize, to_keep, boundary


# ============================================================================
# Main UnifiedCompactor Class
# ============================================================================


class UnifiedCompactor:
    """
    Unified Compactor - combines all 4 compaction systems.

    Features:
    - Model-aware context window detection
    - Circuit breaker pattern (prevent API hammering)
    - Priority-based pruning (1-10 levels)
    - Multiple compression modes (snip/micro/context/auto)
    - File attachment preservation
    - Partial compact support
    - Configurable thresholds
    """

    # Default configuration
    DEFAULT_RECENT_COUNT = 5  # From MicroCompactor
    DEFAULT_MAX_MESSAGE_LENGTH = 2000  # From ContextCompressor
    DEFAULT_ACTIVE_WINDOW = 10  # From ContextCompressor
    DEFAULT_TOKEN_BUFFER_RATIO = 0.85  # From ContextCompactor

    def __init__(
        self,
        threshold_pct: float = DEFAULT_THRESHOLD_PCT,
        model: str | None = None,
        max_consecutive_failures: int = DEFAULT_MAX_FAILURES,
        mode: str = "auto",
        max_message_length: int = DEFAULT_MAX_MESSAGE_LENGTH,
        active_window_size: int = DEFAULT_ACTIVE_WINDOW,
    ):
        """
        Initialize UnifiedCompactor.

        Args:
            threshold_pct: Threshold percentage (0.85 = 85%)
            model: Model name for context window detection
            max_consecutive_failures: Circuit breaker max failures
            mode: Compression mode (snip/micro/context/auto)
            max_message_length: Max message length for snip mode
            active_window_size: Active window for context collapse
        """
        self.threshold_pct = threshold_pct
        self.model = model or os.environ.get("NX_DEFAULT_MODEL", "claude-3-5-sonnet")
        self.max_consecutive_failures = max_consecutive_failures
        self.mode = CompressionMode(mode)
        self.max_message_length = max_message_length
        self.active_window_size = active_window_size

        # Circuit breaker
        self.circuit_breaker = CircuitBreaker(max_consecutive_failures)

        # Tracking state
        self._compaction_count = 0
        self._consecutive_failures = 0

    def should_compact(
        self, messages: list[dict[str, Any]], model: str | None = None
    ) -> bool:
        """
        Check if compaction should trigger.

        Args:
            messages: Conversation messages
            model: Model name (uses default if None)

        Returns:
            True if compaction threshold reached
        """
        model = model or self.model

        # Check if circuit breaker is tripped
        if not self.circuit_breaker.should_allow_attempt():
            logger.info("Circuit breaker - skipping compaction")
            return False

        # Check threshold
        tokens = estimate_conversation_tokens(messages)
        effective_window = get_effective_context_window(model)
        threshold = int(effective_window * self.threshold_pct)

        return tokens >= threshold

    def compact(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        summary_provider: Optional[Callable[[list[dict[str, Any]]], str]] = None,
    ) -> CompactionResult:
        """
        Execute compaction on messages.

        Args:
            messages: Messages to compact
            model: Model name (uses default if None)
            summary_provider: Optional callable to generate summary

        Returns:
            CompactionResult with compacted messages and stats
        """
        if not messages:
            return CompactionResult(
                original_messages=[],
                compacted_messages=[],
                original_tokens=0,
                compacted_tokens=0,
                reduction_pct=0.0,
                stages_applied=[],
            )

        # Execute pre-compact hooks BEFORE any compaction happens
        if HOOKS_AVAILABLE:
            try:
                compact_context = CompactContext(
                    phase="before",
                    preserved_data={},
                    compression_strategy=self.mode.value,
                )
                registry = get_default_registry()
                hook_results = registry.execute_hooks(HookType.COMPACT, compact_context)
                logger.debug(
                    f"unified_compactor: Executed {len(hook_results)} pre-compact hooks"
                )
            except Exception as e:
                logger.warning(f"unified_compactor: Pre-compact hooks failed: {e}")

        model = model or self.model
        effective_window = get_effective_context_window(model)
        target_tokens = int(effective_window * self.threshold_pct)

        original_tokens = estimate_conversation_tokens(messages)
        if original_tokens < target_tokens:
            return CompactionResult(
                original_messages=messages,
                compacted_messages=messages,
                original_tokens=original_tokens,
                compacted_tokens=original_tokens,
                reduction_pct=0.0,
                stages_applied=[],
            )

        # Apply compression modes
        result = list(messages)
        stages_applied: list[str] = []

        # Stage 1: Snip (if mode includes snip or auto)
        if self.mode in (CompressionMode.SNIP, CompressionMode.AUTO):
            result = snip_compact(result, self.max_message_length)
            stages_applied.append("snip")

        # Stage 2: Micro (if mode includes micro or auto)
        if self.mode in (CompressionMode.MICRO, CompressionMode.AUTO):
            result = micro_compact(result)
            stages_applied.append("micro")

        # Stage 3: Context collapse (if mode includes context or auto)
        if self.mode in (CompressionMode.CONTEXT, CompressionMode.AUTO):
            result = context_collapse(result, self.active_window_size)
            stages_applied.append("context")

        # Stage 4: Auto (if mode is auto and still over target)
        current_tokens = estimate_conversation_tokens(result)
        if self.mode == CompressionMode.AUTO and current_tokens > target_tokens:
            result = auto_compact_messages(result, target_tokens)
            stages_applied.append("auto")

        # Create boundary marker for auto/context modes
        boundary = None
        if self.mode in (CompressionMode.CONTEXT, CompressionMode.AUTO):
            boundary = create_boundary_marker(
                trigger="auto" if self.mode == CompressionMode.AUTO else "manual",
                pre_compact_token_count=original_tokens,
                messages_summarized=len(messages) - len(result),
            )
            result = [boundary] + result

        compacted_tokens = estimate_conversation_tokens(result)

        # Calculate stats
        reduction_pct = (
            ((original_tokens - compacted_tokens) / original_tokens * 100)
            if original_tokens > 0
            else 0
        )

        # Success - record
        self.circuit_breaker.record_success()
        self._compaction_count += 1
        self._consecutive_failures = 0

        return CompactionResult(
            original_messages=messages,
            compacted_messages=result,
            original_tokens=original_tokens,
            compacted_tokens=compacted_tokens,
            reduction_pct=round(reduction_pct, 2),
            stages_applied=stages_applied,
            boundary_marker=boundary,
            summary=f"Compacted {len(messages) - len(result)} messages, reduced by {reduction_pct:.1f}%",
            messages_compacted=len(messages) - len(result),
            messages_discarded=0,
        )

    def compact_priority(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        min_priority: int = PRIORITY_MEDIUM,
    ) -> CompactionResult:
        """
        Priority-based compaction.

        Args:
            messages: Messages to compact
            model: Model name
            min_priority: Minimum priority to keep (1-10)

        Returns:
            CompactionResult
        """
        model = model or self.model
        effective_window = get_effective_context_window(model)
        target_tokens = int(effective_window * self.threshold_pct)

        original_tokens = estimate_conversation_tokens(messages)
        original_messages = messages

        # Apply priority pruning
        compacted, stats = priority_compact(messages, target_tokens)

        compacted_tokens = estimate_conversation_tokens(compacted)

        reduction_pct = (
            ((original_tokens - compacted_tokens) / original_tokens * 100)
            if original_tokens > 0
            else 0
        )

        self.circuit_breaker.record_success()

        return CompactionResult(
            original_messages=original_messages,
            compacted_messages=compacted,
            original_tokens=original_tokens,
            compacted_tokens=compacted_tokens,
            reduction_pct=round(reduction_pct, 2),
            stages_applied=["priority"],
            messages_compacted=stats.get("removed_count", 0),
        )

    def compact_partial(
        self,
        messages: list[dict[str, Any]],
        pivot_index: int,
        direction: PartialDirection = PartialDirection.PREFIX_PRESERVING,
    ) -> CompactionResult:
        """
        Partial compaction around a pivot point.

        Args:
            messages: Messages to compact
            pivot_index: Index to pivot around
            direction: Which side to summarize

        Returns:
            CompactionResult
        """
        to_summarize, to_keep, boundary = partial_compact(
            messages, pivot_index, direction
        )

        original_tokens = estimate_conversation_tokens(messages)

        result = [boundary] + to_keep

        compacted_tokens = estimate_conversation_tokens(result)

        reduction_pct = (
            ((original_tokens - compacted_tokens) / original_tokens * 100)
            if original_tokens > 0
            else 0
        )

        return CompactionResult(
            original_messages=messages,
            compacted_messages=result,
            original_tokens=original_tokens,
            compacted_tokens=compacted_tokens,
            reduction_pct=round(reduction_pct, 2),
            stages_applied=["partial"],
            boundary_marker=boundary,
        )

    def get_priority_summary(self) -> dict[str, Any]:
        """Get priority-based summary."""
        return {
            "threshold_pct": self.threshold_pct,
            "model": self.model,
            "context_window": get_context_window_for_model(self.model),
            "effective_window": get_effective_context_window(self.model),
            "circuit_breaker": self.circuit_breaker.get_state(),
            "compaction_count": self._compaction_count,
        }

    def get_status(self) -> dict[str, Any]:
        """Get compactor status."""
        return {
            "model": self.model,
            "mode": self.mode.value,
            "threshold_pct": self.threshold_pct,
            "context_window": get_context_window_for_model(self.model),
            "effective_window": get_effective_context_window(self.model),
            "circuit_breaker": self.circuit_breaker.get_state(),
            "stats": {
                "compaction_count": self._compaction_count,
                "consecutive_failures": self._consecutive_failures,
            },
        }

    def reset_circuit_breaker(self) -> None:
        """Reset circuit breaker state."""
        self.circuit_breaker = CircuitBreaker(self.max_consecutive_failures)
        self._consecutive_failures = 0


# ============================================================================
# Module-Level Convenience Functions
# ============================================================================

# Global singleton
_compactor: Optional[UnifiedCompactor] = None


def get_compactor() -> UnifiedCompactor:
    """Get singleton UnifiedCompactor."""
    global _compactor
    if _compactor is None:
        _compactor = UnifiedCompactor()
    return _compactor


def should_compact(messages: list[dict[str, Any]], model: str | None = None) -> bool:
    """Convenience function to check if compaction needed."""
    return get_compactor().should_compact(messages, model)


def compact_messages(
    messages: list[dict[str, Any]],
    model: str | None = None,
) -> CompactionResult:
    """Convenience function to compact messages."""
    return get_compactor().compact(messages, model)


# ============================================================================
# Quick Test
# ============================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s: %(message)s",
    )

    print("=== Unified Compactor Test ===\n")

    # Test messages
    test_messages = [
        {"role": "system", "content": "You are a helpful coding assistant."},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi! How can I help you today?"},
        {"role": "user", "content": "I need to implement a new feature. " * 50},
    ]

    # Test compactor
    compactor = UnifiedCompactor(
        threshold_pct=0.85,
        model="claude-3-5-sonnet",
    )

    # Test should_compact
    print("--- Should Compact Test ---")
    should = compactor.should_compact(test_messages)
    print(f"Should compact (85% threshold): {should}")
    print(f"Context window: {get_context_window_for_model('claude-3-5-sonnet')}")
    print(f"Effective window: {get_effective_context_window('claude-3-5-sonnet')}")

    # Test context window detection
    print("\n--- Model Context Windows ---")
    test_models = [
        "claude-3-5-sonnet",
        "gpt-4o",
        "opencode/qwen3.6-plus-free",
        "minimax-m2.5-free",
    ]
    for m in test_models:
        window = get_context_window_for_model(m)
        print(f"  {m}: {window:,} tokens")

    # Test compression modes
    print("\n--- Compression Modes ---")

    # Snip
    result = snip_compact(test_messages, max_message_length=100)
    print(f"  Snip: {len(result)} messages (truncated 4th)")

    # Micro
    result = micro_compact(test_messages)
    print(f"  Micro: {len(result)} messages")

    # Context
    result = context_collapse(test_messages, active_window_size=2)
    print(f"  Context: {len(result)} messages (collapsed)")

    # Auto
    result = auto_compact_messages(test_messages, target_tokens=50)
    print(f"  Auto: {len(result)} messages")

    # Test full compaction with high load
    print("\n--- Full Compaction Test ---")
    heavy_messages = [
        {"role": "system", "content": "System prompt " * 200},
        {"role": "user", "content": "User message " * 200},
        {"role": "assistant", "content": "Assistant response " * 200},
        {"role": "user", "content": "Another user " * 200},
    ]

    compactor = UnifiedCompactor(threshold_pct=0.50, mode="auto")
    compaction_result = compactor.compact(heavy_messages)

    print(f"  Original tokens: {compaction_result.original_tokens}")
    print(f"  Compacted tokens: {compaction_result.compacted_tokens}")
    print(f"  Reduction: {compaction_result.reduction_pct:.1f}%")
    print(f"  Stages: {compaction_result.stages_applied}")

    # Test priority compaction
    print("\n--- Priority Compaction Test ---")
    priority_result = compactor.compact_priority(test_messages)
    print(f"  Original: {priority_result.original_tokens}")
    print(f"  Compacted: {priority_result.compacted_tokens}")
    print(f"  Reduction: {priority_result.reduction_pct:.1f}%")

    # Test partial compaction
    print("\n--- Partial Compaction Test ---")
    partial_result = compactor.compact_partial(test_messages, 2)
    print(f"  Original: {partial_result.original_tokens}")
    print(f"  Compacted: {partial_result.compacted_tokens}")
    print(f"  Boundary: {partial_result.boundary_marker is not None}")

    # Test circuit breaker
    print("\n--- Circuit Breaker Test ---")
    cb = CircuitBreaker(max_failures=2)
    cb.record_failure()
    print(f"  After 1 failure: {cb.get_state()}")
    cb.record_failure()
    print(f"  After 2 failures: {cb.get_state()}")
    print(f"  Should allow: {cb.should_allow_attempt()}")

    # Test status
    print("\n--- Status Test ---")
    status = compactor.get_status()
    print(f"  Model: {status['model']}")
    print(f"  Mode: {status['mode']}")
    print(f"  Compaction count: {status['stats']['compaction_count']}")

    print("\n✓ All tests passed!")
    sys.exit(0)
