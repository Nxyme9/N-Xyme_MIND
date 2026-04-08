#!/usr/bin/env python3
"""Rosetta Stone Direct Integration - llama-cpp-python (no Ollama, no HTTP overhead)

This module provides direct LLM inference using llama-cpp-python:
- Zero network overhead (no HTTP, no subprocess)
- Full GPU control with n_gpu_layers
- Direct GGUF model loading
- Rosetta-style tool call parsing

Usage:
    python -m packages.local_llm.rosetta_executor_direct "search memory for security"
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# GGUF model paths - update these to your downloaded models
# Rosetta Stone (0.5B) - tool call translator - tiny, fast
ROSETTA_MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "qwen2.5-0.5b-instruct-q4_k_m.gguf"
# Main LLM (7B) - actual reasoning/code generation
MAIN_MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "qwen2.5-coder-7b-q4_k_m.gguf"

# Default to 7B for tool calling (238ms - faster than 0.5B's 1083ms)
# 7B is proven faster for tool call translation in benchmarks
DEFAULT_MODEL_PATH = MAIN_MODEL_PATH

# GPU layers: 0.5B needs ~19 layers, 7B needs 35
DEFAULT_N_GPU_LAYERS = 35  # Use full for 7B

# Context size
DEFAULT_N_CTX = 4096

# ============================================================================
# LLAMA-CPP-PYTHON DIRECT INTEGRATION
# ============================================================================

class DirectLlamaClient:
    """Direct llama-cpp-python client - no HTTP, no Ollama, no network overhead."""
    
    def __init__(
        self,
        model_path: str = None,
        n_gpu_layers: int = DEFAULT_N_GPU_LAYERS,
        n_ctx: int = DEFAULT_N_CTX,
        n_threads: int = 8,
        verbose: bool = False
    ):
        """Initialize direct llama-cpp-python client.
        
        Args:
            model_path: Path to GGUF model file
            n_gpu_layers: Number of layers to offload to GPU (-1 = all)
            n_ctx: Context window size
            n_threads: CPU threads for inference
            verbose: Enable verbose output
        """
        from llama_cpp import Llama
        
        self.model_path = model_path or str(DEFAULT_MODEL_PATH)
        self.n_gpu_layers = n_gpu_layers
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        
        print(f"[DirectLlama] Loading model: {self.model_path}")
        print(f"[DirectLlama] GPU layers: {n_gpu_layers}, Context: {n_ctx}, Threads: {n_threads}")
        
        self.llm = Llama(
            model_path=self.model_path,
            n_gpu_layers=n_gpu_layers,
            n_ctx=n_ctx,
            n_threads=n_threads,
            verbose=verbose
        )
        
        print(f"[DirectLlama] Model loaded successfully!")
    
    def chat(self, messages: list, temperature: float = 0.3, max_tokens: int = 512) -> Dict[str, Any]:
        """Send chat completion request directly.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            
        Returns:
            Response dict with 'content' and metadata
        """
        response = self.llm.create_chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stop=["[/TOOL_CALL]", "[TOOL_CALL]"]
        )
        
        return {
            "content": response["choices"][0]["message"]["content"],
            "model": response.get("model", "unknown"),
            "usage": response.get("usage", {}),
        }
    
    def generate(self, prompt: str, temperature: float = 0.3, max_tokens: int = 512) -> str:
        """Generate text from prompt (non-chat).
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            
        Returns:
            Generated text
        """
        response = self.llm.create_completion(
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response["choices"][0]["text"]


# ============================================================================
# ROSETTA TRANSLATION (using Direct Client)
# ============================================================================

# Global client instance (lazy loaded)
_llama_client: Optional[DirectLlamaClient] = None

def get_client() -> DirectLlamaClient:
    """Get or create the global llama-cpp-python client."""
    global _llama_client
    if _llama_client is None:
        _llama_client = DirectLlamaClient()
    return _llama_client


def call_llama_direct(prompt: str, system_prompt: str = None) -> str:
    """Call the LLM directly via llama-cpp-python (no Ollama, no HTTP).
    
    Args:
        prompt: User prompt
        system_prompt: Optional system prompt
        
    Returns:
        Model response text
    """
    client = get_client()
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    response = client.chat(messages, temperature=0.3, max_tokens=512)
    return response["content"]


# ============================================================================
# TOOL CALL PARSING (same as original Rosetta pattern)
# ============================================================================

def parse_tool_call(response: str) -> Optional[Dict[str, Any]]:
    """Parse tool call format from LLM response.
    
    Supports two formats:
    1. Rosetta-style: [TOOL_CALL]{tool => "name", args => {...}}[/TOOL_CALL]
    2. Qwen2.5 native: <tool_call>{"name": "...", "arguments": {...}}</tool_call>
    
    Args:
        response: Model output containing tool call
        
    Returns:
        Dict with 'tool' and 'args', or None if no tool call found
    """
    # Pattern 1: Rosetta-style [TOOL_CALL]{...tool => "name"...args => {...}...}[/TOOL_CALL]
    pattern1 = r'\[TOOL_CALL\]\s*\{.*?tool\s*=>\s*"([^"]+)".*?args\s*=>\s*\{([^}]*)\}.*?\}\s*\[/TOOL_CALL\]'
    match = re.search(pattern1, response, re.DOTALL)
    
    if match:
        tool_name = match.group(1)
        args_str = match.group(2)
        
        args = {}
        arg_pattern = r'--(\w+)\s+"([^"]*)"'
        for arg_match in re.finditer(arg_pattern, args_str):
            key = arg_match.group(1)
            value = arg_match.group(2)
            args[key] = value
        
        return {"tool": tool_name, "args": args}
    
    # Pattern 2: Qwen2.5 native format: <tool_call>{"name": "...", "arguments": {...}}</tool_call>
    pattern2 = r'<tool_call>\s*\{[^}]*"name"\s*:\s*"([^"]+)"[^}]*"arguments"\s*:\s*(\{[^}]*\})[^}]*\}\s*</tool_call>'
    match2 = re.search(pattern2, response, re.DOTALL)
    
    if match2:
        tool_name = match2.group(1)
        args_str = match2.group(2)
        
        # Try to parse as JSON
        try:
            args = json.loads(args_str)
            return {"tool": tool_name, "args": args}
        except json.JSONDecodeError as e:
            print(f"[Direct] JSON parse error: {e}, args_str: {args_str}")
            pass
    
    # Pattern 3: Simple JSON {"tool": "...", "args": {...}}
    pattern3 = r'\{[^{]*"tool"\s*:\s*"([^"]+)"[^}]*"args"\s*:\s*\{([^}]*)\}'
    match3 = re.search(pattern3, response, re.DOTALL)
    
    if match3:
        tool_name = match3.group(1)
        args_str = match3.group(2)
        
        # Try to parse as JSON
        try:
            args = json.loads("{" + args_str + "}")
            return {"tool": tool_name, "args": args}
        except:
            pass
    
    return None


def translate_request(request: str, debug: bool = False) -> Optional[Dict[str, Any]]:
    """Translate user request to tool call using direct LLM.
    
    Args:
        request: Natural language request
        debug: Print raw model output
        
    Returns:
        Parsed tool call dict, or None if no valid tool call
    """
    # Optimized system prompt with few-shot examples for tool calling
    system_prompt = """You are a Rosetta Stone tool call translator. Your ONLY job is to convert user requests into MCP tool calls.

