#!/usr/bin/env python3
"""
prepare_training_data.py — One-shot data prep for Mojo training.

Mines sessions → generates positive/negative pairs → exports for trainer.

Usage:
    python3 services/training/prepare_training_data.py

Output:
    data/training/train_pairs.jsonl   (positive + hard negatives)
    data/training/train_meta.json     (stats, tags, agent counts)

Run this before training. Let it cook on GPU.
"""

import json
import random
import sys
from pathlib import Path
from collections import Counter
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent.parent
SESSIONS = ROOT / "data" / "sessions"
TRAINING = ROOT / "data" / "training"
OUTPUT = TRAINING / "train_pairs.jsonl"
META = TRAINING / "train_meta.json"

MIN_SEQ_LENGTH = 3  # Minimum messages for pair mining

def extract_tool_calls(session_path: Path):
    """Extract tool call sequences from a session file."""
    calls = []
    try:
        with open(session_path) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except:
                    continue
                # Extract tool calls from different formats
                tool = entry.get("tool") or entry.get("expected_tool") or ""
                params = entry.get("params") or entry.get("query") or entry.get("approach_used") or ""
                outcome = entry.get("outcome") or ""
                reward = entry.get("reward", 0)
                agent = entry.get("agent") or ""
                if tool and params:
                    calls.append({
                        "tool": tool,
                        "query": str(params)[:500],
                        "outcome": outcome,
                        "reward": reward,
                        "agent": agent,
                    })
    except:
        pass
    return calls

def mine_positive_pairs(calls):
    """Same-session consecutive calls = positive pairs (similar intent)."""
    pairs = []
    for i in range(len(calls) - 1):
        if calls[i]["tool"] and calls[i+1]["tool"]:
            pairs.append({
                "type": "positive",
                "query_a": calls[i]["query"],
                "tool_a": calls[i]["tool"],
                "query_b": calls[i+1]["query"],
                "tool_b": calls[i+1]["tool"],
            })
    return pairs

def mine_corrections(calls):
    """Failure → success sequences within 3 calls = correction pairs."""
    pairs = []
    for i in range(len(calls) - 1):
        if (calls[i].get("outcome") == "failure" or calls[i].get("reward", 0) <= -0.3) and \
           (calls[i+1].get("outcome") == "success" or calls[i+1].get("reward", 0) >= 0.5):
            pairs.append({
                "type": "correction",
                "query": calls[i]["query"],
                "wrong_tool": calls[i]["tool"],
                "correct_tool": calls[i+1]["tool"],
            })
    return pairs

def generate_hard_negatives(all_calls, n_per_positive=2):
    """For each unique tool, find queries for DIFFERENT tools as negatives."""
    tool_queries = {}
    for c in all_calls:
        t = c["tool"]
        q = c["query"]
        if t not in tool_queries:
            tool_queries[t] = []
        tool_queries[t].append(q)

    tools = list(tool_queries.keys())
    negatives = []
    for t in tools:
        other_tools = [ot for ot in tools if ot != t]
        if not other_tools:
            continue
        queries_for_t = tool_queries[t]
        for q in queries_for_t[:n_per_positive]:
            wrong_t = random.choice(other_tools)
            wrong_q = random.choice(tool_queries[wrong_t]) if tool_queries[wrong_t] else ""
            negatives.append({
                "type": "hard_negative",
                "query": q,
                "correct_tool": t,
                "wrong_tool": wrong_t,
                "distractor_query": wrong_q,
            })
    return negatives

def main():
    print("=" * 60)
    print("TRAINING DATA PREP — Mining sessions for pairs")
    print("=" * 60)

    all_calls = []
    all_positives = []
    all_corrections = []
    agent_counts = Counter()
    tool_counts = Counter()
    session_count = 0

    session_files = sorted(SESSIONS.rglob("*.jsonl"))
    print(f"Found {len(session_files)} session files")

    for sf in session_files:
        calls = extract_tool_calls(sf)
        if len(calls) >= MIN_SEQ_LENGTH:
            all_calls.extend(calls)
            all_positives.extend(mine_positive_pairs(calls))
            all_corrections.extend(mine_corrections(calls))
            session_count += 1
            for c in calls:
                if c["agent"]:
                    agent_counts[c["agent"]] += 1
                if c["tool"]:
                    tool_counts[c["tool"]] += 1

    print(f"Processed {session_count} sessions")
    print(f"Extracted {len(all_calls)} tool calls")
    print(f"Found {len(all_positives)} positive pairs")
    print(f"Found {len(all_corrections)} corrections")

    # Generate hard negatives
    hard_negatives = generate_hard_negatives(all_calls, n_per_positive=2)
    print(f"Generated {len(hard_negatives)} hard negatives")

    # Also include existing rosetta pairs
    existing_pairs = []
    rosetta_file = TRAINING / "mojo_rosetta.jsonl"
    if rosetta_file.exists():
        with open(rosetta_file) as f:
            for line in f:
                try:
                    existing_pairs.append(json.loads(line))
                except:
                    pass
    print(f"Loaded {len(existing_pairs)} existing Rosetta pairs")

    # Write training pairs
    pairs = []
    for p in all_corrections:
        pairs.append({
            "type": "correction",
            "query": p["query"],
            "correct_tool": p["correct_tool"],
            "wrong_tool": p.get("wrong_tool", ""),
        })
    for p in all_positives[:2000]:  # Cap positives
        pairs.append({
            "type": "positive",
            "query_a": p["query_a"],
            "query_b": p["query_b"],
            "tool_a": p["tool_a"],
            "tool_b": p["tool_b"],
        })
    for p in hard_negatives[:2000]:  # Cap hard negatives
        pairs.append({
            "type": "hard_negative",
            "query": p["query"],
            "correct_tool": p["correct_tool"],
            "wrong_tool": p["wrong_tool"],
        })
    for p in existing_pairs:
        pairs.append({
            "type": "rosetta",
            "query": p.get("query", ""),
            "expected_tool": p.get("expected_tool", ""),
        })

    random.shuffle(pairs)
    TRAINING.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w") as f:
        for p in pairs:
            f.write(json.dumps(p) + "\n")

    # Write meta
    meta = {
        "total_pairs": len(pairs),
        "corrections": len(all_corrections),
        "positives": min(len(all_positives), 2000),
        "hard_negatives": min(len(hard_negatives), 2000),
        "rosetta_existing": len(existing_pairs),
        "agents_found": dict(agent_counts.most_common(20)),
        "tools_found": len(tool_counts),
        "sessions_processed": session_count,
        "total_tool_calls": len(all_calls),
        "generated_at": datetime.now().isoformat(),
    }
    with open(META, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\nWritten {len(pairs)} total pairs to {OUTPUT}")
    print(f"Meta saved to {META}")
    print("Ready for training.")

if __name__ == "__main__":
    main()
