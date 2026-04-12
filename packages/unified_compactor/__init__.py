"""
Unified Compactor - Consolidates 4 compaction systems into 1.

Combines:
1. MicroCompactor - 50% threshold, keep last 5 messages
2. ContextCompactor - Priority-based (1-10) pruning
3. auto_compact - Model-aware, circuit breaker, file preservation
4. ContextCompressor - Multiple modes: snip/micro/context/auto

Usage:
    from unified_compactor import UnifiedCompactor

    compactor = UnifiedCompactor(
        threshold_pct=0.85,
        model="claude-3-5-sonnet",
        mode="auto"
    )

    if compactor.should_compact(messages, model):
        result = compactor.compact(messages, model)
        print(f"Reduced: {result.original_tokens} → {result.compacted_tokens}")
"""

from unified_compactor.unified_compactor import (
    # Main class
    UnifiedCompactor,
    # Result classes
    CompactionResult,
    PrioritySegment,
    # Supporting classes
    CircuitBreaker,
    CompressionMode,
    ModelCapability,
    PartialDirection,
    # Constants
    DEFAULT_THRESHOLD_PCT,
    WARNING_THRESHOLD,
    CRITICAL_THRESHOLD,
    DEFAULT_MAX_FAILURES,
    PRIORITY_CRITICAL,
    PRIORITY_HIGH,
    PRIORITY_MEDIUM,
    PRIORITY_LOW,
    PRIORITY_DISCARDABLE,
    # Core functions
    get_context_window_for_model,
    get_model_capability,
    get_effective_context_window,
    estimate_conversation_tokens,
    estimate_tokens,
    # Compression functions
    snip_compact,
    micro_compact,
    context_collapse,
    auto_compact_messages,
    priority_compact,
    # Utility functions
    preserve_file_attachments,
    create_boundary_marker,
    create_summary_message,
    partial_compact,
    # Convenience functions
    get_compactor,
    should_compact,
    compact_messages,
)

__version__ = "1.0.0"

__all__ = [
    # Main
    "UnifiedCompactor",
    # Classes
    "CompactionResult",
    "PrioritySegment",
    "CircuitBreaker",
    "CompressionMode",
    "ModelCapability",
    "PartialDirection",
    # Constants
    "DEFAULT_THRESHOLD_PCT",
    "WARNING_THRESHOLD",
    "CRITICAL_THRESHOLD",
    "DEFAULT_MAX_FAILURES",
    "PRIORITY_CRITICAL",
    "PRIORITY_HIGH",
    "PRIORITY_MEDIUM",
    "PRIORITY_LOW",
    "PRIORITY_DISCARDABLE",
    # Core functions
    "get_context_window_for_model",
    "get_model_capability",
    "get_effective_context_window",
    "estimate_conversation_tokens",
    "estimate_tokens",
    # Compression functions
    "snip_compact",
    "micro_compact",
    "context_collapse",
    "auto_compact_messages",
    "priority_compact",
    # Utility functions
    "preserve_file_attachments",
    "create_boundary_marker",
    "create_summary_message",
    "partial_compact",
    # Convenience
    "get_compactor",
    "should_compact",
    "compact_messages",
]
