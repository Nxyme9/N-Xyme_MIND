"""
nx-mind-mcp
===========
MCP Tool Server for MIND state management and session continuity.
Manages project progress, active workflows, session history, and cross-session continuity.

Transport: stdio (default), SSE (optional via --sse flag).
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP
import sys
from pathlib import Path


def _setup_memory_path():
    """Add src to path for memory router."""
    # Derive project root from this file's location
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    src_path = project_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))


_setup_memory_path()

# ---------------------------------------------------------------------------
# Server Init
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="nx-mind",
    version="1.0.0",
    instructions=(
        "N-Xyme MIND MCP Server — manages MIND state across sessions.\n\n"
        "Tools:\n"
        "- get_mind_state: Current MIND state (project, phase, active tasks)\n"
        "- update_mind_state: Update MIND state with new information\n"
        "- get_session_history: History of past sessions with summaries\n"
        "- get_active_workflow: Currently active BMAD workflow and step\n"
        "- set_context: Set project context for current session\n"
        "- sync_to_memory: Sync MIND state to memory MCP\n"
        "- get_project_manifest: Project metadata and progress\n"
    ),
)

logger = logging.getLogger("nx-mind-mcp")

# ---------------------------------------------------------------------------
# Path Resolution
# ---------------------------------------------------------------------------

def get_project_root() -> Path:
    """Get N-Xyme_MIND project root."""
    if "NX_MIND_ROOT" in os.environ:
        return Path(os.environ["NX_MIND_ROOT"])
    # Derive from this file's location
    return Path(__file__).resolve().parent.parent.parent.parent


def get_mind_state_path() -> Path:
    """Get MIND state file path."""
    return get_project_root() / ".context" / "mind-state.json"


def get_manifest_path() -> Path:
    """Get project manifest path."""
    return get_project_root() / ".context" / "project-manifest.json"


def get_session_history_path() -> Path:
    """Get session history path."""
    return get_project_root() / ".context" / "session-history.json"


# ---------------------------------------------------------------------------
# State Management
# ---------------------------------------------------------------------------

DEFAULT_MIND_STATE = {
    "project": None,
    "phase": None,
    "active_tasks": [],
    "context": {},
    "last_updated": None,
    "session_start": None,
}

DEFAULT_MANIFEST = {
    "name": None,
    "description": None,
    "version": None,
    "progress": {},
    "milestones": [],
    "created": None,
    "last_updated": None,
}

DEFAULT_SESSION_HISTORY = {
    "sessions": [],
}


def load_json_file(path: Path, default: dict = None) -> dict:
    """Load JSON file with fallback to default."""
    if default is None:
        default = {}
    if not path.exists():
        return default
    try:
        content = path.read_text(encoding="utf-8")
        return json.loads(content) or default
    except Exception as e:
        logger.warning(f"Failed to load {path}: {e}")
        return default


def save_json_file(path: Path, data: dict) -> dict:
    """Save JSON file with directory creation."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        return {"success": True, "path": str(path)}
    except Exception as e:
        logger.error(f"Failed to save {path}: {e}")
        return {"success": False, "error": str(e)}


def load_mind_state() -> dict:
    """Load current MIND state."""
    return load_json_file(get_mind_state_path(), DEFAULT_MIND_STATE.copy())


def save_mind_state(state: dict) -> dict:
    """Save MIND state."""
    state["last_updated"] = datetime.now().isoformat()
    return save_json_file(get_mind_state_path(), state)


def load_manifest() -> dict:
    """Load project manifest."""
    return load_json_file(get_manifest_path(), DEFAULT_MANIFEST.copy())


def save_manifest(manifest: dict) -> dict:
    """Save project manifest."""
    manifest["last_updated"] = datetime.now().isoformat()
    return save_json_file(get_manifest_path(), manifest)


def load_session_history() -> dict:
    """Load session history."""
    return load_json_file(get_session_history_path(), DEFAULT_SESSION_HISTORY.copy())


def save_session_history(history: dict) -> dict:
    """Save session history."""
    return save_json_file(get_session_history_path(), history)


# ---------------------------------------------------------------------------
# TOOL: get_mind_state
# ---------------------------------------------------------------------------

@mcp.tool(tags={"read", "mind", "state"})
def get_mind_state() -> dict:
    """
    Returns current MIND state including project, phase, and active tasks.
    Reads from .context/mind-state.json.
    
    Returns:
        dict with project, phase, active_tasks, context, and timestamps
    """
    state = load_mind_state()
    state["tool"] = "get_mind_state"
    state["timestamp"] = datetime.now().isoformat()
    return state


# ---------------------------------------------------------------------------
# TOOL: update_mind_state
# ---------------------------------------------------------------------------

