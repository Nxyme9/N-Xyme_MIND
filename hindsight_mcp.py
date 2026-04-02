#!/usr/bin/env python3
"""Hindsight MCP Server for OpenCode - Using embedded pg0."""

import os

os.environ.setdefault("HINDSIGHT_API_LAZY_RERANKER", "1")
os.environ.setdefault("HINDSIGHT_API_SKIP_LLM_VERIFICATION", "1")
os.environ.setdefault("HINDSIGHT_API_LLM_PROVIDER", "ollama")
os.environ.setdefault("HINDSIGHT_API_LLM_MODEL", "qwen2.5:14b")
os.environ.setdefault("HINDSIGHT_API_LLM_BASE_URL", "http://localhost:11434/v1")
os.environ.setdefault("HINDSIGHT_API_LLM_API_KEY", "ollama")

from hindsight_api import MemoryEngine
from hindsight_api.api.mcp import create_mcp_server

memory = MemoryEngine(
    db_url=None,  # Use embedded pg0 (no external PostgreSQL needed)
    memory_llm_provider="ollama",
    memory_llm_api_key="ollama",
    memory_llm_model="qwen2.5:14b",
    memory_llm_base_url="http://localhost:11434/v1",
)

mcp = create_mcp_server(memory, multi_bank=False)
mcp.run(transport="stdio")
