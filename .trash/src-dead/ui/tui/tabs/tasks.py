"""Tasks tab - active plan and task management."""

import json
from pathlib import Path

# Import from parent module
_safe_json = None


def init(safe_json):
    global _safe_json
    _safe_json = safe_json


def get_content() -> str:
    content = "═══ ACTIVE PLAN ═══\n\n"

    boulder = _safe_json(".sisyphus/boulder.json")

    if boulder:
        content += "▸ PLAN STATUS\n"
        content += f"  Plan: {boulder.get('plan_name', 'none')}\n"
        content += f"  Wave: {boulder.get('current_wave', 0)}\n"
        content += f"  Tasks: {boulder.get('tasks_completed', 0)}/{boulder.get('tasks_total', 0)}\n"

        wave_status = boulder.get("wave_1_status", "unknown")
        content += f"  Status: {wave_status}\n"

        next_action = boulder.get("next_action", "None")
        content += f"\n  Next: {next_action[:50]}...\n"

        # Session IDs
        sessions = boulder.get("session_ids", [])
        content += f"\n▸ SESSIONS\n"
        for sid in sessions[:3]:
            content += f"  {sid[:20]}...\n"
    else:
        content += "  No active plan\n"

    # Load plan files
    plan_files = list(Path(".sisyphus/plans").glob("*.json")) + list(
        Path(".sisyphus/plans").glob("*.md")
    )
    content += f"\n▸ AVAILABLE PLANS ({len(plan_files)})\n"
    for pf in plan_files[:5]:
        content += f"  • {pf.name}\n"

    content += "\n═══ QUICK ACTIONS ═══\n"
    content += "  [N] New plan    [C] Continue    [S] Stop plan\n"

    return content
