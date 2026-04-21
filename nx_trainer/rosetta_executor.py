#!/usr/bin/env python3
"""
Rosetta Executor - ACTUAL MCP Execution
"""

import json
import re
import logging
import asyncio
import inspect
import subprocess
from typing import Dict, Any
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("rosetta_executor")


@dataclass
class ToolCall:
    tool: str
    args: Dict[str, Any]
    raw: str


EXECUTION_MAP = {}


def normalize_tool_name(tool_name: str) -> str:
    """Convert camelCase to snake_case and apply mappings"""
    s = re.sub(r'(?<!^)(?=[A-Z])', '_', tool_name).lower()
    mappings = {
        "search_memory_for_security": "memory_search",
        "search_github_repos": "github_search_repos",
        "run": "bash",
        "execute": "bash",
        "search_memory": "memory_search",
        "write_memory": "memory_write",
    }
    if s in mappings:
        return mappings[s]
    for key in mappings:
        if key in s or s in key:
            return mappings[key]
    return s


def _try_import_packages():
    """Try to import real MCP functions from packages"""
    global EXECUTION_MAP
    
    # Only import from project root to avoid package issues
    project_root = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
    
    # Try unified-memory MCP
    try:
        from unified_memory import search_memories, create_memory
        EXECUTION_MAP["memory_search"] = search_memories
        EXECUTION_MAP["memory_write"] = create_memory
        logger.info("Loaded real memory MCP functions")
    except ImportError as e:
        logger.debug(f"Could not import unified_memory: {e}")
    
    # Try nx-context MCP
    try:
        from nx_context import get_active_context, get_product_context, get_user_context
        EXECUTION_MAP["get_active_context"] = get_active_context
        EXECUTION_MAP["get_product_context"] = get_product_context
        EXECUTION_MAP["get_user_context"] = get_user_context
        logger.info("Loaded real nx-context MCP functions")
    except ImportError as e:
        logger.debug(f"Could not import nx_context: {e}")
    
    # Try sqlite MCP
    try:
        import sqlite3
        # We'll use direct sqlite3 calls
        logger.info("Loaded sqlite3 for database operations")
    except ImportError:
        pass


def _execute_subprocess(tool_name: str, args: Dict) -> Dict[str, Any]:
    """Execute tool via subprocess to avoid import issues"""
    
    # Map tool names to CLI commands
    cmd_map = {
        "ls": ["ls", "-la"],
        "list_directory": ["ls"],
        "git_status": ["git", "status"],
        "git_log": ["git", "log", "--oneline", "-10"],
        "pwd": ["pwd"],
        "date": ["date"],
    }
    
    if tool_name in cmd_map:
        cmd = cmd_map[tool_name]
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=30,
                cwd="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND"
            )
            return {
                "success": True,
                "result": result.stdout,
                "tool": tool_name,
                "mode": "subprocess"
            }
        except Exception as e:
            return {"success": False, "error": str(e), "tool": tool_name}
    
    return None


