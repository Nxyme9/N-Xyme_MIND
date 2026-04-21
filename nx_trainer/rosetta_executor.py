#!/usr/bin/env python3
import json
import re
import logging
import asyncio
import inspect
import subprocess
import os
import time
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger("rosetta_executor")

SERVER_PID = None
SERVER_STARTED_BY_US = False

@dataclass
class ToolCall:
    tool: str
    args: Dict[str, Any]
    raw: str

EXECUTION_MAP = {}

PROJECT_ROOT = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
SERVER_PORT = int(os.environ.get("ROSETTA_PORT", "8001"))


def check_server_running() -> bool:
    try:
        import requests
        r = requests.get(f"http://localhost:{SERVER_PORT}/health", timeout=2)
        return r.status_code == 200
    except:
        return False


def start_server() -> bool:
    global SERVER_PID, SERVER_STARTED_BY_US
    
    if check_server_running():
        return True
    
    logger.info(f"Starting Rosetta server on port {SERVER_PORT}...")
    
    server_dir = PROJECT_ROOT / "nx_trainer"
    
    env = os.environ.copy()
    env["ROSETTA_PORT"] = str(SERVER_PORT)
    
    proc = subprocess.Popen(
        ["python3", "rosetta_server.py"],
        cwd=str(server_dir),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    
    SERVER_PID = proc.pid
    SERVER_STARTED_BY_US = True
    
    for _ in range(30):
        time.sleep(0.5)
        if check_server_running():
            logger.info("Server started successfully")
            return True
    
    logger.warning("Server failed to start")
    return False


def normalize_tool_name(tool_name: str) -> str:
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


def load_real_mcp_functions():
    global EXECUTION_MAP
    try:
        from unified_memory import search_memories, create_memory
        EXECUTION_MAP["memory_search"] = search_memories
        EXECUTION_MAP["memory_write"] = create_memory
    except ImportError:
        pass
    try:
        from nx_context import get_active_context, get_product_context, get_user_context
        EXECUTION_MAP["get_active_context"] = get_active_context
        EXECUTION_MAP["get_product_context"] = get_product_context
        EXECUTION_MAP["get_user_context"] = get_user_context
    except ImportError:
        pass


def run_via_subprocess(tool_name: str, args: Dict) -> Optional[Dict]:
    cmd_map = {
        "ls": ["ls", "-la"],
        "list_directory": ["ls"],
        "git_status": ["git", "status"],
        "git_log": ["git", "log", "--oneline", "-10"],
        "pwd": ["pwd"],
        "date": ["date"],
    }
    if tool_name in cmd_map:
        try:
            result = subprocess.run(cmd_map[tool_name], capture_output=True, text=True, timeout=30, cwd=str(PROJECT_ROOT))
            return {"success": True, "result": result.stdout, "tool": tool_name, "mode": "subprocess"}
        except Exception as e:
            return {"success": False, "error": str(e), "tool": tool_name}
    return None


def run_bash_command(command: str) -> Dict[str, Any]:
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30, cwd=str(PROJECT_ROOT))
        return {"success": result.returncode == 0, "result": result.stdout, "error": result.stderr if result.returncode != 0 else None, "mode": "bash"}
    except Exception as e:
        return {"success": False, "error": str(e)}


class RosettaExecutor:
    def __init__(self, auto_start: bool = True):
        self.auto_start = auto_start
        self.server_url = f"http://localhost:{SERVER_PORT}"
        load_real_mcp_functions()
        self._add_fallbacks()
        
        if auto_start:
            start_server()
    
    def _add_fallbacks(self):
        global EXECUTION_MAP
        if "memory_search" not in EXECUTION_MAP:
            async def mock_mem(query: str = "", limit: int = 10):
                return {"query": query, "results": [{"content": f"Mock for: {query}", "score": 0.9}]}
            EXECUTION_MAP["memory_search"] = mock_mem
            EXECUTION_MAP["search_memory"] = mock_mem
        if "get_active_context" not in EXECUTION_MAP:
            async def mock_ctx():
                return {"project": "N-Xyme_MIND", "phase": "development"}
            EXECUTION_MAP["get_active_context"] = mock_ctx
        if "session_list" not in EXECUTION_MAP:
            async def mock_sess(l: int = 10):
                return {"sessions": [{"id": "s1", "messages": 5}]}
            EXECUTION_MAP["session_list"] = mock_sess
        logger.info(f"Loaded {len(EXECUTION_MAP)} functions")
    
    def parse_tool_json(self, json_str: str) -> ToolCall:
        json_str = re.sub(r'```json\s*', '', json_str)
        json_str = re.sub(r'```\s*$', '', json_str)
        json_str = json_str.strip()
        try:
            data = json.loads(json_str)
            if "tool" in data:
                return ToolCall(tool=data.get("tool", ""), args=data.get("args", {}), raw=json_str)
        except:
            pass
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
        logger.info(f"Executing: {tool_name}")
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
                logger.warning(f"Function failed: {e}")
        result = run_via_subprocess(tool_name, tool_call.args)
        if result:
            return result
        if tool_name in ("bash", "run", "execute", "shell"):
            command = tool_call.args.get("command", "")
            if command:
                return run_bash_command(command)
        return {"success": False, "error": f"No handler for {tool_name}", "tool": tool_name}
    
    async def execute_prompt(self, prompt: str, rosetta_url: str = None) -> Dict[str, Any]:
        if rosetta_url is None:
            rosetta_url = self.server_url
        
        if self.auto_start and not check_server_running():
            if not start_server():
                return {"success": False, "error": "Failed to start server"}
        
        import requests
        try:
            response = requests.post(f"{rosetta_url}/inference", json={"prompt": prompt, "max_tokens": 256}, timeout=30)
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
    executor = RosettaExecutor()
    return await executor.execute_tool(ToolCall(tool=tool, args=args, raw=""))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(name)s: %(message)s')
    executor = RosettaExecutor(auto_start=True)
    
    print("Testing Rosetta with auto-start...")
    
    result = asyncio.run(executor.execute_prompt("search memory for security"))
    print(f"Result: {result.get('mode')} - {result.get('success')}")
    if result.get("parsed"):
        print(f"Tool: {result['parsed']['tool']}")