#!/usr/bin/env python3
"""ReAct Agent Loop - The MISSING PIECE that ties everything together.

This is the actual agent loop that:
1. Sends prompt to model
2. Model decides to call tool
3. Tool executes → results returned
4. Results added to conversation
5. Model sees results → continues or answers
6. Repeat until final answer

This is what was missing - the automatic loop that uses tool results.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import asyncio
import json


class ReActAgent:
    """The ReAct (Reasoning + Acting) agent loop."""

    def __init__(self, model: str = "qwen2.5-coder:7b", max_turns: int = 5):
        from brain.local_llm_wrapper import LocalLLMWrapper
        from brain.mcp_tool_registry import get_tools

        self.wrapper = LocalLLMWrapper(model, execute_mcp=True)
        self.tools = get_tools()
        self.max_turns = max_turns
        self.messages = []

    def add_user_message(self, content: str):
        """Add a user message to the conversation."""
        self.messages.append({"role": "user", "content": content})

    async def step(self) -> dict:
        """Execute one step of the ReAct loop.

        Returns:
            dict with: type (text/tool_calls), content/calls, executed results
        """
        result = await self.wrapper.execute_with_tools(self.messages, self.tools)

        # If tool was called, execute it and add result to conversation
        if result.get("type") == "tool_calls" and result.get("calls"):
            executed = result.get("executed", [])

            # Add tool call to conversation
            for call in result["calls"]:
                self.messages.append(
                    {"role": "assistant", "content": f"Calling tool: {call['name']}"}
                )

            # Add tool results to conversation
            for exec_result in executed:
                tool_name = exec_result.get("tool", "unknown")
                tool_output = json.dumps(exec_result.get("result", {}))[:1000]

                self.messages.append(
                    {"role": "tool", "content": tool_output, "name": tool_name}
                )

            return {
                "type": "tool_executed",
                "calls": result["calls"],
                "executed": executed,
                "turn": len([m for m in self.messages if m.get("role") == "assistant"]),
            }

        # If text response, we're done
        elif result.get("type") == "text":
            self.messages.append(
                {"role": "assistant", "content": result.get("content", "")}
            )
            return {"type": "final_answer", "content": result.get("content", "")}

        return {"type": "unknown", "raw": result}

    async def run(self) -> dict:
        """Run the full ReAct loop until final answer or max turns."""
        print("=" * 60)
        print("ReAct AGENT LOOP STARTING")
        print("=" * 60)

        for turn in range(self.max_turns):
            print(f"\n--- TURN {turn + 1} ---")

            step_result = await self.step()

            print(f"Result type: {step_result['type']}")

            if step_result["type"] == "tool_executed":
                for e in step_result.get("executed", []):
                    r = e.get("result", {}).get("result", {})
                    if "status" in r:  # git status
                        print(f"  → Executed: git_status")
                        print(f"     {r['status'][:100]}...")
                    elif "results" in r:  # memory
                        print(f"  → Executed: search_memories")
                        print(f"     Found: {len(r['results'])} results")
                    elif "entries" in r:  # list directory
                        print(f"  → Executed: list_directory")
                        print(f"     {r['count']} entries")
                    elif "project" in r:  # mind state
                        print(f"  → Executed: get_mind_state")
                        print(f"     Project: {r.get('project')} ({r.get('phase')})")
                    else:
                        print(f"  → Executed: {e['tool']}")

                # Continue to next turn with tool results in context
                print(f"\n  → Continuing with tool results...")
                continue

            elif step_result["type"] == "final_answer":
                print(f"\n{'=' * 60}")
                print(f"FINAL ANSWER:")
                print(f"{step_result['content'][:500]}")
                print(f"{'=' * 60}")
                return step_result

        return {"type": "max_turns", "messages": self.messages}


async def demo():
    """Demo the ReAct agent loop."""

    # Create agent
    agent = ReActAgent("qwen2.5-coder:7b")

    # Add user task
    agent.add_user_message(
        "Check the git status and list the src directory, tell me what you found"
    )

    # Run the full loop
    result = await agent.run()

    print(f"\nFinal result type: {result['type']}")

    # Show conversation
    print(f"\n--- CONVERSATION ({len(agent.messages)} messages) ---")
    for i, msg in enumerate(agent.messages):
        role = msg["role"]
        content = msg.get("content", "")[:80]
        print(f"{i + 1}. {role}: {content}...")


async def demo2():
    """Another demo - memory search."""

    print("\n\n" + "=" * 60)
    print("DEMO 2: Memory Search with ReAct Loop")
    print("=" * 60)

    agent = ReActAgent("qwen2.5-coder:7b")
    agent.add_user_message(
        "Search memory for anything related to routing and tell me what you found"
    )

    result = await agent.run()

    if result["type"] == "final_answer":
        print(f"\nAnswer: {result['content'][:300]}")


if __name__ == "__main__":
    asyncio.run(demo())
    asyncio.run(demo2())
