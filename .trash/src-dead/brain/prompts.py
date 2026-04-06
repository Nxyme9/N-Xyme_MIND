#!/usr/bin/env python3
"""Optimized system prompts for tool-use scenarios.

This module provides prompt templates that improve model responses after tool execution.
Addresses the "prompt engineering" issue in the masterplan.
"""

from typing import Any, Dict, List, Optional


# =============================================================================
# Base System Prompts
# =============================================================================

TOOL_USE_SYSTEM_PROMPT: str = """You are an AI assistant with access to tools.

AVAILABLE TOOLS:
{tools_description}

INSTRUCTIONS:
1. When you need to use a tool, respond with a tool call in this format:
   {{"name": "tool_name", "arguments": {{"arg1": "value1"}}}}
2. After receiving tool results, provide a natural language response to the user
3. Don't just repeat the tool output - summarize and explain the results

EXAMPLES:
User: "List files in src directory"
You: {{"name": "list_directory", "arguments": {{"path": "src"}}}}
[Tool Result: {{"entries": ["a.py", "b.py"]}}]
You: "The src directory contains 2 files: a.py and b.py"

Remember: After tool execution, ALWAYS provide a helpful response, not another tool call.
"""


# =============================================================================
# Model-Specific Prompts
# =============================================================================

LLAMA_TOOL_PROMPT: str = """You have access to tools for performing various tasks.

Available tools:
{tools_description}

When you need to use a tool, provide your response in this JSON format:
{{
  "name": "tool_name",
  "arguments": {{
    "arg1": "value1",
    "arg2": "value2"
  }}
}}

IMPORTANT:
- Always output valid JSON for tool calls
- After tool execution, summarize the results in plain English
- Don't simply echo the raw output - explain what it means
- If the result is an error, explain the error and suggest next steps

Example:
User: Check the current directory
You: {{"name": "filesystem_list_directory", "arguments": {{"path": "."}}}}
[Tool Result shows directory contents]
You: I can see you're in the project root. The directory contains several files including...
"""


QWEN_TOOL_PROMPT: str = """You are an AI assistant capable of using tools to help users.

TOOLS AVAILABLE:
{tools_description}

To call a tool, use this JSON format:
{{
  "name": "tool_name",
  "arguments": {{"param": "value"}}
}}

GUIDELINES:
- Analyze the user's request and determine if a tool is needed
- Output ONLY the JSON for tool calls, nothing else
- After receiving results, provide a helpful explanation
- Translate technical output into human-readable responses

Example workflow:
User: Find Python files in src
You: {{"name": "filesystem_search_files", "arguments": {{"path": "src", "pattern": "*.py"}}}}
[Tool returns file list]
You: Found 5 Python files in the src directory: main.py, utils.py, handlers.py, models.py, and config.py
"""


# =============================================================================
# Tool Result Summary Prompt
# =============================================================================

TOOL_RESULT_SUMMARY_PROMPT: str = """You have received the following result from a tool:

{tool_result}

CONTEXT:
- Tool name: {tool_name}
- Original user request: {user_request}

TASK:
Summarize this result in a helpful way that:
1. Explains what the data means
2. Highlights any important details or patterns
3. Connects back to what the user asked for
4. Uses plain language, not technical jargon

Remember: The user cannot see the raw tool output - they only see your response.
"""


# =============================================================================
# Error Recovery Prompt
# =============================================================================

ERROR_RECOVERY_PROMPT: str = """A tool execution failed with the following error:

ERROR: {error_message}
TOOL: {tool_name}
ARGUMENTS: {tool_arguments}

INSTRUCTIONS:
1. Don't blame the user or make excuses
2. Explain what went wrong in simple terms
3. Suggest a specific alternative approach or fix
4. If the error is recoverable, offer to try again with corrected parameters

Example of good error handling:
Instead of: "The tool failed because you gave wrong input"
Say: "The file wasn't found. This could mean the path is incorrect or the file was deleted. Would you like me to check if the file exists, or would you prefer to specify a different path?"

Remember: Errors are opportunities to be helpful, not to give up.
"""


