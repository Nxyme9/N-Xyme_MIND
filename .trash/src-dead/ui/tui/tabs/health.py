"""Health tab - agent health status display."""

from pathlib import Path

# Import from parent module
_safe_json = None
get_agent_health_data = None


def init(safe_json, health_fn):
    global _safe_json, get_agent_health_data
    _safe_json = safe_json
    get_agent_health_data = health_fn


def get_content() -> str:
    health = get_agent_health_data()
    if not health:
        return "No agent health data available"

    content = "AGENT HEALTH STATUS\n\n"
    for agent_name, data in health.items():
        status = data.get("status", "unknown")
        total = data.get("total_checks", 0)
        success = data.get("total_successes", 0)
        fail = data.get("total_failures", 0)
        avg_time = data.get("avg_response_time_ms", 0)
        status_icon = (
            "✓" if status == "healthy" else "⚠" if status == "degraded" else "✗"
        )
        content += f"{status_icon} {agent_name:<20} {status:<10} {success}/{total} ({fail} fail) | {avg_time:.0f}ms\n"
    return content
