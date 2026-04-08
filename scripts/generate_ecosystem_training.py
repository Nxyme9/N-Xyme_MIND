#!/usr/bin/env python3
"""
Generate comprehensive training data for ALL ecosystem tools.
Scans all MCP servers and generates diverse training examples.
"""

import json
import re
import os
from pathlib import Path
from typing import List, Dict, Any

# Output path
OUTPUT_PATH = (
    "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/datasets/rosetta_ecosystem_full.jsonl"
)

# Template prompts for generating varied natural language inputs
PROMPT_TEMPLATES = {
    "search": [
        "Find information about {topic}",
        "Search for {topic}",
        "Look up {topic}",
        "I need to find {topic}",
        "Can you search for {topic}?",
        "Find {topic} for me",
        "Search the system for {topic}",
    ],
    "create": [
        "Create a new {item}",
        "Make a {item}",
        "Add a new {item}",
        "I want to create {item}",
        "Can you create {item}?",
    ],
    "update": [
        "Update {item} with {value}",
        "Change {item} to {value}",
        "Modify {item}",
        "Edit {item}",
        "I need to update {item}",
    ],
    "delete": [
        "Delete {item}",
        "Remove {item}",
        "I want to delete {item}",
        "Can you remove {item}?",
        "Clear {item}",
    ],
    "list": [
        "List all {items}",
        "Show me the {items}",
        "Get all {items}",
        "What {items} are available?",
        "I need to see {items}",
    ],
    "get": [
        "Get the {item}",
        "Show me the {item}",
        "I need the {item}",
        "Retrieve {item}",
        "Fetch the {item}",
    ],
    "execute": [
        "Run {action}",
        "Execute {action}",
        "Start {action}",
        "Trigger {action}",
        "Can you run {action}?",
    ],
}


def extract_tools_from_file(file_path: Path) -> List[Dict[str, Any]]:
    """Extract MCP tool definitions from a Python file."""
    tools = []

    if not file_path.exists():
        return tools

    content = file_path.read_text()

    # Find all @mcp.tool() decorated functions
    # Pattern: @mcp.tool(...)\ndef function_name(...)
    # The decorator can span multiple lines, and def is on the next line
    tool_pattern = r"@mcp\.tool\([^)]*\)\s*\n\s*def\s+(\w+)\s*\(([^)]*)\):"
    docstring_pattern = r'"""([^"]+)"""'

    matches = list(re.finditer(tool_pattern, content, re.MULTILINE))

    for match in matches:
        func_name = match.group(1)
        params_str = match.group(2)

        # Extract docstring (after the function definition)
        func_start = match.end()
        docstring_match = re.search(
            r'"""([^"]+)"""', content[func_start : func_start + 500]
        )
        description = (
            docstring_match.group(1).strip()
            if docstring_match
            else f"Tool: {func_name}"
        )

        # Parse parameters
        params = []
        for param in params_str.split(","):
            param = param.strip()
            if "=" in param:
                param_name, default = param.split("=", 1)
                param_name = param_name.strip()
                # Extract type hint if present
                if ":" in param_name:
                    param_name, type_hint = param_name.split(":", 1)
                    param_name = param_name.strip()
                params.append({"name": param_name, "default": default.strip()})
            elif param:
                if ":" in param:
                    param_name, type_hint = param.split(":", 1)
                    param_name = param_name.strip()
                else:
                    param_name = param
                if param_name:
                    params.append({"name": param_name, "default": None})

        tools.append(
            {
                "name": func_name,
                "description": description,
                "params": params,
                "file": str(file_path),
            }
        )

    return tools


def find_all_mcp_servers() -> List[Path]:
    """Find all MCP server files in the ecosystem."""
    mcp_files = []

    root = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")

    # Search patterns - exclude venv, .venv, node_modules
    patterns = [
        "packages/**/mcp_server.py",
        "athena/**/mcp_server.py",
    ]

    for pattern in patterns:
        for f in root.glob(pattern):
            # Skip venv directories
            if "venv" in f.parts or ".venv" in f.parts or "node_modules" in f.parts:
                continue
            mcp_files.append(f)

    return list(set(mcp_files))


