#!/usr/bin/env python3
"""Bash MCP Server — per-agent gated shell execution with hardcoded delete protection."""
import json, sys, os, subprocess, time, re

PROJECT_ROOT = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND"
AGENTS_DIR = os.path.join(PROJECT_ROOT, "agents")
ACTIVE_AGENT_FILE = os.path.join(PROJECT_ROOT, "data/active-agent.json")
TRASH_DIR = os.path.join(PROJECT_ROOT, "data/trash")

# ═══════════════════════════════════════════════════════════
# HARDCODED DELETE PROTECTION — Works regardless of identity
# This blocks permanent deletes at the command level.
# ALL agents (including subagents with empty identity) are blocked.
# ═══════════════════════════════════════════════════════════

DELETE_PATTERNS = [
    r'\brm\s+(-[a-zA-Z]*[rf][a-zA-Z]*\s+)',     # rm -rf, rm -f, rm -r
    r'\brm\s+(-[a-zA-Z]*\s+)*[^\s]+\s*$',        # rm <file> (any rm usage)
    r'\brm\s+--',                                  # rm --force, rm --recursive
    r'\bunlink\b',                                 # unlink command
    r'\bshred\b',                                  # shred command
    r'\bfind\s+.*-delete\b',                       # find ... -delete
    r'\bfind\s+.*\bexec\s+rm\b',                   # find ... exec rm
]

def is_delete_command(cmd):
    """Check if command would permanently delete files."""
    for pattern in DELETE_PATTERNS:
        if re.search(pattern, cmd):
            return True
    return False

def safe_rm_wrapper(cmd):
    """Replace rm commands with safe alternatives that move to trash."""
    # If it's a simple rm, replace with mv to trash
    if re.match(r'^\s*rm\s+', cmd):
        # Extract the file path(s)
        parts = cmd.split()
        if len(parts) >= 2:
            # Get the target (last argument that doesn't start with -)
            targets = [p for p in parts[1:] if not p.startswith('-')]
            if targets:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                trash_parts = []
                for target in targets:
                    trash_name = f"{timestamp}_{os.path.basename(target)}"
                    trash_parts.append(f"mkdir -p '{TRASH_DIR}' && mv '{target}' '{TRASH_DIR}/{trash_name}'")
                return " && ".join(trash_parts)
    return None

AGENT_DIR_MAP = {
    "catalyst":"sisyphus","sisyphus":"sisyphus","hephaestus":"hephaestus","explore":"explore",
    "oracle":"oracle","momus":"momus","prometheus":"prometheus",
    "kairos":"kairos","librarian":"librarian","masterplan":"masterplan",
    "metis":"metis","architect":"architect","jarvis":"jarvis",
    "vision":"vision","phi4":"phi4","mrwhite":"mrwhite",
}

def resolve_agent(args=None):
    """Resolve agent identity with delegation chain support.
    
    Priority:
    1. Direct _agent injection (XTUI or explicit)
    2. Delegation chain from task() call
    3. Environment variables
    4. Active agent file (fallback)
    """
    # Priority 1: Direct _agent injection
    if args and args.get("_agent"):
        return args["_agent"]
    
    # Priority 2: Delegation chain (ADCS spec)
    if args:
        chain = args.get("_delegation_chain")
        if chain and isinstance(chain, dict) and chain.get("links"):
            # Last link is the current agent in the chain
            return chain["links"][-1].get("agentName", "")
    
    # Priority 3: Environment variables
    for env in ["MCP_CLIENT_AGENT","OPENCODE_AGENT","AGENT_NAME","OPENCODE_USER"]:
        val = os.environ.get(env, "")
        if val and val != "default" and val != "undefined":
            return val
    
    # Priority 4: Active agent file (fallback)
    try:
        with open(ACTIVE_AGENT_FILE) as f:
            state = json.load(f)
            if state.get("agent") and (time.time() * 1000 - state.get("updated", 0) < 15000):
                return state["agent"]
    except:
        pass
    
    return ""

