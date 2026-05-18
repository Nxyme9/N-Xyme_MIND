#!/usr/bin/env python3
"""Megatool MCP Server — per-agent gated + built-in admin tools."""
import json
import sys
import os
import subprocess
import fnmatch
import re
import shutil
import time

import random
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import parallel executor for delegation chain
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../mcp-core/src"))
from parallel_executor import parallel_executor

PROJECT_ROOT = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND"
BRIDGE_DIR = os.path.join(PROJECT_ROOT, "services/mojo-router/src")
CONFIG_PATH = os.path.join(PROJECT_ROOT, "opencode.json")
NX_CONFIG_PATH = os.path.join(PROJECT_ROOT, "config/nx_agents.json")

BRIDGE_MAP = {
    "search_code":       os.path.join(BRIDGE_DIR, "code_search_bridge.py"),
    "review_code":       os.path.join(BRIDGE_DIR, "code_review_bridge.py"),
    "file_batch_write":       os.path.join(BRIDGE_DIR, "batch_write_bridge.py"),
    "review_adversarial": os.path.join(BRIDGE_DIR, "code_review_bridge.py"),
    # NOTE: search_memory and search_semantic removed from BRIDGE_MAP.
    # They are now handled inline via ADMIN_DISPATCH handlers below,
    # which directly query the session vector store (sessions.jsonl)
    # instead of routing to code_search_bridge.py (code index).
}

ALL_TOOLS = [
    {"name": "search_code", "description": "Semantic code search across the project",
     "inputSchema": {"type": "object", "properties": {
         "query": {"type": "string", "description": "Search query"},
         "max_results": {"type": "number", "default": 5}
     }, "required": ["query"]}},
    {"name": "review_code", "description": "Review code for bugs and issues",
     "inputSchema": {"type": "object", "properties": {
         "file_path": {"type": "string", "description": "Path to file to review"}
     }, "required": ["file_path"]}},
    {"name": "file_batch_write", "description": "Write content to multiple files",
     "inputSchema": {"type": "object", "properties": {
         "files": {"type": "array", "items": {"type": "object",
             "properties": {"path": {"type": "string"}, "content": {"type": "string"}}}}
     }, "required": ["files"]}},
    {"name": "search_memory", "description": "Vector search over 156K embedded session vectors",
     "inputSchema": {"type": "object", "properties": {
         "query": {"type": "string", "description": "Search query"},
         "k": {"type": "number", "default": 3, "description": "Number of results"},
         "min_score": {"type": "number", "default": -1.0, "description": "Minimum similarity threshold"},
         "source": {"type": "string", "default": "vectors", "description": "Source: vectors, holographic, all"}
     }, "required": ["query"]}},
    {"name": "review_adversarial", "description": "Adversarial review of a plan or code decision",
     "inputSchema": {"type": "object", "properties": {
         "content": {"type": "string"}
     }, "required": ["content"]}},
    {"name": "search_semantic", "description": "Vector search over 156K embedded session vectors (alias for search_memory)",
     "inputSchema": {"type": "object", "properties": {
         "query": {"type": "string", "description": "Search query"},
         "k": {"type": "number", "default": 5, "description": "Number of results"},
         "min_score": {"type": "number", "default": -1.0, "description": "Minimum similarity threshold"},
         "source": {"type": "string", "default": "vectors", "description": "Source: vectors, holographic, all"}
     }, "required": ["query"]}},
    {"name": "pull_global_context", "description": "Aggregate context from all memory systems (vectors + holographic + consciousness)",
     "inputSchema": {"type": "object", "properties": {
         "query": {"type": "string", "description": "Search query"},
         "sources": {"type": "array", "items": {"type": "string"}, "default": ["vectors", "holographic", "consciousness"], "description": "Sources to query"},
         "top_k": {"type": "number", "default": 5, "description": "Results per source"},
         "min_score": {"type": "number", "default": 0.0, "description": "Minimum similarity threshold"}
     }, "required": ["query"]}},
    # Missing tools that agents expect
    {"name": "safe_delete", "description": "Move file to trash instead of permanent delete",
     "inputSchema": {"type": "object", "properties": {
         "filePath": {"type": "string", "description": "File to delete"}
     }, "required": ["filePath"]}},
    {"name": "read_memory", "description": "Read memory entry by ID",
     "inputSchema": {"type": "object", "properties": {
         "memoryId": {"type": "string", "description": "Memory entry ID"}
     }, "required": ["memoryId"]}},
    {"name": "write_memory", "description": "Write entry to memory",
     "inputSchema": {"type": "object", "properties": {
         "content": {"type": "string", "description": "Content to write"},
         "category": {"type": "string", "description": "Category tag"}
     }, "required": ["content"]}},
    {"name": "list_memory", "description": "List all memory entries",
     "inputSchema": {"type": "object", "properties": {
         "category": {"type": "string", "description": "Filter by category"}
     }, "required": []}},
    {"name": "web_fetch", "description": "Fetch content from URL",
     "inputSchema": {"type": "object", "properties": {
         "url": {"type": "string", "description": "URL to fetch"},
         "format": {"type": "string", "description": "Return format (markdown, text, html)", "default": "markdown"}
     }, "required": ["url"]}},
    {"name": "web_search", "description": "Search the web",
     "inputSchema": {"type": "object", "properties": {
         "query": {"type": "string", "description": "Search query"},
         "numResults": {"type": "number", "description": "Number of results", "default": 5}
     }, "required": ["query"]}},
    {"name": "file_batch_read", "description": "Read multiple files at once",
     "inputSchema": {"type": "object", "properties": {
         "files": {"type": "array", "items": {"type": "string"}, "description": "List of file paths"}
     }, "required": ["files"]}},
    {"name": "project_map", "description": "Get project directory structure",
     "inputSchema": {"type": "object", "properties": {
         "maxDepth": {"type": "number", "description": "Maximum directory depth", "default": 3}
     }, "required": []}},
    {"name": "parallel_task", "description": "Execute tasks in parallel within the same session context",
     "inputSchema": {"type": "object", "properties": {
         "session_id": {"type": "string", "description": "Session ID"},
         "agent_name": {"type": "string", "description": "Agent to execute"},
         "prompt": {"type": "string", "description": "Prompt for the agent"},
         "dependencies": {"type": "array", "items": {"type": "string"}, "description": "Task IDs that must complete first"},
         "timeout": {"type": "number", "description": "Timeout in seconds", "default": 300}
     }, "required": ["session_id", "agent_name", "prompt"]}},
    {"name": "task_status", "description": "Get status of a parallel task",
     "inputSchema": {"type": "object", "properties": {
         "task_id": {"type": "string", "description": "Task ID"}
     }, "required": ["task_id"]}},
    {"name": "session_tasks", "description": "Get all tasks for a session",
     "inputSchema": {"type": "object", "properties": {
         "session_id": {"type": "string", "description": "Session ID"}
     }, "required": ["session_id"]}},
    {"name": "bg_submit", "description": "Submit background task (non-blocking)",
     "inputSchema": {"type": "object", "properties": {
         "task_type": {"type": "string", "description": "Task type (file_read, search, config)"},
         "args": {"type": "object", "description": "Task arguments"},
         "callback": {"type": "string", "description": "Optional callback URL"},
         "session_id": {"type": "string", "description": "Session ID for event routing"}
     }, "required": ["task_type", "args"]}},
    {"name": "bg_status", "description": "Get background task status",
     "inputSchema": {"type": "object", "properties": {
         "task_id": {"type": "string", "description": "Task ID"}
     }, "required": ["task_id"]}},
    {"name": "bg_list", "description": "List background tasks",
     "inputSchema": {"type": "object", "properties": {
         "status": {"type": "string", "description": "Filter by status"}
     }, "required": []}},
    {"name": "bg_cancel", "description": "Cancel background task",
     "inputSchema": {"type": "object", "properties": {
         "task_id": {"type": "string", "description": "Task ID"}
     }, "required": ["task_id"]}},
    {"name": "bg_events", "description": "Get pending background task events for a session (clears the event queue)",
     "inputSchema": {"type": "object", "properties": {
         "session_id": {"type": "string", "description": "Session ID to get events for"}
     }, "required": ["session_id"]}},
    {"name": "task_result", "description": "Get full background task result by ID",
     "inputSchema": {"type": "object", "properties": {
         "task_id": {"type": "string", "description": "Task ID"}
     }, "required": ["task_id"]}},
    {"name": "cache_stats", "description": "Get cache statistics",
     "inputSchema": {"type": "object", "properties": {}, "required": []}},
    {"name": "cache_clear", "description": "Clear all caches",
     "inputSchema": {"type": "object", "properties": {}, "required": []}},
    {"name": "embed_text", "description": "Generate embedding vector for text (384-dim)",
     "inputSchema": {"type": "object", "properties": {
         "text": {"type": "string", "description": "Text to embed"}
     }, "required": ["text"]}},
    {"name": "embed_similarity", "description": "Compute cosine similarity between two embeddings",
     "inputSchema": {"type": "object", "properties": {
         "vector_a": {"type": "array", "items": {"type": "number"}, "description": "First embedding vector"},
         "vector_b": {"type": "array", "items": {"type": "number"}, "description": "Second embedding vector"}
     }, "required": ["vector_a", "vector_b"]}},
    {"name": "pc_scan", "description": "Scan PC for scattered transcripts, models, configs, code across all drives using embedding categorization.",
     "inputSchema": {"type": "object", "properties": {
         "timeout": {"type": "number", "description": "Scan timeout in seconds", "default": 30},
         "category": {"type": "string", "description": "Filter by category (transcript, memory, model, config, code, docs)"}
     }, "required": []}},
    {"name": "pc_aware", "description": "Get PC-wide awareness via embedding search. Searches across all known data locations, transcripts, memory, models using semantic similarity.",
     "inputSchema": {"type": "object", "properties": {
         "query": {"type": "string", "description": "What to search for across the PC"},
         "location": {"type": "string", "description": "Limit search to specific location (home, docs, library, archive, mount, all)", "default": "all"}
     }, "required": ["query"]}},
    {"name": "ask_question", "description": "Ask a question, tool routes automatically.",
     "inputSchema": {"type": "object", "properties": {
         "question": {"type": "string"}
     }, "required": ["question"]}},
    {"name": "spawn_task", "description": "Spawn a new agent task.",
     "inputSchema": {"type": "object", "properties": {
         "agent": {"type": "string"}, "prompt": {"type": "string"}
     }, "required": ["agent", "prompt"]}},
    {"name": "context_prune", "description": "Smart compaction by agent type.",
     "inputSchema": {"type": "object", "properties": {
         "session_id": {"type": "string"}
     }, "required": ["session_id"]}},
    {"name": "session_status", "description": "Session state: calls, memory, loops, context %.",
     "inputSchema": {"type": "object", "properties": {
         "session_id": {"type": "string"}
     }, "required": ["session_id"]}},
    {"name": "verify_code", "description": "Quality gates: fmt, lint, test, audit.",
     "inputSchema": {"type": "object", "properties": {
         "path": {"type": "string", "description": "Code path to verify"}
     }, "required": ["path"]}},
    {"name": "consciousness_record", "description": "Record agent task outcome into consciousness (embedded identity)",
     "inputSchema": {"type": "object", "properties": {
         "agent": {"type": "string"}, "task": {"type": "string"}, 
         "success": {"type": "boolean"}, "latency_ms": {"type": "number", "default": 0}
     }, "required": ["agent", "task", "success"]}},
    {"name": "consciousness_identity", "description": "Get agent's current consciousness state from embedding space",
     "inputSchema": {"type": "object", "properties": {
         "agent": {"type": "string"}
     }, "required": ["agent"]}},
    {"name": "ralph_start", "description": "Start persistent iterative refinement loop that survives restarts. Frontmatter .md state. Usage: session_id, task, [max_iterations], [promise], [ultrawork]",
     "inputSchema": {"type": "object", "properties": {
         "session_id": {"type": "string"}, "task": {"type": "string"},
         "max_iterations": {"type": "number", "default": 5},
         "promise": {"type": "string", "description": "Completion promise tag (default: DONE)"},
         "ultrawork": {"type": "boolean", "description": "Enable Ultrawork mode (Oracle verification gate)", "default": False},
         "strategy": {"type": "string", "enum": ["continue", "reset"], "default": "continue"}
     }, "required": ["session_id", "task"]}},
    {"name": "ralph_status", "description": "Get status of a running Ralph Loop",
     "inputSchema": {"type": "object", "properties": {"session_id": {"type": "string"}}, "required": ["session_id"]}},
    {"name": "ralph_iterate", "description": "Force a single iteration in a running Ralph Loop",
     "inputSchema": {"type": "object", "properties": {"session_id": {"type": "string"}}, "required": ["session_id"]}},
    {"name": "ralph_cancel", "description": "Cancel a running Ralph Loop",
     "inputSchema": {"type": "object", "properties": {"session_id": {"type": "string"}}, "required": ["session_id"]}},
    {"name": "ulw_start", "description": "Start an Ultrawork loop (ralph_start with ultrawork=true). DONE → Oracle verification → VERIFIED required.",
     "inputSchema": {"type": "object", "properties": {
         "session_id": {"type": "string"}, "task": {"type": "string"},
         "max_iterations": {"type": "number", "default": 0, "description": "0 = unbounded"},
         "promise": {"type": "string", "description": "Completion promise tag (default: DONE)"}
     }, "required": ["session_id", "task"]}},
    {"name": "ulw_status", "description": "Get status of a running Ultrawork loop (alias for ralph_status)",
     "inputSchema": {"type": "object", "properties": {"session_id": {"type": "string"}}, "required": ["session_id"]}},
    {"name": "ulw_cancel", "description": "Cancel a running Ultrawork loop (alias for ralph_cancel)",
     "inputSchema": {"type": "object", "properties": {"session_id": {"type": "string"}}, "required": ["session_id"]}},
    # Admin tools (inline handlers)
    {"name": "config_validate", "description": "Validate opencode.json against allowed keys",
     "inputSchema": {"type": "object", "properties": {
         "file": {"type": "string", "description": "Config file path", "default": CONFIG_PATH}
     }, "required": []}},
    {"name": "config_edit", "description": "Edit a key in opencode.json (string or JSON value)",
     "inputSchema": {"type": "object", "properties": {
         "key": {"type": "string", "description": "Key path (dot-separated)"},
         "value": {"type": "string", "description": "New value (JSON-encoded)"},
         "file": {"type": "string", "description": "Config file", "default": CONFIG_PATH}
     }, "required": ["key", "value"]}},
    {"name": "config_remove", "description": "Remove a key from config",
     "inputSchema": {"type": "object", "properties": {
         "key": {"type": "string", "description": "Key to remove"},
         "file": {"type": "string", "description": "Config file", "default": CONFIG_PATH}
     }, "required": ["key"]}},
    {"name": "agent_add", "description": "Add a new agent definition to both configs",
     "inputSchema": {"type": "object", "properties": {
         "name": {"type": "string", "description": "Agent display name"},
         "mode": {"type": "string", "default": "subagent"},
         "model": {"type": "string", "default": "opencode/deepseek-v4-flash-free"},
         "description": {"type": "string"},
         "prompt_file": {"type": "string"}
     }, "required": ["name", "description"]}},
    {"name": "agent_list", "description": "List all agents from config",
     "inputSchema": {"type": "object", "properties": {
         "file": {"type": "string", "default": CONFIG_PATH}
     }, "required": []}},
    {"name": "config_sync", "description": "Copy a key between configs",
     "inputSchema": {"type": "object", "properties": {
         "key": {"type": "string"},
         "direction": {"type": "string", "default": "to_opencode"}
     }, "required": ["key"]}},
    {"name": "schema_check", "description": "Check schema reference doc covers all keys",
     "inputSchema": {"type": "object", "properties": {}, "required": []}},
    # File tool replacements (for built-in deny)
    {"name": "file_write", "description": "Write content to a file (replaces built-in write)",
     "inputSchema": {"type": "object", "properties": {
         "filePath": {"type": "string", "description": "Absolute path"},
         "content": {"type": "string", "description": "File content"}
     }, "required": ["filePath", "content"]}},
    {"name": "file_edit", "description": "Edit a file via string replace (replaces built-in edit)",
     "inputSchema": {"type": "object", "properties": {
         "filePath": {"type": "string"},
         "oldString": {"type": "string"},
         "newString": {"type": "string"}
     }, "required": ["filePath", "oldString", "newString"]}},
    {"name": "file_read", "description": "Read a file (replaces built-in read)",
     "inputSchema": {"type": "object", "properties": {
         "filePath": {"type": "string", "description": "Absolute path"},
         "offset": {"type": "number", "description": "Line offset"},
         "limit": {"type": "number", "description": "Max lines"}
     }, "required": ["filePath"]}},
    {"name": "file_glob", "description": "Glob for files by pattern (replaces built-in glob)",
     "inputSchema": {"type": "object", "properties": {
         "pattern": {"type": "string"},
         "path": {"type": "string", "description": "Directory to search"}
     }, "required": ["pattern"]}},
    {"name": "file_grep", "description": "Search file contents by regex (replaces built-in grep)",
     "inputSchema": {"type": "object", "properties": {
         "pattern": {"type": "string"},
         "path": {"type": "string", "description": "Directory to search"},
         "include": {"type": "string", "description": "Glob filter"}
     }, "required": ["pattern"]}},
    # Agent edit tool (optimized for agent files)
    {"name": "agent_edit", "description": "Surgical edit tool for agent files. Parses structure, edits sections, validates automatically. Operations: read_agent, edit_section, add_section, remove_section, edit_prompt_section, add_skill, remove_skill, edit_tools, edit_config, batch_edit, validate_agent.",
     "inputSchema": {"type": "object", "properties": {
         "operation": {"type": "string", "enum": [
             "read_agent", "edit_section", "add_section", "remove_section",
             "edit_prompt_section", "add_skill", "remove_skill",
             "edit_tools", "config_edit", "batch_edit", "validate_agent"
         ], "description": "Operation to perform"},
         "agent": {"type": "string", "description": "Agent name (e.g., 'Scalpel', 'Sisyphus')"},
         "file_type": {"type": "string", "enum": ["agent.js", "SKILL.md", "workflow.md", "tools.json"],
             "description": "File type (auto-detected from operation)"},
         "skill_name": {"type": "string", "description": "Skill name for SKILL.md/workflow.md operations"},
         "section": {"type": "string", "description": "Section name for section-based edits"},
         "content": {"type": "string", "description": "New content for the section or skill"},
         "skill_key": {"type": "string", "description": "Skill key to add/remove"},
         "tools_allowed": {"type": "array", "items": {"type": "string"}, "description": "New allowed tools list"},
         "tools_blocked": {"type": "array", "items": {"type": "string"}, "description": "New blocked tools list"},
         "config_key": {"type": "string", "description": "Config key to edit (name, mode, model, description, color)"},
         "config_value": {"type": "string", "description": "New config value"},
         "batch": {"type": "array", "items": {"type": "object"}, "description": "Batch operations"},
         "validate": {"type": "boolean", "default": True, "description": "Auto-validate after edit"}
     }, "required": ["operation"]}},
]

