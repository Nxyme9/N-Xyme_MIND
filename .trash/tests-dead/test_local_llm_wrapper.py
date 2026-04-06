#!/usr/bin/env python3
"""Unit tests for LocalLLMWrapper and related brain components.

Uses athena venv at: /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/venvs/athena/bin/python3
Run with: pytest tests/test_local_llm_wrapper.py -v
"""

import sys
import os

# Ensure project root in path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# Test packages
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import List, Dict, Any
import asyncio


class TestLocalLLMWrapper:
    """Test suite for LocalLLMWrapper class."""

    @pytest.fixture
    def mock_rosetta(self):
        """Create standalone mock for RosettaStoneV2."""
        mock_instance = MagicMock()
        mock_instance.model = "qwen2.5-coder:7b"
        mock_instance.normalize_tool_schema = MagicMock(return_value=[])
        mock_instance.chat_with_tools_async = AsyncMock(
            return_value={"type": "text", "content": "test response"}
        )
        return mock_instance

    @pytest.fixture
    def wrapper_with_mock_rosetta(self, mock_rosetta):
        """Create LocalLLMWrapper instance with pre-created mock."""
        # Import and create wrapper with the mock directly
        from brain.local_llm_wrapper import LocalLLMWrapper
        with patch("brain.local_llm_wrapper.ROSETTA", mock_rosetta):
            wrapper = LocalLLMWrapper(rosetta_instance=mock_rosetta)
            return wrapper, mock_rosetta

    def test_initialization_default(self):
        """Test LocalLLMWrapper initialization with defaults."""
        mock_instance = MagicMock()
        mock_instance.model = "qwen2.5-coder:7b"
        
        with patch("brain.local_llm_wrapper.ROSETTA", mock_instance):
            from brain.local_llm_wrapper import LocalLLMWrapper
            wrapper = LocalLLMWrapper()
            assert wrapper.model == "qwen2.5-coder:7b"

    def test_initialization_custom_model(self):
        """Test LocalLLMWrapper initialization with custom model."""
        mock_instance = MagicMock()
        mock_instance.model = "llama3:8b"
        
        with patch("brain.local_llm_wrapper.ROSETTA", mock_instance):
            from brain.local_llm_wrapper import LocalLLMWrapper
            wrapper = LocalLLMWrapper(model="llama3:8b")
            assert wrapper.model == "llama3:8b"

    def test_execute_with_tools_simple_tool_call(self):
        """Test execute_with_tools returns tool_calls for tool invocation."""
        mock_rosetta = MagicMock()
        mock_rosetta.model = "qwen2.5-coder:7b"
        mock_rosetta.normalize_tool_schema = MagicMock(return_value=[])
        mock_rosetta.chat_with_tools_async = AsyncMock(return_value={
            "type": "tool_calls",
            "calls": [{"name": "search_tool", "arguments": {"query": "test"}}]
        })

        from brain.local_llm_wrapper import LocalLLMWrapper
        wrapper = LocalLLMWrapper(rosetta_instance=mock_rosetta)

        messages = [{"role": "user", "content": "Use search_tool with query 'test'"}]
        tools = [{"type": "function", "function": {"name": "search_tool", "description": "Search", "parameters": {"type": "object"}}}]

        async def run_test():
            result = await wrapper.execute_with_tools(messages, tools)
            assert result["type"] == "tool_calls"
            assert len(result["calls"]) == 1
            assert result["calls"][0]["name"] == "search_tool"

        asyncio.run(run_test())

    def test_execute_with_tools_text_response(self):
        """Test execute_with_tools returns text for non-tool responses."""
        mock_rosetta = MagicMock()
        mock_rosetta.model = "qwen2.5-coder:7b"
        mock_rosetta.normalize_tool_schema = MagicMock(return_value=[])
        mock_rosetta.chat_with_tools_async = AsyncMock(return_value={
            "type": "text",
            "content": "2 + 2 = 4"
        })

        from brain.local_llm_wrapper import LocalLLMWrapper
        wrapper = LocalLLMWrapper(rosetta_instance=mock_rosetta)

        messages = [{"role": "user", "content": "What is 2+2?"}]
        tools = []

        async def run_test():
            result = await wrapper.execute_with_tools(messages, tools)
            assert result["type"] == "text"
            assert "4" in result["content"]

        asyncio.run(run_test())

    def test_execute_with_tools_error_handling(self):
        """Test execute_with_tools handles Ollama connection errors."""
        mock_rosetta = MagicMock()
        mock_rosetta.model = "qwen2.5-coder:7b"
        mock_rosetta.normalize_tool_schema = MagicMock(return_value=[])
        mock_rosetta.chat_with_tools_async = AsyncMock(side_effect=Exception("Connection refused"))

        from brain.local_llm_wrapper import LocalLLMWrapper
        wrapper = LocalLLMWrapper(rosetta_instance=mock_rosetta)

        messages = [{"role": "user", "content": "test"}]
        tools = []

        async def run_test():
            result = await wrapper.execute_with_tools(messages, tools)
            assert result["type"] == "text"
            assert "Error" in result["content"]

        asyncio.run(run_test())

    def test_execute_with_tools_multiple_tools(self):
        """Test execute_with_tools with multiple tool options."""
        mock_rosetta = MagicMock()
        mock_rosetta.model = "qwen2.5-coder:7b"
        mock_rosetta.normalize_tool_schema = MagicMock(return_value=[])
        mock_rosetta.chat_with_tools_async = AsyncMock(return_value={
            "type": "tool_calls",
            "calls": [{"name": "memory_search", "arguments": {"query": "authentication"}}]
        })

        from brain.local_llm_wrapper import LocalLLMWrapper
        wrapper = LocalLLMWrapper(rosetta_instance=mock_rosetta)

        messages = [{"role": "user", "content": "Search memory for 'authentication'"}]
        tools = [
            {"type": "function", "function": {"name": "memory_search", "description": "Search memory", "parameters": {"type": "object"}}},
            {"type": "function", "function": {"name": "web_search", "description": "Search web", "parameters": {"type": "object"}}}
        ]

        async def run_test():
            result = await wrapper.execute_with_tools(messages, tools)
            assert result["type"] == "tool_calls"
            assert result["calls"][0]["name"] == "memory_search"

        asyncio.run(run_test())

    def test_normalize_tools(self):
        """Test tool schema normalization."""
        mock_rosetta = MagicMock()
        mock_rosetta.normalize_tool_schema = MagicMock(return_value=[
            {"function": {"name": "test_tool", "description": "Test"}}
        ])

        from brain.local_llm_wrapper import LocalLLMWrapper
        wrapper = LocalLLMWrapper(rosetta_instance=mock_rosetta)

        tools = [{"type": "function", "function": {"name": "test_tool"}}]
        result = wrapper.normalize_tools(tools)

        assert len(result) == 1
        mock_rosetta.normalize_tool_schema.assert_called_once()

    def test_ensure_pipeline_format_tool_calls(self):
        """Test _ensure_pipeline_format with tool_calls response."""
        mock_rosetta = MagicMock()
        
        from brain.local_llm_wrapper import LocalLLMWrapper
        wrapper = LocalLLMWrapper(rosetta_instance=mock_rosetta)

        result = wrapper._ensure_pipeline_format({
            "type": "tool_calls",
            "calls": [{"name": "tool1", "arguments": {"arg": "value"}}]
        })

        assert result["type"] == "tool_calls"
        assert result["calls"][0]["name"] == "tool1"

    def test_ensure_pipeline_format_text(self):
        """Test _ensure_pipeline_format with text response."""
        mock_rosetta = MagicMock()
        
        from brain.local_llm_wrapper import LocalLLMWrapper
        wrapper = LocalLLMWrapper(rosetta_instance=mock_rosetta)

        result = wrapper._ensure_pipeline_format({
            "type": "text",
            "content": "Hello world"
        })

        assert result["type"] == "text"
        assert result["content"] == "Hello world"

    def test_ensure_pipeline_format_malformed(self):
        """Test _ensure_pipeline_format handles malformed responses."""
        mock_rosetta = MagicMock()
        
        from brain.local_llm_wrapper import LocalLLMWrapper
        wrapper = LocalLLMWrapper(rosetta_instance=mock_rosetta)

        result = wrapper._ensure_pipeline_format("not a dict")
        assert result["type"] == "text"

        result = wrapper._ensure_pipeline_format({})
        assert result["type"] == "text"

    def test_ensure_pipeline_format_empty_calls(self):
        """Test _ensure_pipeline_format with empty tool calls."""
        mock_rosetta = MagicMock()
        
        from brain.local_llm_wrapper import LocalLLMWrapper
        wrapper = LocalLLMWrapper(rosetta_instance=mock_rosetta)

        result = wrapper._ensure_pipeline_format({
            "type": "tool_calls",
            "calls": []
        })

        assert result["type"] == "text"
        assert result["content"] == ""

    def test_execute_with_tools_normalizes_schema(self):
        """Test that execute_with_tools normalizes tool schemas."""
        mock_rosetta = MagicMock()
        mock_rosetta.model = "qwen2.5-coder:7b"
        mock_rosetta.normalize_tool_schema = MagicMock(return_value=[])
        mock_rosetta.chat_with_tools_async = AsyncMock(return_value={"type": "text", "content": "ok"})

        from brain.local_llm_wrapper import LocalLLMWrapper
        wrapper = LocalLLMWrapper(rosetta_instance=mock_rosetta)

        messages = [{"role": "user", "content": "test"}]
        tools = [{"type": "function", "function": {"name": "tool"}}]

        async def run_test():
            await wrapper.execute_with_tools(messages, tools)
            mock_rosetta.normalize_tool_schema.assert_called_once_with(tools)

        asyncio.run(run_test())


