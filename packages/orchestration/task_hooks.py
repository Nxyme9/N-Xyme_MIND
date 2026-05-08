#!/usr/bin/env python3
"""Auto-Injector Hook for Agent Dispatch.

Automatically injects contextual memory before every agent dispatch.
Hooks into the task() orchestrator to inject relevant context.

Usage:
    from packages.orchestration.task_hooks import inject_before_task
    # Call before any task() dispatch
    context = inject_before_task(task_description, agent_type)
"""

from typing import Dict, List
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def load_recent_outcomes(limit: int = 10) -> List[Dict]:
    """Load recent outcomes from SQLite."""
    outcomes_db = PROJECT_ROOT / ".sisyphus" / "outcomes.db"

    if not outcomes_db.exists():
        return []

    import sqlite3

    conn = sqlite3.connect(str(outcomes_db))
    cursor = conn.execute(
        """SELECT task_description, agent, success, timestamp 
           FROM outcomes 
           ORDER BY timestamp DESC 
           LIMIT ?""",
        (limit,),
    )

    results = []
    for row in cursor:
        results.append(
            {
                "task": row[0],
                "agent": row[1],
                "success": bool(row[2]),
                "timestamp": row[3],
            }
        )

    conn.close()
    return results


def load_recent_sequences(limit: int = 5) -> List[Dict]:
    """Load recent tool sequences from SQLite."""
    outcomes_db = PROJECT_ROOT / ".sisyphus" / "outcomes.db"

    if not outcomes_db.exists():
        return []

    import sqlite3

    conn = sqlite3.connect(str(outcomes_db))
    cursor = conn.execute(
        """SELECT task_id, sequence, outcome, timestamp 
           FROM tool_sequences 
           ORDER BY timestamp DESC 
           LIMIT ?""",
        (limit,),
    )

    results = []
    for row in cursor:
        results.append(
            {
                "task_id": row[0],
                "sequence": row[1],
                "outcome": row[2],
                "timestamp": row[3],
            }
        )

    conn.close()
    return results


def build_injection_context(task_description: str, agent_type: str) -> str:
    """Build context injection string from recent outcomes and patterns."""

    outcomes = load_recent_outcomes(limit=5)
    sequences = load_recent_sequences(limit=3)

    if not outcomes and not sequences:
        return ""

    lines = ["# Recent Patterns (for context)"]

    # Add success patterns
    if outcomes:
        successful = [o for o in outcomes if o.get("success")]
        if successful:
            lines.append("\n## Successful patterns:")
            for o in successful[:3]:
                lines.append(
                    f"- Task: {o.get('task', '')[:60]}... → Agent: {o.get('agent')}"
                )

    # Add tool usage guidance based on sequences
    if sequences:
        lines.append("\n## Recent tool sequences:")
        for s in sequences[:2]:
            seq = s.get("sequence", "")
            outcome = s.get("outcome", "")
            lines.append(f"- {seq} → {outcome}")

    # Add failure patterns to avoid
    failed = [o for o in outcomes if not o.get("success")]
    if failed:
        lines.append("\n## Failed patterns (avoid):")
        for o in failed[:2]:
            lines.append(f"- Task: {o.get('task', '')[:60]}... with {o.get('agent')}")

    context = "\n".join(lines)

    # Truncate to fit in token budget (500 tokens ≈ 2000 chars)
    if len(context) > 1800:
        context = context[:1800] + "..."

    return context


def inject_before_task(task_description: str, agent_type: str) -> str:
    """Inject contextual memory before agent dispatch.

    Args:
        task_description: The task being dispatched
        agent_type: The agent being dispatched to

    Returns:
        Context string to inject into agent prompt (empty if no patterns found)
    """
    return build_injection_context(task_description, agent_type)


# Convenience function for standalone usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        task = sys.argv[1]
        agent = sys.argv[2] if len(sys.argv) > 2 else "unknown"
    else:
        task = "Test task"
        agent = "hephaestus"

    context = inject_before_task(task, agent)
    if context:
        print(context)
    else:
        print("# No recent patterns available")
