"""Overview tab - system overview with real-time data."""

from pathlib import Path

# Import from parent module (dashboard will inject these)
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


def get_content(live_data: dict) -> str:
    health = get_agent_health_data()
    skills = get_skills_data()
    routing = get_routing_data()

    healthy_agents = sum(1 for a in health.values() if a.get("status") == "healthy")
    total_agents = len(health)

    session_state = _safe_json(".sisyphus/session-state.json")

    daemon_ok = live_data.get("daemon_running", False)
    daemon_pid = live_data.get("daemon_pid", "N/A")
    ollama_ok = live_data.get("ollama_running", False)

    return f"""SYSTEM OVERVIEW

        Core Services
  Daemon: {"Running" if daemon_ok else "Stopped"} | PID: {daemon_pid}
  Ollama: {"Running" if ollama_ok else "Stopped"} | http://localhost:11434

  Data Index
  Files: {live_data.get("indexed_files", 0)} | Chunks: {live_data.get("indexed_chunks", 0)}

  System Components
  Memory: {live_data.get("memory_sources", 0)} sources | {live_data.get("memory_enabled", 0)} enabled
  Router: {live_data.get("router_backends", 0)} backends
  Agents: {total_agents} ({healthy_agents} healthy)
  QT|  Sessions: {session_state.get("session_started", "N/A")[:10]}
  Outcomes: {live_data.get("outcomes", 0)}

  TZ|  Triggers: {len(routing.get("triggers", []))}
  ZN|  Weights: {len(routing.get("weights", {}))} configured

  Agent Skills
  Hephaestus: {skills.get("hephaestus", {}).get("success_count", 0)}/{skills.get("hephaestus", {}).get("total_tasks", 0)} tasks
  Explore: {skills.get("explore", {}).get("success_count", 0)}/{skills.get("explore", {}).get("total_tasks", 0)} tasks
  
  Learning: {live_data.get("learning_feedback", 0)} feedback | {live_data.get("learning_queries", 0)} queries

  Last Update: {live_data.get("timestamp", "N/A")[:19]}"""
