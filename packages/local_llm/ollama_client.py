#!/usr/bin/env python3
"""LocalLLM - Fresh Ollama client with native tool calling support."""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

logger = logging.getLogger("local_llm")


@dataclass
class ToolCall:
    """Represents a tool call from the model."""

    name: str
    arguments: Dict[str, Any]


@dataclass
class ChatResponse:
    """Structured chat response from local LLM."""

    type: str  # "text" or "tool_calls"
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None


class LocalLLM:
    """Direct Ollama API client with tool calling support.

    Provides:
    - chat() - simple chat without tools
    - chat_with_tools() - chat with tool definitions + execution
    - execute_with_tools() - full 2-pass: call model → execute → return results
    """

    DEFAULT_MODEL = "qwen2.5-coder:7b"
    OLLAMA_BASE_URL = "http://localhost:11434"

    # Default generation parameters (optimized for code/tool calling)
    DEFAULT_PARAMS = {
        "temperature": 0.3,  # Lower for deterministic tool selection
        "top_p": 0.95,  # Nucleus sampling
        "top_k": 40,  # Limit vocabulary
        "num_ctx": 131072,  # Context window size (128k for large codebases)
        "num_gpu": 35,  # GPU layers for GGUF models
        "repeat_penalty": 1.1,  # Reduce token repetition
        "seed": 42,  # Reproducibility
        "num_predict": 2048,  # Max tokens to generate
        "stream": False,  # Easier parsing
        "cache_type": "q4_0",  # KV cache quantization
    }

    # Override params for general chat (higher creativity)
    CHAT_PARAMS = {
        "temperature": 0.7,
        "top_p": 0.9,
    }

    # Optimized system prompt for tool calling
    SYSTEM_PROMPT = """You are an expert AI coding assistant with tool calling capabilities.

When asked to perform a task that requires external tools:
1. Analyze the request to identify required tool(s)
2. Call ONLY one tool at a time using the exact JSON format below
3. Wait for the result before continuing
4. Synthesize the final answer from tool results

Tool calling format (MUST follow exactly):
{
  "name": "tool_name",
  "arguments": {"arg1": "value1", "arg2": "value2"}
}

Example:
User: "What is 5 + 3?"
You: {"name": "add", "arguments": {"a": 5, "b": 3}}

Always respond in JSON format when calling tools. If no tool is needed, respond directly."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        base_url: str = OLLAMA_BASE_URL,
        timeout: int = 120,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session_id = f"llm-{int(time.time())}"

        logger.info(f"LocalLLM initialized with model={model}, url={base_url}")

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Simple chat without tools.

        Args:
            messages: List of {"role": "user"|"assistant"|"system", "content": "..."}
            temperature: Sampling temperature (uses DEFAULT_PARAMS if not set)

        Returns:
            {"role": "assistant", "content": "..."}
        """
        import requests

        url = f"{self.base_url}/v1/chat/completions"

        # Use DEFAULT_PARAMS merged with chat-specific overrides, then kwargs
        params = {**self.DEFAULT_PARAMS, **self.CHAT_PARAMS}
        if temperature is not None:
            params["temperature"] = temperature

        payload = {
            "model": self.model,
            "messages": messages,
        }
        payload.update(params)
        payload.update({k: v for k, v in kwargs.items() if k not in ("timeout",)})

        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()

            return data["choices"][0]["message"]
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            return {"role": "assistant", "content": f"Error: {e}"}

    def chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        temperature: Optional[float] = None,
        **kwargs,
    ) -> ChatResponse:
        """Chat with tool definitions - model decides whether to call tools.

        Args:
            messages: Chat history
            tools: Tool definitions in OpenAI format
            temperature: Lower temp = more deterministic tool selection (uses DEFAULT_PARAMS if not set)

        Returns:
            ChatResponse with type="text" or type="tool_calls"
        """
        import requests

        url = f"{self.base_url}/v1/chat/completions"

        # Use DEFAULT_PARAMS with tool calling focus
        params = {**self.DEFAULT_PARAMS}
        if temperature is not None:
            params["temperature"] = temperature

        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
        }
        payload.update(params)
        payload.update({k: v for k, v in kwargs.items() if k not in ("timeout",)})

        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()

            msg = data["choices"][0]["message"]

            # Check for tool calls (standard OpenAI format)
            if msg.get("tool_calls"):
                tool_calls = []
                for tc in msg["tool_calls"]:
                    # Parse the arguments - may be string or dict
                    args = tc.get("function", {}).get("arguments", {})
                    if isinstance(args, str):
                        args = json.loads(args)

                    tool_calls.append(
                        ToolCall(name=tc["function"]["name"], arguments=args)
                    )

                return ChatResponse(type="tool_calls", tool_calls=tool_calls)

            # Check for tool call in content (Ollama returns JSON as text)
            content = msg.get("content", "") or ""
            if content.startswith("{") and '"name"' in content:
                try:
                    # Try parsing as tool call JSON
                    parsed = json.loads(content)
                    if "name" in parsed and "arguments" in parsed:
                        tool_call = ToolCall(
                            name=parsed["name"],
                            arguments=parsed.get("arguments", {}),
                        )
                        return ChatResponse(type="tool_calls", tool_calls=[tool_call])
                except json.JSONDecodeError:
                    pass

            # Text response
            return ChatResponse(type="text", content=content)

        except Exception as e:
            logger.error(f"chat_with_tools failed: {e}")
            return ChatResponse(type="text", content=f"Error: {e}")


# Module-level convenience function
def create_llm(model: Optional[str] = None, **kwargs) -> LocalLLM:
    """Create a LocalLLM instance."""
    return LocalLLM(model=model or LocalLLM.DEFAULT_MODEL, **kwargs)


if __name__ == "__main__":
    # Quick test
    llm = LocalLLM()

    # Test 1: Simple chat
    print("=== Test 1: Simple Chat ===")
    result = llm.chat([{"role": "user", "content": "Hello!"}])
    print(f"Result: {result}")

    # Test 2: Tool calling
    print("\n=== Test 2: Tool Calling ===")
    tools = [
        {
            "type": "function",
            "function": {
                "name": "add",
                "description": "Add two numbers",
                "parameters": {
                    "type": "object",
                    "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                    "required": ["a", "b"],
                },
            },
        }
    ]

    response = llm.chat_with_tools(
        [{"role": "user", "content": "What is 5 + 3?"}], tools=tools
    )
    print(f"Type: {response.type}")
    if response.tool_calls:
        for tc in response.tool_calls:
            print(f"  Tool: {tc.name}, Args: {tc.arguments}")
    else:
        print(f"  Content: {response.content}")
