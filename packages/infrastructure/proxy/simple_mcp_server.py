#!/usr/bin/env python3
"""
Simple stdio MCP server for intelligent-router - no fastmcp dependency.
Works as a drop-in replacement for the FastMCP version.
"""

import json
import sys
import os

# Set up paths BEFORE any imports - filter out paths that shadow stdlib!
import sys
import os

# Clean sys.path first - keep only stdlib paths and add our paths
# Stdlib paths start with /usr/lib or contain lib-dynload
_project_root = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND"
_stdlib_paths = [p for p in sys.path if p.startswith('/usr/lib') or 'lib-dynload' in p]
_project_paths = [
    _project_root,
    os.path.join(_project_root, "packages"),
    os.path.join(_project_root, "athena", "src"),
    os.path.join(_project_root, "src", "infrastructure"),
]
# Stdlib first, then project paths
sys.path = _stdlib_paths + _project_paths

# Import our router (after sys.path is fixed)
# Use absolute imports from the proxy package
sys.path.insert(0, os.path.join(_project_root, "packages"))
from infrastructure.proxy import intelligent_router
from infrastructure.proxy.router_brain import MODEL_CAPABILITIES
from infrastructure.proxy.learning_engine import learning_engine

def route_task(prompt: str, system_prompt: str = "", agent_type: str = "") -> dict:
    """Route a task to the optimal model/provider/IP."""
    return intelligent_router.select_route(prompt, system_prompt, agent_type)

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
    if method == "tools/route_task":
        return route_task(
            params.get("prompt", ""),
            params.get("system_prompt", ""),
            params.get("agent_type", "")
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