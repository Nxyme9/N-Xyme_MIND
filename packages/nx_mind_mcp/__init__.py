#!/usr/bin/env python3
"""nx-mind-mcp package - re-exports from inner module."""

import sys
from pathlib import Path

# Add parent to path so inner module can be found
_project_root = Path(__file__).resolve().parent.parent.parent
_packages_dir = _project_root / "packages"
if str(_packages_dir) not in sys.path:
    sys.path.insert(0, str(_packages_dir))

from .nx_mind_mcp import (
    mcp,
    get_session_context,
    log_task_completion,
    get_mind_state,
    update_mind_state,
    get_session_history,
    get_active_workflow,
    set_context,
    sync_to_memory,
    get_project_manifest,
    # Golden Spine tools
    spine_probe,
    spine_run,
    spine_status,
)

__all__ = [
    "mcp",
    "get_session_context",
    "log_task_completion",
    "get_mind_state",
    "update_mind_state",
    "get_session_history",
    "get_active_workflow",
    "set_context",
    "sync_to_memory",
    "get_project_manifest",
    "spine_probe",
    "spine_run",
    "spine_status",
]
