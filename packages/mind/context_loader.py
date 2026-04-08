"""Context Loader - Auto-injects system context on session start.

This module ensures the system knows itself by loading session state
into context automatically on every session start.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

# Base paths
WORKSPACE = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
SISYPHUS = WORKSPACE / ".sisyphus"
CONTEXT = WORKSPACE / ".context"


def load_session_state() -> dict:
    """Load session state from .sisyphus/"""
    state_file = SISYPHUS / "session-state.json"
    if state_file.exists():
        with open(state_file) as f:
            return json.load(f)
    return {}


def load_mind_state() -> dict:
    """Load mind state from .context/"""
    state_file = CONTEXT / "mind-state.json"
    if state_file.exists():
        with open(state_file) as f:
            return json.load(f)
    return {}


def get_system_identity() -> str:
    """Get system identity description."""
    identity_file = CONTEXT / "system_identity.md"
    if identity_file.exists():
        with open(identity_file) as f:
            return f.read()
    return "N-Xyme_MIND - Personal AI coding workspace"


def generate_context_block() -> str:
    """Generate full context block for injection."""
    session = load_session_state()
    mind = load_mind_state()
    identity = get_system_identity()

    # Build context
    lines = [
        "# System Context - Auto-loaded",
        "",
        "## Who I Am",
        identity,
        "",
        "## Current Session",
    ]

    # Session info
    if session:
        lines.append(f"- **Last Agent**: {session.get('last_agent', 'unknown')}")
        lines.append(f"- **Current Task**: {session.get('current_task', 'none')}")
        lines.append(f"- **Last Updated**: {session.get('last_updated', 'unknown')}")

        # Completed changes (last 5)
        changes = session.get("completed_changes", [])
        if changes:
            lines.append("")
            lines.append("## Recent Work")
            for change in changes[-5:]:
                lines.append(f"- {change}")

    # Memory stats
    if session.get("memory_stats"):
        stats = session["memory_stats"]
        lines.append("")
        lines.append("## Memory Stats")
        for key, val in stats.items():
            lines.append(f"- **{key}**: {val}")

    # Phase
    if mind:
        lines.append("")
        lines.append(f"**Phase**: {mind.get('phase', 'unknown')}")

    lines.append("")
    lines.append(f"*Context loaded: {datetime.now().isoformat()}*")

    return "\n".join(lines)


def update_active_context():
    """Update activeContext.md with current state."""
    context_file = CONTEXT / "activeContext.md"
    content = generate_context_block()

    with open(context_file, "w") as f:
        f.write(content)

    print(f"✓ Updated activeContext.md")
    return content


def get_session_summary() -> str:
    """Get brief session summary for quick reference."""
    session = load_session_state()
    mind = load_mind_state()

    summary = []

    if session:
        summary.append(f"Agent: {session.get('last_agent', '?')}")
        summary.append(f"Task: {session.get('current_task', '?')}")

        if session.get("memory_stats"):
            stats = session["memory_stats"]
            summary.append(f"Files: {stats.get('files_indexed', 0)}")
            summary.append(f"Chunks: {stats.get('chunks_embedded', 0)}")
            summary.append(f"Tests: {stats.get('tests_passing', 0)}")

    if mind:
        summary.append(f"Phase: {mind.get('phase', '?')}")

    return " | ".join(summary)


# CLI for testing
if __name__ == "__main__":
    print("=== N-Xyme_MIND Context Loader ===")
    print()
    print(get_session_summary())
    print()
    update_active_context()
    print()
    print("Context block ready for injection.")
