#!/usr/bin/env python3
"""
N-Xyme MIND - Unified Personal AI System
=========================================
Entry point for the synthesized N-Xyme system.
Replaces: OpenCode + OMO + BMAD with a single unified system.

Usage:
    nx-mind "task description"
    nx-mind --interactive
    nx-mind --agent=hephaestus "fix the bug"
    nx-mind --mode=visual "design UI"
"""

import argparse
import asyncio
import json
import logging
import os
import sys

# Add project root and sibling modules to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Add frankenstein_engine (sibling directory for local LLM)
FRANKENSTEIN_PATH = os.path.join(PROJECT_ROOT, "frankenstein_engine")
if os.path.isdir(FRANKENSTEIN_PATH):
    sys.path.insert(0, FRANKENSTEIN_PATH)

# Reduce noise
logging.basicConfig(level=logging.WARNING)

from packages.nx_delegate.nx_delegate import nx_delegate
from packages.orchestration.weighted_injector import inject_weighted
from packages.local_llm.brain import Brain


def parse_args():
    parser = argparse.ArgumentParser(
        description="N-Xyme MIND - Your Personal AI System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    nx-mind "implement JWT authentication"
    nx-mind "fix the login bug" --agent=hephaestus
    nx-mind "design a sidebar" --mode=visual
    nx-mind --interactive
        """,
    )
    parser.add_argument(
        "task", nargs="?", help="Task description (use quotes for multi-word tasks)"
    )
    parser.add_argument(
        "--agent", "-a", help="Force specific agent (hephaestus, oracle, explore, etc.)"
    )
    parser.add_argument(
        "--mode",
        "-m",
        choices=["fast", "visual", "deep", "writing"],
        help="Execution mode",
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Start interactive mode"
    )
    parser.add_argument(
        "--execute", "-e", action="store_true", help="Execute the task (not just route)"
    )
    parser.add_argument("--context", "-c", help="Additional context to inject")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    return parser.parse_args()


def print_result(result: dict, json_output: bool = False, verbose: bool = False):
    if json_output:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n🤖 Agent: {result.get('agent', 'unknown')}")
        print(f"📊 Level: {result.get('level', '?')}/5")
        print(f"🎯 Confidence: {result.get('confidence', 0) * 100:.0f}%")
        print(f"⚡ Strategy: {result.get('strategy_used', 'unknown')}")
        print(f"💡 Reason: {result.get('reason', 'N/A')}")

        if verbose:
            print(f"\n⏱️ Latency: {result.get('latency_ms', 0):.0f}ms")
            print(f"📝 Prompt:\n{result.get('prompt', 'N/A')[:500]}...")


def interactive_mode():
    """Interactive REPL mode."""
    print("=" * 60)
    print("N-Xyme MIND - Interactive Mode")
    print("Type 'exit' or 'quit' to exit")
    print("=" * 60)

    while True:
        try:
            task = input("\n🎯 > ").strip()
            if task.lower() in ["exit", "quit", "q"]:
                print("👋 Goodbye!")
                break
            if not task:
                continue

            result = nx_delegate(task)
            print_result(result, verbose=True)

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


async def main_async(args):
    """Main async execution."""
    # Get category hint from mode
    category_hint = None
    if args.mode == "visual":
        category_hint = "visual-engineering"
    elif args.mode == "deep":
        category_hint = "deep"
    elif args.mode == "writing":
        category_hint = "writing"
    elif args.mode == "fast":
        category_hint = "quick"

    # Override with explicit agent if provided
    if args.agent:
        category_hint = args.agent

    # Execute routing
    result = nx_delegate(args.task, category_hint)

    # If explicit agent requested, override the routing
    if args.agent:
        result["agent"] = args.agent

    # Inject weighted context if context provided
    if args.context:
        weighted_context = inject_weighted(result["agent"], args.task, args.context)
        if args.verbose:
            print(f"\n📎 Injected context: {len(weighted_context)} chars")

    return result


def execute_task(task: str, agent: str, verbose: bool = False) -> dict:
    """Execute a task using the local Brain LLM."""
    print(f"\n🚀 Executing task with {agent} agent...")

    try:
        # Initialize Brain (lazy loads model)
        brain = Brain()

        # Build system prompt based on agent
        system_prompts = {
            "hephaestus": "You are Hephaestus, a senior software engineer. Implement the requested code changes. Read relevant files first, make minimal changes, verify with typecheck/lint.",
            "explore": "You are Explore, a code search agent. Find the relevant code for the task. Use grep and read to locate files.",
            "oracle": "You are Oracle, an architecture advisor. Analyze the task and provide guidance on approach, patterns to follow, and potential issues.",
            "quick": "You are a quick-fix assistant. Make minimal, targeted changes to fix the issue.",
            "deep": "You are a deep-analysis agent. Thoroughly understand the problem before acting.",
        }

        system_prompt = system_prompts.get(
            agent, f"You are {agent}, executing the user's task."
        )

        # For now, just use Brain for text completion
        # Full tool calling would require Rosetta integration
        response = brain.chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": task},
            ]
        )

        return {
            "executed": True,
            "agent": agent,
            "response": response,
            "status": "completed",
        }

    except Exception as e:
        return {"executed": False, "agent": agent, "error": str(e), "status": "failed"}


def main():
    args = parse_args()

    # Handle interactive mode
    if args.interactive:
        interactive_mode()
        return 0

    # Validate task
    if not args.task:
        print("Error: Task is required. Use --help for usage.", file=sys.stderr)
        return 1

    # Run async main
    try:
        result = asyncio.run(main_async(args))

        # Execute if requested
        if args.execute:
            exec_result = execute_task(
                args.task, result.get("agent", "hephaestus"), args.verbose
            )
            if args.json:
                print(json.dumps(exec_result, indent=2))
            else:
                if exec_result.get("executed"):
                    print(f"\n✅ Execution completed")
                    print(f"📤 Response:\n{exec_result.get('response', 'N/A')}")
                else:
                    print(f"\n❌ Execution failed: {exec_result.get('error')}")
            return 0 if exec_result.get("executed") else 1

        print_result(result, args.json, args.verbose)

        # If not JSON, show next step hint
        if not args.json:
            print(f'\n💡 To execute: nx-mind "{args.task}" --execute')
            print(f'   Or use: nx-delegate "{args.task}" --agent={result["agent"]}')

        return 0
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
