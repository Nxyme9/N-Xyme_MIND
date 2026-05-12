#!/usr/bin/env python3
"""
Rosetta Retrain Script - Add new tools and retrain in one command.

Usage:
    python retrain_rosetta.py --tool "new_tool_name" --args "arg1,arg2"
    
    # Add multiple at once:
    python retrain_rosetta.py --from-file new_tools.jsonl
    
Example:
    python retrain_rosetta.py --tool "nx_brain_smart_search" --args "query,limit"
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

TRAIN_DATA = Path(__file__).parent / "data" / "rosetta_v8_complete_train.jsonl"
MODEL_OUTPUT = Path(__file__).parent / "models" / "rosetta-v14-f16.gguf"


def add_tool(tool_name: str, args: list):
    """Add a single tool to training data."""
    args_str = ", ".join([f'--{a} "value"' for a in args])
    output = f"[TOOL_CALL]{{tool => \"{tool_name}\", args => {{ {args_str} }}[/TOOL_CALL]"
    
    entry = {"text": f"use {tool_name}", "output": output}
    
    with open(TRAIN_DATA, "a") as f:
        f.write(json.dumps(entry) + "\n")
    
    print(f"Added: {tool_name}")


def add_from_file(filepath: str):
    """Add multiple tools from JSONL file."""
    with open(filepath, "r") as f:
        for line in f:
            with open(TRAIN_DATA, "a") as out:
                out.write(line.strip() + "\n")
    print(f"Added tools from: {filepath}")


def retrain():
    """Run the training pipeline."""
    print(f"Training with data: {TRAIN_DATA}")
    print(f"Output: {MODEL_OUTPUT}")
    
    # Run training
    cmd = [
        "python", "packages/training/train_rosetta_unified.py",
        "--data", str(TRAIN_DATA),
        "--output", str(MODEL_OUTPUT)
    ]
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    
    if result.returncode == 0:
        print(f"✅ Training complete: {MODEL_OUTPUT}")
        print("Next: Update oh-my-opencode.json with rosetta-v14-f16")
    else:
        print(f"❌ Training failed")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Retrain Rosetta with new tools")
    parser.add_argument("--tool", type=str, help="Tool name to add")
    parser.add_argument("--args", type=str, help="Comma-separated args: arg1,arg2")
    parser.add_argument("--from-file", type=str, help="Add tools from JSONL file")
    parser.add_argument("--retrain", action="store_true", help="Run training after adding tools")
    
    args = parser.parse_args()
    
    if args.tool and args.args:
        add_tool(args.tool, args.args.split(","))
    elif args.from_file:
        add_from_file(args.from_file)
    
    if args.retrain:
        retrain()


if __name__ == "__main__":
    main()