"""Pre-Compact Hook - Automatic quicksave before context truncation.

This hook triggers an automatic session checkpoint before context compaction
occurs, ensuring critical state is preserved through truncation events.

Pattern: Based on Claude Code's pre-compact hook system.

Control: Enabled via tiered_compaction feature flag.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger("pre_compact_hook")


# Feature flag check - only active when tiered_compaction is enabled
def is_pre_compact_enabled() -> bool:
    """Check if pre-compact hook is enabled via feature flag."""
    # Check environment override first
    if os.environ.get("ENABLE_PRE_COMPACT_HOOK", "").lower() in ("1", "true", "yes"):
        return True
    if os.environ.get("DISABLE_PRE_COMPACT_HOOK", "").lower() in ("1", "true", "yes"):
        return False

    # Check feature flag file if it exists
    try:
        import yaml

        flag_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "configs",
            "feature_flags.yaml",
        )
        if os.path.exists(flag_file):
            with open(flag_file, "r") as f:
                flags = yaml.safe_load(f)
                return flags.get("enabled_features", {}).get("tiered_compaction", False)
    except Exception:
        pass

    return False  # Default disabled


# Try to import quicksave functionality, gracefully degrade if unavailable
_quicksave_available = False
_quicksave_module = None

try:
    from athena.sessions import append_checkpoint

    _quicksave_available = True
    _quicksave_module = "athena.sessions"
except ImportError:
    try:
        # Alternative import path
        from athena.core.sessions import append_checkpoint

        _quicksave_available = True
        _quicksave_module = "athena.core.sessions"
    except ImportError:
        logger.warning(
            "pre_compact_hook: athena.sessions not available - "
            "quicksave functionality disabled"
        )


def _trigger_quicksave(metadata: Optional[Dict[str, Any]] = None) -> bool:
    """Trigger a quicksave/checkpoint.

    Args:
        metadata: Optional metadata about the compaction event

    Returns:
        True if quicksave was triggered successfully
    """
    if not _quicksave_available:
        logger.debug("pre_compact_hook: quicksave not available, skipping")
        return False

    try:
        summary = "Auto-save before context compaction"
        if metadata:
            trigger = metadata.get("compression_strategy", "unknown")
            summary = f"Auto-save before {trigger} compaction"

        append_checkpoint(
            summary=summary, bullets=["Pre-compact checkpoint", "Phase: before"]
        )
        logger.info("pre_compact_hook: Quicksave triggered successfully")
        return True

    except Exception as e:
        logger.warning(f"pre_compact_hook: Quicksave failed: {e}")
        return False


def pre_compact_hook(context: Any) -> Any:
    """Pre-compaction hook callback.

    This hook fires BEFORE context compaction occurs and triggers
    an automatic quicksave to preserve session state.

    Args:
        context: CompactContext with phase="before"

    Returns:
        HookResult allowing the compaction to proceed
    """
    from packages.orchestration.hooks import HookResult, CompactContext

    if not isinstance(context, CompactContext):
        return HookResult(allowed=True, reason="Not a compact context")

    # Only trigger on "before" phase
    if context.phase != "before":
        logger.debug(
            f"pre_compact_hook: Skipping {context.phase} phase (only triggers on 'before')"
        )
        return HookResult(allowed=True)

    logger.info(
        "pre_compact_hook: Context compaction imminent - strategy=%s, preserving=%s",
        context.compression_strategy,
        list(context.preserved_data.keys()),
    )

    # Trigger quicksave
    metadata = {
        "compression_strategy": context.compression_strategy,
        "preserved_keys": list(context.preserved_data.keys()),
    }
    quicksave_success = _trigger_quicksave(metadata)

    if quicksave_success:
        return HookResult(
            allowed=True,
            reason="Pre-compact quicksave completed",
            modified_context={"quicksave_triggered": True},
        )
    else:
        return HookResult(
            allowed=True, reason="Pre-compact hook executed (quicksave unavailable)"
        )


def register() -> None:
    """Register this hook with the default registry.

    Called at module import to auto-register the hook.
    Priority 100 ensures it runs early in the hook chain.

    Registration only occurs if tiered_compaction feature flag is enabled.
    """
    # Check feature flag before registering
    if not is_pre_compact_enabled():
        logger.debug(
            "pre_compact_hook: Not registering (tiered_compaction flag disabled)"
        )
        return

    from packages.orchestration.hooks import (
        HookType,
        get_default_registry,
    )

    registry = get_default_registry()
    registry.register_hook(HookType.COMPACT, pre_compact_hook, priority=100)
    logger.info(
        "pre_compact_hook: Registered with priority 100 "
        f"(quicksave={'available' if _quicksave_available else 'unavailable'})"
    )


# Auto-register on import
try:
    register()
except Exception as e:
    logger.warning(f"pre_compact_hook: Auto-register failed: {e}")
