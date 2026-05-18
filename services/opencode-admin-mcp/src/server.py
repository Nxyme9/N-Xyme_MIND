#!/usr/bin/env python3
"""OpenCode Admin MCP — tools for editing and validating opencode config."""
import json
import sys
import os
import subprocess
import shutil

PROJECT_ROOT = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND"
OPENCODE_CONFIG = os.path.join(PROJECT_ROOT, "opencode.json")
NX_CONFIG = os.path.join(PROJECT_ROOT, "config/nx_agents.json")
SCHEMA_REF = os.path.join(PROJECT_ROOT, "docs/opencode-schema-reference.md")
AGENTS_DIR = os.path.join(PROJECT_ROOT, "agents")

ALLOWED_ROOT_KEYS = {
    "$schema", "model", "skills", "compaction", "plugin", "mcp",
    "permission", "agent", "provider", "instructions"
}

ALL_TOOLS = [
    {"name": "validate_config", "description": "Validate opencode.json against allowed keys and check for issues",
     "inputSchema": {"type": "object", "properties": {
         "file": {"type": "string", "description": "Config file path", "default": OPENCODE_CONFIG}
     }, "required": []}},
    {"name": "edit_config", "description": "Edit a key in opencode.json (string or JSON value)",
     "inputSchema": {"type": "object", "properties": {
         "key": {"type": "string", "description": "Key path (dot-separated, e.g. 'permission' or 'agent.Hephaestus - Builder.mode')"},
         "value": {"type": "string", "description": "New value (JSON-encoded)"},
         "file": {"type": "string", "description": "Config file", "default": OPENCODE_CONFIG}
     }, "required": ["key", "value"]}},
    {"name": "remove_key", "description": "Remove a key from opencode.json or nx_agents.json",
     "inputSchema": {"type": "object", "properties": {
         "key": {"type": "string", "description": "Key to remove"},
         "file": {"type": "string", "description": "Config file", "default": OPENCODE_CONFIG}
     }, "required": ["key"]}},
    {"name": "add_agent", "description": "Add a new agent definition to opencode.json",
     "inputSchema": {"type": "object", "properties": {
         "name": {"type": "string", "description": "Agent display name"},
         "mode": {"type": "string", "description": "all, subagent, or primary", "default": "subagent"},
         "model": {"type": "string", "description": "Model ID", "default": "opencode/deepseek-v4-flash-free"},
         "description": {"type": "string", "description": "Agent description"},
         "prompt_file": {"type": "string", "description": "Path to agent.js prompt file"}
     }, "required": ["name", "description"]}},
    {"name": "list_agents", "description": "List all agents from opencode.json",
     "inputSchema": {"type": "object", "properties": {
         "file": {"type": "string", "description": "Config file", "default": OPENCODE_CONFIG}
     }, "required": []}},
    {"name": "sync_nx_config", "description": "Copy a key between opencode.json and nx_agents.json",
     "inputSchema": {"type": "object", "properties": {
         "key": {"type": "string", "description": "Key to sync"},
         "direction": {"type": "string", "description": "to_opencode or to_nx", "default": "to_opencode"}
     }, "required": ["key"]}},
    {"name": "check_schema_ref", "description": "Check if schema reference doc is up to date",
     "inputSchema": {"type": "object", "properties": {}, "required": []}},
]


def _read_json(path):
    with open(path) as f:
        return json.load(f)


def _write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _set_nested(data, key_path, value):
    parts = key_path.split(".")
    for part in parts[:-1]:
        if part not in data:
            data[part] = {}
        data = data[part]
    data[parts[-1]] = value


def _del_nested(data, key_path):
    parts = key_path.split(".")
    for part in parts[:-1]:
        if part not in data:
            return False
        data = data[part]
    if parts[-1] in data:
        del data[parts[-1]]
        return True
    return False


