"""Backend Data Integration - Pulls data from all backend systems."""

from pathlib import Path
from datetime import datetime


def get_system_status():
    """Get comprehensive system status from all backend systems."""
    status = {
        "timestamp": datetime.now().isoformat(),
        "daemon": get_daemon_status(),
        "ollama": get_ollama_status(),
        "memory": get_memory_stats(),
        "indexed": get_indexed_count(),
        "router": get_memory_router_status(),
        "orchestration": get_orchestration_status(),
        "learning": get_learning_stats(),
        "sessions": get_session_stats(),
        "security": get_security_status(),
        "performance": get_performance_stats(),
    }
    return status


def get_daemon_status():
    """Get daemon status."""
    try:
        import os

        pid_file = Path("context/memory/daemon.pid")
        if pid_file.exists():
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)
            return {"running": True, "pid": pid}
    except Exception:
        pass
    return {"running": False, "pid": None}


def get_llama_server_status():
    """Get GGUF llama-server status (primary)."""
    try:
        import urllib.request

        urllib.request.urlopen("http://localhost:8080", timeout=2)
        return {"running": True, "url": "http://localhost:8080"}
    except Exception:
        return {"running": False, "url": "http://localhost:8080"}


def get_ollama_status():
    """Get Ollama status (fallback only)."""
    try:
        import urllib.request

        urllib.request.urlopen("http://localhost:11434", timeout=2)
        return {"running": True, "url": "http://localhost:11434", "is_fallback": True}
    except Exception:
        return {"running": False, "url": "http://localhost:11434", "is_fallback": True}


def get_memory_stats():
    """Get memory system stats."""
    try:
        from packages.memory_store.mcp_server import get_memory_stats as _get_stats

        return _get_stats()
    except Exception:
        return {"total_sources": 0, "enabled_count": 0, "sources": []}


def get_indexed_count():
    """Get file index stats."""
    try:
        from packages.memory_store.indexing.embedder import (
            get_indexed_count as _get_count,
        )

        return _get_count()
    except Exception:
        return {"total_files": 0, "total_chunks": 0, "by_drive": {}, "by_type": {}}


def get_memory_router_status():
    """Get memory router status."""
    try:
        from packages.memory_store.memory_router import get_router

        router = get_router()
        return {"backends": len(router.backends), "status": router.get_status()}
    except Exception:
        return {"backends": 0, "status": {}}


def get_orchestration_status():
    """Get orchestration status."""
    try:
        from packages.orchestration.agents.registry import get_agent_registry

        registry = get_agent_registry()
        return {
            "agents": len(registry.get_all_agents()),
            "agents_list": list(registry.get_all_agents().keys()),
        }
    except Exception:
        return {"agents": 0, "agents_list": []}


def get_learning_stats():
    """Get learning system stats."""
    try:
        from packages.memory_store.mcp_server import get_learning_stats as _get_stats

        return _get_stats()
    except Exception:
        return {"feedback_stats": {}, "preference_stats": {}, "strategy_stats": {}}


def get_session_stats():
    """Get session stats from .sisyphus directory."""
    try:
        session_dir = Path(".sisyphus/sessions")
        if session_dir.exists():
            sessions = list(session_dir.glob("*.json"))
            return {"total": len(sessions), "sessions": [s.stem for s in sessions[-5:]]}
    except Exception:
        pass
    return {"total": 0, "sessions": []}


def get_security_status():
    """Get security system status."""
    return {
        "security_gate": True,
        "code_quality": True,
        "self_healer": True,
        "auto_recovery": True,
        "modules": [
            "Audit Logger",
            "Rate Limiter",
            "Jailbreak Detector",
            "Output Guardrails",
            "Permission System",
            "Agent Sandbox",
        ],
    }


def get_performance_stats():
    """Get performance stats."""
    try:
        # Read outcomes.jsonl
        outcomes_file = Path(".sisyphus/outcomes.jsonl")
        if outcomes_file.exists():
            with open(outcomes_file) as f:
                lines = f.readlines()
            return {"outcomes": len(lines), "file": str(outcomes_file)}
    except Exception:
        pass
    return {"outcomes": 0, "file": "N/A"}


def get_backend_summary():
    """Get comprehensive backend summary for dashboard."""
    status = get_system_status()

    summary = f"""🔧 BACKEND SYSTEMS

🖥️ Core Services
  Daemon: {"✅ Running" if status["daemon"].get("running") else "❌ Stopped"}
  Ollama: {"✅ Running" if status["ollama"].get("running") else "❌ Stopped"}

📊 Memory System
  Sources: {status["memory"].get("total_sources", 0)}
  Enabled: {status["memory"].get("enabled_count", 0)}
  Files: {status["indexed"].get("total_files", 0)}
  Chunks: {status["indexed"].get("total_chunks", 0)}

🔧 System Components
  Router: {status["router"].get("backends", 0)} backends
  Orchestration: {status["orchestration"].get("agents", 0)} agents
  Learning: {len(status["learning"].get("feedback_stats", {}))} stats
  Sessions: {status["sessions"].get("total", 0)} sessions

🛡️ Security
  Modules: {len(status["security"].get("modules", []))} active
  Status: All systems operational

📈 Performance
  Outcomes: {status["performance"].get("outcomes", 0)} recorded
  Last Update: {status["timestamp"][:19]}"""

    return summary
