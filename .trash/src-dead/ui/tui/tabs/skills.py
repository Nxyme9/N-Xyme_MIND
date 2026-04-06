"""Skills tab - agent skills and performance display."""

from pathlib import Path

# Import from parent module
_safe_json = None
get_skills_data = None


def init(safe_json, skills_fn):
    global _safe_json, get_skills_data
    _safe_json = safe_json
    get_skills_data = skills_fn


def get_content() -> str:
    skills = get_skills_data()
    if not skills:
        return "No skills data available"

    content = "AGENT SKILLS & PERFORMANCE\n\n"
    for agent_name, data in skills.items():
        agent_skills = data.get("skills", {})
        tasks = data.get("total_tasks", 0)
        success = data.get("success_count", 0)
        rate = (success / tasks * 100) if tasks > 0 else 0
        content += f"{agent_name} ({success}/{tasks} = {rate:.0f}%)\n"
        for skill, score in list(agent_skills.items())[:3]:
            content += f"  {skill}: {score:.2f}\n"
        content += "\n"
    return content
