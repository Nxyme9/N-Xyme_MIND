"""Spine Package — Golden Spine execution path for AI model serving.

This package provides isolated execution path for AI model serving with:
- Configuration dataclass (SpineConfig)
- Run record tracking (RunRecord)
- GoldenSpine orchestration (lazy import)

Public API:
- SpineConfig: Configuration dataclass
- get_run_record(): Lazy import of RunRecord class
- get_golden_spine(): Lazy import of GoldenSpine class

Version: 1.0.0
"""

__version__ = "1.0.0"

# Direct import for SpineConfig (no circular dependency risk)
from .config import SpineConfig

# Lazy imports for classes that may cause circular imports
# Use get_run_record() and get_golden_spine() functions


def get_run_record():
    """Get RunRecord class (lazy import to avoid circular imports).

    Returns:
        RunRecord dataclass for tracking execution runs
    """
    from .config import _get_run_record

    return _get_run_record()


def get_golden_spine():
    """Get GoldenSpine class (lazy import to avoid circular imports).

    Returns:
        GoldenSpine class for model serving orchestration, or None if not available
    """
    from .config import _get_golden_spine

    return _get_golden_spine()


# Backwards compatibility - expose classes at module level
# These will be loaded lazily to prevent circular imports
def __getattr__(name: str):
    """Lazy attribute loading for backwards compatibility."""
    if name == "RunRecord":
        return get_run_record()
    if name == "GoldenSpine":
        return get_golden_spine()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "__version__",
    "SpineConfig",
    "get_run_record",
    "get_golden_spine",
    # Lazy exports (accessible via get_* functions or attribute access)
    # "RunRecord",  # Use get_run_record()
    # "GoldenSpine",  # Use get_golden_spine()
]