# =============================================================================
# Helper Functions
# =============================================================================

def get_tool_system_prompt(tools: List[Dict[str, Any]], model_name: Optional[str] = None) -> str:
    """Generate system prompt with tool list.

    Args:
        tools: List of tool definitions with 'name' and 'description' keys.
        model_name: Optional model name for model-specific formatting.

    Returns:
        Formatted system prompt string with tool descriptions.

    Example:
        >>> tools = [
        ...     {"name": "read", "description": "Read a file from the filesystem"},
        ...     {"name": "write", "description": "Write content to a file"}
        ... ]
        >>> prompt = get_tool_system_prompt(tools)
    """
    if not tools:
        tools_description = "No tools available."
    else:
        tool_lines: List[str] = []
        for tool in tools:
            name = tool.get("name", "unknown")
            desc: str = tool.get("description", "No description")
            tool_lines.append(f"- {name}: {desc}")
        tools_description = "\n".join(tool_lines)

    # Use model-specific prompt if available
    if model_name:
        return get_model_prompt(model_name).format(tools_description=tools_description)

    return TOOL_USE_SYSTEM_PROMPT.format(tools_description=tools_description)


def get_model_prompt(model_name: str) -> str:
    """Get model-specific tool-use prompt.

    Args:
        model_name: Model identifier (e.g., 'llama3.2:3b', 'qwen2.5-coder:7b')

    Returns:
        Model-appropriate system prompt template.

    Example:
        >>> prompt = get_model_prompt("llama3.2:3b")
        >>> print(prompt[:50])  # Shows llama-specific format
    """
    model_lower = model_name.lower()

    if "llama" in model_lower:
        return LLAMA_TOOL_PROMPT
    elif "qwen" in model_lower:
        return QWEN_TOOL_PROMPT

    # Default to base prompt for unknown models
    return TOOL_USE_SYSTEM_PROMPT


def summarize_tool_result(
    tool_name: str,
    tool_result: str,
    user_request: str
) -> str:
    """Generate a prompt for summarizing tool results.

    Args:
        tool_name: Name of the tool that was executed.
        tool_result: Raw result from the tool.
        user_request: Original request from the user.

    Returns:
        Formatted prompt for generating a summary.

    Example:
        >>> prompt = summarize_tool_result(
        ...     "read",
        ...     '{"content": "file contents"}',
        ...     "Show me the config file"
        ... )
    """
    return TOOL_RESULT_SUMMARY_PROMPT.format(
        tool_name=tool_name,
        tool_result=tool_result,
        user_request=user_request
    )


def generate_error_recovery_prompt(
    tool_name: str,
    error_message: str,
    tool_arguments: Optional[Dict[str, Any]] = None
) -> str:
    """Generate a prompt for handling tool errors.

    Args:
        tool_name: Name of the tool that failed.
        error_message: Error message from the tool execution.
        tool_arguments: Optional dict of arguments that were passed.

    Returns:
        Formatted prompt for error recovery.

    Example:
        >>> prompt = generate_error_recovery_prompt(
        ...     "read",
        ...     "File not found: /path/to/file.txt",
        ...     {"path": "/path/to/file.txt"}
        ... )
    """
    args_str = str(tool_arguments) if tool_arguments else "None"

    return ERROR_RECOVERY_PROMPT.format(
        tool_name=tool_name,
        error_message=error_message,
        tool_arguments=args_str
    )


# =============================================================================
# Convenience Exports
# =============================================================================

__all__ = [
    "TOOL_USE_SYSTEM_PROMPT",
    "LLAMA_TOOL_PROMPT",
    "QWEN_TOOL_PROMPT",
    "TOOL_RESULT_SUMMARY_PROMPT",
    "ERROR_RECOVERY_PROMPT",
    "get_tool_system_prompt",
    "get_model_prompt",
    "summarize_tool_result",
    "generate_error_recovery_prompt",
]