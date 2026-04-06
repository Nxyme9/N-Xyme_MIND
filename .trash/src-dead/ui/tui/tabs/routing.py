"""Routing tab - routing system configuration and stats."""

from pathlib import Path

# Import from parent module
_safe_json = None
get_routing_data = None


def init(safe_json, routing_fn):
    global _safe_json, get_routing_data
    _safe_json = safe_json
    get_routing_data = routing_fn


def get_content() -> str:
    routing = get_routing_data()
    content = "═══ ROUTING SYSTEM ═══\n\n"

    # Triggers
    triggers = routing.get("triggers", [])
    if triggers:
        content += "▸ TRIGGERS\n"
        if isinstance(triggers, list):
            for t in triggers:
                pat = t.get("pattern", "?")[:30]
                ag = t.get("agent", "?")
                lvl = t.get("level", "?")
                conf = t.get("confidence", 0)
                content += f"  {pat:<30} → {ag:<12} L{lvl} ({conf:.0%})\n"
        elif isinstance(triggers, dict):
            for t in triggers.get("triggers", []):
                pat = t.get("pattern", "?")[:30]
                ag = t.get("agent", "?")
                lvl = t.get("level", "?")
                conf = t.get("confidence", 0)
                content += f"  {pat:<30} → {ag:<12} L{lvl} ({conf:.0%})\n"
        content += "\n"

    # Weights
    weights = routing.get("weights", {})
    if weights:
        content += "▸ AGENT WEIGHTS\n"
        for ag, w in weights.items():
            sr = w.get("success_rate", 0) * 100
            lat = w.get("avg_latency_ms", 0)
            tasks = w.get("total_tasks", 0)
            by_lvl = w.get("by_level", {})
            lvl_info = ", ".join(
                [
                    f"L{k}:{v.get('success_rate', 0) * 100:.0f}%"
                    for k, v in list(by_lvl.items())[:2]
                ]
            )
            content += f"  {ag:<16} {sr:>5.1f}% | {lat:>6.1f}ms | {tasks:>3} tasks | {lvl_info}\n"
        content += "\n"

    # Quick stats
    content += "▸ QUICK STATS\n"
    content += f"  Triggers: {len(triggers) if isinstance(triggers, list) else len(triggers.get('triggers', []))}\n"
    content += f"  Agents: {len(weights)}\n"

    return content
