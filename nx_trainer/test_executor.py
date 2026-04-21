#!/usr/bin/env python3
"""
Test Rosetta Executor - End to end test

Tests parsing and basic functionality without MCP connection.
"""

import asyncio
import json
import sys
sys.path.insert(0, "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")

import sys
sys.path.insert(0, "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/nx_trainer")

from rosetta_executor import RosettaExecutor, ToolCall
from rosetta_registry import is_supported, TOOL_REGISTRY, get_tool_info


def test_parsing():
    """Test JSON parsing"""
    print("\n=== Testing JSON Parsing ===")
    
    executor = RosettaExecutor()
    
    test_cases = [
        ('{"tool": "memory_search", "args": {"query": "security"}}',
         "memory_search", {"query": "security"}),
        ('{"tool": "read_file", "args": {"filePath": "/tmp/test.txt"}}',
         "read_file", {"filePath": "/tmp/test.txt"}),
        ('{"tool": "github_search_repos", "args": {"query": "python"}}',
         "github_search_repos", {"query": "python"}),
    ]
    
    passed = 0
    failed = 0
    
    for json_str, expected_tool, expected_args in test_cases:
        result = executor.parse_tool_json(json_str)
        
        if result.tool == expected_tool and result.args == expected_args:
            print(f"  ✓ Parsed: {expected_tool}")
            passed += 1
        else:
            print(f"  ✗ Failed: {json_str}")
            print(f"    Got: {result.tool}, {result.args}")
            failed += 1
    
    print(f"\nParsing: {passed}/{passed+failed} passed")
    return passed, failed


def test_registry():
    """Test tool registry"""
    print("\n=== Testing Tool Registry ===")
    
    test_tools = [
        "memory_search",
        "read_file",
        "write_file", 
        "github_search_repos",
        "github_list_issues",
        "sqlite_query",
    ]
    
    passed = 0
    failed = 0
    
    for tool in test_tools:
        if is_supported(tool):
            info = get_tool_info(tool)
            print(f"  ✓ {tool}: {info['namespace']}.{info['function']}")
            passed += 1
        else:
            print(f"  ✗ {tool}: NOT SUPPORTED")
            failed += 1
    
    print(f"\nRegistry: {passed}/{passed+failed} supported")
    return passed, failed


def test_coverage():
    """Test tool coverage"""
    print("\n=== Testing Tool Coverage ===")
    
    # Load training data
    data_path = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/nx_trainer/data/v4_real.jsonl"
    import os
    if not os.path.exists(data_path):
        print("  Training data not found, skipping coverage test")
        return 0, 0
    
    try:
        with open(data_path) as f:
            data = [json.loads(line) for line in f]
    except:
        print("  Could not load training data")
        return 0, 1
    
    tools_used = set()
    for item in data:
        msgs = item.get("messages", [])
        if len(msgs) >= 2:
            try:
                resp = json.loads(msgs[1].get("content", "{}"))
                tool = resp.get("tool", "")
                if tool:
                    tools_used.add(tool)
            except:
                pass
    
    supported = sum(1 for t in tools_used if is_supported(t))
    unsupported = sum(1 for t in tools_used if not is_supported(t))
    
    print(f"  Tools in training data: {len(tools_used)}")
    print(f"  Supported by registry: {supported}")
    print(f"  Not supported: {unsupported}")
    
    if unsupported > 0:
        missing = [t for t in tools_used if not is_supported(t)]
        print(f"  Missing: {missing}")
    
    return supported, unsupported


def main():
    print("=" * 50)
    print("Rosetta Executor Test Suite")
    print("=" * 50)
    
    # Run tests
    p1, f1 = test_parsing()
    p2, f2 = test_registry()
    p3, f3 = test_coverage()
    
    total_pass = p1 + p2 + p3
    total_fail = f1 + f2 + f3
    
    print("\n" + "=" * 50)
    print(f"Total: {total_pass} passed, {total_fail} failed")
    print("=" * 50)
    
    if total_fail > 0:
        print("\n⚠️  Some tests failed")
        return 1
    else:
        print("\n✓ All tests passed")
        return 0


if __name__ == "__main__":
    sys.exit(main())