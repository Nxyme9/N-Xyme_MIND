#!/usr/bin/env python3
"""Test file to verify the feedback loop fix works correctly.

Purpose:
    Verify that after tool execution, the model generates a natural language
    response (not {"name": "_none"}).

Run with: pytest tests/test_feedback_loop.py -v

Uses athena venv at: /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/venvs/athena/bin/python3
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
import json


class TestFeedbackLoop:
    """Test suite for feedback loop functionality.

    The feedback loop is the critical mechanism that:
    1. Takes user message → model generates tool call
    2. Executes the tool → returns results
    3. Feeds results back to model → model generates natural language response

    The bug: model was returning {"name": "_none"} instead of natural language.
    """

    @pytest.fixture
    def mock_mcp_executor(self):
        """Create mock MCP tool executor that returns simulated tool results."""
        mock_executor = MagicMock()

        def mock_execute(tool_name: str, args: Dict[str, Any]) -> Any:
            """Simulate tool execution based on tool name."""
            if tool_name == "list_directory":
                return [
                    {"name": "file1.py", "type": "file"},
                    {"name": "file2.py", "type": "file"},
                ]
            elif tool_name == "search_memories":
                return [{"content": "test memory", "score": 0.9}]
            elif tool_name == "get_mind_state":
                return {"project": "test", "phase": "1-analysis", "active_tasks": []}
            else:
                return {"result": f"executed {tool_name} with {args}"}

        mock_executor.execute = mock_execute
        return mock_executor

    @pytest.fixture
    def mock_rosetta(self):
        """Create mock RosettaStoneV2 instance."""
        mock_instance = MagicMock()
        mock_instance.model = "llama3.2:3b"
        mock_instance.normalize_tool_schema = MagicMock(return_value=[])
        return mock_instance

    def test_feedback_loop_basic(self, mock_mcp_executor, mock_rosetta):
        """Test that model generates response after tool execution.

        This is the core test: after tools execute, the model should generate
        a natural language text response, not another tool call or {"name": "_none"}.

        Steps:
        1. User message triggers tool call (list_directory)
        2. Tool executes and returns results
        3. Results are fed back to model
        4. Model generates final text response
        """
        from brain.local_llm_wrapper import LocalLLMWrapper

        # Setup: First call returns tool call, second call returns text response
        mock_rosetta.chat_with_tools_async = AsyncMock(
            side_effect=[
                # First call: model decides to use a tool
                {
                    "type": "tool_calls",
                    "calls": [
                        {"name": "list_directory", "arguments": {"path": "/test"}}
                    ],
                },
                # Second call (after tool execution): model generates text response
                {
                    "type": "text",
                    "content": "I found 2 files in the /test directory: file1.py and file2.py",
                },
            ]
        )

        async def run_test():
            with patch(
                "brain.local_llm_wrapper.MCPToolExecutor",
                return_value=mock_mcp_executor,
            ):
                with patch("brain.local_llm_wrapper.ROSETTA", mock_rosetta):
                    wrapper = LocalLLMWrapper(
                        model="llama3.2:3b",
                        rosetta_instance=mock_rosetta,
                        execute_mcp=True,
                    )
                    wrapper.mcp_executor = mock_mcp_executor

                    # Execute with simple message that triggers tool call
                    messages = [
                        {"role": "user", "content": "List files in src directory"}
                    ]
                    tools = [
                        {
                            "type": "function",
                            "function": {
                                "name": "list_directory",
                                "description": "Get a detailed listing of all files and directories",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "path": {
                                            "type": "string",
                                            "description": "Path to the directory",
                                        }
                                    },
                                    "required": ["path"],
                                },
                            },
                        }
                    ]

                    result = await wrapper.execute_with_tools(messages, tools)

                    # Verify: result should be text (response), not tool_calls
                    assert result.get("type") == "text", (
                        f"Expected text response, got {result.get('type')}"
                    )
                    assert result.get("content"), "Response should not be empty"

                    # The key check: Should NOT be {"name": "_none"}
                    result_str = json.dumps(result)
                    assert "_none" not in result_str, (
                        "Model returned _none - feedback loop broken!"
                    )

                    content = result.get("content") or ""
                    print(f"✓ Test passed: Got text response: {content[:100]}...")

        asyncio.run(run_test())

    def test_tool_executes_successfully(self, mock_mcp_executor, mock_rosetta):
        """Verify tool actually executes and results are used in the response.

        The feedback loop requires the tool to execute and return results,
        which are then fed back to the model for the final response.
        The executed results are used internally but the final result is text.
        """
        from brain.local_llm_wrapper import LocalLLMWrapper

        # Setup: First call returns tool call
        mock_rosetta.chat_with_tools_async = AsyncMock(
            side_effect=[
                {
                    "type": "tool_calls",
                    "calls": [{"name": "get_mind_state", "arguments": {}}],
                },
                {
                    "type": "text",
                    "content": "The current mind state shows no active tasks.",
                },
            ]
        )

        async def run_test():
            with patch(
                "brain.local_llm_wrapper.MCPToolExecutor",
                return_value=mock_mcp_executor,
            ):
                with patch("brain.local_llm_wrapper.ROSETTA", mock_rosetta):
                    wrapper = LocalLLMWrapper(
                        model="llama3.2:3b",
                        rosetta_instance=mock_rosetta,
                        execute_mcp=True,
                    )
                    wrapper.mcp_executor = mock_mcp_executor

                    messages = [
                        {"role": "user", "content": "What's the current mind state?"}
                    ]
                    tools = [
                        {
                            "type": "function",
                            "function": {
                                "name": "get_mind_state",
                                "description": "Returns current MIND state",
                                "parameters": {"type": "object", "properties": {}},
                            },
                        }
                    ]

                    result = await wrapper.execute_with_tools(messages, tools)

                    # Verify final result is text (successful feedback loop)
                    assert result.get("type") == "text", "Response should be text type"

                    # The text response is generated from tool results
                    content = result.get("content", "")
                    assert len(content) > 0, "Response should not be empty"

                    # The model should reference the tool results in its response
                    assert (
                        "mind state" in content.lower() or "active" in content.lower()
                    ), f"Response should mention tool results: {content}"

                    print(
                        f"✓ Test passed: Tool executed and model generated response: {content[:60]}..."
                    )

        asyncio.run(run_test())

    def test_natural_language_response(self, mock_mcp_executor, mock_rosetta):
        """Verify response is natural language, not JSON tool call.

        After tool execution, the model should return a natural language
        response that explains the tool results, not another tool call structure.
        """
        from brain.local_llm_wrapper import LocalLLMWrapper

        mock_rosetta.chat_with_tools_async = AsyncMock(
            side_effect=[
                {
                    "type": "tool_calls",
                    "calls": [
                        {"name": "search_memories", "arguments": {"query": "test"}}
                    ],
                },
                {
                    "type": "text",
                    "content": "I found a relevant memory about your test query with a confidence score of 0.9",
                },
            ]
        )

        async def run_test():
            with patch(
                "brain.local_llm_wrapper.MCPToolExecutor",
                return_value=mock_mcp_executor,
            ):
                with patch("brain.local_llm_wrapper.ROSETTA", mock_rosetta):
                    wrapper = LocalLLMWrapper(
                        model="llama3.2:3b",
                        rosetta_instance=mock_rosetta,
                        execute_mcp=True,
                    )
                    wrapper.mcp_executor = mock_mcp_executor

                    messages = [
                        {"role": "user", "content": "Search for memories about test"}
                    ]
                    tools = [
                        {
                            "type": "function",
                            "function": {
                                "name": "search_memories",
                                "description": "Search across all memory sources",
                                "parameters": {
                                    "type": "object",
                                    "properties": {"query": {"type": "string"}},
                                    "required": ["query"],
                                },
                            },
                        }
                    ]

                    result = await wrapper.execute_with_tools(messages, tools)

                    # Verify response is text type
                    assert result.get("type") == "text", "Response should be text type"

                    content = result.get("content") or ""

                    # Verify it's not a JSON tool call structure
                    # Natural language should not start with { and contain "name":
                    assert not (
                        content.strip().startswith("{") and '"name"' in content
                    ), "Response appears to be JSON tool call, not natural language"

                    # Verify it's not empty or just whitespace
                    assert len(content.strip()) > 0, "Response should not be empty"

                    # Verify it doesn't contain _none (the fix we're solving for)
                    assert "_none" not in content, (
                        f"Response still contains _none: {content[:100]}"
                    )

                    # Verify it's not a raw JSON tool call response
                    is_json_tool_call = (
                        content.strip().startswith("{")
                        and '"name"' in content
                        and '"arguments"' in content
                    )
                    assert not is_json_tool_call, (
                        f"Response appears to be JSON tool call, not processed: {content[:100]}"
                    )

                    print(
                        f"✓ Test passed: Got natural language response: {content[:100]}..."
                    )

        asyncio.run(run_test())

    def test_feedback_loop_with_no_tool_call(self):
        """Test that direct text responses work without the feedback loop.

        When the model doesn't generate a tool call, it should return text directly
        without going through the feedback loop mechanism.
        """
        from brain.local_llm_wrapper import LocalLLMWrapper

        mock_rosetta = MagicMock()
        mock_rosetta.model = "llama3.2:3b"
        mock_rosetta.normalize_tool_schema = MagicMock(return_value=[])
        mock_rosetta.chat_with_tools_async = AsyncMock(
            return_value={"type": "text", "content": "Hello! How can I help you today?"}
        )

        async def run_test():
            wrapper = LocalLLMWrapper(
                model="llama3.2:3b", rosetta_instance=mock_rosetta, execute_mcp=True
            )

            messages = [{"role": "user", "content": "Hello"}]
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "test",
                        "description": "test",
                        "parameters": {},
                    },
                }
            ]

            result = await wrapper.execute_with_tools(messages, tools)

            # Should return text directly without feedback loop
            assert result.get("type") == "text"
            assert "Hello" in result.get("content", "")
            assert "executed" not in result, "Should not execute tools when none called"

            print(f"✓ Test passed: Direct text response works: {result.get('content')}")

        asyncio.run(run_test())


class TestFeedbackLoopIntegration:
    """Integration tests for feedback loop with actual components."""

    def test_get_tools_from_registry(self):
        """Verify we can get tools from the MCP tool registry."""
        from brain.mcp_tool_registry import get_tools

        tools = get_tools()

        # Should have tools available
        assert isinstance(tools, list), "get_tools should return a list"

        # Each tool should have type "function"
        for tool in tools:
            assert tool.get("type") == "function", (
                f"Tool should be function type: {tool}"
            )

        print(f"✓ Test passed: Got {len(tools)} tools from registry")

    def test_wrapper_import(self):
        """Verify LocalLLMWrapper can be imported and instantiated."""
        from brain.local_llm_wrapper import LocalLLMWrapper

        # Should be able to create instance (may fail if no Ollama, but import should work)
        try:
            wrapper = LocalLLMWrapper(model="llama3.2:3b", execute_mcp=False)
            assert wrapper.model == "llama3.2:3b"
            print(f"✓ Test passed: LocalLLMWrapper imported and instantiated")
        except Exception as e:
            # If Ollama not available, that's okay for import test
            if "Ollama" in str(e) or "connection" in str(e).lower():
                pytest.skip("Ollama not available")
            raise


if __name__ == "__main__":
    """Run tests directly with pytest."""
    pytest.main([__file__, "-v", "-s"])
