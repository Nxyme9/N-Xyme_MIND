"""Observations tab - learning observations and knowledge."""

import json
from pathlib import Path

# Import from parent module
_safe_json = None


def init(safe_json):
    global _safe_json
    _safe_json = safe_json


def get_content() -> str:
    content = "═══ LEARNING OBSERVATIONS ═══\n\n"

    # Load observations
    obs_files = sorted(Path(".sisyphus/observations").glob("*.json"))

    if not obs_files:
        content += "  No observations recorded\n"
        return content

    # Categorize observations
    prefs = []
    errs = []
    corrs = []
    decs = []

    for of in obs_files:
        name = of.name
        if "pref" in name:
            prefs.append(of)
        elif "err" in name:
            errs.append(of)
        elif "corr" in name:
            corrs.append(of)
        elif "dec" in name:
            decs.append(of)

    content += "▸ OBSERVATIONS BY TYPE\n"
    content += f"  Preferences: {len(prefs)}\n"
    content += f"  Errors: {len(errs)}\n"
    content += f"  Corrections: {len(corrs)}\n"
    content += f"  Decisions: {len(decs)}\n"

    # Show latest observation
    if obs_files:
        latest = obs_files[-1]
        try:
            data = json.loads(latest.read_text())
            content += "\n▸ LATEST\n"
            # Try to show relevant fields
            for k, v in list(data.items())[:4]:
                content += f"  {k}: {str(v)[:30]}...\n"
        except (json.JSONDecodeError, OSError):
            pass

    # Cross-session knowledge
    knowledge = _safe_json(".sisyphus/cross_session/knowledge.json")
    if knowledge:
        content += "\n▸ KNOWLEDGE GRAPH\n"
        entities = knowledge.get("entities", [])
        relations = knowledge.get("relations", [])
        content += f"  Entities: {len(entities)}\n"
        content += f"  Relations: {len(relations)}\n"

    content += "\n═══ QUICK ACTIONS ═══\n"
    content += "  [V] View all    [C] Clear old    [E] Export\n"

    return content