def generate_tool_call(tool: Dict[str, Any], params: Dict[str, Any]) -> str:
    """Generate a tool call string in Rosetta format."""
    args_parts = []
    for key, value in params.items():
        if isinstance(value, str):
            args_parts.append(f'--{key} "{value}"')
        elif isinstance(value, bool):
            if value:
                args_parts.append(f"--{key}")
        elif value is not None:
            args_parts.append(f"--{key} {value}")

    args_str = ", ".join(args_parts) if args_parts else ""

    if args_str:
        return f'[TOOL_CALL]{{tool => "{tool["name"]}", args => {{ {args_str} }}}}[/TOOL_CALL]'
    else:
        return f'[TOOL_CALL]{{tool => "{tool["name"]}", args => {{ }}}}[/TOOL_CALL]'


def generate_training_examples(tools: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Generate training examples from extracted tools."""
    examples = []

    for tool in tools:
        tool_name = tool["name"]

        # Determine action type from tool name
        action_type = "get"
        for key in PROMPT_TEMPLATES.keys():
            if key in tool_name.lower():
                action_type = key
                break

        # Get templates for this action
        templates = PROMPT_TEMPLATES.get(action_type, PROMPT_TEMPLATES["get"])

        # Generate diverse prompts based on tool description and params
        # Try different parameter combinations
        param_combinations = []

        # Single param variations
        for param in tool["params"]:
            if param["default"] is None:  # Required param
                param_combinations.append({param["name"]: f"test_{param['name']}"})

        # Two param combinations
        if len(tool["params"]) >= 2:
            for i in range(min(2, len(tool["params"]))):
                for j in range(i + 1, min(3, len(tool["params"]))):
                    combo = {}
                    if tool["params"][i]["default"] is None:
                        combo[tool["params"][i]["name"]] = f"test_value_{i}"
                    if tool["params"][j]["default"] is None:
                        combo[tool["params"][j]["name"]] = f"test_value_{j}"
                    if combo:
                        param_combinations.append(combo)

        # No params case
        if not param_combinations:
            param_combinations.append({})

        # Generate examples
        for template in templates[:3]:  # Limit templates per tool
            for params in param_combinations[:2]:  # Limit param combos
                # Create prompt from template
                prompt = template

                # Replace placeholders
                if "{topic}" in prompt:
                    prompt = prompt.replace("{topic}", tool_name.replace("_", " "))
                elif "{item}" in prompt:
                    prompt = prompt.replace("{item}", tool_name.replace("_", " "))
                elif "{items}" in prompt:
                    prompt = prompt.replace("{items}", tool_name.replace("_", " "))
                elif "{action}" in prompt:
                    prompt = prompt.replace("{action}", tool_name.replace("_", " "))

                # Add param context to prompt if we have params
                if params:
                    param_str = ", ".join([f"{k}={v}" for k, v in params.items()])
                    prompt = f"{prompt} with {param_str}"

                # Generate tool call
                tool_call = generate_tool_call(tool, params)

                examples.append({"input": prompt, "output": tool_call})

    return examples


def main():
    print("=" * 60)
    print("Generating Ecosystem Training Data")
    print("=" * 60)

    # Find all MCP servers
    mcp_files = find_all_mcp_servers()
    print(f"Found {len(mcp_files)} MCP server files")

    # Extract tools from each file
    all_tools = []
    for mcp_file in mcp_files:
        tools = extract_tools_from_file(mcp_file)
        print(f"  {mcp_file.name}: {len(tools)} tools")
        all_tools.extend(tools)

    print(f"\nTotal tools extracted: {len(all_tools)}")

    # Remove duplicates by name
    unique_tools = {}
    for tool in all_tools:
        if tool["name"] not in unique_tools:
            unique_tools[tool["name"]] = tool

    print(f"Unique tools: {len(unique_tools)}")

    # Generate training examples
    print("\nGenerating training examples...")
    examples = generate_training_examples(list(unique_tools.values()))
    print(f"Generated {len(examples)} training examples")

    # Save to JSONL
    output_path = Path(OUTPUT_PATH)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        for example in examples:
            f.write(json.dumps(example) + "\n")

    print(f"\nSaved to: {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024:.1f} KB")

    # Show sample examples
    print("\n" + "=" * 60)
    print("Sample examples:")
    print("=" * 60)
    for i, example in enumerate(examples[:5]):
        print(f"\n[{i + 1}] Input: {example['input']}")
        print(f"    Output: {example['output']}")


if __name__ == "__main__":
    main()
