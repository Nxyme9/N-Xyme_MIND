"""
Hybrid Agent Loop — Cloud Reasoning + Rosetta Tool Execution
============================================================

Architecture:
    User Input
        ↓
    ┌─────────────────────────────┐
    │  CLOUD MODEL               │
    │  (minimax-m2.5-free)       │
    │  Reasoning, Planning        │
    └─────────────────────────────┘
        ↓ (tool call detected)
    ┌─────────────────────────────┐
    │  ROSETTA (GGUF)            │
    │  Tool execution ONLY         │
    │  Fast, local, [TOOL_CALL]   │
    └─────────────────────────────┘
        ↓
    ┌─────────────────────────────┐
    │  CLOUD MODEL               │
    │  Final response synthesis   │
    └─────────────────────────────┘

Usage:
    hybrid = HybridAgentLoop()
    result = await hybrid.run(
        user_message="Search for files and read the README",
        cloud_model="opencode/minimax-m2.5-free",
        rosetta_url="http://localhost:9000/v1"
    )
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("hybrid_agent")

TOOL_CALL_PATTERN = re.compile(
    r'\[TOOL_CALL\]\{tool\s*=>\s*"([^"]+)"(?:,\s*args\s*=>\s*\{(.+?)\})?\}\[/TOOL_CALL\]',
    re.DOTALL,
)


@dataclass
class HybridConfig:
    """Configuration for hybrid agent loop."""

    # Cloud settings - use OpenRouter API directly
    cloud_provider: str = "openrouter"
    cloud_model: str = "qwen/qwen3-coder:free"
    cloud_api_base: str = "https://openrouter.ai/api/v1"  # Correct OpenRouter endpoint
    cloud_api_key: str = ""

    # Rosetta (local GGUF) settings
    rosetta_url: str = "http://localhost:8080/v1"  # Default GGUF port
    rosetta_model: str = "local-model"
    rosetta_api_key: str = "not-needed"

    max_iterations: int = 10
    tool_call_timeout: float = 30.0
    reasoning_timeout: float = 120.0

    @classmethod
    def from_env(cls) -> "HybridConfig":
        import os

        return cls(
            cloud_api_key=os.getenv("OPENROUTER_API_KEY", ""),
            rosetta_url=os.getenv("ROSETTA_URL", "http://localhost:8080/v1"),
            rosetta_model=os.getenv("ROSETTA_MODEL", "local-model"),
        )


class RosettaToolExecutor:
    """Execute tools using Rosetta's [TOOL_CALL] format."""

    def __init__(self, base_url: str, api_key: str = "not-needed"):
        self.base_url = base_url
        self.api_key = api_key

    async def execute(self, tool_name: str, args: dict) -> dict:
        """Execute a tool via Rosetta."""
        import aiohttp

        prompt = f"""You are a tool executor. Execute this tool call:

[TOOL_CALL]{{tool => "{tool_name}", args => {json.dumps(args)}}}[/TOOL_CALL]

Execute the tool and return the result in this format:
RESULT: <your execution result>
"""

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": "rosetta-v5-q8_0",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 512,
            "temperature": 0.1,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        result = data["choices"][0]["message"]["content"]
                        return {"success": True, "result": result}
                    else:
                        error = await resp.text()
                        return {
                            "success": False,
                            "error": f"HTTP {resp.status}: {error}",
                        }
        except Exception as e:
            return {"success": False, "error": str(e)}


@dataclass
class HybridResult:
    """Result from hybrid agent loop."""

    success: bool
    answer: str
    tool_calls: list = field(default_factory=list)
    iterations: int = 0
    latency_ms: float = 0.0
    model_used: str = "cloud"  # "cloud" or "rosetta"

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "answer": self.answer,
            "tool_calls": self.tool_calls,
            "iterations": self.iterations,
            "latency_ms": self.latency_ms,
            "model_used": self.model_used,
        }