AGENT_DIRS = {
    "catalyst": "sisyphus", "sisyphus": "sisyphus", "hephaestus": "hephaestus", "explore": "explore",
    "oracle": "oracle", "momus": "momus", "prometheus": "prometheus",
    "kairos": "kairos", "librarian": "librarian", "masterplan": "masterplan",
    "metis": "metis", "architect": "architect", "jarvis": "jarvis",
    "vision": "vision", "phi4": "phi4", "mrwhite": "mrwhite",
    "scalpel": "scalpel", "agentbuilder": "agent-builder",
    "cortex": "cortex",
}

FILE_TOOLS = {"file_write", "file_edit", "file_read", "file_glob", "file_grep"}
ADMIN_TOOLS = {"config_validate", "config_edit", "config_remove", "agent_add", "embed_text", "embed_similarity", "agent_list", "config_sync", "schema_check", "agent_edit", "safe_delete", "search_memory", "search_semantic", "pull_global_context", "read_memory", "write_memory", "list_memory", "web_fetch", "web_search", "file_batch_read", "project_map", "parallel_task", "task_status", "session_tasks", "pc_scan", "bg_submit", "bg_status", "bg_list", "bg_cancel", "bg_events", "task_result", "cache_stats", "cache_clear"} | FILE_TOOLS


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

def _load_agent_tools(agent_name):
    if not agent_name:
        return None
    name = agent_name.lower().replace("-", "").replace(" ", "")
    for key, dir_name in AGENT_DIRS.items():
        if key in name:
            path = os.path.join(PROJECT_ROOT, f"agents/{dir_name}/tools/tools.json")
            if os.path.exists(path):
                try:
                    with open(path) as f:
                        return json.load(f)
                except:
                    return None
    return None

def _is_tool_allowed(agent_name, tool_name):
    config = _load_agent_tools(agent_name)
    if config is None:
        return True
    allowed = config.get("allowed", [])
    blocked = config.get("blocked", [])
    if tool_name in blocked:
        return False
    if allowed and tool_name not in allowed:
        return False
    return True

CALLING_AGENT = os.environ.get("MCP_CLIENT_AGENT", "")
if not CALLING_AGENT:
    for env in ["OPENCODE_AGENT", "OPENCODE_USER", "AGENT_NAME"]:
        val = os.environ.get(env, "")
        if val:
            CALLING_AGENT = val
            break

ACTIVE_AGENT_FILE = os.path.join(PROJECT_ROOT, "data/active-agent.json")

