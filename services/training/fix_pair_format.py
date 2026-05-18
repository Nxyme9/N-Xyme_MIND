#!/usr/bin/env python3
"""
fix_pair_format.py — Run BEFORE next full pipeline re-run.

Converts the existing examples.jsonl (which has empty corrected_approach fields)
into proper Rosetta training pairs with query → expected_tool.

Usage:
    python3 services/training/fix_pair_format.py
    # Output: data/training/rosetta_pairs.jsonl (ready for Q0.5 head training)
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
EXAMPLES = ROOT / "data" / "training" / "examples.jsonl"
OUTPUT = ROOT / "data" / "training" / "rosetta_pairs.jsonl"

def main():
    pairs = []
    failures = 0
    successes = 0

    if not EXAMPLES.exists():
        print(f"No input file at {EXAMPLES}")
        return

    with open(EXAMPLES) as f:
        for line in f:
            try:
                rec = json.loads(line)
            except:
                continue

            query = rec.get("approach_used", "") or rec.get("params", "") or ""
            tool = rec.get("tool", "") or ""
            outcome = rec.get("outcome", "")
            corrected = rec.get("corrected_approach", "") or ""
            reward = rec.get("reward", 0)

            if not query or not tool:
                continue

            if outcome == "success" and reward >= 0.5 and corrected:
                pairs.append({
                    "source": "pipeline",
                    "query": query,
                    "expected_tool": corrected,  # Use corrected version, not raw tool
                    "context": json.dumps(rec),
                })
                successes += 1

            elif outcome == "failure" and corrected:
                pairs.append({
                    "source": "correction",
                    "query": query,
                    "expected_tool": corrected,  # The RIGHT tool
                    "wrong_tool": tool,           # The WRONG tool that was used
                    "context": json.dumps(rec),
                })
                failures += 1

    with open(OUTPUT, "w") as f:
        for p in pairs:
            f.write(json.dumps(p) + "\n")

    print(f"Written {len(pairs)} training pairs:")
    print(f"  {successes} positive (correction matches tool)")
    print(f"  {failures} negative (failure → corrected tool)")
    print(f"  To: {OUTPUT}")

if __name__ == "__main__":
    main()