class HybridAgentLoop:
    """
    Hybrid agent loop that uses:
    - Cloud model for reasoning and final response
    - Rosetta for tool execution

    Flow:
        1. Send task to cloud model
        2. If response contains [TOOL_CALL], execute via Rosetta
        3. Loop back to cloud with tool results
        4. Final response from cloud
    """

    def __init__(self, config: Optional[HybridConfig] = None):
        self.config = config or HybridConfig.from_env()
        self.tool_executor = RosettaToolExecutor(
            base_url=self.config.rosetta_url, api_key=self.config.rosetta_api_key
        )

    async def run(self, user_message: str) -> HybridResult:
        """
        Run hybrid agent loop.

        Args:
            user_message: The user's request

        Returns:
            HybridResult with answer, tool calls, and metadata
        """
        start_time = time.time()
        messages = [{"role": "user", "content": user_message}]
        tool_calls_history = []
        iteration = 0

        while iteration < self.config.max_iterations:
            iteration += 1
            logger.info(f"Iteration {iteration}: Calling cloud model")

            response = await self._call_cloud(messages)
            messages.append({"role": "assistant", "content": response})

            tool_calls = self._extract_tool_calls(response)

            if not tool_calls:
                latency = (time.time() - start_time) * 1000
                return HybridResult(
                    success=True,
                    answer=response,
                    tool_calls=tool_calls_history,
                    iterations=iteration,
                    latency_ms=latency,
                    model_used="cloud",
                )

            logger.info(
                f"Detected {len(tool_calls)} tool call(s) - executing via Rosetta"
            )
            for tc in tool_calls:
                tool_calls_history.append(tc)
                result = await self.tool_executor.execute(tc["name"], tc["args"])
                tool_result = f"[TOOL_CALL_RESULT] {tc['name']}: {result.get('result', result.get('error', 'Unknown error'))} [/TOOL_CALL_RESULT]"
                messages.append({"role": "user", "content": tool_result})

        latency = (time.time() - start_time) * 1000
        return HybridResult(
            success=False,
            answer="Max iterations reached",
            tool_calls=tool_calls_history,
            iterations=iteration,
            latency_ms=latency,
            model_used="cloud",
        )

    async def _call_cloud(self, messages: list) -> str:
        """Call cloud model API."""
        import aiohttp

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.cloud_api_key}",
            "HTTP-Referer": "https://n-xyme.github.io",
            "X-Title": "N-Xyme-MIND",
        }

        payload = {
            "model": self.config.cloud_model,
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.7,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config.cloud_api_base}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.reasoning_timeout),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        error = await resp.text()
                        raise Exception(f"Cloud API error: {resp.status} - {error}")
        except asyncio.TimeoutError:
            raise Exception("Cloud model request timed out")
        except Exception as e:
            logger.error(f"Cloud API call failed: {e}")
            raise

    def _extract_tool_calls(self, text: str) -> list:
        """Extract [TOOL_CALL] patterns from text."""
        matches = TOOL_CALL_PATTERN.findall(text)
        tool_calls = []

        for match in matches:
            tool_name = match[0]
            args_str = match[1] if len(match) > 1 else "{}"

            # Parse args string to dict
            try:
                args = self._parse_args(args_str)
            except Exception:
                args = {}

            tool_calls.append(
                {
                    "name": tool_name,
                    "args": args,
                    "raw": f'[TOOL_CALL]{{tool => "{tool_name}", args => {{{args_str}}}}}[/TOOL_CALL]',
                }
            )

        return tool_calls

    def _parse_args(self, args_str: str) -> dict:
        args = {}
        patterns = [
            r'--(\w+)\s+"([^"]+)"',
            r"--(\w+)\s+(\S+)",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, args_str):
                key = match.group(1)
                value = match.group(2).strip('"')
                args[key] = value

        return args


if __name__ == "__main__":
    config = HybridConfig.from_env()
    hybrid = HybridAgentLoop(config)
    result = asyncio.run(hybrid.run("Use math_add to calculate 2 + 2"))
    print(json.dumps(result.to_dict(), indent=2))
