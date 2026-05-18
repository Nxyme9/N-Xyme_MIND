"""
Megatool MCP Server — exposes daemon megatools as MCP tools for ALL agents.
Each agent gets an optimized subset based on their role.
Run: python3 -m megatool-mcp
"""
import json, subprocess, os, sys
from pathlib import Path

DAEMON = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/services/mojo-router/src/daemon"

def _call_daemon(msg_type, query="", id="mcp"):
    q = json.dumps({"type": msg_type, "query": query, "id": id})
    try:
        proc = subprocess.run([DAEMON], input=q, capture_output=True, text=True, timeout=30)
        return json.loads(proc.stdout.strip())
    except Exception as e:
        return {"type": "error", "message": str(e)}

# ===== MEGATOOL DEFINITIONS =====
# Each agent gets their own optimized set

MEGATOOLS = {
    # ── HEPHAESTUS: Builder tools ──
    "code_search": {
        "description": "Semantic code search across the entire project. Finds files by MEANING, not just keywords.",
        "args": {"query": "What to search for (e.g. 'routing engine error handling')"},
        "agent_target": "hephaestus",
        "handler": lambda args: _call_daemon("code_search", args["query"])
    },
    "code_review": {
        "description": "Memory-backed code review. Checks a file against past decisions, patterns, and known bugs.",
        "args": {"file": "Path to the file to review"},
        "agent_target": "hephaestus, momus",
        "handler": lambda args: _call_daemon("code_review", args["file"])
    },
    "batch_write": {
        "description": "Generate multiple code files from a single spec. Routes to Hephaestus automatically.",
        "args": {"spec": "What to build", "files": "Comma-separated list of files to generate"},
        "agent_target": "hephaestus",
        "handler": lambda args: _call_daemon("batch_write", f"{args['spec']} | files: {args.get('files', '')}")
    },
    
    # ── MOMUS: Critic tools ──
    "memory_search": {
        "description": "Search holographic memory for past decisions, errors, patterns, and context.",
        "args": {"query": "What to search for in memory"},
        "agent_target": "all",
        "handler": lambda args: _call_daemon("memory_search", args["query"])
    },
    "adversarial_review": {
        "description": "Deep adversarial code review — find edge cases, failure modes, security issues.",
        "args": {"file": "Path to file for deep review", "context": "Optional context about what to check"},
        "agent_target": "momus",
        "handler": lambda args: _call_daemon("code_review", args["file"])
    },
    
    # ── EXPLORE: Search tools ──
    "semantic_search": {
        "description": "Find code by semantic meaning — understands intent, not just keywords. Best for 'where is X implemented?'",
        "args": {"query": "What to search for semantically"},
        "agent_target": "explore",
        "handler": lambda args: _call_daemon("code_search", args["query"])
    },
}

if __name__ == "__main__":
    # Simple MCP-like JSON-L interface
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        try:
            req = json.loads(line)
            tool = req.get("tool", "")
            agent = req.get("agent", "")
            args = req.get("args", {})
            
            if tool in MEGATOOLS:
                result = MEGATOOLS[tool]["handler"](args)
                print(json.dumps({"type": "megatool_result", "tool": tool, "result": result, "agent": agent}), flush=True)
            else:
                print(json.dumps({"type": "error", "message": f"Unknown megatool: {tool}"}), flush=True)
        except Exception as e:
            print(json.dumps({"type": "error", "message": str(e)}), flush=True)
