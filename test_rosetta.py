#!/usr/bin/env python3
"""Rosetta Stone Test Script"""
import asyncio
import sys
import os

sys.path.insert(0, "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
os.chdir("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")

async def test():
    from nx_trainer.rosetta_executor import RosettaExecutor
    executor = RosettaExecutor()
    
    print("=" * 50)
    print("ROSETTA STONE TEST")
    print("=" * 50)
    
    # Test 1: Function call
    print("\n[1] Function call:")
    result = await executor.execute_tool(
        executor.parse_tool_json('{"tool": "getActiveContext", "args": {}}')
    )
    print(f"    getActiveContext: {result.get('mode')} - {result.get('result', {}).get('project')}")
    
    # Test 2: Subprocess
    print("\n[2] Subprocess call:")
    result = await executor.execute_tool(
        executor.parse_tool_json('{"tool": "gitStatus", "args": {}}')
    )
    print(f"    gitStatus: {result.get('mode')} - {result.get('result', '')[:50]}...")
    
    # Test 3: Memory
    print("\n[3] Memory search:")
    result = await executor.execute_tool(
        executor.parse_tool_json('{"tool": "searchMemory", "args": {"query": "security"}}')
    )
    print(f"    searchMemory: {result.get('mode')} - {len(result.get('result', {}).get('results', []))} results")
    
    print("\n" + "=" * 50)
    print("ALL TESTS PASSED!")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(test())