def handle_validate_config(arguments):
    file_path = arguments.get("file", OPENCODE_CONFIG)
    if not os.path.exists(file_path):
        return {"content": [{"type": "text", "text": f"Error: File not found: {file_path}"}]}

    try:
        cfg = _read_json(file_path)
    except json.JSONDecodeError as e:
        return {"content": [{"type": "text", "text": f"Error: Invalid JSON: {e}"}]}

    issues = []
    file_key = os.path.basename(file_path)

    if file_key == "opencode.json":
        unknown = set(cfg.keys()) - ALLOWED_ROOT_KEYS
        if unknown:
            issues.append(f"Unrecognized keys (move to nx_agents.json): {', '.join(sorted(unknown))}")

        agents = cfg.get("agent", {})
        for name, acfg in agents.items():
            if "mode" not in acfg:
                issues.append(f"Agent '{name}' missing 'mode'")
            if "prompt" not in acfg:
                issues.append(f"Agent '{name}' missing 'prompt'")
            if "model" not in acfg:
                issues.append(f"Agent '{name}' missing 'model'")

        mcp = cfg.get("mcp", {})
        for name, mcfg in mcp.items():
            cmd = mcfg.get("command", [])
            if cmd and not os.path.exists(cmd[0]):
                issues.append(f"MCP '{name}' command not found: {cmd[0]}")

        plugins = cfg.get("plugin", [])
        for p in plugins:
            if p.endswith(".js") and not os.path.exists(p):
                issues.append(f"Plugin not found: {p}")

    if not issues:
        return {"content": [{"type": "text", "text": "Config valid. No issues found."}]}

    result = f"Found {len(issues)} issue(s):\n" + "\n".join(f"  - {i}" for i in issues)
    return {"content": [{"type": "text", "text": result}]}


def handle_edit_config(arguments):
    file_path = arguments.get("file", OPENCODE_CONFIG)
    key = arguments.get("key", "")
    raw_value = arguments.get("value", "")

    if not key:
        return {"content": [{"type": "text", "text": "Error: 'key' is required"}]}

    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError:
        value = raw_value

    if not os.path.exists(file_path):
        return {"content": [{"type": "text", "text": f"Error: File not found: {file_path}"}]}

    try:
        cfg = _read_json(file_path)
    except json.JSONDecodeError as e:
        return {"content": [{"type": "text", "text": f"Error: Invalid JSON: {e}"}]}

    _set_nested(cfg, key, value)
    _write_json(file_path, cfg)

    return {"content": [{"type": "text", "text": f"Set {file_path}: {key} = {json.dumps(value)}"}]}


def handle_remove_key(arguments):
    file_path = arguments.get("file", OPENCODE_CONFIG)
    key = arguments.get("key", "")

    if not key:
        return {"content": [{"type": "text", "text": "Error: 'key' is required"}]}

    if not os.path.exists(file_path):
        return {"content": [{"type": "text", "text": f"Error: File not found: {file_path}"}]}

    cfg = _read_json(file_path)

    if _del_nested(cfg, key):
        _write_json(file_path, cfg)
        return {"content": [{"type": "text", "text": f"Removed '{key}' from {os.path.basename(file_path)}"}]}
    else:
        return {"content": [{"type": "text", "text": f"Key '{key}' not found in {os.path.basename(file_path)}"}]}


def handle_add_agent(arguments):
    name = arguments.get("name", "")
    mode = arguments.get("mode", "subagent")
    model = arguments.get("model", "opencode/deepseek-v4-flash-free")
    description = arguments.get("description", "")
    prompt_file = arguments.get("prompt_file", "")

    if not name or not description:
        return {"content": [{"type": "text", "text": "Error: 'name' and 'description' are required"}]}

    if not prompt_file:
        agent_dir_name = name.lower().replace(" - ", "-").replace(" ", "-").split("-")[0]
        prompt_file = f"{{file:{AGENTS_DIR}/{agent_dir_name}/agent.js}}"

    cfg = _read_json(OPENCODE_CONFIG)
    if "agent" not in cfg:
        cfg["agent"] = {}

    cfg["agent"][name] = {
        "description": description,
        "mode": mode,
        "model": model,
        "prompt": prompt_file
    }

    _write_json(OPENCODE_CONFIG, cfg)

    # Also add to nx_agents.json
    nx = _read_json(NX_CONFIG)
    if "agent" not in nx:
        nx["agent"] = {}
    nx["agent"][name] = cfg["agent"][name]
    _write_json(NX_CONFIG, nx)

    return {"content": [{"type": "text", "text": f"Added agent '{name}' to both configs"}]}


