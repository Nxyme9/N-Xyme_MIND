#!/usr/bin/env python3
"""Hindsight MCP - Module runner."""

import os
from hindsight_api import MemoryEngine
from hindsight_api.api.mcp import create_mcp_server


def main():
    memory = MemoryEngine(
        db_url=os.environ.get(
            "HINDSIGHT_DATABASE_URL",
            "postgresql://hindsight:hindsight@localhost:5432/hindsight",
        ),
        memory_llm_provider="ollama",
        memory_llm_api_key=os.environ.get("MEMORY_LLM_API_KEY", "ollama"),
        memory_llm_model="qwen2.5:14b",
        memory_llm_base_url="http://localhost:11434/v1",
    )
    mcp = create_mcp_server(memory, multi_bank=True)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
