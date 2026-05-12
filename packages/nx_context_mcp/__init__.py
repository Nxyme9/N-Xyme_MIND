#!/usr/bin/env python3
"""nx-context-mcp - Context injection MCP server for opencode.

Exposes the memory bank context tools (activeContext, productContext,
userContext, constraints, bmad agents/workflows, style, archive)
as MCP tools via FastMCP.

Tools exposed:
- get_active_context: Current active context from memory bank
- get_product_context: Product identity/soul from memory bank
- get_user_context: User preferences from memory bank
- get_constraints: Behavioral constraints from memory bank
- get_user_profile: Immutable user profile from memory bank
- get_style_context: Personalized style context from usage learning
- get_archive_context: Relevant context from past session archives
- get_bmad_agents: List available BMAD agents
- get_bmad_workflows: List BMAD workflows by phase
- health_check: Lightweight health check
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Optional

from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Path Setup
# ---------------------------------------------------------------------------

def _setup_paths():
    """Add project root to path."""
    project_root = Path(__file__).resolve().parent.parent.parent
    packages_root = project_root / "packages"
    if str(packages_root) not in sys.path:
        sys.path.insert(0, str(packages_root))
    return project_root

PROJECT_ROOT = _setup_paths()
logger = logging.getLogger("nx-context-mcp")

# ---------------------------------------------------------------------------
# Server Init
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="nx-context",
    version="1.0.0",
    instructions=(
        "N-Xyme Context MCP Server — context injection tools for opencode agent.\n\n"
        "Tools:\n"
        "- get_active_context: Get current active context from memory bank\n"
        "- get_product_context: Get product identity/soul from memory bank\n"
        "- get_user_context: Get user preferences from memory bank\n"
        "- get_constraints: Get behavioral constraints from memory bank\n"
        "- get_user_profile: Get immutable user profile\n"
        "- get_style_context: Get personalized style context from usage learning\n"
        "- get_archive_context: Get relevant context from past session archives\n"
        "- get_bmad_agents: List available BMAD agents\n"
        "- get_bmad_workflows: List BMAD workflows by phase\n"
        "- health_check: Lightweight health check\n"
    ),
)

# ---------------------------------------------------------------------------
# Memory Bank File Paths
# ---------------------------------------------------------------------------

def _context_path(filename: str) -> Path:
    """Get path to memory bank file."""
    return PROJECT_ROOT / ".context" / filename


def _read_md_file(path: Path) -> tuple[str, dict[str, Any]]:
    """Read a markdown file with frontmatter. Returns (content, frontmatter)."""
    import yaml
    try:
        raw = path.read_text()
        if raw.startswith("---"):
            parts = raw.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1]) or {}
                return parts[2].strip(), frontmatter
        return raw.strip(), {}
    except Exception as e:
        return f"Error reading {path}: {e}", {}


def _read_json_file(path: Path) -> dict[str, Any]:
    """Read a JSON file."""
    import json
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _read_md_content(filename: str) -> dict[str, Any]:
    """Read a memory bank markdown file."""
    path = _context_path(filename)
    content, fm = _read_md_file(path)
    return {"content": content, "frontmatter": fm, "path": str(path)}


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_active_context() -> dict[str, Any]:
    """Returns current active context from memory bank.
    
    Reads activeContext.md which contains the current session/project state.
    Automatically updates timestamp on each access to prevent stale context.
    
    Returns:
        dict with content, frontmatter, and metadata
    """
    try:
        return _read_md_content("activeContext.md")
    except Exception as e:
        return {"error": str(e), "content": "", "frontmatter": {}}


@mcp.tool()
def get_product_context() -> dict[str, Any]:
    """Returns product context (identity/soul) from memory bank.
    
    Reads productContext.md which defines the agent's identity.
    
    Returns:
        dict with identity content and metadata
    """
    try:
        return _read_md_content("productContext.md")
    except Exception as e:
        return {"error": str(e), "content": "", "frontmatter": {}}


@mcp.tool()
def get_user_context() -> dict[str, Any]:
    """Returns user context from memory bank.
    
    Reads userContext.md which contains user preferences and context.
    
    Returns:
        dict with user context and metadata
    """
    try:
        return _read_md_content("userContext.md")
    except Exception as e:
        return {"error": str(e), "content": "", "frontmatter": {}}


@mcp.tool()
def get_constraints() -> dict[str, Any]:
    """Returns behavioral constraints from memory bank.
    
    Reads constraints.md which defines limits and rules.
    
    Returns:
        dict with constraints content and metadata
    """
    try:
        return _read_md_content("constraints.md")
    except Exception as e:
        return {"error": str(e), "content": "", "frontmatter": {}}


@mcp.tool()
def get_user_profile() -> dict[str, Any]:
    """Returns immutable user profile from memory bank.
    
    Reads user_profile.md which contains full identity, psychological profile,
    timeline, and immutable instructions.
    
    Returns:
        dict with user profile content and metadata
    """
    try:
        return _read_md_content("user_profile.md")
    except Exception as e:
        return {"error": str(e), "content": "", "frontmatter": {}}


@mcp.tool()
def get_style_context() -> dict[str, Any]:
    """Returns personalized style context from usage pattern learning.
    
    Reads from style_learner.py to get user preferences, communication style,
    and behavioral patterns.
    
    Returns:
        dict with personalized style context
    """
    try:
        from style_learner import StyleLearner
        
        learner = StyleLearner(project_root=PROJECT_ROOT)
        prefs = learner.get_preferences()
        return {"status": "success", "preferences": prefs}
    except ImportError:
        return {"status": "unavailable", "message": "style_learner not available"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_archive_context(query: str = "", max_sessions: int = 3) -> dict[str, Any]:
    """Returns relevant context from past session archives.
    
    Uses archive_scanner.py to find related sessions and build context.
    
    Args:
        query: Current task/question to find related sessions
        max_sessions: Maximum number of sessions to include (default 3)
    
    Returns:
        dict with relevant archive context
    """
    try:
        from archive_scanner import ArchiveScanner
        
        scanner = ArchiveScanner(project_root=PROJECT_ROOT)
        results = scanner.find_related(query, max_sessions=max_sessions)
        return {"status": "success", "sessions": results, "query": query}
    except ImportError:
        return {"status": "unavailable", "message": "archive_scanner not available"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_bmad_agents() -> dict[str, Any]:
    """Lists available BMAD agents from _bmad/_config/agents/.
    
    Returns:
        dict with list of agents and metadata
    """
    try:
        agents_dir = PROJECT_ROOT / "_bmad" / "_config" / "agents"
        if not agents_dir.exists():
            return {"status": "unavailable", "agents": [], "message": "No agents directory"}

        agents = []
        for f in agents_dir.glob("*.md"):
            name = f.stem
            try:
                content = f.read_text()
                # Extract first line as description
                first_line = content.strip().split("\n")[0] if content.strip() else ""
                agents.append({"name": name, "description": first_line})
            except Exception:
                agents.append({"name": name, "description": ""})

        return {"status": "success", "agents": agents, "count": len(agents)}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_bmad_workflows(phase: Optional[str] = None) -> dict[str, Any]:
    """Lists BMAD workflows by phase from _bmad/bmm/workflows/.
    
    Args:
        phase: Optional phase filter (e.g., "1-analysis", "2-plan-workflows")
    
    Returns:
        dict with workflows grouped by phase
    """
    try:
        workflows_dir = PROJECT_ROOT / "_bmad" / "bmm" / "workflows"
        if not workflows_dir.exists():
            return {"status": "unavailable", "workflows": {}, "message": "No workflows directory"}

        workflows: dict[str, list] = {}
        for f in workflows_dir.glob("**/*.md"):
            phase_name = f.parent.name if f.parent != workflows_dir else "general"
            if phase and phase_name != phase:
                continue
            if phase_name not in workflows:
                workflows[phase_name] = []
            workflows[phase_name].append({"name": f.stem, "path": str(f.relative_to(PROJECT_ROOT))})

        return {"status": "success", "workflows": workflows, "total": sum(len(v) for v in workflows.values())}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def health_check() -> dict[str, Any]:
    """Lightweight health check - fast response for monitoring.
    
    Returns status without loading heavy dependencies.
    
    Returns:
        dict with health status
    """
    try:
        # Check memory bank files exist
        context_dir = PROJECT_ROOT / ".context"
        files = ["activeContext.md", "productContext.md", "userContext.md", "constraints.md"]
        existing = [f for f in files if (context_dir / f).exists()]
        
        # Check bmad config
        bmad_agents = (PROJECT_ROOT / "_bmad" / "_config" / "agents").exists()
        bmad_workflows = (PROJECT_ROOT / "_bmad" / "bmm" / "workflows").exists()
        
        healthy = len(existing) >= 2  # At least 2 of 4 core files exist
        
        return {
            "status": "ok" if healthy else "degraded",
            "memory_bank_files": len(existing),
            "bmad_configured": bmad_agents and bmad_workflows,
            "healthy": healthy,
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "healthy": False}


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    "mcp",
    "get_active_context",
    "get_product_context",
    "get_user_context",
    "get_constraints",
    "get_user_profile",
    "get_style_context",
    "get_archive_context",
    "get_bmad_agents",
    "get_bmad_workflows",
    "health_check",
]


if __name__ == "__main__":
    mcp.run()