TOOL DEFINITIONS:
- memory_search: search the memory system (args: query, limit?)
- read_file: read a file (args: file_path)
- write_file: write a file (args: file_path, content?)
- list_directory: list files in directory (args: path?)
- git_status: check git status (args: none)
- git_log: get git history (args: limit?)
- git_diff: get git diff (args: file?)
- github_list_issues: list GitHub issues (args: repo?)
- fetch_url: fetch a URL (args: url)
- context7_query_docs: query documentation (args: library_id, query)

RULES:
1. Output ONLY valid JSON - nothing else
2. Format: {"tool": "tool_name", "args": {"param": "value"}}
3. If unclear, use memory_search with the key phrase as query

EXACT EXAMPLES - COPY THESE EXACTLY:
Input: "search memory for security"
Output: {"tool": "memory_search", "args": {"query": "security"}}

Input: "show me the README"
Output: {"tool": "read_file", "args": {"file_path": "README.md"}}

Input: "what files changed"
Output: {"tool": "git_status", "args": {}}

Input: "look up authentication in memory"
Output: {"tool": "memory_search", "args": {"query": "authentication"}}

Input: "show me config.py"
Output: {"tool": "read_file", "args": {"file_path": "config.py"}}

Now convert this request:"""

    response = call_llama_direct(request, system_prompt)
    
    if debug:
        print(f"[Direct] Raw response: {repr(response)}")
    
    # Try to parse as simple JSON first
    try:
        result = json.loads(response.strip())
        if result.get("tool") and result["tool"] != "none":
            return result
    except json.JSONDecodeError:
        pass
    
    return parse_tool_call(response)


# ============================================================================
# MCP TOOL EXECUTION (Simulated - same as original)
# ============================================================================

class MCPToolExecutor:
    """Execute MCP tools. Placeholder - real implementation would use MCP."""
    
    TOOL_HANDLERS = {
        "memory_search": lambda args: {"results": [f"Found: {args.get('query', '')}"], "count": 1},
        "athena_smart_search": lambda args: {"results": [f"Athena: {args.get('query', '')}"], "count": 1},
        "read_file": lambda args: {"content": f"# Content of {args.get('path', 'unknown')}\n\nTest content."},
        "write_file": lambda args: {"success": True, "path": args.get("path", "")},
        "list_directory": lambda args: {"files": ["file1.py", "file2.py", "dir/"], "path": args.get("path", ".")},
        "git_status": lambda args: {"status": "clean", "branch": "main", "modified": []},
        "git_log": lambda args: {"commits": ["abc123 - initial commit", "def456 - added feature"]},
        "git_diff": lambda args: {"diff": "--- a/file.py\n+++ b/file.py\n@@ -1,1 +1,2"},
        "github_list_issues": lambda args: {"issues": [{"number": 1, "title": "Bug fix"}, {"number": 2, "title": "Feature"}]},
        "fetch_url": lambda args: {"content": f"Content from {args.get('url', '')}", "status": 200},
        "context7_query_docs": lambda args: {"docs": f"Documentation for {args.get('library_id', '')}"},
        "sequential_thinking": lambda args: {"thought": args.get("thought", ""), "next": True},
        "get_active_context": lambda args: {"context": "Working on Rosetta Stone integration"},
        "get_user_context": lambda args: {"user": "developer", "preferences": {"model": "qwen"}},
        "route_task": lambda args: {"agent": "hephaestus", "level": 3},
        "get_health": lambda args: {"status": "healthy", "level": args.get("level", "l0")},
        "run_typecheck": lambda args: {"passed": True, "errors": []},
        "run_lint": lambda args: {"passed": True, "warnings": []},
        "browser_navigate": lambda args: {"url": args.get("url", ""), "success": True},
    }
    
    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute an MCP tool."""
        if tool_name in self.TOOL_HANDLERS:
            return self.TOOL_HANDLERS[tool_name](arguments)
        return {"tool": tool_name, "args": arguments, "note": "Simulated execution"}


