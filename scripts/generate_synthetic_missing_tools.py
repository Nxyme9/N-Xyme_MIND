#!/usr/bin/env python3
"""Generate synthetic training data for missing tools."""

import json
import random
from pathlib import Path

# Missing tools with their parameter schemas
MISSING_TOOLS = {
    "orchestrate": {"user_input": "str", "context": "dict"},
    "detect_state": {"user_input": "str"},
    "list_workflows": {},
    "execute_workflow": {"workflow": "str", "context": "dict"},
    "run_quality_gates": {"files": "list"},
    "get_orchestrator_status": {},
    "search_memories": {
        "query": "str",
        "limit": "int",
        "strict": "bool",
        "rerank": "bool",
    },
    "get_memory_stats": {},
    "recall_session": {"session_id": "str", "limit": "int"},
    "find_context": {"task": "str", "context_type": "str"},
    "memory_search": {"query": "str", "limit": "int"},
    "memory_write": {"content": "str", "kind": "str", "metadata": "dict"},
    "memory_stats": {},
    "get_capabilities": {},
    "route_task": {"task_description": "str"},
    "route": {"task_description": "str"},
    "score_complexity": {"task_description": "str"},
    "available_agents": {},
    "get_routing_history": {"limit": "int"},
    "spawn": {"agent": "str", "task": "str", "context": "dict"},
    "task_status": {"task_id": "str"},
    "health_check": {},
    "get_session": {"agent_type": "str"},
    "return_session": {"session_id": "str", "agent_type": "str"},
    "pool_stats": {},
    "warm_pool": {"agents": "list"},
    "record_outcome": {
        "task": "str",
        "agent": "str",
        "success": "bool",
        "latency_ms": "int",
    },
    "get_outcomes": {"task_type": "str", "agent": "str", "limit": "int"},
    "log_outcome": {"task": "str", "outcome": "str", "success": "bool"},
    "get_recommendations": {"task_description": "str"},
    "learning_stats": {},
    "get_learning_progress": {},
    "retrain": {"agent": "str"},
    "status": {},
}

# Variations for different input phrasings
INPUT_VARIATIONS = {
    "orchestrate": [
        "orchestrate: build a new feature",
        "run the planning workflow",
        "execute BMAD workflow for refactoring",
        "start orchestration for testing",
    ],
    "detect_state": [
        "detect if user is stuck",
        "check user state",
        "analyze if user needs help",
        "detect FRICTION state",
    ],
    "list_workflows": [
        "show available workflows",
        "what workflows can you run",
        "list all BMAD workflows",
    ],
    "execute_workflow": [
        "execute the testing workflow",
        "run quality gates workflow",
        "start the planning workflow",
    ],
    "run_quality_gates": [
        "run quality gates on src/",
        "run gates on config files",
        "execute quality checks",
    ],
    "get_orchestrator_status": [
        "check orchestrator status",
        "how is the system running",
        "system health check",
    ],
    "search_memories": [
        "search memory for auth",
        "find in memory about config",
        "search all memories for deploy",
    ],
    "get_memory_stats": [
        "get memory statistics",
        "show memory stats",
        "memory usage info",
    ],
    "recall_session": [
        "recall session abc123",
        "get previous session context",
        "load session history",
    ],
    "find_context": [
        "find context for testing task",
        "get relevant context for debugging",
        "find context about refactoring",
    ],
    "memory_search": [
        "search memory for security",
        "find info in memory about API",
    ],
    "memory_write": [
        "remember that we are working on auth",
        "save to memory: tested feature works",
        "write this to episodic memory",
    ],
    "memory_stats": [
        "show memory statistics",
        "how much memory is used",
    ],
    "get_capabilities": [
        "what can you do",
        "list capabilities",
        "show your skills",
    ],
    "route_task": [
        "route: implement auth",
        "route task: write tests",
        "delegate refactoring",
    ],
    "route": [
        "route this task",
        "which agent should handle this",
    ],
    "score_complexity": [
        "how complex is debugging this error",
        "score the complexity of this task",
    ],
    "available_agents": [
        "show available agents",
        "what agents do you have",
    ],
    "get_routing_history": [
        "show routing history",
        "recent routing decisions",
    ],
    "spawn": [
        "spawn Hephaestus for implementation",
        "delegate to explore agent",
        "start agent: hephaestus",
    ],
    "task_status": [
        "check task abc123 status",
        "what is task status",
    ],
    "health_check": [
        "system health check",
        "check if all services running",
    ],
    "get_session": [
        "get session for hephaestus",
        "acquire agent session",
    ],
    "return_session": [
        "return session to pool",
        "release agent session",
    ],
    "pool_stats": [
        "show session pool stats",
        "how many sessions available",
    ],
    "warm_pool": [
        "warm up the pool",
        "pre-warm agent sessions",
    ],
    "record_outcome": [
        "record successful outcome",
        "log task completion",
    ],
    "get_outcomes": [
        "get recent outcomes",
        "show task results",
    ],
    "log_outcome": [
        "log this outcome",
        "record result",
    ],
    "get_recommendations": [
        "get agent recommendations",
        "recommend best agent for this",
    ],
    "learning_stats": [
        "show learning stats",
        "routing performance",
    ],
    "get_learning_progress": [
        "how is learning going",
        "learning progress",
    ],
    "retrain": [
        "retrain the model",
        "start model retraining",
    ],
    "status": [
        "show system status",
        "overall status",
    ],
}


