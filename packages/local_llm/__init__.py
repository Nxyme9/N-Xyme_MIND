#!/usr/bin/env python3
"""Local LLM Package - Fresh implementation of local Ollama tool calling.

This package provides:
- Direct Ollama API client with tool calling support
- MCP tool executor for executing tools
- execute_with_tools() function for 2-pass tool execution
"""

from packages.local_llm.ollama_client import LocalLLM
from packages.local_llm.wrapper import execute_with_tools

__all__ = ["LocalLLM", "execute_with_tools"]
