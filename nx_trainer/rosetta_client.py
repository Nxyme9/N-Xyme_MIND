#!/usr/bin/env python3
"""
Rosetta Client - Python client for Rosetta Server

Usage:
    from rosetta_client import RosettaClient
    
    client = RosettaClient()
    
    # Just get the JSON tool call (no execution)
    result = client.call("search memory for security")
    
    # Or execute directly
    result = client.execute("search memory for security")
"""

import requests
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("rosetta_client")


DEFAULT_URL = "http://localhost:8000"


class RosettaClient:
    """Python client for Rosetta Stone inference server"""
    
    def __init__(self, base_url: str = DEFAULT_URL, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
    
    def call(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> Dict[str, Any]:
        """
        Call Rosetta - returns JSON tool call WITHOUT executing
        
        Returns:
            {
                "success": True/False,
                "tool_call": {"tool": "x", "args": {...}},
                "raw_output": "...",
                "tokens_used": 123,
            }
        """
        try:
            response = requests.post(
                f"{self.base_url}/inference",
                json={
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                }
            
            data = response.json()
            
            tool_json = data.get("tool_call", {})
            
            return {
                "success": True,
                "tool_call": tool_json,
                "raw_output": data.get("raw_output", ""),
                "tokens_used": data.get("tokens_used", 0),
            }
            
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": f"Could not connect to Rosetta at {self.base_url}",
                "hint": "Is the server running? python -m rosetta_server",
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Request timed out",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
    
    def execute(self, prompt: str, max_tokens: int = 512) -> Dict[str, Any]:
        """
        Call Rosetta AND execute the tool directly
        
        Returns:
            {
                "success": True/False,
                "tool_call": {"tool": "x", "args": {...}},
                "result": "...",
                "error": "...",
            }
        """
        from rosetta_executor import RosettaExecutor, ToolCall
        import asyncio
        
        result = self.call(prompt, max_tokens)
        
        if not result.get("success"):
            return result
        
        tool_json = result.get("tool_call", {})
        
        if not tool_json:
            return {
                "success": False,
                "error": "No tool call in response",
                "raw": result.get("raw_output"),
            }
        
        tool = tool_json.get("tool", "")
        args = tool_json.get("args", {})
        
        tool_call = ToolCall(tool=tool, args=args, raw=result.get("raw_output", ""))
        
        executor = RosettaExecutor()
        
        loop = asyncio.get_event_loop()
        exec_result = loop.run_until_complete(executor.execute_tool(tool_call))
        
        return {
            "success": exec_result.get("success", False),
            "tool_call": {"tool": tool, "args": args},
            "result": exec_result.get("result"),
            "error": exec_result.get("error"),
            "raw_rosetta": result.get("raw_output"),
        }
    
    def health(self) -> Dict[str, Any]:
        """Check server health"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.json() if response.status_code == 200 else {"status": "unhealthy"}
        except:
            return {"status": "unreachable", "url": self.base_url}
    
    def tools(self) -> list:
        """List available tools"""
        try:
            response = requests.get(f"{self.base_url}/tools", timeout=5)
            if response.status_code == 200:
                return response.json().get("tools", [])
            return []
        except:
            return []

    def models(self) -> list:
        """List available models"""
        try:
            response = requests.get(f"{self.base_url}/models", timeout=5)
            if response.status_code == 200:
                return response.json().get("models", [])
            return []
        except:
            return []


class RosettaCLI:
    """CLI wrapper for Rosetta"""
    
    def __init__(self):
        self.client = RosettaClient()
    
    def run(self, args: list) -> int:
        """Run CLI commands"""
        if not args:
            print("Rosetta CLI -usage: rosetta [call|execute|health|tools] <prompt>")
            return 1
        
        cmd = args[0]
        
        if cmd == "health":
            result = self.client.health()
            print(json.dumps(result, indent=2))
            return 0 if result.get("status") == "healthy" else 1
        
        if cmd == "tools":
            tools = self.client.tools()
            print(f"Available tools: {len(tools)}")
            for t in tools[:15]:
                print(f"  - {t.get('name')}: {t.get('description', '')}")
            if len(tools) > 15:
                print(f"  ... and {len(tools) - 15} more")
            return 0
        
        if cmd == "models":
            models = self.client.models()
            for m in models:
                print(f"  - {m.get('id')}: {m.get('base_model')}")
            return 0
        
        if cmd == "call":
            prompt = " ".join(args[1:])
            result = self.client.call(prompt)
            print(json.dumps(result, indent=2))
            return 0 if result.get("success") else 1
        
        if cmd == "execute":
            prompt = " ".join(args[1:])
            result = self.client.execute(prompt)
            print(json.dumps(result, indent=2))
            return 0 if result.get("success") else 1
        
        print(f"Unknown command: {cmd}")
        return 1


def main():
    import sys
    cli = RosettaCLI()
    sys.exit(cli.run(sys.argv[1:]) if len(sys.argv) > 1 else cli.run([])


if __name__ == "__main__":
    main()