def _execute_bash(command: str) -> Dict[str, Any]:
    """Execute a bash command"""
    try:
        result = subprocess.run(
            command, 
            shell=True,
            capture_output=True, 
            text=True, 
            timeout=30,
            cwd="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND"
        )
        return {
            "success": result.returncode == 0,
            "result": result.stdout,
            "error": result.stderr if result.returncode != 0 else None,
            "mode": "bash"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


class RosettaExecutor:
    def __init__(self, use_mocks: bool = True):
        self.use_mocks = use_mocks
        self._load_exec_map()
    
    def _load_exec_map(self):
        global EXECUTION_MAP
        
        # First try to import real packages
        _try_import_packages()
        
        # Add mock implementations as fallback
        async def mock_memory_search(query: str, limit: int = 10):
            return {"query": query, "results": [{"content": f"Mock result for: {query}", "score": 0.9}]}
        
        async def mock_get_active_context():
            return {"project": "N-Xyme_MIND", "phase": "development"}
        
        async def mock_session_list(limit: int = 10):
            return {"sessions": [{"id": "s1", "messages": 5}]}
        
        async def mock_text(content: str):
            return {"text": content}
        
        # Only add mocks if not already loaded
        if "memory_search" not in EXECUTION_MAP:
            EXECUTION_MAP["memory_search"] = mock_memory_search
        if "search_memory" not in EXECUTION_MAP:
            EXECUTION_MAP["search_memory"] = mock_memory_search
        if "get_active_context" not in EXECUTION_MAP:
            EXECUTION_MAP["get_active_context"] = mock_get_active_context
        if "session_list" not in EXECUTION_MAP:
            EXECUTION_MAP["session_list"] = mock_session_list
        
        logger.info(f"Loaded {len(EXECUTION_MAP)} MCP functions")
    
    def parse_tool_json(self, json_str: str) -> ToolCall:
        # Clean markdown code blocks
        json_str = re.sub(r'```json\s*', '', json_str)
        json_str = re.sub(r'```\s*$', '', json_str)
        json_str = json_str.strip()
        
        try:
            data = json.loads(json_str)
            if "tool" in data:
                return ToolCall(tool=data.get("tool", ""), args=data.get("args", {}), raw=json_str)
        except:
            pass
        
        # Find JSON object - look for { }
        start = -1
        end = -1
        for i, c in enumerate(json_str):
            if c == '{':
                start = i
            elif c == '}' and start >= 0:
                end = i + 1
                break
        
        if start >= 0 and end > start:
            try:
                data = json.loads(json_str[start:end])
                return ToolCall(tool=data.get("tool", ""), args=data.get("args", {}), raw=json_str)
            except:
                pass
        
        return ToolCall(tool="text", args={"content": json_str}, raw=json_str)
    
    async def execute_tool(self, tool_call: ToolCall) -> Dict[str, Any]:
        tool_name = normalize_tool_name(tool_call.tool.strip())
        logger.info(f"Executing: {tool_name} with {tool_call.args}")
        
        # Try registered function
        exec_func = EXECUTION_MAP.get(tool_name)
        
        if not exec_func:
            for key in EXECUTION_MAP:
                if key in tool_name or tool_name in key:
                    exec_func = EXECUTION_MAP[key]
                    break
        
        if exec_func:
            try:
                args = tool_call.args
                sig = inspect.signature(exec_func)
                valid_args = {}
                for pn in sig.parameters:
                    if pn in args:
                        valid_args[pn] = args[pn]
                    elif pn == "query" and "searchTerm" in args:
                        valid_args[pn] = args["searchTerm"]
                
                if asyncio.iscoroutinefunction(exec_func):
                    result = await exec_func(**valid_args)
                else:
                    result = exec_func(**valid_args)
                
                return {"success": True, "result": result, "tool": tool_name, "mode": "function"}
            except Exception as e:
                logger.warning(f"Function execution failed: {e}")
        
        # Try subprocess
        result = _execute_subprocess(tool_name, tool_call.args)
        if result:
            return result
        
        # Try bash for shell-like commands
        if tool_name in ("bash", "run", "execute", "shell"):
            command = tool_call.args.get("command", "")
            if command:
                return _execute_bash(command)
        
        return {"success": False, "error": f"No handler for {tool_name}", "tool": tool_name}
    
    async def execute_prompt(self, prompt: str, rosetta_url: str = "http://localhost:8001") -> Dict[str, Any]:
        import requests
        text = f'The user said: "{prompt}"\n\nGenerate the tool call in JSON format:'
        try:
            response = requests.post(f"{rosetta_url}/inference", json={"prompt": text, "max_tokens": 256}, timeout=30)
            if response.status_code != 200:
                return {"success": False, "error": f"HTTP {response.status_code}"}
            
            data = response.json()
            tool_call = self.parse_tool_json(data.get("raw_output", ""))
            result = await self.execute_tool(tool_call)
            result["raw_rosetta"] = data.get("raw_output", "")
            result["parsed"] = {"tool": tool_call.tool, "args": tool_call.args}
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}


async def execute_simple(tool: str, args: Dict) -> Dict[str, Any]:
    """Simple sync interface"""
    executor = RosettaExecutor()
    return await executor.execute_tool(ToolCall(tool=tool, args=args, raw=""))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(name)s: %(message)s')
    executor = RosettaExecutor()
    
    print("Testing MCP execution...")
    import requests
    
    # Start test
    try:
        r = requests.post("http://localhost:8001/inference", json={"prompt": "search memory for security", "max_tokens": 256}, timeout=30)
        data = r.json()
        print(f"Raw: {data.get('raw_output', '')[:100]}")
        
        tc = executor.parse_tool_json(data.get("raw_output", ""))
        print(f"Parsed: {tc.tool} -> {tc.args}")
        
        result = asyncio.run(executor.execute_tool(tc))
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")
        print("Server not running. Testing direct function call...")
        
        result = asyncio.run(executor.execute_tool(ToolCall(
            tool="get_active_context", 
            args={}, 
            raw=""
        )))
        print(f"Direct call: {result}")