# ============================================================================
# FULL PIPELINE
# ============================================================================

async def execute_request(request: str) -> Dict[str, Any]:
    """Execute full pipeline: translate -> execute -> return."""
    
    print(f"[Direct] Translating: '{request}'")
    tool_call = translate_request(request)
    
    if not tool_call:
        return {"error": "No tool call detected", "request": request}
    
    print(f"[Direct] Tool: {tool_call['tool']}")
    print(f"[Direct] Args: {tool_call['args']}")
    
    executor = MCPToolExecutor()
    result = await executor.execute(tool_call["tool"], tool_call["args"])
    
    return {
        "tool": tool_call["tool"],
        "args": tool_call["args"],
        "result": result,
    }


def run_sync(request: str) -> Dict[str, Any]:
    """Synchronous wrapper."""
    import asyncio
    return asyncio.run(execute_request(request))


def test_direct_pipeline():
    """Test the direct pipeline."""
    test_cases = [
        "search memory for security",
        "show me README.md",
        "check git status",
    ]
    
    print("=" * 50)
    print("Direct llama-cpp-python Pipeline Test")
    print("=" * 50)
    
    for request in test_cases:
        print(f"\n>>> {request}")
        result = run_sync(request)
        print(f"    Tool: {result.get('tool', 'ERROR')}")
        print(f"    Result: {result.get('result', result.get('error'))}")


def main():
    if len(sys.argv) < 2:
        test_direct_pipeline()
    else:
        request = " ".join(sys.argv[1:])
        result = run_sync(request)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()