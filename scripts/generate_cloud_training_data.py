#!/usr/bin/env python3
"""Cloud Model Data Generator - Generate training data using cloud models.

This script uses OpenRouter's free cloud models to generate tool calling examples.
It reads prompts from training_prompts.json and calls the cloud model for each,
collecting valid tool calls as training data.

Usage:
    python scripts/generate_cloud_training_data.py [--model MODEL] [--max-requests N]
"""

import json
import os
import sys
import argparse
import time
import random
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import tool loader
from packages.local_llm.mcp_tool_loader import MCPToolLoader

# Try to import openai - if not available, use requests
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    import requests


class CloudModelCaller:
    """Call cloud models to generate tool calling training data."""
    
    # System prompt for tool calling
    SYSTEM_PROMPT = """You are a tool calling assistant. Your job is to:
1. Analyze user requests
2. If the request requires a tool (like reading a file, searching memory, etc.), call the appropriate tool
3. If no tool is needed, respond with plain text

You have access to these tools:
{tools_description}

Guidelines:
- Only call a tool when it genuinely helps answer the user
- Choose the most appropriate tool for the request
- If the user is just chatting or asking a general question, don't call any tool
- Be specific with tool arguments - use realistic values

Respond ONLY with tool calls when needed, otherwise respond with text."""
    
    def __init__(self, api_key: str, base_url: str = "https://opencode.ai/zen/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.tools = self._load_tools()
        
    def _load_tools(self) -> List[Dict]:
        """Load tool schemas from mcp_tool_loader."""
        loader = MCPToolLoader()
        return loader.get_tools_openai_format()
    
    def _get_tools_description(self) -> str:
        """Format tools for the system prompt."""
        desc = []
        for tool in self.tools:
            func = tool.get("function", {})
            name = func.get("name", "unknown")
            descr = func.get("description", "")
            params = func.get("parameters", {})
            props = params.get("properties", {})
            required = params.get("required", [])
            
            param_str = ", ".join(required) if required else "none"
            desc.append(f"- {name}: {descr} (required: {param_str})")
        
        return "\n".join(desc)
    
    def _call_requests(self, model: str, messages: List[Dict], temperature: float = 0.1, is_free: bool = False) -> Dict:
        """Call using requests (OpenCode Zen format)."""
        headers = {
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/nxyme/N-Xyme_MIND",
            "X-Title": "Rosetta Stone Training Data Generator",
        }
        
        # Add auth if provided (for non-free models)
        if self.api_key and self.api_key != "dummy":
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        # OpenCode Zen format: strip "zenmux/" prefix if present
        model_id = model.replace("zenmux/", "")
        
        data = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1000,
        }
        
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=data,
            timeout=60,
        )
        
        if response.status_code != 200:
            raise Exception(f"API error: {response.status_code} - {response.text}")
        
        result = response.json()
        
        return {
            "content": result["choices"][0]["message"].get("content"),
            "tool_calls": result["choices"][0]["message"].get("tool_calls", []),
        }
    
    def _parse_custom_tool_calls(self, content: str) -> List[Dict]:
        """Parse custom [TOOL_CALL] format from model response."""
        import re
        tool_calls = []
        
        # Match [TOOL_CALL] blocks
        pattern = r'\[TOOL_CALL\]\s*\{tool\s*=>\s*"([^"]+)",\s*args\s*=>\s*\{([^}]*)\}\}'
        matches = re.findall(pattern, content)
        
        for tool_name, args_str in matches:
            # Parse arguments
            args = {}
            arg_pattern = r'--(\w+)\s+"([^"]*)"'
            for key, value in re.findall(arg_pattern, args_str):
                args[key] = value
            
            tool_calls.append({
                "id": f"call_{len(tool_calls)}",
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps(args) if args else "{}"
                }
            })
        
        return tool_calls
    
    def call(self, prompt: str, model: str = "zenmux/xiaomi/mimo-v2-flash-free", temperature: float = 0.1) -> Dict:
        """Call cloud model with a prompt and get tool calls."""
        
        is_free = ":free" in model or "free" in model
        system = self.SYSTEM_PROMPT.format(tools_description=self._get_tools_description())
        
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
        
        try:
            result = self._call_requests(model, messages, temperature, is_free=is_free)
            
            # Check for custom tool call format in content
            if result.get("content") and not result.get("tool_calls"):
                custom_calls = self._parse_custom_tool_calls(result["content"])
                if custom_calls:
                    result["tool_calls"] = custom_calls
            
            return result
        except Exception as e:
            return {"error": str(e), "tool_calls": [], "content": None}


