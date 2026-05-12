#!/usr/bin/env python3
"""
OpenCode Rosetta Integration

Usage in OpenCode:
    Use the 'rosetta' agent type which routes through Rosetta for tool calling
    
Or as a tool (from OpenCode):
    # Example: use 'rosetta' agent type which routes through Rosetta

This script provides:
1. Shell wrapper for CLI usage
2. Can be called from OpenCode as a subagent
"""

import sys
import json
import asyncio

sys.path.insert(0, "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/nx_trainer")

from rosetta_client import RosettaClient
from rosetta_executor import RosettaExecutor, ToolCall


def run_rosetta(prompt: str, execute: bool = False, url: str = "http://localhost:8000") -> dict:
    """
    Main function for OpenCode integration
    
    Args:
        prompt: Natural language prompt (e.g., "search memory for security")
        execute: If True, actually execute the tool. If False, just return the JSON.
        url: Rosetta server URL
    
    Returns:
        dict with success, tool_call, result, etc.
    """
    client = RosettaClient(base_url=url)
    
    result = client.call(prompt)
    
    if not result.get("success"):
        return {
            "success": False,
            "error": result.get("error", "Unknown error"),
            "prompt": prompt,
        }
    
    tool_call = result.get("tool_call", {})
    tool_name = tool_call.get("tool", "unknown")
    tool_args = tool_call.get("args", {})
    
    response = {
        "success": True,
        "prompt": prompt,
        "tool_call": tool_call,
        "raw_output": result.get("raw_output"),
        "tokens_used": result.get("tokens_used", 0),
    }
    
    if execute:
        executor = RosettaExecutor()
        tool_obj = ToolCall(tool=tool_name, args=tool_args, raw=result.get("raw_output", ""))
        
        loop = asyncio.get_event_loop()
        exec_result = loop.run_until_complete(executor.execute_tool(tool_obj))
        
        response["execution"] = exec_result
        response["success"] = exec_result.get("success", False)
    
    return response


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Rosetta for OpenCode")
    parser.add_argument("prompt", nargs="*", help="Natural language prompt")
    parser.add_argument("--execute", "-e", action="store_true", help="Execute tool")
    parser.add_argument("--url", "-u", default="http://localhost:8000", help="Rosetta server URL")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    if not args.prompt:
        print("Usage: rosetta_opencode.py [options] <prompt>")
        print("  -e, --execute    Execute the tool")
        print("  -u, --url       Rosetta server URL")
        print("  -j, --json      Output as JSON")
        return 1
    
    prompt = " ".join(args.prompt)
    
    result = run_rosetta(prompt, execute=args.execute, url=args.url)
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result.get("success"):
            print(f"✓ Tool: {result['tool_call'].get('tool')}")
            print(f"  Args: {result['tool_call'].get('args')}")
            if args.execute and result.get("execution"):
                exec_res = result["execution"]
                if exec_res.get("success"):
                    print(f"  ✓ Executed successfully")
                    if exec_res.get("result"):
                        print(f"  Result: {str(exec_res['result'])[:200]}...")
                else:
                    print(f"  ✗ Error: {exec_res.get('error')}")
        else:
            print(f"✗ Error: {result.get('error')}")
    
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())