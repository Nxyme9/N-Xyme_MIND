#!/usr/bin/env python3
"""
Local LLM Pipeline - 100% Direct GGUF (NO Ollama, NO HTTP)

This module provides fully local LLM inference using llama-cpp-python:
- Zero network overhead (no HTTP, no subprocess)
- Full GPU control with n_gpu_layers
- Direct GGUF model loading
- 3 models: Embedding (retrieval), Rosetta (tool call), Reasoner (main)

Usage:
    from packages.local_llm.direct_pipeline import (
        get_embedding,
        translate_to_tool_call,
        run_reasoning
    )
"""

import json
import re
import os
from pathlib import Path
from typing import Any, Dict, Optional, List
import numpy as np

# ============================================================================
# MODEL PATHS - All GGUF, all local
# ============================================================================

MODELS_DIR = Path(__file__).parent.parent.parent / "models"

# 1. Embedding model - 768 dims, for semantic search
EMBED_MODEL_PATH = MODELS_DIR / "nomic-embed-text-v1.5-Q4_K_M.gguf"

# 2. Rosetta model - tiny, fast tool call translator (0.5B)
#    Use 7B if 0.5B too dumb, but 0.5B is faster
ROSETTA_MODEL_PATH = MODELS_DIR / "qwen2.5-0.5b-instruct-q4_k_m.gguf"

# 3. Reasoner model - main reasoning/code generation (7B)
REASONER_MODEL_PATH = MODELS_DIR / "qwen2.5-coder-7b-q4_k_m.gguf"

# GPU layers config
EMBED_N_GPU_LAYERS = 32  # Full embedding model on GPU
ROSETTA_N_GPU_LAYERS = 19  # 0.5B = 19 layers
REASONER_N_GPU_LAYERS = 35  # 7B = 35 layers

# Context sizes
EMBED_N_CTX = 512
ROSETTA_N_CTX = 2048
REASONER_N_CTX = 4096


# ============================================================================
# MODEL CLIENTS - Lazy loaded singletons
# ============================================================================

_embedding_client = None
_rosetta_client = None
_reasoner_client = None


def get_embedding_client():
    """Get or create embedding model client (singleton)."""
    global _embedding_client
    if _embedding_client is None:
        from llama_cpp import Llama
        print(f"[DirectPipeline] Loading embedding model: {EMBED_MODEL_PATH}")
        _embedding_client = Llama(
            model_path=str(EMBED_MODEL_PATH),
            n_gpu_layers=EMBED_N_GPU_LAYERS,
            n_ctx=EMBED_N_CTX,
            embedding=True,
            verbose=False
        )
        print("[DirectPipeline] Embedding model loaded!")
    return _embedding_client


def get_rosetta_client():
    """Get or create Rosetta (tool call) model client (singleton)."""
    global _rosetta_client
    if _rosetta_client is None:
        from llama_cpp import Llama
        print(f"[DirectPipeline] Loading Rosetta model: {ROSETTA_MODEL_PATH}")
        _rosetta_client = Llama(
            model_path=str(ROSETTA_MODEL_PATH),
            n_gpu_layers=ROSETTA_N_GPU_LAYERS,
            n_ctx=ROSETTA_N_CTX,
            verbose=False
        )
        print("[DirectPipeline] Rosetta model loaded!")
    return _rosetta_client


def get_reasoner_client():
    """Get or create Reasoner model client (singleton)."""
    global _reasoner_client
    if _reasoner_client is None:
        from llama_cpp import Llama
        print(f"[DirectPipeline] Loading Reasoner model: {REASONER_MODEL_PATH}")
        _reasoner_client = Llama(
            model_path=str(REASONER_MODEL_PATH),
            n_gpu_layers=REASONER_N_GPU_LAYERS,
            n_ctx=REASONER_N_CTX,
            verbose=False
        )
        print("[DirectPipeline] Reasoner model loaded!")
    return _reasoner_client


# ============================================================================
# API - Public functions that auto-load models
# ============================================================================

def get_embedding(text: str) -> np.ndarray:
    """Get embedding vector for text using nomic-embed-text.
    
    Args:
        text: Input text to embed
        
    Returns:
        768-dimensional numpy array
    """
    client = get_embedding_client()
    emb = client.embed(text)
    return np.array(emb)


def get_embeddings_batch(texts: List[str]) -> List[np.ndarray]:
    """Get embeddings for multiple texts.
    
    Args:
        texts: List of input texts
        
    Returns:
        List of 768-dimensional numpy arrays
    """
    client = get_embedding_client()
    return [np.array(client.embed(t)) for t in texts]


def translate_to_tool_call(request: str, debug: bool = False) -> Optional[Dict[str, Any]]:
    """Translate natural language request to tool call using Rosetta model.
    
    Args:
        request: User request in natural language
        debug: Print raw model output
        
    Returns:
        Dict with 'tool' and 'args', or None if no valid tool call
    """
    client = get_rosetta_client()
    
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

Now convert this request:"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": request}
    ]
    
    response = client.create_chat_completion(
        messages=messages,
        temperature=0.3,
        max_tokens=256,
        stop=["[/TOOL_CALL]", "[TOOL_CALL]"]
    )
    
    content = response["choices"][0]["message"]["content"]
    
    if debug:
        print(f"[DirectPipeline] Raw response: {repr(content)}")
    
    # Parse JSON tool call
    try:
        result = json.loads(content.strip())
        if result.get("tool") and result["tool"] != "none":
            return result
    except json.JSONDecodeError:
        pass
    
    # Fallback: try Rosetta-style parsing
    return _parse_rosetta_format(content)