def main():
    parser = argparse.ArgumentParser(description="Generate training data using cloud models")
    parser.add_argument("--model", type=str, 
                        default="minimax-m2.5-free", 
                        help="Cloud model to use (OpenCode Zen)")
    parser.add_argument("--max-prompts", type=int, default=100, help="Max prompts to process (0 = all)")
    parser.add_argument("--output", type=str, default="datasets/cloud_generated_tool_calls.jsonl", help="Output file")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between requests (seconds)")
    parser.add_argument("--api-key", type=str, help="API key (or use OPENROUTER_API_KEY env)")
    parser.add_argument("--rpm", type=int, default=8, help="Requests per minute limit")
    args = parser.parse_args()
    
    # Get API key from env or argument (free models don't need key)
    api_key = args.api_key or os.environ.get("OPENCODE_ZEN_API_KEY", os.environ.get("OPENROUTER_API_KEY", ""))
    
    # Free models don't require API key (IP-based)
    is_free_model = "free" in args.model
    
    if not api_key and not is_free_model:
        print("ERROR: No API key found. Set OPENCODE_ZEN_API_KEY env var or use --api-key")
        sys.exit(1)
    
    if is_free_model:
        print(f"Using OpenCode Zen free model (IP-based): {args.model}")
    
    # Load prompts
    prompts_file = PROJECT_ROOT / "datasets/training_prompts.json"
    if not prompts_file.exists():
        print(f"ERROR: {prompts_file} not found. Run generate_training_prompts.py first.")
        sys.exit(1)
    
    with open(prompts_file) as f:
        prompts_data = json.load(f)
    
    # Flatten prompts with tool info
    all_prompts = []
    for tool_name, data in prompts_data.items():
        for prompt in data["prompts"]:
            all_prompts.append({
                "tool_name": tool_name,
                "description": data["description"],
                "prompt": prompt,
            })
    
    if args.max_prompts > 0 and args.max_prompts < len(all_prompts):
        all_prompts = all_prompts[:args.max_prompts]
    
    print(f"Loaded {len(all_prompts)} prompts")
    print(f"Using model: {args.model}")
    print(f"Output: {args.output}")
    print()
    
    # Initialize caller with OpenCode Zen
    caller = CloudModelCaller(api_key=api_key if api_key else "dummy", base_url="https://opencode.ai/zen/v1")
    
    # Rate limiting using token bucket
    rate_limit = args.rpm  # requests per minute
    tokens = float(rate_limit)
    last_refill = time.time()
    
    def get_token():
        nonlocal tokens, last_refill
        now = time.time()
        elapsed = now - last_refill
        tokens = min(rate_limit, tokens + elapsed * (rate_limit / 60.0))
        last_refill = now
        if tokens >= 1:
            tokens -= 1
            return True
        return False
    
    # Process prompts
    output_path = PROJECT_ROOT / args.output
    valid_count = 0
    error_count = 0
    rate_limited_count = 0
    
    with open(output_path, "w") as outfile:
        for i, item in enumerate(all_prompts):
            if i % 10 == 0:
                print(f"Processing {i+1}/{len(all_prompts)}...")
            
            # Wait for rate limit token
            while not get_token():
                wait_time = (1 - tokens) * (60.0 / rate_limit)
                print(f"  Rate limited, waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
            
            result = caller.call(item["prompt"], model=args.model)
            
            if "error" in result:
                error_count += 1
                err_msg = result.get("error", "")
                if "429" in err_msg:
                    rate_limited_count += 1
                    print(f"  Rate limited: {err_msg[:60]}...")
                else:
                    print(f"  Error: {err_msg[:80]}")
                continue
            
            # Debug: show what model returned
            content = result.get("content", "")
            tool_calls = result.get("tool_calls", [])
            
            if content and not tool_calls:
                print(f"  Model responded with text (no tool call): {content[:80]}...")
            
            # Check if tool call was made
            if tool_calls:
                valid_count += 1
                
                # Save as training example
                example = {
                    "messages": [
                        {"role": "system", "content": caller.SYSTEM_PROMPT.format(tools_description=caller._get_tools_description())},
                        {"role": "user", "content": item["prompt"]},
                    ],
                    "tool_calls": result["tool_calls"],
                    "tool_name": item["tool_name"],  # Expected tool (for validation)
                    "valid": True,
                }
                
                outfile.write(json.dumps(example) + "\n")
            
            # Small delay between requests
            time.sleep(0.5)
    
    print(f"\n--- Results ---")
    print(f"Total prompts: {len(all_prompts)}")
    print(f"Valid tool calls: {valid_count}")
    print(f"Errors: {error_count} (rate limited: {rate_limited_count})")
    print(f"Output: {output_path}")
    
    # Calculate coverage
    tool_coverage = {}
    with open(output_path) as f:
        for line in f:
            data = json.loads(line)
            tool = data["tool_calls"][0]["function"]["name"]
            tool_coverage[tool] = tool_coverage.get(tool, 0) + 1
    
    print(f"\n--- Tool Coverage ---")
    for tool, count in sorted(tool_coverage.items(), key=lambda x: -x[1]):
        print(f"  {tool}: {count}")


if __name__ == "__main__":
    main()