def load_tools(agent_name):
    if not agent_name:
        return None
    name = agent_name.lower().replace("-","").replace(" ","")
    for key, dn in AGENT_DIR_MAP.items():
        if key in name:
            path = os.path.join(AGENTS_DIR, dn, "tools/tools.json")
            if os.path.exists(path):
                try:
                    with open(path) as f:
                        return json.load(f)
                except:
                    return None
    return None

def is_tool_allowed(agent_name):
    cfg = load_tools(agent_name)
    if cfg is None:
        return True
    allowed = cfg.get("allowed", [])
    blocked = cfg.get("blocked", [])
    if "bash" in blocked:
        return False
    if allowed and "bash" not in allowed:
        return False
    return True

TOOL_DEF = {"name": "bash", "description": "Execute shell commands with per-agent gating and delete protection",
    "inputSchema": {"type": "object", "properties": {
        "command": {"type": "string", "description": "Command to run"},
        "description": {"type": "string", "description": "What this command does"},
        "workdir": {"type": "string", "description": "Working directory"},
    }, "required": ["command"]}}

CACHED_AGENT = resolve_agent()

def handle_initialize():
    return {"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"bash-mcp","version":"1.1.0"}}

def handle_tools_list():
    return {"tools": [TOOL_DEF]}

def handle_tool_call(name, args):
    nonlocal_agent = resolve_agent(args)
    if name != "bash":
        return {"content": [{"type":"text","text":f"Unknown tool: {name}"}]}
    if not is_tool_allowed(nonlocal_agent):
        return {"content": [{"type":"text","text":f"Error: bash not in {nonlocal_agent or 'default'}'s allowed tools"}]}
    cmd = args.get("command", "")
    cwd = args.get("workdir", PROJECT_ROOT)
    if not cmd.strip():
        return {"content": [{"type":"text","text":"Error: empty command"}]}

    # ═══════════════════════════════════════════════════════
    # DELETE PROTECTION — Enforced for ALL agents, ALL subagents
    # ═══════════════════════════════════════════════════════
    if is_delete_command(cmd):
        # Try to convert to safe move-to-trash
        safe_cmd = safe_rm_wrapper(cmd)
        if safe_cmd:
            # Execute the safe version instead
            try:
                result = subprocess.run(["bash", "-c", safe_cmd], capture_output=True, text=True, timeout=60, cwd=cwd)
                output = result.stdout.strip()
                if result.stderr.strip():
                    err = result.stderr.strip()
                    output = output + f"\n[stderr]: {err}" if output else f"[stderr]: {err}"
                msg = f"⚠️ DELETE PROTECTED: '{cmd}' was converted to safe move-to-trash.\n"
                msg += f"Result: {output or '(no output)'}"
                return {"content": [{"type":"text","text": msg}]}
            except Exception as e:
                return {"content": [{"type":"text","text": f"Error executing safe delete: {str(e)}"}]}
        else:
            return {"content": [{"type":"text","text": f"❌ BLOCKED: Permanent delete command detected: '{cmd}'\nUse safe_delete tool instead. All deletions go to data/trash/ for 30-day recovery."}]}

    try:
        result = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=60, cwd=cwd)
        output = result.stdout.strip()
        if result.stderr.strip():
            err = result.stderr.strip()
            output = output + f"\n[stderr]: {err}" if output else f"[stderr]: {err}"
        return {"content": [{"type":"text","text": output or "(no output)"}]}
    except subprocess.TimeoutExpired:
        return {"content": [{"type":"text","text": "Error: command timed out after 60s"}]}
    except Exception as e:
        return {"content": [{"type":"text","text": f"Error: {str(e)}"}]}

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            method = req.get("method","")
            rid = req.get("id",None)
            if method == "initialize":
                result = handle_initialize()
            elif method == "tools/list":
                result = handle_tools_list()
            elif method == "tools/call":
                params = req.get("params",{})
                result = handle_tool_call(params.get("name",""), params.get("arguments",{}))
            else:
                result = {"error": f"Unknown method: {method}"}
            print(json.dumps({"jsonrpc":"2.0","id":rid,"result":result}), flush=True)
        except Exception as e:
            print(json.dumps({"jsonrpc":"2.0","id":None,"error":{"code":-32603,"message":str(e)}}), flush=True)

if __name__ == "__main__":
    main()