@mcp.tool(tags={"write", "mind", "state"})
def update_mind_state(
    project: Optional[str] = None,
    phase: Optional[str] = None,
    active_tasks: Optional[list] = None,
    context: Optional[dict] = None,
    clear_context: bool = False,
) -> dict:
    """
    Updates MIND state with new information.
    
    Args:
        project: Project name to set
        phase: Current phase (e.g., "1-analysis", "2-planning")
        active_tasks: List of active tasks
        context: Additional context key-value pairs
        clear_context: Whether to clear existing context
    
    Returns:
        dict with updated state and status
    """
    state = load_mind_state()
    
    # Update provided fields
    if project is not None:
        state["project"] = project
    if phase is not None:
        state["phase"] = phase
    if active_tasks is not None:
        state["active_tasks"] = active_tasks
    if context is not None:
        if clear_context:
            state["context"] = context
        else:
            state["context"] = {**state.get("context", {}), **context}
    
    # Ensure session_start is set
    if "session_start" not in state or state["session_start"] is None:
        state["session_start"] = datetime.now().isoformat()
    
    result = save_mind_state(state)
    result["tool"] = "update_mind_state"
    result["timestamp"] = datetime.now().isoformat()
    result["updated_state"] = {
        "project": state.get("project"),
        "phase": state.get("phase"),
        "active_tasks": state.get("active_tasks", [])[:5],  # Preview
    }
    return result


# ---------------------------------------------------------------------------
# TOOL: get_session_history
# ---------------------------------------------------------------------------

@mcp.tool(tags={"read", "history", "sessions"})
def get_session_history(limit: int = 10) -> dict:
    """
    Returns history of past sessions with summaries.
    
    Args:
        limit: Maximum number of sessions to return (default: 10)
    
    Returns:
        dict with session history list
    """
    history = load_session_history()
    sessions = history.get("sessions", [])
    
    # Sort by date descending and limit
    sessions = sorted(sessions, key=lambda s: s.get("date", ""), reverse=True)
    sessions = sessions[:limit]
    
    result = {
        "tool": "get_session_history",
        "sessions": sessions,
        "count": len(sessions),
        "total": len(history.get("sessions", [])),
        "timestamp": datetime.now().isoformat()
    }
    return result


# ---------------------------------------------------------------------------
# TOOL: get_active_workflow
# ---------------------------------------------------------------------------

@mcp.tool(tags={"read", "workflow", "bmad"})
def get_active_workflow() -> dict:
    """
    Returns currently active BMAD workflow and step.
    Scans _bmad/catalyst/ for active workflow files.
    
    Returns:
        dict with active workflow info, phase, and step
    """
    project_root = get_project_root()
    catalyst_dir = project_root / "_bmad" / "catalyst"
    
    result = {
        "tool": "get_active_workflow",
        "active": False,
        "workflow": None,
        "phase": None,
        "step": None,
        "timestamp": datetime.now().isoformat()
    }
    
    if not catalyst_dir.exists():
        result["error"] = f"Catalyst directory not found: {catalyst_dir}"
        return result
    
    try:
        # Look for active workflow files
        # Check for .active or similar marker
        active_marker = catalyst_dir / ".active"
        if active_marker.exists():
            try:
                active_info = json.loads(active_marker.read_text())
                result["active"] = True
                result["workflow"] = active_info.get("workflow")
                result["phase"] = active_info.get("phase")
                result["step"] = active_info.get("step")
                return result
            except Exception:
                pass
        
        # Alternative: scan for most recent workflow
        # Look for workflow directories
        workflow_files = []
        for ext in [".md", ".yaml", ".yml", ".json"]:
            workflow_files.extend(catalyst_dir.rglob(f"*{ext}"))
        
        if workflow_files:
            # Get most recently modified
            latest = max(workflow_files, key=lambda p: p.stat().st_mtime)
            result["workflow"] = latest.stem
            result["phase"] = latest.parent.name
            result["step"] = "current"
            result["active"] = True
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


# ---------------------------------------------------------------------------
# TOOL: set_context
# ---------------------------------------------------------------------------

@mcp.tool(tags={"write", "context", "session"})
def set_context(key: str, value: str) -> dict:
    """
    Sets project context for current session.
    
    Args:
        key: Context key (e.g., "task", "goal", "constraints")
        value: Context value
    
    Returns:
        dict with confirmation and current context
    """
    state = load_mind_state()
    
    if "context" not in state:
        state["context"] = {}
    
    state["context"][key] = value
    state["session_start"] = datetime.now().isoformat()
    
    result = save_mind_state(state)
    result["tool"] = "set_context"
    result["key"] = key
    result["value"] = value
    result["timestamp"] = datetime.now().isoformat()
    return result


# ---------------------------------------------------------------------------
# TOOL: sync_to_memory
# ---------------------------------------------------------------------------

