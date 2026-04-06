#!/usr/bin/env python3
"""Full Agent Loop Demo - Shows real tool execution with result feedback loop.

This demonstrates the complete flow:
1. Model receives message → decides to call tool
2. Tool is executed → results returned
3. Model receives results → can continue with more tools or answer

Usage: python tests/demo_agent_loop.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import asyncio
import json


async def full_agent_loop():
    """Full agent loop with tool execution and feedback."""

    from brain.local_llm_wrapper import LocalLLMWrapper
    from brain.mcp_tool_registry import get_tools

    # Setup
    wrapper = LocalLLMWrapper("qwen2.5-coder:7b", execute_mcp=True)
    tools = get_tools()

    # Find most reliable tools
    reliable_tools = [
        t
        for t in tools
        if any(
            x in t.get("function", {}).get("name", "")
            for x in [
                "search_memories",
                "get_mind_state",
                "git_status",
                "list_directory",
            ]
        )
    ]

    print("=" * 60)
    print("FULL AGENT LOOP WITH TOOL EXECUTION")
    print("=" * 60)

    # === TURN 1: User asks question that needs tools ===
    messages = [{"role": "user", "content": "What's the current project status?"}]

    print(f"\n>>> USER: {messages[0]['content']}")

    # Execute with tools
    result = await wrapper.execute_with_tools(messages, reliable_tools)

    print(f"\n<<< MODEL RESPONSE:")
    print(f"    Type: {result.get('type')}")

    if result.get("calls"):
        tool_call = result["calls"][0]
        print(f"    Tool call: {tool_call['name']}")
        print(f"    Args: {json.dumps(tool_call['arguments'])[:100]}")

        if result.get("executed"):
            exec_result = result["executed"][0]
            print(f"\n    --- TOOL EXECUTED ---")
            print(f"    Tool: {exec_result['tool']}")

            # Show actual result
            r = exec_result.get("result", {}).get("result", {})
            if "status" in r:  # git_status
                print(f"    Git status: {r['status'][:200]}")
            if "results" in r:  # memory search
                print(f"    Memory results: {len(r['results'])} found")
            if "project" in r:  # mind state
                print(f"    Project: {r.get('project')}")
                print(f"    Phase: {r.get('phase')}")

    # === TURN 2: Add tool result to conversation & get final answer ===
    if result.get("executed"):
        # Add tool result as assistant message
        tool_result_str = json.dumps(
            result["executed"][0].get("result", {}).get("result", {})
        )[:500]
        messages.append(
            {"role": "assistant", "content": f"Called {result['calls'][0]['name']}"}
        )
        messages.append(
            {
                "role": "tool",
                "name": result["calls"][0]["name"],
                "content": tool_result_str,
            }
        )

        # Get final answer with tool context
        messages.append(
            {"role": "user", "content": "Based on that information, what's the status?"}
        )

        print(f"\n>>> FOLLOWUP: Based on that information, what's the status?")

        # Second call with tool result in context
        result2 = await wrapper.execute_with_tools(messages, reliable_tools)

        print(f"\n<<< FINAL ANSWER:")
        if result2.get("type") == "text":
            print(f"    {result2.get('content', '')[:300]}")
        elif result2.get("calls"):
            print(f"    (Called another tool: {result2['calls'][0]['name']})")

    print("\n" + "=" * 60)
    print("AGENT LOOP COMPLETE - Tools executed and fed back!")
    print("=" * 60)


async def multi_tool_demo():
    """Demo showing multiple tool calls in sequence."""

    print("\n\n" + "=" * 60)
    print("MULTI-TOOL SEQUENCE DEMO")
    print("=" * 60)

    from brain.local_llm_wrapper import LocalLLMWrapper
    from brain.mcp_tool_registry import get_tools

    wrapper = LocalLLMWrapper("qwen2.5-coder:7b", execute_mcp=True)
    tools = get_tools()

    # Ask something that might need multiple tools
    messages = [{"role": "user", "content": "Check git status and list src directory"}]

    print(f"\n>>> USER: {messages[0]['content']}")

    result = await wrapper.execute_with_tools(messages, tools[:20])

    print(f"\n<<< MODEL:")
    print(f"    Type: {result.get('type')}")

    if result.get("calls"):
        for i, call in enumerate(result["calls"]):
            print(f"\n    Tool {i + 1}: {call['name']}")
            print(f"    Args: {json.dumps(call['arguments'])[:80]}")

    if result.get("executed"):
        print(f"\n    --- EXECUTED {len(result['executed'])} TOOLS ---")
        for e in result["executed"]:
            r = e.get("result", {}).get("result", {})
            if "status" in r:
                print(f"    ✓ git_status: {r['status'][:100]}...")
            if "entries" in r:
                print(f"    ✓ list_directory: {r['count']} entries")
            if "project" in r:
                print(f"    ✓ get_mind_state: {r['project']} ({r['phase']})")


if __name__ == "__main__":
    asyncio.run(full_agent_loop())
    asyncio.run(multi_tool_demo())