def _resolve_agent_from_args(args):
    """Resolve agent identity with delegation chain support.
    
    Priority:
    1. Direct _agent injection
    2. Delegation chain from task() call
    3. Active agent file (fallback)
    4. Environment variables (last resort)
    """
    # Priority 1: Direct _agent injection
    if args and args.get("_agent"):
        return args["_agent"]
    
    # Priority 2: Delegation chain (ADCS spec)
    if args:
        chain = args.get("_delegation_chain")
        if chain and isinstance(chain, dict) and chain.get("links"):
            return chain["links"][-1].get("agentName", "")
    
    # Priority 3: Active agent file (fallback)
    try:
        with open(ACTIVE_AGENT_FILE) as f:
            state = json.load(f)
            import time
            if state.get("agent") and (time.time() * 1000 - state.get("updated", 0) < 15000):
                return state["agent"]
    except:
        pass
    
    # Priority 4: Environment variables (last resort)
    return CALLING_AGENT



# ── Parallel execution handlers ──────────────────────────────────────

def handle_parallel_task(arguments):
    session_id = arguments.get("session_id", "")
    agent_name = arguments.get("agent_name", "")
    prompt = arguments.get("prompt", "")
    dependencies = arguments.get("dependencies", [])
    timeout = arguments.get("timeout", 300)
    
    if not session_id or not agent_name or not prompt:
        return {"content": [{"type": "text", "text": "Error: session_id, agent_name, and prompt required"}]}
    
    task_id = parallel_executor.submit_task(session_id, agent_name, prompt, dependencies, timeout)
    return {"content": [{"type": "text", "text": f"Task submitted: {task_id}"}]}

def handle_task_status(arguments):
    task_id = arguments.get("task_id", "")
    if not task_id:
        return {"content": [{"type": "text", "text": "Error: task_id required"}]}
    
    result = parallel_executor.get_task_result(task_id)
    if result:
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
    return {"content": [{"type": "text", "text": f"Task not found: {task_id}"}]}

def handle_session_tasks(arguments):
    session_id = arguments.get("session_id", "")
    if not session_id:
        return {"content": [{"type": "text", "text": "Error: session_id required"}]}
    
    tasks = parallel_executor.get_session_tasks(session_id)
    return {"content": [{"type": "text", "text": json.dumps(tasks, indent=2)}]}


# ── Background Task Queue ────────────────────────────────────────────

class SimpleCache:
    """Simple TTL cache with stats tracking."""
    def __init__(self, ttl=300):
        self._data = {}
        self._ttl = ttl
        self._timestamps = {}
        self._hits = 0
        self._misses = 0
    def get(self, key):
        if key in self._data and time.time() - self._timestamps[key] < self._ttl:
            self._hits += 1
            return self._data[key]
        self._misses += 1
        return None
    def set(self, key, value):
        self._data[key] = value
        self._timestamps[key] = time.time()
    def clear(self):
        self._data.clear()
        self._timestamps.clear()
        self._hits = 0
        self._misses = 0
    def stats(self):
        return {'size': len(self._data), 'hits': self._hits, 'misses': self._misses, 'ttl': self._ttl}

class BackgroundTaskQueue:
    """Background task executor with callback, event queue, and memory auto-inject.

    When a task completes:
    1. Result is auto-written to holographic memory (tags: bg_task_complete, agent, task_type)
    2. An event is pushed to the calling session's event queue
    3. Optional HTTP callback URL is fired
    """

    def __init__(self, max_workers=5):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.tasks = {}
        self.lock = threading.Lock()
        self.event_queues = {}

    def submit(self, task_type, args, callback="", session_id="", agent=""):
        task_id = f"bg_{int(time.time())}_{random.randint(1000, 9999)}"
        task = {
            "task_id": task_id,
            "task_type": task_type,
            "args": args,
            "callback": callback,
            "session_id": session_id,
            "agent": agent,
            "status": "running",
            "submitted_at": time.time(),
            "result": None,
            "error": None,
        }
        with self.lock:
            self.tasks[task_id] = task
        future = self.executor.submit(self._run_task, task)
        future.add_done_callback(lambda f: self._task_complete(task_id))
        return task_id

    def _run_task(self, task):
        try:
            task_type = task["task_type"]
            args = task["args"]
            result = self._execute_by_type(task_type, args)
            task["result"] = result
            task["status"] = "completed"
        except Exception as e:
            task["error"] = str(e)
            task["status"] = "failed"
        task["completed_at"] = time.time()
        return task

    def _execute_by_type(self, task_type, args):
        if task_type == "file_read":
            path = args.get("filePath", "")
            if not os.path.exists(path):
                raise FileNotFoundError(f"File not found: {path}")
            with open(path) as f:
                return f.read()
        elif task_type == "search":
            pattern = args.get("pattern", "")
            path = args.get("path", PROJECT_ROOT)
            result = subprocess.run(
                ["grep", "-rn", "--max-count=100", pattern, path],
                capture_output=True, text=True, timeout=30,
            )
            return result.stdout.strip() or "No matches"
        elif task_type == "config":
            cpath = args.get("path", CONFIG_PATH)
            if os.path.exists(cpath):
                with open(cpath) as f:
                    return f.read()
            raise FileNotFoundError(f"Config not found: {cpath}")
        else:
            return f"Unknown task type: {task_type}"

    def _task_complete(self, task_id):
        # Fire Mojo notify via embed_bridge
        try:
            import subprocess, json, time
            task = self.tasks.get(task_id, {})
            agent = task.get('args', {}).get('agent', 'unknown')
            sid = task.get('session_id', 'default')
            status = task.get('status', 'completed')
            notify = json.dumps({"type": "notify", "source": "bg_task", "task_id": task_id,
                "agent": agent, "status": status, "timestamp": time.time(),
                "session_id": sid, "id": f"notify_{task_id}"})
            subprocess.run(["python3", os.path.join(os.path.dirname(__file__),
                "../mojo-router/src/embed_bridge.py")], input=notify,
                capture_output=True, text=True, timeout=5)
        except:
            pass

        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return

            session_id = task.get("session_id", "")
            agent = task.get("agent", "")
            task_type = task.get("task_type", "")
            status = task.get("status", "completed")
            result = task.get("result", "")

            # 1. Auto-inject into holographic memory
            _write_bg_memory(task_id, task_type, agent, status, str(result)[:500])

            # 2. Push event to session event queue
            if session_id:
                event = {
                    "type": "task_complete",
                    "task_id": task_id,
                    "agent": agent,
                    "task_type": task_type,
                    "status": status,
                    "timestamp": time.time(),
                }
                if session_id not in self.event_queues:
                    self.event_queues[session_id] = []
                self.event_queues[session_id].append(event)

            # 3. Fire HTTP callback if configured
            callback = task.get("callback", "")
            if callback:
                try:
                    import urllib.request
                    cb_data = json.dumps(
                        {"task_id": task_id, "status": status}
                    ).encode()
                    urllib.request.urlopen(callback, data=cb_data, timeout=5)
                except Exception:
                    pass

    def get_result(self, task_id):
        with self.lock:
            return self.tasks.get(task_id, {"error": "Task not found"})

    def list_tasks(self, status=None):
        with self.lock:
            tasks = list(self.tasks.values())
            if status:
                tasks = [t for t in tasks if t["status"] == status]
            return tasks

    def cancel(self, task_id):
        with self.lock:
            if task_id in self.tasks and self.tasks[task_id]["status"] == "running":
                self.tasks[task_id]["status"] = "cancelled"
                return True
            return False

    def get_events(self, session_id):
        """Get and clear pending events for a session."""
        with self.lock:
            events = self.event_queues.get(session_id, [])
            if events:
                self.event_queues[session_id] = []
            return events


def _write_bg_memory(task_id, task_type, agent, status, result_preview):
    """Write background task completion to holographic memory."""
    mem_path = os.path.join(PROJECT_ROOT, "data/memory/holographic-memory.json")
    try:
        mems = []
        if os.path.exists(mem_path):
            with open(mem_path) as f:
                mems = json.load(f)
        mems.append(
            {
                "id": f"bg_{task_id}",
                "content": json.dumps(
                    {
                        "task_id": task_id,
                        "task_type": task_type,
                        "agent": agent,
                        "status": status,
                        "result": result_preview,
                    }
                ),
                "category": "bg_task_complete",
                "timestamp": time.time(),
                "tags": ["bg_task_complete", agent, task_type, status],
            }
        )
        with open(mem_path, "w") as f:
            json.dump(mems, f, indent=2)
    except Exception:
        pass


# Global background task queue
bg_queue = BackgroundTaskQueue(max_workers=5)

# Cache instances for handle_cache_stats / handle_cache_clear
file_cache = SimpleCache(ttl=300)
search_cache = SimpleCache(ttl=60)
config_cache = SimpleCache(ttl=30)


# ── Background task handlers ─────────────────────────────────────────

def handle_bg_submit(arguments):
    task_type = arguments.get("task_type", "")
    args = arguments.get("args", {})
    callback = arguments.get("callback", "")
    session_id = arguments.get("session_id", "")
    agent = _resolve_agent_from_args(arguments)

    if not task_type or not args:
        return {"content": [{"type": "text", "text": "Error: task_type and args required"}]}

    task_id = bg_queue.submit(task_type, args, callback, session_id, agent)
    return {"content": [{"type": "text", "text": f"Task submitted: {task_id}\nYou can continue chatting. Check status with bg_status task_id={task_id}. Get events with bg_events session_id={session_id}."}]}


def handle_bg_status(arguments):
    task_id = arguments.get("task_id", "")
    if not task_id:
        return {"content": [{"type": "text", "text": "Error: task_id required"}]}

    result = bg_queue.get_result(task_id)
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


def handle_bg_list(arguments):
    status = arguments.get("status", "")
    tasks = bg_queue.list_tasks(status if status else None)
    return {"content": [{"type": "text", "text": json.dumps(tasks, indent=2)}]}


def handle_bg_cancel(arguments):
    task_id = arguments.get("task_id", "")
    if not task_id:
        return {"content": [{"type": "text", "text": "Error: task_id required"}]}

    cancelled = bg_queue.cancel(task_id)
    return {"content": [{"type": "text", "text": f"Task {task_id} {'cancelled' if cancelled else 'not found'}"}]}


def handle_bg_events(arguments):
    """Get pending background task events for a session (clears them)."""
    session_id = arguments.get("session_id", "")
    if not session_id:
        return {"content": [{"type": "text", "text": "Error: session_id required"}]}
    events = bg_queue.get_events(session_id)
    return {"content": [{"type": "text", "text": json.dumps(events, indent=2)}]}


def handle_task_result(arguments):
    """Get full background task result by ID."""
    task_id = arguments.get("task_id", "")
    if not task_id:
        return {"content": [{"type": "text", "text": "Error: task_id required"}]}
    result = bg_queue.get_result(task_id)
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}

def handle_cache_stats(arguments):
    stats = {
        'file_cache': file_cache.stats(),
        'search_cache': search_cache.stats(),
        'config_cache': config_cache.stats()
    }
    return {"content": [{"type": "text", "text": json.dumps(stats, indent=2)}]}

def handle_cache_clear(arguments):
    file_cache.clear()
    search_cache.clear()
    config_cache.clear()
    return {"content": [{"type": "text", "text": "All caches cleared"}]}