@mcp.tool(tags={"write", "sync", "memory"})
def sync_to_memory(target: str = "memory") -> dict:
    """
    Syncs MIND state to memory MCP as entities/relations.
    Creates entities for project, phase, tasks in the memory knowledge graph.
    
    Note: This returns the data needed for memory MCP integration.
    The actual memory write would be done by the memory MCP server.
    
    Args:
        target: Target MCP name (default: "memory")
    
    Returns:
        dict with entities and relations ready for memory MCP
    """
    state = load_mind_state()
    manifest = load_manifest()
    
    # Build entities for memory MCP
    entities = []
    relations = []
    
    # Project entity
    if state.get("project"):
        entities.append({
            "entityType": "Project",
            "name": state["project"],
            "observations": [
                f"Current phase: {state.get('phase', 'unknown')}",
                f"Active tasks: {len(state.get('active_tasks', []))}",
                f"Last updated: {state.get('last_updated', 'unknown')}",
            ]
        })
    
    # Phase entity
    if state.get("phase"):
        entities.append({
            "entityType": "Phase",
            "name": state["phase"],
            "observations": [
                f"Project: {state.get('project', 'unknown')}",
                f"Active: {len(state.get('active_tasks', []))} tasks",
            ]
        })
        if state.get("project"):
            relations.append({
                "from": state["project"],
                "relationType": "has_phase",
                "to": state["phase"]
            })
    
    # Task entities
    for task in state.get("active_tasks", [])[:5]:
        task_name = task.get("name", str(task))
        entities.append({
            "entityType": "Task",
            "name": task_name,
            "observations": [
                f"Status: {task.get('status', 'pending')}",
                f"Phase: {state.get('phase', 'unknown')}",
            ]
        })
        if state.get("phase"):
            relations.append({
                "from": state["phase"],
                "relationType": "has_task",
                "to": task_name
            })
    
    result = {
        "tool": "sync_to_memory",
        "target": target,
        "entities": entities,
        "relations": relations,
        "entity_count": len(entities),
        "relation_count": len(relations),
        "timestamp": datetime.now().isoformat()
    }
    return result


# ---------------------------------------------------------------------------
# TOOL: get_project_manifest
# ---------------------------------------------------------------------------

@mcp.tool(tags={"read", "manifest", "project"})
def get_project_manifest() -> dict:
    """
    Returns project metadata and progress.
    Reads from .context/project-manifest.json.
    
    Returns:
        dict with project name, description, version, progress, milestones
    """
    manifest = load_manifest()
    manifest["tool"] = "get_project_manifest"
    manifest["timestamp"] = datetime.now().isoformat()
    return manifest


# ----------------------------------------------------------------------------
# TOOL: sync_memory (NEW)
# ----------------------------------------------------------------------------

@mcp.tool(tags={"write", "sync", "memory", "unified"})
def sync_memory() -> dict:
    """
    Sync current MIND state to unified memory system.
    
    Returns:
        dict with sync status and memory source results
    """
    try:
        from memory.router import get_router, get_unified_memory
        from memory.registry import get_enabled_connectors
        
        # Get current state
        state = load_mind_state()
        manifest = load_manifest()
        
        # Build query for current context
        project = state.get("project", "")
        phase = state.get("phase", "")
        tasks = state.get("active_tasks", [])
        
        query_text = f"{project} {phase} {' '.join([str(t) for t in tasks[:5]])}"
        
        # Search unified memory for related content
        result = get_unified_memory(query_text, max_results=5)
        
        return {
            "status": "ok",
            "tool": "sync_memory",
            "project": project,
            "phase": phase,
            "task_count": len(tasks),
            "unified_results": result.total_results,
            "sources_queried": result.sources_queried,
            "sources_failed": result.sources_failed,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "tool": "sync_memory",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# ----------------------------------------------------------------------------
# TOOL: get_memory_stats (NEW)
# ----------------------------------------------------------------------------

@mcp.tool(tags={"read", "memory", "stats"})
def get_memory_stats() -> dict:
    """
    Get memory system statistics from unified memory.
    
    Returns:
        dict with memory source stats and health
    """
    try:
        from memory.registry import get_enabled_connectors
        
        connectors = get_enabled_connectors()
        
        sources = []
        for conn in connectors:
            try:
                health = conn.health_check()
                sources.append({
                    "name": conn.name,
                    "enabled": True,
                    "status": str(health.status),
                    "message": health.message,
                })
            except Exception as e:
                sources.append({
                    "name": conn.name,
                    "enabled": True,
                    "status": "error",
                    "message": str(e),
                })
        
        return {
            "status": "ok",
            "tool": "get_memory_stats",
            "sources": sources,
            "total_sources": len(sources),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "tool": "get_memory_stats",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="N-Xyme MIND MCP Server")
    parser.add_argument("--sse", action="store_true", help="Use SSE transport")
    parser.add_argument("--port", type=int, default=8767, help="SSE port")
    args = parser.parse_args()
    
    if args.sse:
        mcp.run(transport="sse", port=args.port)
    else:
        mcp.run(transport="stdio")
