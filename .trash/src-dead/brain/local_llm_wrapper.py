#!/usr/bin/env python3
"""LocalLLMWrapper — Rosetta Stone integration layer for brain pipeline.

Wraps RosettaStoneV2 to provide async tool execution compatible with the brain pipeline.
Converts MCP tool schemas to Rosetta-compatible format and executes MCP tools.
"""

import logging
import asyncio
import json
from typing import List, Dict, Any, Optional

from src.tools.rosetta_stone_v2 import RosettaStoneV2, ROSETTA

# Import MCP tool executor for actual tool execution
try:
    from brain.mcp_tool_executor import MCPToolExecutor

    MCP_EXECUTOR_AVAILABLE = True
except ImportError:
    MCP_EXECUTOR_AVAILABLE = False

logger = logging.getLogger(__name__)


class LocalLLMWrapper:
    """Async wrapper around RosettaStoneV2 for brain pipeline integration.

    Provides:
    - async execute_with_tools() method compatible with brain pipeline
    - Tool schema normalization using RosettaStoneV2.normalize_tool_schema()
    - Pipeline-compatible output format: {"type": "tool_calls", "calls": [...]}
    - MCP tool execution (the missing piece!)
    """

    def __init__(
        self,
        model: str = "qwen2.5-coder:7b",
        rosetta_instance: Optional[RosettaStoneV2] = None,
        execute_mcp: bool = True,  # NEW: actually execute MCP tools
    ):
        """Initialize wrapper with optional custom RosettaStoneV2 instance.

        Args:
            model: Ollama model name for tool calling (default: qwen2.5-coder:7b)
            rosetta_instance: Optional RosettaStoneV2 instance (uses singleton if not provided)
            execute_mcp: If True, actually execute MCP tools after parsing (default: True)
        """
        self.model = model
        self.rosetta = rosetta_instance or ROSETTA
        self.rosetta.model = model
        self.execute_mcp = execute_mcp and MCP_EXECUTOR_AVAILABLE

        # Initialize MCP executor
        self.mcp_executor = MCPToolExecutor() if MCP_EXECUTOR_AVAILABLE else None

        if self.execute_mcp:
            logger.info(
                f"LocalLLMWrapper initialized with model: {model}, MCP execution: ON"
            )
        else:
            logger.info(
                f"LocalLLMWrapper initialized with model: {model}, MCP execution: OFF"
            )

    async def execute_with_tools(
        self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]], **kwargs
    ) -> Dict[str, Any]:
        """Execute LLM with tools using RosettaStoneV2.

        This is the PRIMARY entry point for brain pipeline integration.
        Converts MCP tool schemas to Rosetta-compatible format, executes,
        and if MCP execution is enabled, actually runs the tools!

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            tools: List of tool schemas in MCP or OpenAI format
            **kwargs: Additional options passed to Ollama (temperature, etc.)

        Returns:
            Dict with pipeline-compatible format:
            - {"type": "tool_calls", "calls": [...], "executed": [...]} (if MCP enabled)
            - {"type": "tool_calls", "calls": [...]} (if MCP disabled)
            - {"type": "text", "content": "..."}
        """
        try:
            # Normalize tool schemas to Rosetta/Ollama format
            normalized_tools = self.rosetta.normalize_tool_schema(tools)

            logger.debug(
                f"Executing with {len(normalized_tools)} tools, {len(messages)} messages"
            )

            # Execute via RosettaStoneV2 async method
            # Note: timeout is not supported by ollama.chat(), remove it
            kwargs_clean = {k: v for k, v in kwargs.items() if k != "timeout"}
            result = await self.rosetta.chat_with_tools_async(
                messages=messages, tools=normalized_tools, **kwargs_clean
            )

            # Ensure pipeline-compatible format
            formatted = self._ensure_pipeline_format(result)

            # NEW: Execute MCP tools if enabled and tool call detected
            if (
                self.execute_mcp
                and formatted.get("type") == "tool_calls"
                and formatted.get("calls")
            ):
                executed_results = await self._execute_mcp_tools(formatted["calls"])
                if executed_results:
                    formatted["executed"] = executed_results
                    logger.info(f"Executed {len(executed_results)} MCP tools")

                    # === SECOND PASS: Feed results back to model ===
                    # Build tool result messages
                    tool_messages = []
                    for exec_result in executed_results:
                        tool_name = exec_result.get("tool", "unknown")
                        tool_content = json.dumps(
                            exec_result.get("result", exec_result.get("error", ""))
                        )
                        tool_messages.append(
                            {
                                "role": "tool",
                                "content": tool_content,
                                "tool_call_id": f"call_{tool_name}",
                            }
                        )

                    # Build assistant's tool call intent message
                    tool_names = ", ".join(
                        [call.get("name", "unknown") for call in formatted["calls"]]
                    )
                    assistant_intent = f"I will use tool(s): {tool_names}"

                    # Add assistant's tool call intent + tool results to messages
                    augmented_messages = messages + [
                        {"role": "assistant", "content": assistant_intent},
                        *tool_messages,
                    ]

                    # Second pass - generate final response with tool results
                    # Instead of calling model again (which returns _none), format results directly
                    try:
                        # Format tool results into a nice response
                        response_parts = []
                        for exec_result in executed_results:
                            tool_name = exec_result.get("tool", "unknown")
                            result_data = exec_result.get("result", {})

                            # Format based on result type
                            if isinstance(result_data, dict):
                                # Include actual result data in response
                                if "matches" in result_data:
                                    matches = result_data.get("matches", [])
                                    count = result_data.get("count", 0)
                                    response_parts.append(
                                        f"Found {count} result(s): {matches[:5]}"
                                    )
                                elif "entries" in result_data:
                                    entries = result_data.get("entries", [])
                                    response_parts.append(
                                        f"Returned {len(entries)} items: {entries[:5]}"
                                    )
                                elif "project" in result_data:
                                    # Include mind state data
                                    response_parts.append(
                                        f"Mind state: {result_data.get('project')}, "
                                        f"phase: {result_data.get('phase')}, "
                                        f"tasks: {result_data.get('active_tasks')}"
                                    )
                                else:
                                    # Include relevant fields from result
                                    useful_keys = [
                                        k
                                        for k in result_data.keys()
                                        if k not in ("success", "error")
                                    ]
                                    if useful_keys:
                                        info = ", ".join(
                                            f"{k}: {result_data[k]}"
                                            for k in useful_keys[:3]
                                        )
                                        response_parts.append(f"Result: {info}")
                                    else:
                                        response_parts.append(
                                            f"Tool completed successfully."
                                        )
                            else:
                                response_parts.append(
                                    f"Result: {str(result_data)[:100]}"
                                )

                        final_content = (
                            " ".join(response_parts)
                            if response_parts
                            else "Task completed."
                        )
                        logger.info(
                            "Second pass complete - formatted tool results directly"
                        )
                        return {"type": "text", "content": final_content}
                    except Exception as e:
                        logger.error(
                            f"Second pass failed: {e}, falling back to executed results"
                        )
                        # Fallback: return executed results as formatted output
                        return {
                            "type": "tool_calls",
                            "calls": formatted["calls"],
                            "executed": executed_results,
                        }

            return formatted

        except Exception as e:
            logger.error(f"execute_with_tools failed: {e}")
            return {"type": "text", "content": f"Error: {str(e)}"}

    async def _execute_mcp_tools(self, calls: List[Dict]) -> List[Dict]:
        """Execute MCP tools and return results.

        Args:
            calls: List of tool calls from model

        Returns:
            List of execution results with tool name and result
        """
        if not self.mcp_executor:
            logger.warning("MCP executor not available")
            return []

        executed = []
        for call in calls:
            tool_name = call.get("name", "")
            args = call.get("arguments", {})

            logger.info(f"Executing MCP tool: {tool_name} with args: {args}")

            try:
                # Run in executor to avoid blocking
                result = await asyncio.to_thread(
                    self.mcp_executor.execute, tool_name, args
                )
                executed.append(
                    {"tool": tool_name, "arguments": args, "result": result}
                )
                logger.info(f"MCP tool {tool_name} executed successfully")
            except Exception as e:
                logger.error(f"MCP tool {tool_name} failed: {e}")
                executed.append({"tool": tool_name, "arguments": args, "error": str(e)})

        return executed

    def _ensure_pipeline_format(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure result is in pipeline-compatible format.

        RosettaStoneV2 already returns correct format, but we validate
        and ensure consistency.

        Args:
            result: Result from RosettaStoneV2

        Returns:
            Pipeline-compatible result dict
        """
        if not isinstance(result, dict):
            return {"type": "text", "content": str(result)}

        result_type = result.get("type")

        # NEW: Also filter _none from text responses
        if result_type == "text":
            content = result.get("content", "")
            if "_none" in content:
                # Check if it's just _none JSON or actual content
                if content.strip() == '{"name": "_none", "arguments": {}}':
                    return {"type": "text", "content": "No tool needed."}
                # Otherwise try to extract useful content
                return {"type": "text", "content": content}

        if result_type == "tool_calls":
            calls = result.get("calls", [])
            # Validate and clean tool calls
            valid_calls = []
            for call in calls:
                # Filter out _none - it's not a real tool call, it's the model outputting JSON
                if isinstance(call, dict) and "name" in call:
                    if call["name"] == "_none":
                        # Model didn't want to call any tool - check for content in arguments
                        args = call.get("arguments", {})
                        if isinstance(args, dict) and "content" in args:
                            return {"type": "text", "content": args["content"]}
                        # No content - model just returned _none, convert to text
                        return {"type": "text", "content": "No tool needed."}
                    valid_calls.append(
                        {"name": call["name"], "arguments": call.get("arguments", {})}
                    )

            if valid_calls:
                return {"type": "tool_calls", "calls": valid_calls}
            else:
                return {"type": "text", "content": ""}

        elif result_type == "text":
            return {"type": "text", "content": result.get("content", "")}

        # Fallback for unknown format
        return {"type": "text", "content": str(result)}

    def normalize_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Public method to normalize tool schemas.

        Useful for pre-processing tools before execution.

        Args:
            tools: List of tool schemas in any format

        Returns:
            List of normalized tool schemas
        """
        return self.rosetta.normalize_tool_schema(tools)


# Module-level convenience function
async def execute_with_tools(
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
    model: str = "qwen2.5-coder:7b",
    **kwargs,
) -> Dict[str, Any]:
    """Convenience function for quick tool execution.

    Creates a LocalLLMWrapper and executes in one call.

    Args:
        messages: List of message dicts
        tools: List of tool schemas
        model: Ollama model name
        **kwargs: Additional options

    Returns:
        Pipeline-compatible result dict
    """
    wrapper = LocalLLMWrapper(model=model)
    return await wrapper.execute_with_tools(messages, tools, **kwargs)
