"""Agents tab - agent configuration display."""

_safe_json = None


def init(safe_json):
    global _safe_json
    _safe_json = safe_json


def get_content() -> str:
    agents = _safe_json("opencode.json").get("agent", {})
    content = "AGENT CONFIGURATION (opencode.json)\n\n"
    if agents:
        content += f"{'Agent':<25} {'Model':<30} {'Edit':<10} {'Bash':<10}\n"
        content += "-" * 75 + "\n"
        for name, cfg in agents.items():
            model = cfg.get("model", "default")
            edit = cfg.get("permission", {}).get("edit", "inherit")
            bash = cfg.get("permission", {}).get("bash", {}).get("*", "inherit")
            content += f"{name:<25} {model:<30} {edit:<10} {bash:<10}\n"
    else:
        content += "  No agents configured in opencode.json"
    return content
