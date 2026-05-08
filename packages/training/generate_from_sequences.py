#!/usr/bin/env python3
"""Generate Training Data from Tool Sequences.

Extract training examples from tool_sequences table with:
- Positive examples: successful tool call patterns
- Negative examples: when NOT to call tools
- Context enrichment: task type, complexity

Usage:
    python generate_from_sequences.py --output datasets/sequence_training.jsonl
    python generate_from_sequences.py --positive-only
    python generate_from_sequences.py --negative-only
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).parent.parent
OUTCOMES_DB = PROJECT_ROOT / ".sisyphus" / "outcomes.db"


def get_tool_sequences(limit: int = 1000) -> List[Dict]:
    """Get tool sequences from database."""
    if not OUTCOMES_DB.exists():
        return []

    conn = sqlite3.connect(str(OUTCOMES_DB))
    cursor = conn.execute(
        """SELECT task_id, sequence, outcome, timestamp, duration_ms
           FROM tool_sequences
           ORDER BY timestamp DESC
           LIMIT ?""",
        (limit,),
    )

    results = []
    for row in cursor:
        results.append(
            {
                "task_id": row[0],
                "sequence": row[1],
                "outcome": row[2],
                "timestamp": row[3],
                "duration_ms": row[4],
            }
        )

    conn.close()
    return results


def get_outcomes(limit: int = 1000) -> List[Dict]:
    """Get outcomes from database."""
    if not OUTCOMES_DB.exists():
        return []

    conn = sqlite3.connect(str(OUTCOMES_DB))
    cursor = conn.execute(
        """SELECT task_description, agent, success, timestamp, latency_ms, tokens_used
           FROM outcomes
           ORDER BY timestamp DESC
           LIMIT ?""",
        (limit,),
    )

    results = []
    for row in cursor:
        results.append(
            {
                "task_description": row[0],
                "agent": row[1],
                "success": bool(row[2]),
                "timestamp": row[3],
                "latency_ms": row[4],
                "tokens_used": row[5],
            }
        )

    conn.close()
    return results


def generate_positive_examples() -> List[Dict]:
    """Generate positive examples (successful patterns)."""
    examples = []

    # Get successful outcomes
    outcomes = get_outcomes(limit=500)
    successful = [o for o in outcomes if o.get("success")]

    for outcome in successful:
        # Extract tool call pattern from agent
        agent = outcome.get("agent", "")
        task = outcome.get("task_description", "")

        if not task:
            continue

        examples.append(
            {
                "input": f"Task: {task[:200]}",
                "output": f'[TOOL_CALL]{{tool => \'{agent}_delegate\', args => {{ --task "{task[:100]}", --agent "{agent}" }}}}[/TOOL_CALL]',
                "tool_name": f"{agent}_delegate",
                "category": "routing",
                "outcome": "success",
                "context": {
                    "latency_ms": outcome.get("latency_ms"),
                    "tokens": outcome.get("tokens_used"),
                },
            }
        )

    return examples


def generate_negative_examples() -> List[Dict]:
    """Generate negative examples (when NOT to call tools)."""
    examples = []

    # Get failed outcomes - what went wrong
    outcomes = get_outcomes(limit=500)
    failed = [o for o in outcomes if not o.get("success")]

    # Simple tasks that shouldn't need tool calls
    simple_tasks = [
        ("What is 2 + 2?", "math"),
        ("What is the capital of France?", "knowledge"),
        ("Hello, how are you?", "conversation"),
        ("What time is it?", "simple_query"),
        ("Tell me a joke", "entertainment"),
    ]

    for task, task_type in simple_tasks:
        examples.append(
            {
                "input": task,
                "output": f"[TOOL_CALL]{{tool => 'direct_answer', args => {{ --text \"This is a simple {task_type} question that doesn't require tools.\" }}}}[/TOOL_CALL]",
                "tool_name": "direct_answer",
                "category": "fallback",
                "outcome": "negative_example",
                "context": {"reason": f"Simple {task_type} - no tool needed"},
            }
        )

    # Failed outcomes as negative examples
    for outcome in failed[:50]:
        task = outcome.get("task_description", "")
        agent = outcome.get("agent", "")

        if task:
            examples.append(
                {
                    "input": f"Task: {task[:200]}",
                    "output": f'[TOOL_CALL]{{tool => \'analyze_failure\', args => {{ --previous_agent "{agent}", --task "{task[:100]}" }}}}[/TOOL_CALL]',
                    "tool_name": "analyze_failure",
                    "category": "error_handling",
                    "outcome": "negative_learned",
                    "context": {
                        "failed_agent": agent,
                        "reason": "Previous attempt failed - try different approach",
                    },
                }
            )

    return examples


def generate_sequence_examples() -> List[Dict]:
    """Generate examples from tool sequences."""
    examples = []

    sequences = get_tool_sequences(limit=200)

    for seq in sequences:
        sequence = seq.get("sequence", "")
        outcome_type = seq.get("outcome", "")

        if not sequence:
            continue

        # Parse sequence (format: "tool1 → tool2 → tool3")
        tools = [t.strip() for t in sequence.split(" → ")]

        if len(tools) == 1:
            # Single tool - direct pattern
            examples.append(
                {
                    "input": f"Tool sequence: {tools[0]}",
                    "output": f"[TOOL_CALL]{{tool => '{tools[0]}', args => {{}}}}[/TOOL_CALL]",
                    "tool_name": tools[0],
                    "category": "single_tool",
                    "outcome": outcome_type,
                    "context": {"sequence_length": 1},
                }
            )
        elif len(tools) == 2:
            # Two tools - pattern
            examples.append(
                {
                    "input": f"Need: {tools[0]}, then {tools[1]}",
                    "output": f"[TOOL_CALL]{{tool => 'sequence', args => {{ --steps \"{tools[0]} → {tools[1]}\" }}}}[/TOOL_CALL]",
                    "tool_name": "sequence",
                    "category": "multi_tool",
                    "outcome": outcome_type,
                    "context": {"tools": tools, "sequence_length": 2},
                }
            )
        else:
            # More tools - complex pattern
            examples.append(
                {
                    "input": f"Complex task with {len(tools)} steps",
                    "output": f"[TOOL_CALL]{{tool => 'orchestrate', args => {{ --steps \"{', '.join(tools)}\" }}}}[/TOOL_CALL]",
                    "tool_name": "orchestrate",
                    "category": "complex",
                    "outcome": outcome_type,
                    "context": {"tools": tools, "sequence_length": len(tools)},
                }
            )

    return examples


def generate_all_examples() -> Dict[str, List[Dict]]:
    """Generate all training examples."""
    return {
        "positive": generate_positive_examples(),
        "negative": generate_negative_examples(),
        "sequences": generate_sequence_examples(),
    }


def save_examples(examples: List[Dict], output_file: Path):
    """Save examples to JSONL file."""
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, "w") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")

    return len(examples)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate Training from Sequences")
    parser.add_argument(
        "--output", default="datasets/sequence_training.jsonl", help="Output file"
    )
    parser.add_argument(
        "--positive-only", action="store_true", help="Generate only positive examples"
    )
    parser.add_argument(
        "--negative-only", action="store_true", help="Generate only negative examples"
    )
    parser.add_argument(
        "--sequences-only", action="store_true", help="Generate only sequence examples"
    )
    parser.add_argument(
        "--limit", type=int, default=500, help="Max examples per category"
    )

    args = parser.parse_args()

    output_path = PROJECT_ROOT / args.output

    if args.positive_only:
        examples = generate_positive_examples()[: args.limit]
    elif args.negative_only:
        examples = generate_negative_examples()[: args.limit]
    elif args.sequences_only:
        examples = generate_sequence_examples()[: args.limit]
    else:
        all_examples = generate_all_examples()
        examples = (
            all_examples["positive"][: args.limit]
            + all_examples["negative"][: args.limit]
            + all_examples["sequences"][: args.limit]
        )

    count = save_examples(examples, output_path)

    print(f"Generated {count} training examples")
    print(f"Saved to: {output_path}")

    # Print breakdown
    if not args.positive_only and not args.negative_only and not args.sequences_only:
        pos = len([e for e in examples if e.get("outcome") == "success"])
        neg = len([e for e in examples if "negative" in e.get("outcome", "")])
        seq = len(examples) - pos - neg
        print(f"  - Positive: {pos}")
        print(f"  - Negative: {neg}")
        print(f"  - Sequences: {seq}")


if __name__ == "__main__":
    main()