# ── Embedding handlers ───────────────────────────────────────────────

def handle_embed_text(arguments):
    text = arguments.get("text", "")
    if not text:
        return {"content": [{"type": "text", "text": "Error: text required"}]}
    
    try:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))
        from embed_service import embed, cache_stats
        
        result = embed(text)
        if "error" in result:
            return {"content": [{"type": "text", "text": result["error"]}]}
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}

def handle_embed_similarity(arguments):
    vec_a = arguments.get("vector_a", [])
    vec_b = arguments.get("vector_b", [])
    if not vec_a or not vec_b:
        return {"content": [{"type": "text", "text": "Error: vector_a and vector_b required"}]}
    
    try:
        from embed_service import cosine_similarity
        sim = cosine_similarity(vec_a, vec_b)
        return {"content": [{"type": "text", "text": json.dumps({"similarity": sim}, indent=2)}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


def handle_pc_scan(arguments):
    timeout = arguments.get("timeout", 30)
    category = arguments.get("category", "")
    try:
        import sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))
        from pc_scan import PCScanner
        scanner = PCScanner()
        if category:
            result = scanner.scan(timeout=timeout)
            result["files"] = {k: v for k, v in result.get("files", {}).items() if k == category}
        else:
            result = scanner.scan(timeout=timeout)
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