def handle_list_agents(arguments):
    file_path = arguments.get("file", OPENCODE_CONFIG)
    cfg = _read_json(file_path)
    agents = cfg.get("agent", {})

    if not agents:
        return {"content": [{"type": "text", "text": "No agents defined"}]}

    lines = [f"Agents in {os.path.basename(file_path)}:"]
    for name, acfg in sorted(agents.items()):
        mode = acfg.get("mode", "?")
        model = acfg.get("model", "?")
        desc = acfg.get("description", "")[:60]
        lines.append(f"  {name} [{mode}] {model}")
        if desc:
            lines.append(f"    {desc}")
    return {"content": [{"type": "text", "text": "\n".join(lines)}]}


def handle_sync_nx_config(arguments):
    key = arguments.get("key", "")
    direction = arguments.get("direction", "to_opencode")

    if not key:
        return {"content": [{"type": "text", "text": "Error: 'key' is required"}]}

    oc = _read_json(OPENCODE_CONFIG)
    nx = _read_json(NX_CONFIG)

    if direction == "to_opencode":
        if key in nx:
            oc[key] = nx[key]
            _write_json(OPENCODE_CONFIG, oc)
            return {"content": [{"type": "text", "text": f"Synced '{key}' from nx_agents.json to opencode.json"}]}
        else:
            return {"content": [{"type": "text", "text": f"Key '{key}' not found in nx_agents.json"}]}
    else:
        if key in oc:
            nx[key] = oc[key]
            _write_json(NX_CONFIG, nx)
            return {"content": [{"type": "text", "text": f"Synced '{key}' from opencode.json to nx_agents.json"}]}
        else:
            return {"content": [{"type": "text", "text": f"Key '{key}' not found in opencode.json"}]}


def handle_check_schema_ref():
    if not os.path.exists(SCHEMA_REF):
        return {"content": [{"type": "text", "text": "Schema reference doc not found at docs/opencode-schema-reference.md"}]}

    with open(SCHEMA_REF) as f:
        content = f.read()

    oc = _read_json(OPENCODE_CONFIG)
    oc_keys = set(oc.keys())
    ref_mentioned = []
    for key in oc_keys:
        if key in content:
            ref_mentioned.append(key)

    missing_from_ref = oc_keys - set(ref_mentioned) - {"$schema"}
    if missing_from_ref:
        msg = f"Schema ref exists but missing docs for keys: {', '.join(sorted(missing_from_ref))}"
    else:
        msg = "Schema reference covers all config keys"

    return {"content": [{"type": "text", "text": msg}]}


def handle_initialize():
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {"tools": {}},
        "serverInfo": {"name": "opencode-admin-mcp", "version": "1.0.0"}
    }


def handle_tools_list():
    return {"tools": ALL_TOOLS}


def handle_tool_call(name, arguments):
    handlers = {
        "validate_config": handle_validate_config,
        "edit_config": handle_edit_config,
        "remove_key": handle_remove_key,
        "add_agent": handle_add_agent,
        "list_agents": handle_list_agents,
        "sync_nx_config": handle_sync_nx_config,
        "check_schema_ref": handle_check_schema_ref,
    }
    handler = handlers.get(name)
    if not handler:
        return {"content": [{"type": "text", "text": f"Error: Unknown tool '{name}'"}]}
    try:
        return handler(arguments)
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            method = request.get("method", "")
            req_id = request.get("id", None)

            if method == "initialize":
                result = handle_initialize()
            elif method == "tools/list":
                result = handle_tools_list()
            elif method == "tools/call":
                params = request.get("params", {})
                result = handle_tool_call(params.get("name", ""), params.get("arguments", {}))
            else:
                result = {"error": f"Unknown method: {method}"}

            response = {"jsonrpc": "2.0", "id": req_id, "result": result}
            print(json.dumps(response), flush=True)
        except Exception as e:
            error_response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(e)}}
            print(json.dumps(error_response), flush=True)


if __name__ == "__main__":
    main()
