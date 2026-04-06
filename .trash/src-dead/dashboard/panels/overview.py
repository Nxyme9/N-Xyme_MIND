# Overview Panel
"""System overview panel content generator."""

from typing import Any, Dict


def get_content(dashboard: Any) -> str:
    """Get overview panel content.

    Args:
        dashboard: Dashboard instance with live_data attribute

    Returns:
        Panel content string
    """
    d = dashboard.live_data
    mc = d.get("module_counts", {})

    return f"""N-Xyme MIND ECOSYSTEM OVERVIEW

Total Modules: {d.get("total_modules", 439)} across 20 subsystems

Core Services
  Daemon: {"Running" if d.get("daemon", {}).get("running") else "Stopped"} | PID: {d.get("daemon", {}).get("pid", "N/A")}
  Ollama: {"Running" if d.get("ollama", {}).get("running") else "Stopped"} | Models: {len(d.get("ollama_models", []))}
  {", ".join(d.get("ollama_models", [])[:8]) if d.get("ollama_models") else "  (none detected)"}

Memory System ({mc.get("memory", 58)} modules)
  Sources: {d.get("memory", {}).get("total_sources", 0)} | Enabled: {d.get("memory", {}).get("enabled_count", 0)}
  Files: {d.get("indexed", {}).get("total_files", 0)} | Chunks: {d.get("indexed", {}).get("total_chunks", 0)}
  Knowledge Graph: {d.get("kg_entities", 0)} entities, {d.get("kg_relationships", 0)} relationships

Intelligence ({mc.get("intelligence", 36)} modules)
  Feedback: {d.get("learning", {}).get("feedback", 0)} events | Queries: {d.get("learning", {}).get("queries", 0)}
  Tools: {d.get("tool_count", 0)} registered

Orchestration ({mc.get("orchestration", 13)} modules)
  Agents: {d.get("orchestration", {}).get("agents", 0)} | {", ".join(d.get("orchestration", {}).get("agent_list", [])[:5])}

Proxy/VPN ({mc.get("proxy", 21)} modules)
  API Keys: {d.get("api_key_total", 0)} | VPN IPs: {d.get("vpn_pool", {}).get("available_ips", 0)}/{d.get("vpn_pool", {}).get("total_ips", 0)}
  Router: {d.get("intelligent_router", {}).get("total_requests", 0)} requests | Cache: {d.get("lru_cache", {}).get("hits", 0)} hits

Brain ({mc.get("brain", 9)} modules) | Learning ({mc.get("learning", 8)} modules)
Security ({mc.get("security", 9)} modules) | Model Router ({mc.get("model_router", 10)} modules)
Workers ({mc.get("workers", 3)} modules) | Blocks ({mc.get("blocks", 12)} modules)

Data Freshness
  Last updated: {dashboard.data_age}s ago | {"🟢 Live" if dashboard.data_age < 10 else "🟡 Stale" if dashboard.data_age < 30 else "🔴 Old"}
  Refreshes: {len(dashboard._refresh_times)} in last 10min

Last Update: {d.get("timestamp", "N/A")[:19]}"""
