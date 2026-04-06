"""Settings tab - comprehensive system configuration display."""

from pathlib import Path

# Import from parent module
_safe_json = None
get_agent_health_data = None
get_skills_data = None
get_routing_data = None


def init(safe_json, health_fn, skills_fn, routing_fn):
    global _safe_json, get_agent_health_data, get_skills_data, get_routing_data
    _safe_json = safe_json
    get_agent_health_data = health_fn
    get_skills_data = skills_fn
    get_routing_data = routing_fn


def get_content() -> str:
    content = "═══ SYSTEM CONFIGURATION ═══\n\n"

    # Load all config data
    health = get_agent_health_data()
    skills = get_skills_data()
    routing = get_routing_data()
    menu_evo = _safe_json(".sisyphus/menu_evolution.json")
    ml_model = _safe_json(".sisyphus/ml_model.json")
    boulder = _safe_json(".sisyphus/boulder.json")
    session = _safe_json(".sisyphus/session-state.json")

    # Agent Health
    content += "▸ AGENT HEALTH\n"
    for name, data in health.items():
        status = data.get("status", "unknown")
        checks = data.get("total_checks", 0)
        success = data.get("total_successes", 0)
        fail = data.get("total_failures", 0)
        content += f"  {name:<18} {status:<10} {success}/{checks} ok, {fail} fail\n"
    content += "\n"

    # Agent Skills
    content += "▸ AGENT SKILLS\n"
    for name, data in skills.items():
        tasks = data.get("total_tasks", 0)
        success = data.get("success_count", 0)
        if tasks > 0:
            rate = (success / tasks) * 100
            content += f"  {name:<18} {success}/{tasks} ({rate:.0f}%)\n"
    content += "\n"

    # Routing
    content += "▸ ROUTING SYSTEM\n"
    triggers = routing.get("triggers", [])
    content += f"  Triggers: {len(triggers)}\n"
    weights = routing.get("weights", {})
    content += f"  Weights: {len(weights)} agents\n"
    for agent, w in list(weights.items())[:5]:
        sr = w.get("success_rate", 0) * 100
        tasks = w.get("total_tasks", 0)
        content += f"    {agent:<15} {sr:>5.1f}% | {tasks:>3} tasks\n"
    content += "\n"

    # Menu Evolution
    content += "▸ MENU EVOLUTION\n"
    if menu_evo and isinstance(menu_evo, list):
        for item in menu_evo[-5:]:
            t = item.get("timestamp", "")[:19]
            i = item.get("item_name", "?")
            e = item.get("event_type", "?")
            content += f"  [{e}] {i} @ {t}\n"
    content += "\n"

    # ML Model
    content += "▸ ML MODEL WEIGHTS\n"
    mw = ml_model.get("model_weights", {})
    for agent, weights in list(mw.items())[:4]:
        content += f"  {agent}: "
        kw = list(weights.keys())[:3]
        content += ", ".join(kw) + "...\n"
    content += "\n"

    # Active Plan (Boulder)
    content += "▸ ACTIVE PLAN\n"
    if boulder:
        content += f"  Plan: {boulder.get('plan_name', 'none')}\n"
        content += f"  Wave: {boulder.get('current_wave', 0)}/1\n"
        content += f"  Tasks: {boulder.get('tasks_completed', 0)}/{boulder.get('tasks_total', 0)}\n"
    content += "\n"

    # Session State
    content += "▸ CURRENT SESSION\n"
    if session:
        content += f"  Agent: {session.get('last_agent', 'N/A')}\n"
        content += f"  Task: {session.get('current_task', 'N/A')[:40]}...\n"
        started = session.get("session_started", "")[:10]
        content += f"  Started: {started}\n"
    content += "\n"

    return content
