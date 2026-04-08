#!/usr/bin/env python3
"""Rosetta Stone Integration - Use rosetta model to translate requests to tool calls.

This module integrates the Rosetta Stone model into the tool execution pipeline:
1. User request → Rosetta Stone model → [TOOL_CALL] format
2. Parse tool call → Execute via MCP
3. Return results

Usage:
    python -m packages.local_llm.rosetta_integration "search memory for security"
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent


def call_rosetta(prompt: str, model: str = "rosetta") -> str:
    """Call the Rosetta Stone model to translate a request to tool call."""
    result = subprocess.run(
        ["ollama", "run", model, prompt],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.strip()


def parse_tool_call(response: str) -> Optional[Dict[str, Any]]:
    """Parse [TOOL_CALL] format from Rosetta Stone response.
    
    Expected format:
    [TOOL_CALL]{tool => "tool_name", args => { --key "value" }}[/TOOL_CALL]
    """
    # Match the [TOOL_CALL] block
    pattern = r'\[TOOL_CALL\]\s*\{.*?tool\s*=>\s*"([^"]+)".*?args\s*=>\s*\{([^}]*)\}.*?\}\s*\[/TOOL_CALL\]'
    match = re.search(pattern, response, re.DOTALL)
    
    if not match:
        return None
    
    tool_name = match.group(1)
    args_str = match.group(2)
    
    # Parse arguments: --key "value" format
    args = {}
    arg_pattern = r'--(\w+)\s+"([^"]*)"'
    for arg_match in re.finditer(arg_pattern, args_str):
        key = arg_match.group(1)
        value = arg_match.group(2)
        args[key] = value
    
    return {"tool": tool_name, "args": args}


def translate_request(request: str) -> Optional[Dict[str, Any]]:
    """Translate user request to tool call using Rosetta Stone.
    
    Args:
        request: User's natural language request
        
    Returns:
        Dict with 'tool' and 'args', or None if no tool call needed
    """
    print(f"[Rosetta] Translating: '{request}'")
    
    response = call_rosetta(request)
    print(f"[Rosetta] Response: {response}")
    
    tool_call = parse_tool_call(response)
    
    if tool_call:
        print(f"[Rosetta] Detected tool: {tool_call['tool']}")
        print(f"[Rosetta] Args: {tool_call['args']}")
    else:
        print(f"[Rosetta] No tool call detected")
    
    return tool_call


def test_rosetta():
    """Test Rosetta Stone with various requests."""
    test_cases = [
        "search memory for security",
        "show me README.md",
        "check git status",
        "list issues for microsoft/vscode",
        "fetch https://docs.python.org",
    ]
    
    print("=" * 50)
    print("Rosetta Stone Integration Test")
    print("=" * 50)
    
    for request in test_cases:
        print(f"\n>>> {request}")
        result = translate_request(request)
        if result:
            print(f"    Tool: {result['tool']}")
            print(f"    Args: {result['args']}")
        print("-" * 40)


def main():
    if len(sys.argv) < 2:
        # Run tests
        test_rosetta()
    else:
        # Translate single request
        request = " ".join(sys.argv[1:])
        result = translate_request(request)
        
        if result:
            print(json.dumps(result, indent=2))
        else:
            print(json.dumps({"error": "No tool call detected"}, indent=2))


if __name__ == "__main__":
    main()