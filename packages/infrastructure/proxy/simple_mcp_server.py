#!/usr/bin/env python3
"""
Simple stdio MCP server for intelligent-router - no fastmcp dependency.
Works as a drop-in replacement for the FastMCP version.
"""

# CRITICAL: Set up environment BEFORE any imports - must use system Python stdlib!
import sys
import os

# Completely clear sys.path and rebuild with ONLY stdlib + project paths
# Filter out ALL venv paths that shadow stdlib modules
_project_root = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND"

# Use standard library paths - exclude ANYTHING from venvs
# Keep paths that are clearly stdlib or site-packages without venvs
_stdlib_paths = []
_new_path = []
for p in sys.path:
    # Skip any path containing 'venvs' or '.venv' or 'athena'
    if 'venvs' in p or '.venv' in p or '/athena/' in p or p.endswith('athena'):
        continue
    # Keep paths that look like stdlib
    if 'lib-dynload' in p or p.startswith('/usr/lib'):
        _stdlib_paths.append(p)
    else:
        _new_path.append(p)

# Add our project paths at the END (lowest priority - after stdlib)
# CRITICAL: packages/infrastructure must come BEFORE src to override the older version
_project_paths = [
    # packages/infrastructure should be found FIRST
    os.path.join(_project_root, "packages", "infrastructure"),
    os.path.join(_project_root, "packages"),
    _project_root,
    os.path.join(_project_root, "athena", "src"),
    # src is the OLD version - keep it last
    os.path.join(_project_root, "src"),
    os.path.join(_project_root, "src", "infrastructure"),
]

# Rebuild sys.path: stdlib first, then EXPLICIT packages/infrastructure FIRST
sys.path = _stdlib_paths + _project_paths + _new_path

# Now safe to import our router
from infrastructure.proxy import intelligent_router
from infrastructure.proxy.router_brain import MODEL_CAPABILITIES
from infrastructure.proxy.learning_engine import learning_engine

import json

def route_task(prompt: str, system_prompt: str = "", agent_type: str = "", session_id: str = "") -> dict:
    """Route a task to the optimal model/provider/IP."""
    return intelligent_router.select_route(prompt, system_prompt, agent_type, session_id)

def record_success(route: dict, input_tokens: int, output_tokens: int, latency_ms: float) -> dict:
    """Record a successful request."""
    intelligent_router.record_success(route, input_tokens, output_tokens, latency_ms)
    return {"status": "success"}

def record_failure(route: dict, error_type: str, latency_ms: float = 0) -> dict:
    """Record a failed request."""
    intelligent_router.record_failure(route, error_type, latency_ms)
    return {"status": "recorded"}

def get_router_status() -> dict:
    """Get full router status."""
    return intelligent_router.get_status()

def get_available_models() -> list:
    """Get list of available models with capabilities."""
    return [{"model": name, **caps} for name, caps in MODEL_CAPABILITIES.items()]

def get_routing_history(limit: int = 10) -> list:
    """Get recent routing decisions."""
    import sqlite3
    conn = sqlite3.connect(learning_engine.db_path)
    try:
        cursor = conn.execute("""SELECT timestamp, categories, complexity, selected_model, 
            selected_provider, latency_ms, success FROM outcomes 
            ORDER BY timestamp DESC LIMIT ?""", (limit,))
        return [{"timestamp": r[0], "categories": r[1], "complexity": r[2], 
                 "model": r[3], "provider": r[4], "latency_ms": r[5], "success": bool(r[6])} 
                for r in cursor.fetchall()]
    finally:
        conn.close()

# MCP Protocol - JSON-RPC over stdio
def handle_request(method: str, params: dict) -> dict:
    """Handle a single MCP request."""
    # Support both "tools/route_task" and "tools/call" (MCP SDK style)
    if method == "tools/call":
        # MCP SDK sends {"name": "route_task", "arguments": {...}}
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})
        if tool_name == "route_task":
            return route_task(
                tool_args.get("task_description", ""),
                tool_args.get("system_prompt", ""),
                tool_args.get("agent_type", ""),
                tool_args.get("session_id", "")
            )
        elif tool_name == "record_success":
            return record_success(
                tool_args.get("route", {}),
                tool_args.get("input_tokens", 0),
                tool_args.get("output_tokens", 0),
                tool_args.get("latency_ms", 0)
            )
        elif tool_name == "record_failure":
            return record_failure(
                tool_args.get("route", {}),
                tool_args.get("error_type", ""),
                tool_args.get("latency_ms", 0)
            )
        elif tool_name == "get_router_status":
            return get_router_status()
        elif tool_name == "get_available_models":
            return get_available_models()
        elif tool_name == "get_routing_history":
            return get_routing_history(tool_args.get("limit", 10))
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    # Legacy direct method calls
    if method == "tools/route_task":
        return route_task(
            params.get("prompt", ""),
            params.get("system_prompt", ""),
            params.get("agent_type", ""),
            params.get("session_id", "")  # Pass session_id
        )
    elif method == "tools/record_success":
        return record_success(
            params.get("route", {}),
            params.get("input_tokens", 0),
            params.get("output_tokens", 0),
            params.get("latency_ms", 0)
        )
    elif method == "tools/record_failure":
        return record_failure(
            params.get("route", {}),
            params.get("error_type", ""),
            params.get("latency_ms", 0)
        )
    elif method == "tools/get_router_status":
        return get_router_status()
    elif method == "tools/get_available_models":
        return get_available_models()
    elif method == "tools/get_routing_history":
        return get_routing_history(params.get("limit", 10))
    else:
        return {"error": f"Unknown method: {method}"}

def main():
    """Main loop - read JSON requests from stdin, write responses to stdout."""
    print("=== Intelligent Router MCP Server (Simple) ===", file=sys.stderr)
    print(f"Python: {sys.version}", file=sys.stderr)
    
    # Test route on startup
    result = route_task("test", agent_type="test")
    print(f"Test: model={result.get('model')}, best={result.get('analysis', {}).get('best_model')}", file=sys.stderr)
    
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            
            request = json.loads(line.strip())
            method = request.get("method", "")
            params = request.get("params", {})
            id = request.get("id", 1)
            
            response = handle_request(method, params)
            
            # Write response
            output = {"id": id, "result": response}
            print(json.dumps(output), flush=True)
            
        except Exception as e:
            error = {"id": 1, "error": {"message": str(e)}}
            print(json.dumps(error), flush=True)

if __name__ == "__main__":
    main()