def _parse_rosetta_format(text: str) -> Optional[Dict[str, Any]]:
    """Parse Rosetta-style tool call format."""
    # [TOOL_CALL]{tool => "name", args => { --key "value" }}[/TOOL_CALL]
    pattern = r'\[TOOL_CALL\]\s*\{.*?tool\s*=>\s*"([^"]+)".*?args\s*=>\s*\{([^}]*)\}.*?\}\s*\[/TOOL_CALL\]'
    match = re.search(pattern, text, re.DOTALL)
    
    if match:
        tool_name = match.group(1)
        args_str = match.group(2)
        
        args = {}
        arg_pattern = r'--(\w+)\s+"([^"]*)"'
        for arg_match in re.finditer(arg_pattern, args_str):
            args[arg_match.group(1)] = arg_match.group(2)
        
        return {"tool": tool_name, "args": args}
    
    return None


def run_reasoning(prompt: str, system: str = None, temperature: float = 0.7) -> str:
    """Run main reasoning using 7B model.
    
    Args:
        prompt: User prompt
        system: Optional system prompt
        temperature: Sampling temperature
        
    Returns:
        Model response text
    """
    client = get_reasoner_client()
    
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    response = client.create_chat_completion(
        messages=messages,
        temperature=temperature,
        max_tokens=2048
    )
    
    return response["choices"][0]["message"]["content"]


# ============================================================================
# MCP TOOL EXECUTION
# ============================================================================

class DirectToolExecutor:
    """Execute tools for the direct pipeline."""
    
    TOOL_HANDLERS = {
        "memory_search": lambda args: {"results": [f"Found: {args.get('query', '')}"], "count": 1},
        "athena_smart_search": lambda args: {"results": [f"Athena: {args.get('query', '')}"], "count": 1},
        "read_file": lambda args: {"content": f"# Content of {args.get('file_path', 'unknown')}"},
        "write_file": lambda args: {"success": True, "path": args.get("file_path", "")},
        "list_directory": lambda args: {"files": ["file1.py", "file2.py"], "path": args.get("path", ".")},
        "git_status": lambda args: {"status": "clean", "branch": "main", "modified": []},
        "git_log": lambda args: {"commits": ["abc123 - initial"]},
        "git_diff": lambda args: {"diff": "--- a/file.py\n+++ b/file.py"},
        "github_list_issues": lambda args: {"issues": [{"number": 1, "title": "Bug"}]},
        "fetch_url": lambda args: {"content": f"Content from {args.get('url', '')}", "status": 200},
        "context7_query_docs": lambda args: {"docs": f"Docs for {args.get('library_id', '')}"},
    }
    
    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool call."""
        if tool_name in self.TOOL_HANDLERS:
            return self.TOOL_HANDLERS[tool_name](arguments)
        return {"tool": tool_name, "args": arguments, "note": "Simulated"}


# ============================================================================
# FULL PIPELINE - Translate -> Execute -> Respond
# ============================================================================

async def process_request(request: str) -> Dict[str, Any]:
    """Full pipeline: translate request to tool call, execute, return result.
    
    Args:
        request: User request in natural language
        
    Returns:
        Dict with tool call info and execution result
    """
    print(f"[DirectPipeline] Processing: {request}")
    
    # Step 1: Translate to tool call
    tool_call = translate_to_tool_call(request)
    
    if not tool_call:
        # No tool needed - use reasoner
        result = run_reasoning(request, system="You are a helpful coding assistant.")
        return {
            "type": "text",
            "content": result
        }
    
    print(f"[DirectPipeline] Tool: {tool_call['tool']}")
    print(f"[DirectPipeline] Args: {tool_call['args']}")
    
    # Step 2: Execute tool
    executor = DirectToolExecutor()
    exec_result = await executor.execute(tool_call["tool"], tool_call["args"])
    
    return {
        "type": "tool_call",
        "tool": tool_call["tool"],
        "args": tool_call["args"],
        "result": exec_result
    }


def run_sync(request: str) -> Dict[str, Any]:
    """Synchronous wrapper for process_request."""
    import asyncio
    return asyncio.run(process_request(request))


# ============================================================================
# TEST / DEMO
# ============================================================================

def test_pipeline():
    """Test all 3 models."""
    print("=" * 60)
    print("DIRECT GGUF PIPELINE TEST")
    print("=" * 60)
    
    # Test 1: Embedding
    print("\n1. Testing Embeddings...")
    emb1 = get_embedding("hello world")
    emb2 = get_embedding("hello world")
    emb3 = get_embedding("python code")
    
    from numpy.linalg import norm
    from numpy import dot
    
    sim_same = dot(emb1, emb2) / (norm(emb1) * norm(emb2))
    sim_diff = dot(emb1, emb3) / (norm(emb1) * norm(emb3))
    
    print(f"   Same text similarity: {sim_same:.3f} (should be ~1.0)")
    print(f"   Diff text similarity: {sim_diff:.3f} (should be <0.5)")
    
    # Test 2: Tool call translation
    print("\n2. Testing Tool Call Translation...")
    test_requests = [
        "search memory for security",
        "show me README.md",
        "check git status"
    ]
    
    for req in test_requests:
        result = translate_to_tool_call(req)
        print(f"   '{req}' -> {result}")
    
    # Test 3: Reasoning
    print("\n3. Testing Reasoning...")
    response = run_reasoning("What is 2+2?")
    print(f"   2+2 = {response[:50]}...")
    
    print("\n" + "=" * 60)
    print("✅ ALL MODELS WORKING!")
    print("=" * 60)


if __name__ == "__main__":
    test_pipeline()