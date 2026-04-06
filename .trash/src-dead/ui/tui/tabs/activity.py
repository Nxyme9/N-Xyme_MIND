"""Activity tab - live activity feed."""

import time

# Import from parent module
get_routing_data = None


def init(routing_fn):
    global get_routing_data
    get_routing_data = routing_fn


def _get_timestamp() -> str:
    """Get current timestamp for activity feed."""
    return time.strftime("%H:%M:%S")


def get_content(live_data: dict) -> str:
    content = "═══ LIVE ACTIVITY FEED ═══\n\n"

    # Get live data
    d = live_data
    daemon_running = d.get("daemon_running", False)
    ollama_running = d.get("ollama_running", False)

    # Show current status events
    content += "▸ RECENT EVENTS\n"
    content += f"  {_get_timestamp()} [System] Dashboard started\n"

    if daemon_running:
        content += f"  {_get_timestamp()} [Daemon] Memory daemon running\n"
    else:
        content += f"  {_get_timestamp()} [Daemon] Memory daemon stopped\n"

    if ollama_running:
        content += f"  {_get_timestamp()} [Ollama] Local models available\n"
    else:
        content += f"  {_get_timestamp()} [Ollama] Local models unavailable\n"

    # Show routing events
    content += "\n▸ ROUTING EVENTS\n"

    # Get routing data
    routing = get_routing_data()
    triggers = routing.get("triggers", [])
    weights = routing.get("weights", {})

    content += f"  Triggers: {len(triggers)} configured\n"
    content += f"  Agents: {len(weights)} weighted\n"

    # Show recent task completions
    content += "\n▸ TASK METRICS\n"
    content += f"  Total outcomes: {d.get('outcomes', 0)}\n"
    content += f"  Learning events: {d.get('learning_feedback', 0)}\n"
    content += f"  Indexed files: {d.get('indexed_files', 0)}\n"

    content += "\n▸ LIVE INDICATORS\n"
    last_updated = d.get("last_updated", 0)
    if last_updated > 0:
        age = time.time() - last_updated
        if age < 10:
            status = "🟢 Live"
        elif age < 30:
            status = "🟡 Stale"
        else:
            status = "🔴 Offline"
        content += f"  Data stream: {status}\n"

    content += "\n▸ KEYBOARD SHORTCUTS\n"
    content += "  K: Knowledge  L: Costs  M: Activity  R: Refresh\n"

    return content
