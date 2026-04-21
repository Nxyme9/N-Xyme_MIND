#!/usr/bin/env python3
"""
Rosetta Executor - ACTUAL MCP Execution
"""

import json
import re
import logging
import asyncio
import inspect
from typing import Dict, Any
from dataclasses import dataclass
import sys
sys.path.insert(0, "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")

logger = logging.getLogger("rosetta_executor")


@dataclass
class ToolCall:
    tool: str
    args: Dict[str, Any]
    raw: str


EXECUTION_MAP = {}


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


class RosettaExecutor:
    def __init__(self):
        self._load_exec_map()
    
    def _load_exec_map(self):
        global EXECUTION_MAP
        
        # Mock implementations for demonstration
        async def mock_memory_search(query: str, limit: int = 10):
            return {"query": query, "results": [{"content": f"Mock result for: {query}", "score": 0.9}]}
        
        async def mock_get_active_context():
            return {"project": "N-Xyme_MIND", "phase": "development"}
        
        async def mock_session_list(limit: int = 10):
            return {"sessions": [{"id": "s1", "messages": 5}]}
        
        EXECUTION_MAP["memory_search"] = mock_memory_search
        EXECUTION_MAP["search_memory"] = mock_memory_search
        EXECUTION_MAP["get_active_context"] = mock_get_active_context
        EXECUTION_MAP["session_list"] = mock_session_list
        
        logger.info(f"Loaded {len(EXECUTION_MAP)} mock MCP functions (demo mode)")
    
    def parse_tool_json(self, json_str: str) -> ToolCall:
        # Clean markdown code blocks
        import re
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
        
        exec_func = EXECUTION_MAP.get(tool_name)
        
        if not exec_func:
            for key in EXECUTION_MAP:
                if key in tool_name or tool_name in key:
                    exec_func = EXECUTION_MAP[key]
                    break
        
        if not exec_func:
            return {"success": False, "error": f"No MCP for {tool_name}", "tool": tool_name}
        
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
            
            return {"success": True, "result": result, "tool": tool_name}
        except Exception as e:
            return {"success": False, "error": str(e), "tool": tool_name}
    
    async def execute_prompt(self, prompt: str, rosetta_url: str = "http://localhost:8000") -> Dict[str, Any]:
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
    executor = RosettaExecutor()
    return await executor.execute_tool(ToolCall(tool=tool, args=args, raw=""))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor = RosettaExecutor()
    
    print("Testing MCP execution...")
    import requests
    
    # Start test
    r = requests.post("http://localhost:8001/inference", json={"prompt": "search memory for security", "max_tokens": 256}, timeout=30)
    data = r.json()
    print(f"Raw: {data.get('raw_output', '')[:100]}")
    
    tc = executor.parse_tool_json(data.get("raw_output", ""))
    print(f"Parsed: {tc.tool} -> {tc.args}")
    
    result = asyncio.run(executor.execute_tool(tc))
    print(f"Result: {result}")