def generate_tool_call(tool_name, variation):
    """Generate tool call output from input variation."""
    return f'[TOOL_CALL]{{tool => "{tool_name}", args => {{ }}}}[/TOOL_CALL]'


def generate_output(tool_name, args):
    """Generate the output format for a tool call."""
    if not args:
        return f'[TOOL_CALL]{{tool => "{tool_name}", args => {{ }}}}[/TOOL_CALL]'

    args_str = ", ".join(f'--{k} "{v}"' for k, v in args.items())
    return f'[TOOL_CALL]{{tool => "{tool_name}", args => {{ {args_str} }}}}[/TOOL_CALL]'


def generate_examples():
    """Generate synthetic training examples."""
    examples = []

    for tool_name, params in MISSING_TOOLS.items():
        variations = INPUT_VARIATIONS.get(tool_name, [f"use {tool_name}"])

        # Generate 3-5 variations per tool
        for i, variation in enumerate(variations[:5]):
            # Build args based on tool
            args = {}
            for param, ptype in params.items():
                if (
                    param == "user_input"
                    or param == "task_description"
                    or param == "query"
                ):
                    args[param] = (
                        variation.split(":")[-1].strip()
                        if ":" in variation
                        else "test task"
                    )
                elif param == "task":
                    args[param] = "test task"
                elif param == "agent":
                    args[param] = "hephaestus"
                elif param == "limit":
                    args[param] = 10
                elif param == "success":
                    args[param] = "true"
                elif param == "latency_ms":
                    args[param] = 1000
                elif param == "context":
                    args[param] = "{}"
                elif param == "metadata":
                    args[param] = "{}"
                elif param == "files":
                    args[param] = "[]"
                elif param == "agents":
                    args[param] = "[]"
                elif param == "strict" or param == "rerank":
                    args[param] = "false"
                elif param == "kind":
                    args[param] = "episodic"
                elif param == "context_type":
                    args[param] = "all"
                elif param == "task_type":
                    args[param] = "implementation"

            # Build output
            if args:
                args_str = ", ".join(f'--{k} "{v}"' for k, v in args.items())
                output = f'[TOOL_CALL]{{tool => "{tool_name}", args => {{ {args_str} }}}}[/TOOL_CALL]'
            else:
                output = (
                    f'[TOOL_CALL]{{tool => "{tool_name}", args => {{ }}}}[/TOOL_CALL]'
                )

            examples.append(
                {"input": variation, "output": output, "tool": tool_name, "args": args}
            )

    return examples


def main():
    examples = generate_examples()

    # Save to JSONL
    output_path = Path("datasets/rosetta_synthetic_missing_tools.jsonl")
    with open(output_path, "w") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")

    print(f"Generated {len(examples)} examples for {len(MISSING_TOOLS)} missing tools")
    print(f"Saved to: {output_path}")

    # Show sample
    print("\n=== SAMPLE EXAMPLES ===")
    for ex in examples[:5]:
        print(f"Input: {ex['input']}")
        print(f"Output: {ex['output']}")
        print()


if __name__ == "__main__":
    main()
