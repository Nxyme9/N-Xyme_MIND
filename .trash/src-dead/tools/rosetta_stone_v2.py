import json
import asyncio
import ollama
from typing import List, Dict, Any, Optional
import re


class RosettaStoneV2:
    """Tool calling wrapper for Ollama models without native tool support.
    Uses LLM-assisted parsing as fallback. Supports both sync and async."""

    def __init__(self, model="qwen2.5-coder:7b"):
        self.model = model

    # ─────────────────────────────────────────────────────────────────
    # Async wrapper for brain.py integration
    # ─────────────────────────────────────────────────────────────────

    async def chat_with_tools_async(
        self, messages: List[Dict], tools: List[Dict], **kwargs
    ) -> Dict:
        """Async wrapper - routes to native Ollama or RosettaStoneV2 based on model capability.

        This is the PRIMARY entry point for brain.py integration.
        Returns: {"type": "tool_calls", "calls": [...]} or {"type": "text", "content": "..."}
        """
        # Try native first (fastest path)
        try:
            result = await self._try_native_tool_call(messages, tools, **kwargs)
            if result:
                return result
        except Exception as e:
            # Native failed, fall through to RosettaStoneV2
            pass

        # Fallback to RosettaStoneV2 (Phase 1: direct, Phase 2: LLM translator)
        return await asyncio.to_thread(self.chat_with_tools, messages, tools, **kwargs)

    async def _try_native_tool_call(
        self, messages: List[Dict], tools: List[Dict], **kwargs
    ) -> Optional[Dict]:
        """Try native Ollama tool calling - fastest path if model supports it."""
        tool_schema = self._convert_to_ollama_tools(tools)
        tool_names = {t.get("function", {}).get("name", "") for t in tools}

        # Use httpx for async (faster than ollama SDK for high throughput)
        import httpx

        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tool_schema,
            "options": kwargs.get("options", {"temperature": 0.1, "num_predict": 256}),
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{kwargs.get('ollama_url', 'http://localhost:11434')}/api/chat",
                json=payload,
            )

            # Parse JSON lines response
            import json

            tool_calls_found = []

            for line in resp.text.strip().split("\n"):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    msg = data.get("message", {})

                    # Check native tool_calls first
                    if "tool_calls" in msg:
                        for tc in msg["tool_calls"]:
                            tool_calls_found.append(
                                {
                                    "name": tc["function"]["name"],
                                    "arguments": tc["function"]["arguments"],
                                }
                            )

                    # Also check content for JSON tool call (qwen workaround)
                    content = msg.get("content", "")
                    if content and not tool_calls_found:
                        try:
                            parsed = json.loads(content)
                            if isinstance(parsed, dict) and "name" in parsed:
                                name = parsed.get("name", "")
                                if name != "_none" and name in tool_names:
                                    tool_calls_found.append(
                                        {
                                            "name": name,
                                            "arguments": parsed.get("arguments", {}),
                                        }
                                    )
                        except (json.JSONDecodeError, AttributeError):
                            pass
                except (json.JSONDecodeError, AttributeError):
                    pass

            if tool_calls_found:
                return {"type": "tool_calls", "calls": tool_calls_found}

        return None

    def _convert_to_ollama_tools(self, tools: List[Dict]) -> List[Dict]:
        """Convert tool schemas to Ollama format."""
        ollama_tools = []
        for t in tools:
            func = t.get("function", t)
            ollama_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": func.get("name", "unknown"),
                        "description": func.get("description", ""),
                        "parameters": func.get(
                            "parameters", {"type": "object", "properties": {}}
                        ),
                    },
                }
            )
        return ollama_tools

    # ─────────────────────────────────────────────────────────────────
    # Output format conversion for AgentLoop
    # ─────────────────────────────────────────────────────────────────

    def to_agentloop_format(self, rosetta_result: Dict) -> Dict:
        """Convert RosettaStoneV2 output to AgentLoop expected format.

        Rosetta: {"type": "tool_calls", "calls": [{"name": "X", "arguments": {...}}]}
        AgentLoop: {"func": "X", "params": {...}}
        """
        if rosetta_result.get("type") != "tool_calls":
            return {"func": None, "params": {}}

        calls = rosetta_result.get("calls", [])
        if not calls:
            return {"func": None, "params": {}}

        call = calls[0]  # Take first tool call
        return {"func": call.get("name", ""), "params": call.get("arguments", {})}

    # ─────────────────────────────────────────────────────────────────
    # Tool schema normalization (for brain.py)
    # ─────────────────────────────────────────────────────────────────

    def normalize_tool_schema(self, tool_schemas: List[Dict]) -> List[Dict]:
        """Normalize ToolSchema from ToolRegistry to OpenAI/Ollama format."""
        normalized = []
        for ts in tool_schemas:
            if isinstance(ts, dict):
                # Already in dict format
                if "function" in ts:
                    normalized.append(ts)
                else:
                    normalized.append({"function": ts})
            else:
                # Object with attributes - convert
                normalized.append(
                    {
                        "function": {
                            "name": getattr(ts, "name", "unknown"),
                            "description": getattr(ts, "description", ""),
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    p.name: {
                                        "type": p.type,
                                        "description": p.description,
                                    }
                                    for p in getattr(ts, "params", [])
                                },
                                "required": [
                                    p.name
                                    for p in getattr(ts, "params", [])
                                    if getattr(p, "required", False)
                                ],
                            },
                        }
                    }
                )
        return normalized

    def chat_with_tools(self, messages, tools, **kwargs):
        tool_desc = self._format_tools(tools)
        tool_names = [t.get("function", t).get("name", "") for t in tools]

        system = (
            "You are a tool executor. You MUST use tools when appropriate. "
            'Respond with ONLY JSON: {"name": "tool_name", "arguments": {"param": "value"}}. '
            'If NO tool applies, respond: {"name": "_none", "arguments": {}}. '
            "No markdown. No text. Just JSON."
        )
        full_messages = [
            {"role": "system", "content": system + chr(10) + chr(10) + tool_desc}
        ] + messages
        resp = ollama.chat(
            model=self.model, messages=full_messages, format="json", **kwargs
        )
        content = resp.message.content.strip()

        parsed = self._try_parse(content)
        if parsed:
            name = parsed.get("name", "")
            if name == "_none":
                return {"type": "text", "content": content}
            if name in tool_names:
                args = parsed.get("arguments", parsed.get("parameters", {}))
                if not isinstance(args, dict):
                    args = {}
                return {
                    "type": "tool_calls",
                    "calls": [{"name": name, "arguments": args}],
                }

        translator_system = (
            "Extract tool calls from model responses. "
            'Respond with ONLY JSON: {"name": "tool_name", "arguments": {"param": "value"}}. '
            f"Available tools: {tool_names}. "
            'If no tool call, return {"name": "_none", "arguments": {}}.'
        )
        translator_messages = [
            {"role": "system", "content": translator_system},
            {"role": "user", "content": "Model response: " + content},
        ]
        translator_resp = ollama.chat(
            model=self.model, messages=translator_messages, format="json", **kwargs
        )
        translator_content = translator_resp.message.content.strip()

        parsed = self._try_parse(translator_content)
        if parsed:
            name = parsed.get("name", "")
            if name == "_none":
                return {"type": "text", "content": content}
            if name in tool_names:
                args = parsed.get("arguments", parsed.get("parameters", {}))
                if not isinstance(args, dict):
                    args = {}
                return {
                    "type": "tool_calls",
                    "calls": [{"name": name, "arguments": args}],
                }

        return {"type": "text", "content": content}

    TOOL_CALL_OPTIONS = {
        "temperature": 0.0,
        "top_p": 0.1,
        "num_predict": 128,
        "num_ctx": 2048,
        "repeat_penalty": 1.0,
    }

    FAST_OPTIONS = {
        "temperature": 0.0,
        "num_predict": 64,
        "num_ctx": 1024,
    }

    def _try_parse(self, content):
        try:
            return json.loads(content)
        except (json.JSONDecodeError, ValueError):
            pass
        cleaned = content.replace("", "").strip()
        try:
            return json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            pass
        return None

    def _format_tools(self, tools):
        lines = []
        for t in tools:
            func = t.get("function", t)
            name = func.get("name", "?")
            desc = func.get("description", "")
            line = f"- {name}: {desc}"
            params = func.get("parameters", {}).get("properties", {})
            if params:
                plist = []
                for pn, pi in params.items():
                    pt = pi.get("type", "any")
                    pd = pi.get("description", "")
                    plist.append(f"{pn}({pt}): {pd}")
                line += " | " + ", ".join(plist)
            lines.append(line)
        return chr(10).join(lines)


# Singleton instance
ROSETTA = RosettaStoneV2()
