#!/usr/bin/env python3
"""BrainBridge — Connects TUI to BrainPipeline for tool execution with feedback loop.

This module provides a bridge between the Textual-based TUI (ultimate_dashboard.py)
and the BrainPipeline's LocalLLMWrapper for executing MCP tools with proper feedback.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional

from brain.local_llm_wrapper import LocalLLMWrapper
from brain.mcp_tool_registry import get_tools

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BrainBridge:
    """Bridge TUI to BrainPipeline for tool execution with feedback loop.
    
    This class provides a clean interface for the TUI to process user messages
    through the BrainPipeline, enabling MCP tool execution with proper response
    formatting for display in the TUI.
    
    Attributes:
        llm_wrapper: LocalLLMWrapper instance for LLM tool calling
        tools: List of available MCP tools for execution
    """
    
    def __init__(self, model: str = "llama3.2:3b"):
        """Initialize bridge with local LLM wrapper.
        
        Args:
            model: Ollama model to use (default: llama3.2:3b - better tool calling)
        """
        self.llm_wrapper = LocalLLMWrapper(model=model, execute_mcp=True)
        self.tools = get_tools()
        logger.info(f"BrainBridge initialized with {len(self.tools)} tools")
    
    async def process_message(self, user_message: str) -> Dict[str, Any]:
        """Process user message through BrainPipeline with tool execution.
        
        Args:
            user_message: The user's input message
            
        Returns:
            Dict with:
            - type: "text" or "tool_calls"
            - content: response text or tool call info
            - executed: list of executed tools (if any)
        """
        messages = [{"role": "user", "content": user_message}]
        
        try:
            result = await self.llm_wrapper.execute_with_tools(
                messages=messages,
                tools=self.tools
            )
            logger.debug(f"BrainBridge result type: {result.get('type')}")
            return result
        except Exception as e:
            logger.error(f"BrainBridge processing failed: {e}")
            return {
                "type": "text",
                "content": f"Error: {str(e)}",
                "executed": []
            }
    
    async def process_with_context(
        self, 
        user_message: str, 
        conversation_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process message with full conversation context.
        
        Args:
            user_message: Current user message
            conversation_history: Previous messages in conversation
            
        Returns:
            Dict with response and optional tool executions
        """
        messages = conversation_history + [{"role": "user", "content": user_message}]
        
        try:
            result = await self.llm_wrapper.execute_with_tools(
                messages=messages,
                tools=self.tools
            )
            return result
        except Exception as e:
            logger.error(f"BrainBridge processing with context failed: {e}")
            return {
                "type": "text",
                "content": f"Error: {str(e)}",
                "executed": []
            }
    
    def format_for_tui(self, result: Dict[str, Any]) -> str:
        """Format BrainPipeline result for TUI display.
        
        Args:
            result: Result from process_message() or process_with_context()
            
        Returns:
            Formatted string for display in TUI
        """
        result_type = result.get("type", "text")
        
        if result_type == "text":
            return result.get("content", "")
        
        elif result_type == "tool_calls":
            calls = result.get("calls", [])
            executed = result.get("executed", [])
            
            lines = []
            
            if calls:
                tool_names = ", ".join([call.get("name", "unknown") for call in calls])
                lines.append(f"🔧 Tool calls: {tool_names}")
            
            if executed:
                lines.append("\n📋 Execution results:")
                for exec_result in executed:
                    tool_name = exec_result.get("tool", "unknown")
                    if "error" in exec_result:
                        lines.append(f"  - {tool_name}: ❌ {exec_result.get('error')}")
                    else:
                        result_content = exec_result.get("result", "")
                        # Truncate long results for display
                        if isinstance(result_content, str) and len(result_content) > 200:
                            result_content = result_content[:200] + "..."
                        lines.append(f"  - {tool_name}: ✅ {result_content}")
            
            return "\n".join(lines) if lines else "No tool execution results"
        
        return str(result)
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names.
        
        Returns:
            List of tool names available for execution
        """
        return [tool.get("function", {}).get("name", "?") for tool in self.tools]


# Module-level convenience function
async def execute_message(
    message: str,
    model: str = "llama3.2:3b",
    conversation_history: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Convenience function for quick message execution.
    
    Creates a BrainBridge and processes the message in one call.
    
    Args:
        message: User message to process
        model: Ollama model to use
        conversation_history: Optional conversation context
        
    Returns:
        BrainPipeline result dict
    """
    bridge = BrainBridge(model=model)
    
    if conversation_history:
        return await bridge.process_with_context(message, conversation_history)
    return await bridge.process_message(message)


# Example usage for testing
if __name__ == "__main__":
    async def test_bridge():
        """Test the BrainBridge functionality."""
        bridge = BrainBridge(model="llama3.2:3b")
        
        print(f"Available tools: {bridge.get_available_tools()[:5]}...")
        print("\nTesting simple message...")
        
        result = await bridge.process_message("Hello, what time is it?")
        print(f"Result type: {result.get('type')}")
        print(f"Content: {result.get('content', '')[:100]}...")
        
        print("\nTesting with context...")
        history = [{"role": "user", "content": "My name is Test"}]
        result = await bridge.process_with_context("What's my name?", history)
        print(f"Result: {result}")
    
    asyncio.run(test_bridge())