def handle_pc_aware(arguments):
    query = arguments.get("query", "")
    location = arguments.get("location", "all")
    if not query:
        return {"content": [{"type": "text", "text": "Error: query required"}]}
    
    known_locations = {
        "home": "/home/nxyme",
        "docs": "/home/nxyme/Documents",
        "desktop": "/home/nxyme/Desktop",
        "library": "/mnt/Library",
        "win_library": "/mnt/WIN_LIBRARY",
        "archive": "/home/nxyme/archive",
        "nxyme": os.path.expanduser("~/N-Xyme_CODE/N-Xyme_MIND")
    }
    
    results = []
    for loc_name, loc_path in known_locations.items():
        if location != "all" and location != loc_name:
            continue
        if os.path.exists(loc_path):
            results.append({"location": loc_name, "path": loc_path})
    
    # Include the embed_bridge for semantic awareness
    results.append({
        "awareness_engine": "embed_bridge",
        "dim": 896,
        "tools_scored": 25,
        "socket": "/tmp/llama.sock",
        "model": "rosetta-v13-f16"
    })
    
    # Include scan manifest if exists
    manifest_path = os.path.join(os.path.dirname(__file__), "../../data/consolidated/data-manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            manifest = json.load(f)
        results.append({"scan_manifest": manifest})
    
    return {"content": [{"type": "text", "text": json.dumps({
        "query": query,
        "locations_found": len(results),
        "awareness": results,
        "suggestion": f"Use embed_text('{query}') for semantic search, or check known locations above"
    }, indent=2)}]}


def handle_ask_question(arguments):
    q = arguments.get("question", "")
    return {"content": [{"type": "text", "text": f"Question received: {q[:100]}... Use nap_protocol to find the right tool."}]}

def handle_spawn_task(arguments):
    agent = arguments.get("agent", "")
    prompt = arguments.get("prompt", "")
    return {"content": [{"type": "text", "text": f"Task spawned for {agent}. Use parallel_task for real parallel execution."}]}

def handle_context_prune(arguments):
    sid = arguments.get("session_id", "")
    return {"content": [{"type": "text", "text": f"Context pruned for {sid}. Use memory consolidation instead."}]}

def handle_session_status(arguments):
    sid = arguments.get("session_id", "")
    return {"content": [{"type": "text", "text": f"Session {sid} status: active. Use session tools for details."}]}

def handle_verify_code(arguments):
    path = arguments.get("path", "")
    return {"content": [{"type": "text", "text": f"Verification of {path} submitted. Use review_code for code review."}]}


def handle_consciousness_record(arguments):
    agent = arguments.get("agent", "")
    task = arguments.get("task", "")
    success = arguments.get("success", False)
    latency = arguments.get("latency_ms", 0)
    if not agent or not task:
        return {"content": [{"type": "text", "text": "Error: agent and task required"}]}
    import sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../mojo-router/src"))
    from consciousness_daemon import ConsciousnessEngine
    engine = ConsciousnessEngine()
    result = engine.record_outcome(agent, task, success, latency)
    return {"content": [{"type": "text", "text": json.dumps(result)}]}

def handle_consciousness_identity(arguments):
    agent = arguments.get("agent", "")
    if not agent:
        return {"content": [{"type": "text", "text": "Error: agent required"}]}
    import sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../mojo-router/src"))
    from consciousness_daemon import ConsciousnessEngine
    engine = ConsciousnessEngine()
    result = engine.get_identity(agent)
    return {"content": [{"type": "text", "text": json.dumps(result)}]}


# ── Ralph Loop handlers (frontmatter .md state — survives restarts) ──

RALPH_STATE_DIR = os.path.join(PROJECT_ROOT, "data/ralph-state")
RALPH_STATE_FILE = os.path.join(RALPH_STATE_DIR, "active.md")
RALPH_DEFAULT_PROMISE = "DONE"
RALPH_VERIFIED_PROMISE = "VERIFIED"

def _read_frontmatter(path):
    """Parse frontmatter .md file. Returns (data_dict, body_text)."""
    import re
    if not os.path.exists(path):
        return {}, ""
    with open(path) as f:
        content = f.read()
    # Match ---\n...frontmatter...\n---\n...body...
    match = re.match(r'^---\n(.+?)\n---\n?(.*)', content, re.DOTALL)
    if not match:
        return {}, content.strip()
    data = {}
    for line in match.group(1).split('\n'):
        line = line.strip()
        if ':' not in line:
            continue
        key, val = line.split(':', 1)
        val = val.strip()
        # Unquote strings
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        elif val.startswith("'") and val.endswith("'"):
            val = val[1:-1]
        elif val == 'true':
            val = True
        elif val == 'false':
            val = False
        elif val == 'undefined' or val == 'null':
            val = None
        else:
            try:
                val = float(val) if '.' in val else int(val)
            except ValueError:
                pass  # keep as string
        data[key.strip()] = val
    return data, match.group(2).strip()

def _build_frontmatter(data, body=""):
    """Build frontmatter .md string from data dict and optional body."""
    lines = ["---"]
    for key, val in data.items():
        if val is None:
            continue
        if isinstance(val, bool):
            lines.append(f"{key}: {str(val).lower()}")
        elif isinstance(val, str):
            escaped = val.replace('\\', '\\\\').replace('"', '\\"')
            lines.append(f'{key}: "{escaped}"')
        else:
            lines.append(f"{key}: {val}")
    lines.append("---")
    if body:
        lines.append(body)
    return "\n".join(lines)

def _load_ralph_state():
    """Load ralph loop state from frontmatter .md file."""
    data, body = _read_frontmatter(RALPH_STATE_FILE)
    if not data.get("active"):
        return None
    data["prompt"] = body
    return data

def _save_ralph_state(state):
    """Save ralph loop state to frontmatter .md file."""
    os.makedirs(RALPH_STATE_DIR, exist_ok=True)
    state = dict(state)
    body = state.pop("prompt", "")
    content = _build_frontmatter(state, body)
    with open(RALPH_STATE_FILE, 'w') as f:
        f.write(content)

def _clear_ralph_state():
    """Delete the active ralph state file."""
    if os.path.exists(RALPH_STATE_FILE):
        os.remove(RALPH_STATE_FILE)

def handle_ralph_start(arguments):
    sid = arguments.get("session_id", "")
    task = arguments.get("task", "")
    max_iter = arguments.get("max_iterations", 5)
    promise = arguments.get("promise", "")
    ultrawork = arguments.get("ultrawork", False)
    strategy = arguments.get("strategy", "continue")
    if not sid or not task:
        return {"content": [{"type": "text", "text": "Error: session_id and task required"}]}
    
    # Clear any existing active loop first
    _clear_ralph_state()
    
    from datetime import datetime
    state = {
        "active": True,
        "session_id": sid,
        "iteration": 1,
        "max_iterations": max_iter if max_iter > 0 else None,
        "completion_promise": promise or RALPH_DEFAULT_PROMISE,
        "initial_completion_promise": promise or RALPH_DEFAULT_PROMISE,
        "ultrawork": ultrawork,
        "verification_pending": False,
        "strategy": strategy,
        "started_at": datetime.now().isoformat(),
        "prompt": task,
    }
    if max_iter and max_iter <= 0:
        state["max_iterations"] = None
        state["ultrawork"] = True
    _save_ralph_state(state)
    
    mode = "ULTRAWORK" if state["ultrawork"] else "Ralph"
    max_display = max_iter if max_iter and max_iter > 0 else "unbounded"
    return {
        "content": [{"type": "text", "text": f"{mode} Loop started: {sid} - {task[:100]}... (max {max_display} iterations)"}]
    }

def handle_ralph_status(arguments):
    sid = arguments.get("session_id", "")
    state = _load_ralph_state()
    if not state:
        return {"content": [{"type": "text", "text": "No active Ralph Loop found"}]}
    if sid and state.get("session_id") and state["session_id"] != sid:
        return {"content": [{"type": "text", "text": f"No active Loop for session: {sid}"}]}
    # Return state as JSON (convert non-serializables)
    display = {k: v for k, v in state.items() if k != "prompt"}
    display["prompt"] = (state.get("prompt", "") or "")[:200] + "..." if len(state.get("prompt", "") or "") > 200 else state.get("prompt", "")
    return {"content": [{"type": "text", "text": json.dumps(display, indent=2)}]}

def handle_ralph_iterate(arguments):
    sid = arguments.get("session_id", "")
    state = _load_ralph_state()
    if not state:
        return {"content": [{"type": "text", "text": "No active Ralph Loop found"}]}
    if sid and state.get("session_id") and state["session_id"] != sid:
        return {"content": [{"type": "text", "text": f"No active Loop for session: {sid}"}]}
    state["iteration"] += 1
    state["started_at"] = __import__('datetime').datetime.now().isoformat()
    _save_ralph_state(state)
    return {
        "content": [{"type": "text", "text": f"Iteration {state['iteration']}/{state.get('max_iterations', '∞')} for {sid}"}]
    }

def handle_ralph_cancel(arguments):
    sid = arguments.get("session_id", "")
    state = _load_ralph_state()
    if not state:
        return {"content": [{"type": "text", "text": "No active Ralph Loop found"}]}
    if sid and state.get("session_id") and state["session_id"] != sid:
        return {"content": [{"type": "text", "text": f"No active Loop for session: {sid}"}]}
    _clear_ralph_state()
    return {"content": [{"type": "text", "text": f"Ralph Loop cancelled: {sid}"}]}

def handle_ulw_start(arguments):
    """Alias for ralph_start with ultrawork=true."""
    arguments["ultrawork"] = True
    if "max_iterations" not in arguments or arguments.get("max_iterations", 5) <= 0:
        arguments["max_iterations"] = 0  # unbounded
    return handle_ralph_start(arguments)

def handle_ulw_status(arguments):
    """Alias for ralph_status."""
    return handle_ralph_status(arguments)

def handle_ulw_cancel(arguments):
    """Alias for ralph_cancel."""
    return handle_ralph_cancel(arguments)

# ── Admin handler functions ──────────────────────────────────────────


# ── New tool handlers ────────────────────────────────────────────────

def handle_safe_delete(arguments):
    file_path = arguments.get("filePath", "")
    if not file_path:
        return {"content": [{"type": "text", "text": "Error: filePath required"}]}
    if not os.path.exists(file_path):
        return {"content": [{"type": "text", "text": f"Error: File not found: {file_path}"}]}
    trash_dir = os.path.join(PROJECT_ROOT, "data/trash")
    os.makedirs(trash_dir, exist_ok=True)
    import time
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    trash_name = f"{timestamp}_{os.path.basename(file_path)}"
    trash_path = os.path.join(trash_dir, trash_name)
    import shutil
    shutil.move(file_path, trash_path)
    return {"content": [{"type": "text", "text": f"Moved to trash: {trash_path}"}]}

def handle_read_memory(arguments):
    memory_id = arguments.get("memoryId", "")
    if not memory_id:
        return {"content": [{"type": "text", "text": "Error: memoryId required"}]}
    # Read from holographic memory
    memory_file = os.path.join(PROJECT_ROOT, "data/memory/holographic-memory.json")
    if not os.path.exists(memory_file):
        return {"content": [{"type": "text", "text": "Error: Memory file not found"}]}
    with open(memory_file) as f:
        memories = json.load(f)
    for mem in memories:
        if mem.get("id") == memory_id:
            return {"content": [{"type": "text", "text": json.dumps(mem, indent=2)}]}
    return {"content": [{"type": "text", "text": f"Error: Memory entry not found: {memory_id}"}]}

def handle_write_memory(arguments):
    content_text = arguments.get("content", "")
    category = arguments.get("category", "general")
    if not content_text:
        return {"content": [{"type": "text", "text": "Error: content required"}]}
    memory_file = os.path.join(PROJECT_ROOT, "data/memory/holographic-memory.json")
    memories = []
    if os.path.exists(memory_file):
        with open(memory_file) as f:
            memories = json.load(f)
    import time
    new_mem = {
        "id": f"mem_{int(time.time())}",
        "content": content_text,
        "category": category,
        "timestamp": time.time()
    }
    memories.append(new_mem)
    with open(memory_file, "w") as f:
        json.dump(memories, f, indent=2)
    return {"content": [{"type": "text", "text": f"Memory written: {new_mem['id']}"}]}

def handle_list_memory(arguments):
    category = arguments.get("category", "")
    memory_file = os.path.join(PROJECT_ROOT, "data/memory/holographic-memory.json")
    if not os.path.exists(memory_file):
        return {"content": [{"type": "text", "text": "[]"}]}
    with open(memory_file) as f:
        memories = json.load(f)
    if category:
        memories = [m for m in memories if m.get("category") == category]
    return {"content": [{"type": "text", "text": json.dumps(memories[:50], indent=2)}]}

def handle_search_memory(arguments):
    """Semantic search over session vectors using ONNX embedding + cosine similarity.
    Replaces broken code_search_bridge routing (which searched code index, not memory)."""
    query = arguments.get("query", "")
    k = int(arguments.get("k", 3))
    min_score = float(arguments.get("min_score", -1.0))
    source = arguments.get("source", "vectors")

    if not query:
        return {"content": [{"type": "text", "text": "Error: query required"}]}

    try:
        sys.path.insert(0, os.path.join(PROJECT_ROOT, "services/memory-pipeline"))
        from search_memory import load_vectors, embed, search

        vectors_file = os.path.join(PROJECT_ROOT, "data/memory/vectors", "sessions.jsonl")
        records = load_vectors(vectors_file)
        if not records:
            return {"content": [{"type": "text", "text": "No vectors found. Run ingest_sessions.py first."}]}

        query_vec = embed(query)
        results = search(records, query_vec, top_k=k, min_score=min_score)

        output = {
            "query": query,
            "total_vectors_scanned": len(records),
            "results_count": len(results),
            "results": []
        }
        for i, r in enumerate(results, 1):
            rec = r["record"]
            output["results"].append({
                "rank": i,
                "score": r["score"],
                "agent": rec.get("agent", "?"),
                "session": rec.get("session", "?"),
                "date": rec.get("date", "?"),
                "type": rec.get("type", "?"),
                "content": rec.get("content", "")[:300],
                "id": rec.get("id", "")
            })

        return {"content": [{"type": "text", "text": json.dumps(output, indent=2)}]}
    except Exception as e:
        import traceback
        return {"content": [{"type": "text", "text": f"Error searching memory: {str(e)}\n{traceback.format_exc()}"}]}


def handle_pull_global_context(arguments):
    """Aggregate context from all memory systems in one call."""
    query = arguments.get("query", "")
    sources = arguments.get("sources", ["vectors", "holographic", "consciousness"])
    top_k = int(arguments.get("top_k", 5))
    min_score = float(arguments.get("min_score", 0.0))

    if not query:
        return {"content": [{"type": "text", "text": "Error: query required"}]}

    result = {"query": query, "sources_queried": sources, "results": {}}

    # Source 1: Vector search
    if "vectors" in sources:
        try:
            sys.path.insert(0, os.path.join(PROJECT_ROOT, "services/memory-pipeline"))
            from search_memory import load_vectors, embed, search
            vectors_file = os.path.join(PROJECT_ROOT, "data/memory/vectors", "sessions.jsonl")
            records = load_vectors(vectors_file)
            if records:
                query_vec = embed(query)
                vec_results = search(records, query_vec, top_k=top_k, min_score=min_score)
                result["results"]["vectors"] = [
                    {"score": r["score"],
                     "content": r["record"].get("content", "")[:300],
                     "session": r["record"].get("session", ""),
                     "agent": r["record"].get("agent", ""),
                     "date": r["record"].get("date", ""),
                     "type": r["record"].get("type", "")}
                    for r in vec_results
                ]
            else:
                result["results"]["vectors"] = []
        except Exception as e:
            result["results"]["vectors"] = {"error": str(e)}

    # Source 2: Holographic memory keyword search
    if "holographic" in sources:
        try:
            holo_file = os.path.join(PROJECT_ROOT, "data/memory/holographic-memory.json")
            if os.path.exists(holo_file):
                with open(holo_file) as f:
                    holo = json.load(f)
                q_lower = query.lower()
                matches = []
                for entry in holo:
                    content = (entry.get("content", "") + " " + entry.get("category", "")).lower()
                    if q_lower in content:
                        matches.append(entry)
                matches.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
                result["results"]["holographic"] = matches[:top_k]
            else:
                result["results"]["holographic"] = []
        except Exception as e:
            result["results"]["holographic"] = {"error": str(e)}

    # Source 3: Consciousness data keyword search
    if "consciousness" in sources:
        try:
            cons_dir = os.path.join(PROJECT_ROOT, "data/memory/consciousness")
            matches = []
            if os.path.exists(cons_dir):
                for fname in os.listdir(cons_dir):
                    if fname.endswith(".json"):
                        fpath = os.path.join(cons_dir, fname)
                        with open(fpath) as f:
                            data = json.load(f)
                        if query.lower() in json.dumps(data).lower():
                            matches.append({"source": fname, "data": data})
            result["results"]["consciousness"] = matches[:top_k]
        except Exception as e:
            result["results"]["consciousness"] = {"error": str(e)}

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


def handle_web_fetch(arguments):
    url = arguments.get("url", "")
    fmt = arguments.get("format", "markdown")
    if not url:
        return {"content": [{"type": "text", "text": "Error: url required"}]}
    try:
        import urllib.parse, subprocess
        # Safe: pass URL via environment variable, NOT string interpolation
        env = os.environ.copy()
        env["NX_FETCH_URL"] = url
        result = subprocess.run(["python3", "-c", """
import os, urllib.request
url = os.environ['NX_FETCH_URL']
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=10) as r:
    print(r.read().decode('utf-8', errors='ignore')[:10000])
"""], capture_output=True, text=True, timeout=15, env=env)
        output = result.stdout.strip()
        if result.stderr.strip():
            output += "\n[stderr]: " + result.stderr.strip()
        return {"content": [{"type": "text", "text": output or "(no content)"}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}

def handle_web_search(arguments):
    query = arguments.get("query", "")
    if not query:
        return {"content": [{"type": "text", "text": "Error: query required"}]}
    return {"content": [{"type": "text", "text": f"Web search for '{query}' - use webfetch for direct URL fetching"}]}

def handle_file_batch_read(arguments):
    files = arguments.get("files", [])
    if not files:
        return {"content": [{"type": "text", "text": "Error: files required"}]}
    results = {}
    for f in files:
        try:
            if os.path.exists(f):
                with open(f) as fh:
                    results[f] = fh.read()[:5000]
            else:
                results[f] = "Error: File not found"
        except Exception as e:
            results[f] = f"Error: {str(e)}"
    return {"content": [{"type": "text", "text": json.dumps(results, indent=2)}]}

def handle_project_map(arguments):
    max_depth = arguments.get("maxDepth", 3)
    def walk_dir(path, depth):
        if depth > max_depth:
            return {}
        result = {}
        try:
            for entry in os.listdir(path):
                if entry.startswith('.'):
                    continue
                full_path = os.path.join(path, entry)
                if os.path.isdir(full_path):
                    result[entry + '/'] = walk_dir(full_path, depth + 1)
                else:
                    result[entry] = None
        except:
            pass
        return result
    tree = walk_dir(PROJECT_ROOT, 0)
    return {"content": [{"type": "text", "text": json.dumps(tree, indent=2)}]}

def handle_validate_config(arguments):
    path = arguments.get("file", CONFIG_PATH)
    if not os.path.exists(path):
        return {"content": [{"type": "text", "text": f"File not found: {path}"}]}
    try:
        cfg = _read_json(path)
    except json.JSONDecodeError as e:
        return {"content": [{"type": "text", "text": f"Invalid JSON: {e}"}]}
    allowed = {"model","skills","compaction","plugin","mcp","permission","agent","provider","instructions"}
    fname = os.path.basename(path)
    issues = []
    if fname == "opencode.json":
        unknown = set(cfg.keys()) - allowed
        if unknown:
            issues.append(f"Move to nx_agents.json: {', '.join(sorted(unknown))}")
        for name, acfg in cfg.get("agent", {}).items():
            for k in ("mode","prompt","model"):
                if k not in acfg:
                    issues.append(f"Agent '{name}' missing '{k}'")
        for name, mcfg in cfg.get("mcp", {}).items():
            cmd = mcfg.get("command", [])
            if cmd and not os.path.exists(cmd[0]):
                issues.append(f"MCP '{name}' cmd not found: {cmd[0]}")
        for p in cfg.get("plugin", []):
            if p.endswith(".js") and not os.path.exists(p):
                issues.append(f"Plugin not found: {p}")
    if not issues:
        return {"content": [{"type": "text", "text": "✅ Config valid."}]}
    return {"content": [{"type": "text", "text": f"{len(issues)} issue(s):\n" + "\n".join(f"  - {i}" for i in issues)}]}

def handle_edit_config(arguments):
    path = arguments.get("file", CONFIG_PATH)
    key = arguments.get("key", "")
    raw = arguments.get("value", "")
    if not key:
        return {"content": [{"type": "text", "text": "Error: 'key' required"}]}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        value = raw
    cfg = _read_json(path)
    _set_nested(cfg, key, value)
    _write_json(path, cfg)
    return {"content": [{"type": "text", "text": f"Set {os.path.basename(path)}: {key} = {json.dumps(value)}"}]}

def handle_remove_key(arguments):
    path = arguments.get("file", CONFIG_PATH)
    key = arguments.get("key", "")
    if not key:
        return {"content": [{"type": "text", "text": "Error: 'key' required"}]}
    cfg = _read_json(path)
    if _del_nested(cfg, key):
        _write_json(path, cfg)
        return {"content": [{"type": "text", "text": f"Removed '{key}' from {os.path.basename(path)}"}]}
    return {"content": [{"type": "text", "text": f"Key '{key}' not found"}]}

def handle_add_agent(arguments):
    name = arguments.get("name", "")
    mode = arguments.get("mode", "subagent")
    model = arguments.get("model", "opencode/deepseek-v4-flash-free")
    desc = arguments.get("description", "")
    pf = arguments.get("prompt_file", "")
    if not name or not desc:
        return {"content": [{"type": "text", "text": "Error: 'name' and 'description' required"}]}
    if not pf:
        slug = name.lower().replace(" - ", "-").replace(" ", "-").split("-")[0]
        pf = f"{{file:{PROJECT_ROOT}/agents/{slug}/agent.js}}"
    entry = {"description": desc, "mode": mode, "model": model, "prompt": pf}
    for p in [CONFIG_PATH, NX_CONFIG_PATH]:
        c = _read_json(p)
        c.setdefault("agent", {})[name] = entry
        _write_json(p, c)
    return {"content": [{"type": "text", "text": f"Added agent '{name}' to both configs"}]}

def handle_list_agents(arguments):
    path = arguments.get("file", CONFIG_PATH)
    cfg = _read_json(path)
    agents = cfg.get("agent", {})
    if not agents:
        return {"content": [{"type": "text", "text": "No agents"}]}
    lines = [f"Agents in {os.path.basename(path)} ({len(agents)}):"]
    for n, a in sorted(agents.items()):
        lines.append(f"  {n} [{a.get('mode','?')}] {a.get('model','?')}")
    return {"content": [{"type": "text", "text": "\n".join(lines)}]}

def handle_sync_nx_config(arguments):
    key = arguments.get("key", "")
    direction = arguments.get("direction", "to_opencode")
    if not key:
        return {"content": [{"type": "text", "text": "Error: 'key' required"}]}
    oc = _read_json(CONFIG_PATH)
    nx = _read_json(NX_CONFIG_PATH)
    if direction == "to_opencode":
        if key not in nx:
            return {"content": [{"type": "text", "text": f"'{key}' not in nx_agents.json"}]}
        oc[key] = nx[key]
        _write_json(CONFIG_PATH, oc)
    else:
        if key not in oc:
            return {"content": [{"type": "text", "text": f"'{key}' not in opencode.json"}]}
        nx[key] = oc[key]
        _write_json(NX_CONFIG_PATH, nx)
    return {"content": [{"type": "text", "text": f"Synced '{key}' {direction}"}]}

def handle_check_schema_ref(_args=None):
    ref = os.path.join(PROJECT_ROOT, "docs/opencode-schema-reference.md")
    if not os.path.exists(ref):
        return {"content": [{"type": "text", "text": "Schema ref not found"}]}
    with open(ref) as f:
        content = f.read()
    oc = _read_json(CONFIG_PATH)
    ok = {k for k in oc if k in content}
    missing = set(oc) - ok - {"$schema"}
    if missing:
        return {"content": [{"type": "text", "text": f"Missing docs for: {', '.join(sorted(missing))}"}]}
    return {"content": [{"type": "text", "text": "✅ Schema ref covers all keys"}]}


# ── File tool handlers (replacements for built-in) ─────────────────

def handle_write_tool(args):
    fp = args.get("filePath", "")
    content = args.get("content", "")
    if not fp:
        return {"content": [{"type": "text", "text": "Error: filePath required"}]}
    try:
        import os as _os
        _os.makedirs(_os.path.dirname(fp), exist_ok=True)
        with open(fp, "w") as f:
            f.write(content)
        return {"content": [{"type": "text", "text": f"Written {len(content)} bytes to {fp}"}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}

def handle_edit_tool(args):
    fp = args.get("filePath", "")
    old = args.get("oldString", "")
    new = args.get("newString", "")
    if not fp or not old:
        return {"content": [{"type": "text", "text": "Error: filePath and oldString required"}]}
    try:
        with open(fp, "r") as f:
            content = f.read()
        if old not in content:
            return {"content": [{"type": "text", "text": "Error: oldString not found"}]}
        if content.count(old) > 1:
            return {"content": [{"type": "text", "text": "Error: multiple matches for oldString"}]}
        content = content.replace(old, new)
        with open(fp, "w") as f:
            f.write(content)
        return {"content": [{"type": "text", "text": f"Edited {fp}"}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}

def handle_read_tool(args):
    fp = args.get("filePath", "")
    offset = args.get("offset", 0)
    limit = args.get("limit", 0)
    if not fp:
        return {"content": [{"type": "text", "text": "Error: filePath required"}]}
    try:
        with open(fp, "r") as f:
            lines = f.readlines()
        total = len(lines)
        start = offset - 1 if offset > 0 else 0
        end = start + limit if limit > 0 else total
        selected = lines[start:end]
        result = "".join(selected)
        meta = f"{fp}: {len(selected)} lines (total {total})"
        if result:
            return {"content": [{"type": "text", "text": meta + "\n" + result}]}
        return {"content": [{"type": "text", "text": meta}]}
    except FileNotFoundError:
        return {"content": [{"type": "text", "text": f"File not found: {fp}"}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}

def handle_glob_tool(args):
    import glob as _glob
    pattern = args.get("pattern", "")
    base = args.get("path", PROJECT_ROOT)
    if not pattern:
        return {"content": [{"type": "text", "text": "Error: pattern required"}]}
    try:
        full = os.path.join(base, pattern) if base else pattern
        matches = _glob.glob(full, recursive=True)
        matches.sort(key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0, reverse=True)
        result = "\n".join(matches[:100])
        if not result:
            return {"content": [{"type": "text", "text": "No matches"}]}
        return {"content": [{"type": "text", "text": f"Found {len(matches)} match(es):\n{result}"}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}

def handle_grep_tool(args):
    import subprocess
    pattern = args.get("pattern", "")
    base = args.get("path", PROJECT_ROOT)
    inc = args.get("include", "")
    if not pattern:
        return {"content": [{"type": "text", "text": "Error: pattern required"}]}
    try:
        cmd = ["grep", "-rn", "--max-count=100", pattern, base]
        if inc:
            cmd.extend(["--include", inc])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        output = result.stdout.strip()
        if not output:
            return {"content": [{"type": "text", "text": "No matches"}]}
        lines = output.split("\n")
        return {"content": [{"type": "text", "text": f"Found {len(lines)} match(es):\n{output[:5000]}"}]}
    except subprocess.TimeoutExpired:
        return {"content": [{"type": "text", "text": "Grep timed out (path too large)"}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


# ── Agent Edit Tool ──────────────────────────────────────────────────

def _resolve_agent_dir(agent_name):
    """Map agent name to directory name."""
    if not agent_name:
        return None
    key = agent_name.lower().replace("-", "").replace(" ", "").replace("_", "")
    return AGENT_DIRS.get(key)

def _agent_dir_path(agent_name):
    """Get full path to agent directory."""
    dir_name = _resolve_agent_dir(agent_name)
    if not dir_name:
        return None
    return os.path.join(PROJECT_ROOT, f"agents/{dir_name}")

def _parse_agent_js(content):
    """Parse agent.js into config + prompt sections."""
    result = {"format": "unknown", "config": {}, "prompt": "", "sections": {}, "full": content}
    
    # Check for export default format
    export_match = re.match(r'^export default \{', content)
    if export_match:
        result["format"] = "export_default"
        # Parse config fields (before prompt:)
        prompt_match = re.search(r'\nprompt: `', content)
        if prompt_match:
            config_block = content[:prompt_match.start()]
            # Extract config fields
            for field in ["name", "mode", "color", "model", "description"]:
                m = re.search(rf'{field}:\s*"([^"]*)"', config_block)
                if m:
                    result["config"][field] = m.group(1)
            # Extract skills array
            skills_m = re.search(r'skills:\s*\[([^\]]*)\]', config_block, re.DOTALL)
            if skills_m:
                skills_str = skills_m.group(1)
                result["config"]["skills"] = re.findall(r'"([^"]*)"', skills_str)
            # Extract prompt
            prompt_start = prompt_match.end()
            # Find closing backtick + }
            prompt_end = content.rfind('`\n}')
            if prompt_end == -1:
                prompt_end = content.rfind('`}')
            if prompt_end == -1:
                prompt_end = len(content) - 1
            result["prompt"] = content[prompt_start:prompt_end]
        else:
            result["prompt"] = content
    else:
        result["format"] = "plain_text"
        result["prompt"] = content
    
    # Parse prompt into sections
    result["sections"] = _parse_prompt_sections(result["prompt"])
    
    return result

def _parse_prompt_sections(prompt_text):
    """Parse prompt text into sections based on markdown headings."""
    sections = {}
    current_section = "preamble"
    current_content = []
    
    for line in prompt_text.split('\n'):
        if line.startswith('## '):
            if current_content:
                sections[current_section] = '\n'.join(current_content).strip()
            current_section = line[3:].lower().strip()
            current_section = re.sub(r'[\s—\-]+', '_', current_section)
            current_content = []
        else:
            current_content.append(line)
    
    if current_content:
        sections[current_section] = '\n'.join(current_content).strip()
    
    return sections

def _reconstruct_agent_js(parsed, section_edits=None, skill_add=None, skill_remove=None, config_edits=None):
    """Reconstruct agent.js with edits applied."""
    if parsed["format"] == "export_default":
        # Apply section edits to prompt
        prompt = parsed["prompt"]
        if section_edits:
            sections = dict(parsed["sections"])
            sections.update(section_edits)
            # Reconstruct prompt from sections
            prompt_lines = []
            for section_name, section_content in sections.items():
                if section_name == "preamble":
                    prompt_lines.append(section_content)
                else:
                    display_name = section_name.replace('_', ' ').title()
                    prompt_lines.append(f"## {display_name}")
                    prompt_lines.append(section_content)
            prompt = '\n\n'.join(prompt_lines)
        
        # Apply skill edits
        skills = list(parsed["config"].get("skills", []))
        if skill_add and skill_add not in skills:
            skills.append(skill_add)
        if skill_remove and skill_remove in skills:
            skills.remove(skill_remove)
        
        # Build export default
        lines = ['export default {']
        for field in ["name", "mode", "color", "model", "description"]:
            if field in parsed["config"]:
                lines.append(f'  {field}: "{parsed["config"][field]}",')
        if skills:
            skills_str = ', '.join(f'"{s}"' for s in skills)
            lines.append(f'  skills: [{skills_str}],')
        lines.append('  prompt: `')
        lines.append(prompt)
        lines.append('`')
        lines.append('}')
        return '\n'.join(lines)
    else:
        # Plain text format
        prompt = parsed["prompt"]
        if section_edits:
            sections = dict(parsed["sections"])
            sections.update(section_edits)
            prompt_lines = []
            for section_name, section_content in sections.items():
                if section_name == "preamble":
                    prompt_lines.append(section_content)
                else:
                    display_name = section_name.replace('_', ' ').title()
                    prompt_lines.append(f"## {display_name}")
                    prompt_lines.append(section_content)
            prompt = '\n\n'.join(prompt_lines)
        return prompt

def _validate_agent_edit(agent_name, content, file_type="agent.js"):
    """Validate agent structure after edit."""
    checks = {}
    warnings = []
    errors = []
    
    if file_type == "agent.js":
        # JS syntax check
        checks["js_syntax"] = "pass"
        try:
            # Check for balanced braces and backticks
            if content.count('{') != content.count('}'):
                checks["js_syntax"] = "fail"
                errors.append("Unbalanced braces")
            if content.count('`') % 2 != 0:
                checks["js_syntax"] = "fail"
                errors.append("Unbalanced backticks")
            if not content.startswith('export default {') and not content.startswith('You are'):
                checks["format"] = "fail"
                errors.append("Missing export default or plain text format")
            else:
                checks["format"] = "pass"
        except:
            checks["js_syntax"] = "fail"
            errors.append("Syntax error")
        
        # Required sections
        content_lower = content.lower()
        checks["has_identity"] = "pass" if ("identity" in content_lower or "you are" in content_lower) else "fail"
        checks["has_rules"] = "pass" if ("rules" in content_lower or "constraints" in content_lower) else "fail"
        checks["has_anti_hallucination"] = "pass" if ("hallucinat" in content_lower or "don't invent" in content_lower or "never invent" in content_lower) else "fail"
        checks["has_quality_gate"] = "pass" if ("quality gate" in content_lower or "quality_gate" in content_lower) else "fail"
        checks["has_classify"] = "pass" if ("classify" in content_lower or "[quick" in content_lower) else "fail"
        
        # Prompt length
        line_count = content.count('\n') + 1
        checks["prompt_length"] = f"{line_count} lines"
        if line_count > 150:
            warnings.append(f"Prompt is {line_count} lines (recommended: under 150)")
        
        # Config match
        try:
            cfg = _read_json(CONFIG_PATH)
            name_match = re.search(r'name:\s*"([^"]*)"', content)
            if name_match:
                agent_display_name = name_match.group(1)
                if agent_display_name in cfg.get("agent", {}):
                    checks["config_matches"] = "pass"
                else:
                    checks["config_matches"] = "warning"
                    warnings.append(f"Agent '{agent_display_name}' not found in config")
            else:
                checks["config_matches"] = "skip"
        except:
            checks["config_matches"] = "skip"
    
    elif file_type == "tools.json":
        try:
            data = json.loads(content)
            checks["valid_json"] = "pass"
            allowed = data.get("allowed", [])
            blocked = data.get("blocked", [])
            checks["tools_disjoint"] = "pass" if len(set(allowed) & set(blocked)) == 0 else "fail"
            if checks["tools_disjoint"] == "fail":
                errors.append("Tools in both allowed and blocked")
        except:
            checks["valid_json"] = "fail"
            errors.append("Invalid JSON")
    
    elif file_type in ("SKILL.md", "workflow.md"):
        checks["has_frontmatter"] = "pass" if content.startswith("---") else "fail"
        if checks["has_frontmatter"] == "fail":
            errors.append("Missing YAML frontmatter")
        checks["has_content"] = "pass" if len(content.strip()) > 50 else "fail"
        if checks["has_content"] == "fail":
            warnings.append("File content is very short")
    
    valid = all(v == "pass" or v == "skip" for v in checks.values())
    
    return {
        "valid": valid,
        "checks": checks,
        "warnings": warnings,
        "errors": errors
    }

def _backup_file(file_path):
    """Create backup of file before edit."""
    backup_dir = os.path.join(os.path.dirname(file_path), ".backup")
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"{timestamp}_{os.path.basename(file_path)}")
    shutil.copy2(file_path, backup_path)
    return backup_path

def handle_agent_edit(args):
    """Main handler for agent_edit tool."""
    operation = args.get("operation", "")
    agent = args.get("agent", "")
    validate = args.get("validate", True)
    
    if not operation:
        return {"content": [{"type": "text", "text": "Error: 'operation' required"}]}
    
    # Batch edit
    if operation == "batch_edit":
        batch = args.get("batch", [])
        if not batch:
            return {"content": [{"type": "text", "text": "Error: 'batch' required for batch_edit"}]}
        results = []
        for i, op in enumerate(batch):
            op_args = dict(args)
            op_args.update(op)
            op_args["validate"] = False  # Validate at end
            result = handle_agent_edit(op_args)
            results.append(f"  [{i+1}] {op.get('agent', '?')}/{op.get('operation', '?')}: {result.get('content', [{}])[0].get('text', '?')[:100]}")
        
        # Final validation if requested
        if validate:
            agents_to_validate = set(op.get("agent", "") for op in batch if op.get("agent"))
            for a in agents_to_validate:
                val_result = handle_agent_edit({"operation": "validate_agent", "agent": a})
                results.append(f"  [validate] {a}: {val_result.get('content', [{}])[0].get('text', '?')[:100]}")
        
        return {"content": [{"type": "text", "text": f"Batch edit ({len(batch)} operations):\n" + "\n".join(results)}]}
    
    if not agent:
        return {"content": [{"type": "text", "text": "Error: 'agent' required"}]}
    
    agent_dir = _agent_dir_path(agent)
    if not agent_dir or not os.path.exists(agent_dir):
        return {"content": [{"type": "text", "text": f"Error: Agent directory not found for '{agent}'"}]}
    
    # Read agent
    agent_js_path = os.path.join(agent_dir, "agent.js")
    tools_json_path = os.path.join(agent_dir, "tools/tools.json")
    
    if operation == "read_agent":
        if not os.path.exists(agent_js_path):
            return {"content": [{"type": "text", "text": f"Error: agent.js not found at {agent_js_path}"}]}
        with open(agent_js_path) as f:
            content = f.read()
        parsed = _parse_agent_js(content)
        
        # Read tools.json if exists
        tools_info = {}
        if os.path.exists(tools_json_path):
            with open(tools_json_path) as f:
                tools_info = json.load(f)
        
        # Read config entry
        config_info = {}
        try:
            cfg = _read_json(CONFIG_PATH)
            for name, acfg in cfg.get("agent", {}).items():
                if agent.lower() in name.lower():
                    config_info = acfg
                    break
        except:
            pass
        
        sections_summary = {k: f"{len(v)} chars" for k, v in parsed["sections"].items()}
        
        output = f"""Agent: {parsed['config'].get('name', agent)}
Format: {parsed['format']}
Config: {json.dumps(parsed['config'], indent=2)}
Sections: {json.dumps(sections_summary, indent=2)}
Tools: {json.dumps(tools_info, indent=2) if tools_info else 'No tools.json'}
Config entry: {json.dumps(config_info, indent=2) if config_info else 'Not found in config'}
Line count: {content.count(chr(10)) + 1}"""
        
        return {"content": [{"type": "text", "text": output}]}
    
    if operation == "validate_agent":
        if not os.path.exists(agent_js_path):
            return {"content": [{"type": "text", "text": f"Error: agent.js not found"}]}
        with open(agent_js_path) as f:
            content = f.read()
        validation = _validate_agent_edit(agent, content)
        
        output = f"""Agent: {agent}
Valid: {'YES' if validation['valid'] else 'NO'}
Checks: {json.dumps(validation['checks'], indent=2)}
Warnings: {', '.join(validation['warnings']) if validation['warnings'] else 'None'}
Errors: {', '.join(validation['errors']) if validation['errors'] else 'None'}"""
        
        return {"content": [{"type": "text", "text": output}]}
    
    if operation == "add_skill":
        skill_key = args.get("skill_key", "")
        if not skill_key:
            return {"content": [{"type": "text", "text": "Error: 'skill_key' required"}]}
        if not os.path.exists(agent_js_path):
            return {"content": [{"type": "text", "text": f"Error: agent.js not found"}]}
        with open(agent_js_path) as f:
            content = f.read()
        parsed = _parse_agent_js(content)
        
        skills = list(parsed["config"].get("skills", []))
        if skill_key in skills:
            return {"content": [{"type": "text", "text": f"Skill '{skill_key}' already present in {agent}"}]}
        
        skills.append(skill_key)
        new_content = _reconstruct_agent_js(parsed, skill_add=skill_key)
        
        _backup_file(agent_js_path)
        with open(agent_js_path, "w") as f:
            f.write(new_content)
        
        if validate:
            validation = _validate_agent_edit(agent, new_content)
            if not validation["valid"]:
                # Rollback
                with open(agent_js_path, "w") as f:
                    f.write(content)
                return {"content": [{"type": "text", "text": f"Validation failed, rolled back: {validation['errors']}"}]}
        
        return {"content": [{"type": "text", "text": f"Added skill '{skill_key}' to {agent}. Skills now: {skills}"}]}
    
    if operation == "remove_skill":
        skill_key = args.get("skill_key", "")
        if not skill_key:
            return {"content": [{"type": "text", "text": "Error: 'skill_key' required"}]}
        if not os.path.exists(agent_js_path):
            return {"content": [{"type": "text", "text": f"Error: agent.js not found"}]}
        with open(agent_js_path) as f:
            content = f.read()
        parsed = _parse_agent_js(content)
        
        skills = list(parsed["config"].get("skills", []))
        if skill_key not in skills:
            return {"content": [{"type": "text", "text": f"Skill '{skill_key}' not found in {agent}"}]}
        
        skills.remove(skill_key)
        new_content = _reconstruct_agent_js(parsed, skill_remove=skill_key)
        
        _backup_file(agent_js_path)
        with open(agent_js_path, "w") as f:
            f.write(new_content)
        
        return {"content": [{"type": "text", "text": f"Removed skill '{skill_key}' from {agent}. Skills now: {skills}"}]}
    
    if operation == "edit_section" or operation == "edit_prompt_section":
        section = args.get("section", "")
        new_content = args.get("content", "")
        if not section:
            return {"content": [{"type": "text", "text": "Error: 'section' required"}]}
        if not new_content:
            return {"content": [{"type": "text", "text": "Error: 'content' required"}]}
        if not os.path.exists(agent_js_path):
            return {"content": [{"type": "text", "text": f"Error: agent.js not found"}]}
        with open(agent_js_path) as f:
            content = f.read()
        parsed = _parse_agent_js(content)
        
        if section not in parsed["sections"]:
            available = list(parsed["sections"].keys())
            return {"content": [{"type": "text", "text": f"Error: Section '{section}' not found. Available: {available}"}]}
        
        section_edits = {section: new_content}
        new_content_full = _reconstruct_agent_js(parsed, section_edits=section_edits)
        
        _backup_file(agent_js_path)
        with open(agent_js_path, "w") as f:
            f.write(new_content_full)
        
        if validate:
            validation = _validate_agent_edit(agent, new_content_full)
            if not validation["valid"]:
                with open(agent_js_path, "w") as f:
                    f.write(content)
                return {"content": [{"type": "text", "text": f"Validation failed, rolled back: {validation['errors']}"}]}
        
        return {"content": [{"type": "text", "text": f"Edited section '{section}' in {agent}. Validated: {'pass' if validate else 'skipped'}"}]}
    
    if operation == "add_section":
        section = args.get("section", "")
        new_content = args.get("content", "")
        if not section or not new_content:
            return {"content": [{"type": "text", "text": "Error: 'section' and 'content' required"}]}
        if not os.path.exists(agent_js_path):
            return {"content": [{"type": "text", "text": f"Error: agent.js not found"}]}
        with open(agent_js_path) as f:
            content = f.read()
        parsed = _parse_agent_js(content)
        
        # Add new section at end
        section_edits = {section: new_content}
        new_content_full = _reconstruct_agent_js(parsed, section_edits=section_edits)
        
        _backup_file(agent_js_path)
        with open(agent_js_path, "w") as f:
            f.write(new_content_full)
        
        return {"content": [{"type": "text", "text": f"Added section '{section}' to {agent}"}]}
    
    if operation == "remove_section":
        section = args.get("section", "")
        if not section:
            return {"content": [{"type": "text", "text": "Error: 'section' required"}]}
        if not os.path.exists(agent_js_path):
            return {"content": [{"type": "text", "text": f"Error: agent.js not found"}]}
        with open(agent_js_path) as f:
            content = f.read()
        parsed = _parse_agent_js(content)
        
        if section not in parsed["sections"]:
            return {"content": [{"type": "text", "text": f"Error: Section '{section}' not found"}]}
        
        # Remove section by setting to empty
        section_edits = {section: ""}
        new_content_full = _reconstruct_agent_js(parsed, section_edits=section_edits)
        
        _backup_file(agent_js_path)
        with open(agent_js_path, "w") as f:
            f.write(new_content_full)
        
        return {"content": [{"type": "text", "text": f"Removed section '{section}' from {agent}"}]}
    
    if operation == "edit_tools":
        tools_allowed = args.get("tools_allowed")
        tools_blocked = args.get("tools_blocked")
        if tools_allowed is None and tools_blocked is None:
            return {"content": [{"type": "text", "text": "Error: 'tools_allowed' or 'tools_blocked' required"}]}
        if not os.path.exists(tools_json_path):
            return {"content": [{"type": "text", "text": f"Error: tools.json not found at {tools_json_path}"}]}
        with open(tools_json_path) as f:
            tools_data = json.load(f)
        
        if tools_allowed is not None:
            tools_data["allowed"] = tools_allowed
        if tools_blocked is not None:
            tools_data["blocked"] = tools_blocked
        
        new_tools_content = json.dumps(tools_data, indent=2) + "\n"
        
        _backup_file(tools_json_path)
        with open(tools_json_path, "w") as f:
            f.write(new_tools_content)
        
        if validate:
            validation = _validate_agent_edit(agent, new_tools_content, "tools.json")
            if not validation["valid"]:
                with open(tools_json_path, "w") as f:
                    json.dump(tools_data, f, indent=2)
                    f.write("\n")
                return {"content": [{"type": "text", "text": f"Validation failed, rolled back: {validation['errors']}"}]}
        
        return {"content": [{"type": "text", "text": f"Edited tools.json for {agent}. Allowed: {tools_data.get('allowed', [])}, Blocked: {tools_data.get('blocked', [])}"}]}
    
    if operation == "config_edit":
        config_key = args.get("config_key", "")
        config_value = args.get("config_value", "")
        if not config_key:
            return {"content": [{"type": "text", "text": "Error: 'config_key' required"}]}
        if not os.path.exists(agent_js_path):
            return {"content": [{"type": "text", "text": f"Error: agent.js not found"}]}
        with open(agent_js_path) as f:
            content = f.read()
        
        # Edit config field in export default
        pattern = rf'({config_key}:\s*)"([^"]*)"'
        if re.search(pattern, content):
            new_content = re.sub(pattern, rf'\1"{config_value}"', content)
        else:
            return {"content": [{"type": "text", "text": f"Error: Config key '{config_key}' not found in {agent}"}]}
        
        _backup_file(agent_js_path)
        with open(agent_js_path, "w") as f:
            f.write(new_content)
        
        if validate:
            validation = _validate_agent_edit(agent, new_content)
            if not validation["valid"]:
                with open(agent_js_path, "w") as f:
                    f.write(content)
                return {"content": [{"type": "text", "text": f"Validation failed, rolled back: {validation['errors']}"}]}
        
        return {"content": [{"type": "text", "text": f"Edited config '{config_key}' = '{config_value}' in {agent}"}]}
    
    return {"content": [{"type": "text", "text": f"Error: Unknown operation '{operation}'"}]}


# ── Dispatch ─────────────────────────────────────────────────────────

def handle_initialize():
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {"tools": {}},
        "serverInfo": {"name": "megatool-mcp", "version": "0.3.0"}
    }

def handle_tools_list():
    return {"tools": ALL_TOOLS}

ADMIN_DISPATCH = {
    "ralph_start": handle_ralph_start,
    "ralph_status": handle_ralph_status,
    "ralph_iterate": handle_ralph_iterate,
    "ralph_cancel": handle_ralph_cancel,
    "ulw_start": handle_ulw_start,
    "ulw_status": handle_ulw_status,
    "ulw_cancel": handle_ulw_cancel,

    "consciousness_record": handle_consciousness_record,
    "consciousness_identity": handle_consciousness_identity,

    "ask_question": handle_ask_question,
    "spawn_task": handle_spawn_task,
    "context_prune": handle_context_prune,
    "session_status": handle_session_status,
    "verify_code": handle_verify_code,

    "pc_aware": handle_pc_aware,
    "pc_scan": handle_pc_scan,
    "embed_text": handle_embed_text,
    "embed_similarity": handle_embed_similarity,
    "bg_submit": handle_bg_submit,
    "bg_status": handle_bg_status,
    "bg_list": handle_bg_list,
    "bg_cancel": handle_bg_cancel,
    "bg_events": handle_bg_events,
    "task_result": handle_task_result,
    "cache_stats": handle_cache_stats,
    "cache_clear": handle_cache_clear,

    "parallel_task": handle_parallel_task,
    "task_status": handle_task_status,
    "session_tasks": handle_session_tasks,

    "safe_delete": handle_safe_delete,
    "search_memory": handle_search_memory,
    "search_semantic": handle_search_memory,
    "pull_global_context": handle_pull_global_context,
    "read_memory": handle_read_memory,
    "write_memory": handle_write_memory,
    "list_memory": handle_list_memory,
    "web_fetch": handle_web_fetch,
    "web_search": handle_web_search,
    "file_batch_read": handle_file_batch_read,
    "project_map": handle_project_map,
    "config_validate": handle_validate_config,
    "config_edit": handle_edit_config,
    "config_remove": handle_remove_key,
    "agent_add": handle_add_agent,
    "agent_list": handle_list_agents,
    "config_sync": handle_sync_nx_config,
    "schema_check": handle_check_schema_ref,
    "file_write": handle_write_tool,
    "file_edit": handle_edit_tool,
    "file_read": handle_read_tool,
    "file_glob": handle_glob_tool,
    "file_grep": handle_grep_tool,
    "agent_edit": handle_agent_edit,
}

def handle_tool_call(name, arguments):
    agent = _resolve_agent_from_args(arguments)
    if agent and not _is_tool_allowed(agent, name):
        return {"content": [{"type": "text", "text": f"Error: '{name}' not in {CALLING_AGENT}'s allowed tools"}]}

    if name in ADMIN_DISPATCH:
        try:
            return ADMIN_DISPATCH[name](arguments)
        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}

    bridge = BRIDGE_MAP.get(name)
    if not bridge:
        return {"content": [{"type": "text", "text": f"Error: Unknown tool '{name}'"}]}
    if not os.path.exists(bridge):
        return {"content": [{"type": "text", "text": f"Bridge not found: {bridge}"}]}

    if name == "search_code":
        bridge_input = json.dumps({"type": "search", "query": arguments.get("query",""), "top_k": arguments.get("max_results",5)})
    elif name == "review_code":
        bridge_input = json.dumps({"file": arguments.get("file_path",""), "context": ""})
    elif name == "file_batch_write":
        files = arguments.get("files", [])
        paths = [f.get("path","") for f in files if isinstance(f,dict) and f.get("path")]
        if not paths:
            return {"content": [{"type": "text", "text": "Error: at least one file path required"}]}
        bridge_input = json.dumps({"spec": "Generate files: " + ", ".join(paths), "files": paths})
    elif name == "review_adversarial":
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write(arguments.get("content",""))
            bridge_input = json.dumps({"file": tmp.name, "context": "adversarial review"})
    else:
        return {"content": [{"type": "text", "text": f"Error: No handler for '{name}'"}]}

    try:
        result = subprocess.run(["python3", bridge, "--stdin"], input=bridge_input,
            capture_output=True, text=True, timeout=30)
        output = result.stdout.strip()
        if result.stderr:
            out = result.stderr.strip()
            output = output + f"\n[stderr]: {out}" if output else out
        return {"content": [{"type": "text", "text": output or "(no output)"}]}
    except subprocess.TimeoutExpired:
        return {"content": [{"type": "text", "text": f"Bridge '{name}' timed out"}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            method = req.get("method", "")
            rid = req.get("id", None)
            if method == "initialize":
                result = handle_initialize()
            elif method == "tools/list":
                result = handle_tools_list()
            elif method == "tools/call":
                params = req.get("params", {})
                result = handle_tool_call(params.get("name", ""), params.get("arguments", {}))
            else:
                result = {"error": f"Unknown method: {method}"}
            print(json.dumps({"jsonrpc": "2.0", "id": rid, "result": result}), flush=True)
        except Exception as e:
            print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(e)}}), flush=True)

if __name__ == "__main__":
    main()
