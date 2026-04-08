"""
athena-context-mcp
==================
MCP Tool Server for context injection from Athena memory bank.
Provides access to active context, product context, user context, constraints,
BMAD agents, and workflows for OpenCode sessions.

Transport: stdio (default), SSE (optional via --sse flag).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from datetime import datetime

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
    name="athena-context",
    version="1.0.0",
    instructions=(
        "Athena Context MCP Server — inject context from Athena memory bank.\n\n"
        "Tools:\n"
        "- get_active_context: Current active context\n"
        "- get_product_context: Product/identity context (soul)\n"
        "- get_user_context: User context\n"
        "- get_constraints: Behavioral constraints\n"
        "- get_user_profile: Immutable user identity (210 lines)\n"
        "- get_style_context: Personalized style from usage patterns\n"
        "- get_archive_context: Relevant past session context\n"
        "- get_bmad_agents: List available BMAD agents\n"
        "- get_bmad_workflows: List BMAD workflows by phase\n"
        "- inject_context: Write context for prompt injection\n"
        "- search_unified: Semantic search across memory\n"
        "- query_unified_memory: Cross-source memory search\n"
    ),
)

logger = logging.getLogger("athena-context-mcp")

# ---------------------------------------------------------------------------
# Path Resolution
# ---------------------------------------------------------------------------

def get_project_root() -> Path:
    """Get N-Xyme_MIND project root."""
    if "ATHENA_CONTEXT_ROOT" in os.environ:
        return Path(os.environ["ATHENA_CONTEXT_ROOT"])
    # Derive from this file's location
    return Path(__file__).resolve().parent.parent.parent.parent


def get_athena_yaml_path() -> Path:
    """Get athena.yaml path."""
    return get_project_root() / "athena" / "athena.yaml"


def load_athena_config() -> dict:
    """Load and parse athena.yaml for path configuration."""
    yaml_path = get_athena_yaml_path()
    if not yaml_path.exists():
        logger.warning(f"athena.yaml not found at {yaml_path}")
        return {}
    
    import yaml
    with open(yaml_path, "r") as f:
        return yaml.safe_load(f) or {}


def get_memory_bank_path() -> Path:
    """Get memory bank path from athena.yaml identity config."""
    config = load_athena_config()
    identity = config.get("identity", {})
    
    # Default to .context/memory_bank relative to project root
    if identity:
        # Check if active_context points to a specific location
        active_context = identity.get("active_context", "")
        if active_context:
            # Extract directory from the path
            return Path(active_context).parent
    
    # Default fallback
    return get_project_root() / ".context" / "memory_bank"


# ---------------------------------------------------------------------------
# Context Reading Tools
# ---------------------------------------------------------------------------

def read_memory_bank_file(filename: str) -> dict:
    """Read a memory bank file and return structured content."""
    memory_bank = get_memory_bank_path()
    file_path = memory_bank / filename
    
    result = {
        "file": str(file_path),
        "exists": file_path.exists(),
        "content": "",
        "error": None
    }
    
    if not file_path.exists():
        result["error"] = f"File not found: {file_path}"
        return result
    
    try:
        content = file_path.read_text(encoding="utf-8")
        
        # Parse frontmatter if present
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1].strip()
                body = parts[2].strip()
                
                # Parse frontmatter as YAML
                try:
                    import yaml
                    fm = yaml.safe_load(frontmatter) or {}
                    result["frontmatter"] = fm
                except Exception:
                    pass
                
                result["content"] = body
                result["raw"] = content
            else:
                result["content"] = content
        else:
            result["content"] = content
            
    except Exception as e:
        result["error"] = str(e)
    
    return result


# ---------------------------------------------------------------------------
# TOOL: query_unified_memory (NEW)
# ----------------------------------------------------------------------------

@mcp.tool(tags={"read", "memory", "search", "unified"})
def query_unified_memory(
    query: str,
    limit: int = 10,
) -> dict:
    """
    Query the unified memory router for cross-source memory search.
    
    Args:
        query: The search query string
        limit: Maximum number of results to return (default 10)
    
    Returns:
        dict with unified search results from all memory sources
    """
    try:
        from memory.router import get_router, UnifiedMemoryQuery
        
        router = get_router()
        um_query = UnifiedMemoryQuery(
            query=query,
            max_results_per_source=limit,
        )
        
        result = router.search(um_query)
        
        return {
            "status": "ok",
            "tool": "query_unified_memory",
            "query": query,
            "results": [
                {
                    "content": r.content[:500],
                    "source": r.source,
                    "score": r.score,
                }
                for r in result.results[:limit]
            ],
            "sources_queried": result.sources_queried,
            "total_results": result.total_results,
            "query_time_ms": round(result.query_time_ms, 2),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "tool": "query_unified_memory",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# ----------------------------------------------------------------------------
# TOOL: search_unified (NEW)
# ----------------------------------------------------------------------------

@mcp.tool(tags={"read", "memory", "semantic"})
def search_unified(
    query: str,
    context_type: str = "all",
) -> dict:
    """
    Semantic search using unified memory with context filtering.
    
    Args:
        query: The search query
        context_type: Type of context ("all", "semantic", "episodic", "session")
    
    Returns:
        dict with semantic search results
    """
    try:
        from memory.router import get_router
        
        router = get_router()
        
        # Enable semantic search
        router.set_semantic_enabled(True)
        results = router.semantic_search(query, top_k=5)
        
        return {
            "status": "ok",
            "tool": "search_unified",
            "query": query,
            "context_type": context_type,
            "results": results,
            "count": len(results),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "tool": "search_unified",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# ----------------------------------------------------------------------------
# TOOL: query_sources (NEW)
# ----------------------------------------------------------------------------

@mcp.tool(tags={"read", "memory", "sources"})
def query_sources() -> dict:
    """
    Get list of available memory sources and their status.
    
    Returns:
        dict with memory source information
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
                })
            except:
                sources.append({
                    "name": conn.name,
                    "enabled": True,
                    "status": "unknown",
                })
        
        return {
            "status": "ok",
            "tool": "query_sources",
            "sources": sources,
            "count": len(sources),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "tool": "query_sources",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# ---------------------------------------------------------------------------
# TOOL: get_active_context
# ---------------------------------------------------------------------------

@mcp.tool(tags={"read", "context", "memory"})
def get_active_context() -> dict:
    """
    Returns current active context from memory bank.
    Reads activeContext.md which contains the current session/project state.
    
    Returns:
        dict with content, frontmatter, and metadata
    """
    result = read_memory_bank_file("activeContext.md")
    result["tool"] = "get_active_context"
    result["timestamp"] = datetime.now().isoformat()
    return result


# ---------------------------------------------------------------------------
# TOOL: get_product_context
# ---------------------------------------------------------------------------

@mcp.tool(tags={"read", "context", "identity"})
def get_product_context() -> dict:
    """
    Returns product context (identity/soul) from memory bank.
    Reads productContext.md which defines the agent's identity.
    
    Returns:
        dict with identity content and metadata
    """
    result = read_memory_bank_file("productContext.md")
    result["tool"] = "get_product_context"
    result["timestamp"] = datetime.now().isoformat()
    return result


# ---------------------------------------------------------------------------
# TOOL: get_user_context
# ---------------------------------------------------------------------------

@mcp.tool(tags={"read", "context", "user"})
def get_user_context() -> dict:
    """
    Returns user context from memory bank.
    Reads userContext.md which contains user preferences and context.
    
    Returns:
        dict with user context and metadata
    """
    result = read_memory_bank_file("userContext.md")
    result["tool"] = "get_user_context"
    result["timestamp"] = datetime.now().isoformat()
    return result


# ---------------------------------------------------------------------------
# TOOL: get_constraints
# ---------------------------------------------------------------------------

@mcp.tool(tags={"read", "context", "constraints"})
def get_constraints() -> dict:
    """
    Returns behavioral constraints from memory bank.
    Reads constraints.md which defines limits and rules.
    
    Returns:
        dict with constraints content and metadata
    """
    result = read_memory_bank_file("constraints.md")
    result["tool"] = "get_constraints"
    result["timestamp"] = datetime.now().isoformat()
    return result


# ---------------------------------------------------------------------------
# TOOL: get_user_profile (NEW)
# ---------------------------------------------------------------------------

@mcp.tool(tags={"read", "context", "user", "profile"})
def get_user_profile() -> dict:
    """
    Returns immutable user profile from memory bank.
    Reads user_profile.md which contains full identity, psychological profile,
    timeline, and immutable instructions.
    
    Returns:
        dict with user profile content and metadata
    """
    result = read_memory_bank_file("user_profile.md")
    result["tool"] = "get_user_profile"
    result["timestamp"] = datetime.now().isoformat()
    return result


# ---------------------------------------------------------------------------
# TOOL: get_style_context (NEW)
# ---------------------------------------------------------------------------

@mcp.tool(tags={"read", "context", "style", "personalization"})
def get_style_context() -> dict:
    """
    Returns personalized style context from usage pattern learning.
    Reads from style_learner.py to get user preferences, communication style,
    and behavioral patterns.
    
    Returns:
        dict with personalized style context
    """
    try:
        from athena_context_mcp.style_learner import get_learner
        learner = get_learner()
        style = learner.get_style_context()
        
        return {
            "tool": "get_style_context",
            "exists": True,
            "content": style,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "tool": "get_style_context",
            "exists": False,
            "content": "",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# ---------------------------------------------------------------------------
# TOOL: get_archive_context (NEW)
# ---------------------------------------------------------------------------

@mcp.tool(tags={"read", "context", "archive", "history"})
def get_archive_context(
    query: str = "",
    max_sessions: int = 3
) -> dict:
    """
    Returns relevant context from past session archives.
    Uses archive_scanner.py to find related sessions and build context.
    
    Args:
        query: Current task/question to find related sessions
        max_sessions: Maximum number of sessions to include (default 3)
    
    Returns:
        dict with relevant archive context
    """
    try:
        from athena_context_mcp.archive_scanner import get_scanner
        
        scanner = get_scanner()
        
        if not query:
            # No query - just get recent sessions
            result = scanner.scan_archives(limit=max_sessions)
            return {
                "tool": "get_archive_context",
                "query": query,
                "content": f"Recent sessions: {result.get('sessions', [])}",
                "sessions_found": result.get("total", 0),
                "timestamp": datetime.now().isoformat()
            }
        
        # Build context from related sessions
        summary = scanner.build_context_summary(
            queries=[query],
            max_sessions_per_query=max_sessions
        )
        
        return {
            "tool": "get_archive_context",
            "query": query,
            "content": summary.get("combined_summary", ""),
            "sessions_found": summary.get("total_sessions", 0),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "tool": "get_archive_context",
            "query": query,
            "content": "",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# ---------------------------------------------------------------------------
# TOOL: get_bmad_agents
# ---------------------------------------------------------------------------

@mcp.tool(tags={"read", "bmad", "agents"})
def get_bmad_agents() -> dict:
    """
    Lists available BMAD agents from _bmad/_config/agents/.
    
    Returns:
        dict with list of agents and metadata
    """
    project_root = get_project_root()
    agents_dir = project_root / "_bmad" / "_config" / "agents"
    
    result = {
        "tool": "get_bmad_agents",
        "directory": str(agents_dir),
        "exists": agents_dir.exists(),
        "agents": [],
        "timestamp": datetime.now().isoformat()
    }
    
    if not agents_dir.exists():
        result["error"] = f"Agents directory not found: {agents_dir}"
        return result
    
    try:
        # List all agent files/directories
        for item in sorted(agents_dir.iterdir()):
            if item.is_file() and item.suffix in [".md", ".yaml", ".yml", ".json"]:
                agent_info = {
                    "name": item.stem,
                    "path": str(item),
                    "type": item.suffix[1:]
                }
                # Read content for brief description
                try:
                    content = item.read_text(encoding="utf-8")
                    # Extract first 200 chars as preview
                    agent_info["preview"] = content[:200].strip()
                except Exception:
                    pass
                result["agents"].append(agent_info)
            elif item.is_dir():
                agent_info = {
                    "name": item.name,
                    "path": str(item),
                    "type": "directory"
                }
                result["agents"].append(agent_info)
    except Exception as e:
        result["error"] = str(e)
    
    result["count"] = len(result["agents"])
    return result


# ---------------------------------------------------------------------------
# TOOL: get_bmad_workflows
# ---------------------------------------------------------------------------

@mcp.tool(tags={"read", "bmad", "workflows"})
def get_bmad_workflows(phase: str = None) -> dict:
    """
    Lists BMAD workflows by phase from _bmad/bmm/workflows/.
    
    Args:
        phase: Optional phase filter (e.g., "1-analysis", "2-plan-workflows")
    
    Returns:
        dict with workflows grouped by phase
    """
    project_root = get_project_root()
    workflows_dir = project_root / "_bmad" / "bmm" / "workflows"
    
    result = {
        "tool": "get_bmad_workflows",
        "directory": str(workflows_dir),
        "exists": workflows_dir.exists(),
        "workflows": {},
        "timestamp": datetime.now().isoformat()
    }
    
    if not workflows_dir.exists():
        result["error"] = f"Workflows directory not found: {workflows_dir}"
        return result
    
    try:
        # Get all phase directories
        phases = []
        for item in sorted(workflows_dir.iterdir()):
            if item.is_dir():
                phases.append(item.name)
            elif item.is_file() and item.suffix in [".md", ".yaml", ".yml"]:
                # Root-level workflow files
                if "workflows" not in result["workflows"]:
                    result["workflows"]["root"] = []
                result["workflows"]["root"].append({
                    "name": item.stem,
                    "path": str(item),
                    "type": item.suffix[1:]
                })
        
        # For each phase, list workflows
        for phase_name in phases:
            if phase and phase != phase_name:
                continue
                
            phase_dir = workflows_dir / phase_name
            workflows = []
            
            for item in sorted(phase_dir.iterdir()):
                if item.is_file() and item.suffix in [".md", ".yaml", ".yml", ".json"]:
                    workflow_info = {
                        "name": item.stem,
                        "path": str(item),
                        "type": item.suffix[1:]
                    }
                    # Read for preview
                    try:
                        content = item.read_text(encoding="utf-8")
                        workflow_info["preview"] = content[:200].strip()
                    except Exception:
                        pass
                    workflows.append(workflow_info)
            
            if workflows:
                result["workflows"][phase_name] = workflows
        
        # Count total
        total = sum(len(wfs) for wfs in result["workflows"].values())
        result["count"] = total
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


# ---------------------------------------------------------------------------
# TOOL: inject_context
# ---------------------------------------------------------------------------

@mcp.tool(tags={"write", "context", "injection"})
def inject_context(
    context_type: str = "active",
    output_path: str = None
) -> dict:
    """
    Writes context into session for prompt injection.
    Combines available context into a single injectable block.
    
    Args:
        context_type: Which context to inject ("active", "product", "user", "all")
        output_path: Optional path to write the injected context
    
    Returns:
        dict with injected context content and metadata
    """
    project_root = get_project_root()
    
    # Build context block
    context_block = []
    context_block.append(f"# Athena Context Injection")
    context_block.append(f"# Generated: {datetime.now().isoformat()}")
    context_block.append("")
    
    available_contexts = []
    
    if context_type in ["active", "all"]:
        active = read_memory_bank_file("activeContext.md")
        if active["exists"]:
            context_block.append("## Active Context")
            context_block.append(active["content"])
            context_block.append("")
            available_contexts.append("active")
    
    if context_type in ["product", "all"]:
        product = read_memory_bank_file("productContext.md")
        if product["exists"]:
            context_block.append("## Product Context (Identity)")
            context_block.append(product["content"])
            context_block.append("")
            available_contexts.append("product")
    
    if context_type in ["user", "all"]:
        user = read_memory_bank_file("userContext.md")
        if user["exists"]:
            context_block.append("## User Context")
            context_block.append(user["content"])
            context_block.append("")
            available_contexts.append("user")
    
    if context_type in ["all"]:
        constraints = read_memory_bank_file("constraints.md")
        if constraints["exists"]:
            context_block.append("## Constraints")
            context_block.append(constraints["content"])
            context_block.append("")
            available_contexts.append("constraints")
    
    # NEW: Include user_profile.md for user context (rich identity data)
    if context_type in ["all", "user"]:
        user_profile = read_memory_bank_file("user_profile.md")
        if user_profile["exists"]:
            context_block.append("## User Profile (Immutable Identity)")
            # Truncate to avoid context overflow - keep first 100 lines
            profile_content = user_profile["content"]
            lines = profile_content.split("\n")
            if len(lines) > 100:
                profile_content = "\n".join(lines[:100]) + "\n... [truncated]"
            context_block.append(profile_content)
            context_block.append("")
            available_contexts.append("user_profile")
    
    # NEW: Include learned style context for personalization
    if context_type in ["all", "user"]:
        try:
            from athena_context_mcp.style_learner import get_learner
            learner = get_learner()
            style = learner.get_style_context()
            if style:
                context_block.append("## Personalized Style (Learned)")
                context_block.append(f"- Communication: {style.get('communication_style', 'unknown')}")
                context_block.append(f"- Directness: {style.get('communication_directness', 'unknown')}")
                context_block.append(f"- Preferred agents: {style.get('preferred_agents', [])}")
                context_block.append(f"- Peak hours: {style.get('peak_hours', [])}")
                context_block.append("")
                available_contexts.append("style")
        except Exception:
            pass  # Style learner not available
    
    # NEW: Include archive context for session continuity
    if context_type in ["all"]:
        try:
            from athena_context_mcp.archive_scanner import get_scanner
            scanner = get_scanner()
            recent = scanner.scan_archives(limit=3)
            if recent.get("sessions"):
                context_block.append("## Recent Sessions")
                for sess in recent["sessions"][:3]:
                    context_block.append(f"- {sess.get('session_id', 'unknown')}: {sess.get('summary', 'No summary')}")
                context_block.append("")
                available_contexts.append("archive")
        except Exception:
            pass  # Archive scanner not available
    
    result = {
        "tool": "inject_context",
        "context_type": context_type,
        "available_contexts": available_contexts,
        "content": "\n".join(context_block),
        "timestamp": datetime.now().isoformat()
    }
    
    # Write to output path if specified
    if output_path:
        output_file = Path(output_path)
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(result["content"], encoding="utf-8")
            result["output_file"] = str(output_file)
            result["written"] = True
        except Exception as e:
            result["write_error"] = str(e)
    
    return result


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Athena Context MCP Server")
    parser.add_argument("--sse", action="store_true", help="Use SSE transport")
    parser.add_argument("--port", type=int, default=8766, help="SSE port")
    args = parser.parse_args()
    
    if args.sse:
        mcp.run(transport="sse", port=args.port)
    else:
        mcp.run(transport="stdio")