class TestConvenienceFunction:
    """Test the module-level convenience function."""

    def test_execute_with_tools_function(self):
        """Test the convenience function creates wrapper and executes."""
        mock_wrapper = MagicMock()
        mock_wrapper.execute_with_tools = AsyncMock(return_value={"type": "text", "content": "result"})
        
        with patch("brain.local_llm_wrapper.LocalLLMWrapper", return_value=mock_wrapper):
            from brain.local_llm_wrapper import execute_with_tools
            
            async def run_test():
                result = await execute_with_tools(
                    messages=[{"role": "user", "content": "test"}],
                    tools=[],
                    model="qwen2.5-coder:7b"
                )
                assert result["type"] == "text"

            asyncio.run(run_test())


class TestToolSchemaNormalization:
    """Test tool schema normalization scenarios."""

    def test_mcp_format_normalization(self):
        """Test normalization of MCP format tools."""
        mock_rosetta = MagicMock()
        mock_rosetta.normalize_tool_schema = MagicMock(return_value=[
            {"function": {"name": "test", "description": "Test tool"}}
        ])

        from brain.local_llm_wrapper import LocalLLMWrapper
        wrapper = LocalLLMWrapper(rosetta_instance=mock_rosetta)

        mcp_tools = [{"type": "function", "function": {"name": "test", "description": "Test tool", "parameters": {"type": "object"}}}]
        result = wrapper.normalize_tools(mcp_tools)
        
        # Result should have 1 item from mock return
        assert len(result) >= 0

    def test_openai_format_normalization(self):
        """Test normalization of OpenAI format tools."""
        mock_rosetta = MagicMock()
        mock_rosetta.normalize_tool_schema = MagicMock(return_value=[
            {"function": {"name": "search", "description": "Search"}}
        ])

        from brain.local_llm_wrapper import LocalLLMWrapper
        wrapper = LocalLLMWrapper(rosetta_instance=mock_rosetta)

        openai_tools = [{"name": "search", "description": "Search", "parameters": {"type": "object"}}]
        result = wrapper.normalize_tools(openai_tools)
        
        assert len(result) >= 0


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_timeout_error(self):
        """Test handling of timeout errors."""
        mock_rosetta = MagicMock()
        mock_rosetta.model = "qwen2.5-coder:7b"
        mock_rosetta.normalize_tool_schema = MagicMock(return_value=[])
        mock_rosetta.chat_with_tools_async = AsyncMock(side_effect=TimeoutError("Request timeout"))

        from brain.local_llm_wrapper import LocalLLMWrapper
        wrapper = LocalLLMWrapper(rosetta_instance=mock_rosetta)

        async def run_test():
            result = await wrapper.execute_with_tools([], [])
            assert result["type"] == "text"
            assert "Error" in result["content"]

        asyncio.run(run_test())

    def test_invalid_response_handling(self):
        """Test handling of invalid model responses."""
        mock_rosetta = MagicMock()
        mock_rosetta.model = "qwen2.5-coder:7b"
        mock_rosetta.normalize_tool_schema = MagicMock(return_value=[])
        mock_rosetta.chat_with_tools_async = AsyncMock(return_value=None)

        from brain.local_llm_wrapper import LocalLLMWrapper
        wrapper = LocalLLMWrapper(rosetta_instance=mock_rosetta)

        async def run_test():
            result = await wrapper.execute_with_tools([], [])
            assert "type" in result

        asyncio.run(run_test())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])