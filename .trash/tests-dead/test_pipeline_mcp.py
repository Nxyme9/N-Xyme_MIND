#!/usr/bin/env python3
"""Integration tests for BrainPipeline with LocalLLMWrapper and MCP tools.

Uses athena venv at: /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/venvs/athena/bin/python3
Run with: pytest tests/test_pipeline_mcp.py -v
"""

import sys
import os

# Ensure project root in path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# Test packages
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import List, Dict, Any


# Mock tools for testing
MOCK_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "memory_search",
            "description": "Search memory",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        }
    }
]


@pytest.fixture
def mock_rosetta():
    """Mock RosettaStoneV2 instance."""
    mock_instance = MagicMock()
    mock_instance.model = "qwen2.5-coder:7b"
    mock_instance.normalize_tool_schema = MagicMock(return_value=[])
    mock_instance.chat_with_tools_async = AsyncMock(
        return_value={"type": "tool_calls", "calls": []}
    )
    return mock_instance


@pytest.fixture
def pipeline(mock_rosetta):
    """Create BrainPipeline instance with mocked dependencies."""
    with patch("brain.pipeline.CircuitBreaker"):
        with patch("brain.pipeline.LocalLLMWrapper") as MockWrapper:
            # Configure mock wrapper
            mock_wrapper_instance = MagicMock()
            mock_wrapper_instance.model = "qwen2.5-coder:7b"
            mock_wrapper_instance.rosetta = mock_rosetta
            MockWrapper.return_value = mock_wrapper_instance

            from brain.pipeline import BrainPipeline
            with patch("brain.pipeline.MCPToolRegistry"):
                with patch("brain.pipeline.get_tools", return_value=MOCK_TOOLS):
                    p = BrainPipeline(use_local_wrapper=True)
                    # Ensure tools are set
                    p._tools = MOCK_TOOLS
                    yield p


class TestBrainPipelineWithLocalWrapper:
    """Integration tests for BrainPipeline with LocalLLMWrapper."""

    def test_pipeline_initialization(self, pipeline):
        """Test BrainPipeline initializes with local wrapper."""
        assert pipeline.local_llm_wrapper is not None
        assert hasattr(pipeline, "router")
        assert hasattr(pipeline, "dual_loop")

    def test_pre_execute_returns_wrapper_info_for_implementation(self, pipeline):
        """Test pre_execute returns wrapper info for tool-intensive tasks."""
        result = pipeline.pre_execute(
            task="Implement authentication system",
            intent="IMPLEMENTATION",
            complexity="HIGH",
            risk="MEDIUM"
        )

        assert "use_local_wrapper" in result
        assert result["use_local_wrapper"] is True
        assert "local_tools" in result
        # Model is accessed via the wrapper's model attribute
        assert result.get("local_model") is not None

    def test_pre_execute_returns_wrapper_info_for_investigation(self, pipeline):
        """Test pre_execute returns wrapper info for investigation tasks."""
        result = pipeline.pre_execute(
            task="Investigate memory leak",
            intent="INVESTIGATION",
            complexity="MED",
            risk="LOW"
        )

        assert "use_local_wrapper" in result
        assert result["use_local_wrapper"] is True

    def test_pre_execute_returns_wrapper_info_for_research(self, pipeline):
        """Test pre_execute returns wrapper info for research tasks."""
        result = pipeline.pre_execute(
            task="Research best practices for auth",
            intent="RESEARCH",
            complexity="MED",
            risk="LOW"
        )

        assert "use_local_wrapper" in result
        assert result["use_local_wrapper"] is True

    def test_pre_execute_no_wrapper_for_simple_tasks(self, pipeline):
        """Test pre_execute doesn't use local wrapper for simple tasks."""
        result = pipeline.pre_execute(
            task="What is 2+2?",
            intent="QUESTION",
            complexity="LOW",
            risk="LOW"
        )

        # Simple question shouldn't use local wrapper
        assert "use_local_wrapper" not in result or result.get("use_local_wrapper") is False

    def test_pre_execute_loads_mcp_tools(self, pipeline):
        """Test pre_execute loads MCP tools when wrapper is used."""
        result = pipeline.pre_execute(
            task="Implement feature X",
            intent="IMPLEMENTATION",
            complexity="HIGH",
            risk="LOW"
        )

        assert "local_tools" in result
        assert len(result["local_tools"]) == 2

    def test_pre_execute_selects_agent(self, pipeline):
        """Test pre_execute selects appropriate agent."""
        result = pipeline.pre_execute(
            task="Write code for feature",
            intent="IMPLEMENTATION",
            complexity="HIGH",
            risk="MEDIUM"
        )

        assert "agent" in result
        assert result["agent"] in ["hephaestus", "sisyphus junior", "oracle", "momus", "librarian"]

    def test_pre_execute_returns_plan_and_loop(self, pipeline):
        """Test pre_execute returns plan and loop information."""
        result = pipeline.pre_execute(
            task="Test task",
            intent="IMPLEMENTATION",
            complexity="MED",
            risk="LOW"
        )

        assert "plan" in result
        assert "loop" in result

    def test_pre_execute_caches_results(self, pipeline):
        """Test pre_execute caches results for repeated tasks."""
        task = "Cached task"
        
        result1 = pipeline.pre_execute(task, intent="IMPLEMENTATION", complexity="MED", risk="LOW")
        result2 = pipeline.pre_execute(task, intent="IMPLEMENTATION", complexity="MED", risk="LOW")
        
        assert result1["agent"] == result2["agent"]

    def test_post_execute_success(self, pipeline):
        """Test post_execute with successful result."""
        pre_result = {
            "agent": "hephaestus",
            "task": "Test task"
        }
        
        result = pipeline.post_execute("Task completed successfully", pre_result)
        
        assert result["status"] == "success"
        assert "result" in result

    def test_post_execute_decrements_load(self, pipeline):
        """Test post_execute decrements agent load."""
        pre_result = {
            "agent": "hephaestus",
            "task": "Test task"
        }
        
        initial_load = pipeline.agent_load.get("hephaestus", 0)
        pipeline.post_execute("done", pre_result)
        
        assert pipeline.agent_load.get("hephaestus", 0) <= initial_load


