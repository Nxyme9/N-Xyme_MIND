"""N-Xyme MCP Package — Custom MCP tools for OpenCode.

This package contains MCP wrappers for N-Xyme's internal intelligence components.

Available MCPs:
    nx_delegate — Reliable task delegation (replaces OMO task())
    nx_brain — Brain/memory integration (see packages.nx_brain_mcp)
    orchestration — Agent orchestration (see packages.orchestration)
"""

__version__ = "1.0.0"

from .nx_delegate import (
    nx_delegate,
    nx_delegate_record_outcome,
    nx_delegate_with_id,
    get_unified_router,
    health_check,
)

__all__ = [
    "__version__",
    "nx_delegate",
    "nx_delegate_record_outcome",
    "nx_delegate_with_id",
    "get_unified_router",
    "health_check",
]