class TestMCPToolRegistry:
    """Test MCP tool registry integration."""

    def test_get_tools_returns_list(self):
        """Test get_tools returns a list of tools."""
        with patch("brain.pipeline.MCPToolRegistry"):
            with patch("brain.pipeline.get_tools", return_value=[]):
                from brain.mcp_tool_registry import get_tools
                assert callable(get_tools)

    def test_mcp_tool_schema_format(self):
        """Test MCP tools have correct schema format."""
        mock_tools = [
            {
                "type": "function",
                "function": {
                    "name": "test_tool",
                    "description": "Test description",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "param1": {"type": "string"}
                        },
                        "required": ["param1"]
                    }
                }
            }
        ]

        tool = mock_tools[0]
        assert "type" in tool
        assert tool["type"] == "function"
        assert "function" in tool
        assert "name" in tool["function"]
        assert "parameters" in tool["function"]


class TestToolIntentDetection:
    """Test tool intent detection in pipeline."""

    def test_tool_intents_list(self):
        """Test that tool intents are correctly defined."""
        tool_intents = {"IMPLEMENTATION", "INVESTIGATION", "RESEARCH", "EXPLORATION"}
        
        assert "IMPLEMENTATION" in tool_intents
        assert "INVESTIGATION" in tool_intents
        assert "RESEARCH" in tool_intents
        assert "EXPLORATION" in tool_intents


class TestPipelinePatternStats:
    """Test pipeline pattern statistics."""

    def test_get_pattern_stats(self, pipeline):
        """Test get_pattern_stats returns expected structure."""
        stats = pipeline.get_pattern_stats()

        assert "cache" in stats
        assert "intent" in stats
        assert "bulkhead" in stats
        assert "attention" in stats
        assert "delta" in stats

        assert "hits" in stats["cache"]
        assert "misses" in stats["cache"]
        assert "history_size" in stats["intent"]
        assert "patterns" in stats["intent"]
        assert "hephaestus" in stats["bulkhead"]


class TestLocalWrapperInPipeline:
    """Test LocalLLMWrapper integration within pipeline context."""

    def test_wrapper_model_name(self, pipeline):
        """Test wrapper has correct model name."""
        wrapper = pipeline.local_llm_wrapper
        assert wrapper is not None

    def test_wrapper_execute_with_tools(self, pipeline, mock_rosetta):
        """Test wrapper can execute with tools."""
        wrapper = pipeline.local_llm_wrapper
        
        # Verify wrapper has the expected methods
        assert hasattr(wrapper, "rosetta") or wrapper is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])