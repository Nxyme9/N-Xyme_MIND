"""Local Model Complexity Analysis — Uses Ollama local models for task complexity analysis with circuit breaker."""

import asyncio
import json
import logging
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger("local-model-analysis")


@dataclass
class LocalModelAnalysis:
    """Result from local model complexity analysis."""

    level: int
    confidence: float
    reason: str
    model_used: str
    latency_ms: float
    fallback_to_keyword: bool = False


class LocalModelAnalyzer:
    """Analyzes task complexity using local Ollama models with circuit breaker."""

    COMPLEXITY_PROMPT = """Analyze the following task and determine its complexity level on a scale of 1-5:

Level 1 (Trivial): Single-line typo fixes, version bumps, bracket fixes
Level 2 (Simple): Single-file bug fixes, config changes, simple feature additions
Level 3 (Moderate): Multi-file changes, refactoring, middleware, auth, endpoints
Level 4 (Complex): New features, system design, new modules, architecture decisions
Level 5 (Architect): Major refactoring, migration, redesign entire systems, overhaul

Task: {task_description}

Current keyword-based level: {keyword_level}

Respond with ONLY a JSON object in this exact format:
{{"level": <1-5>, "confidence": <0.0-1.0>, "reason": "<brief explanation>"}}

Do not include any other text. Only output the JSON object."""

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "qwen2.5-coder:7b",
        timeout_ms: int = 5000,
        circuit_breaker_threshold: int = 2,
        circuit_breaker_timeout: float = 60.0,
    ):
        self._ollama_url = ollama_url
        self._model = model
        self._timeout_ms = timeout_ms

        # Circuit breaker state
        self._circuit_breaker_threshold = circuit_breaker_threshold
        self._circuit_breaker_timeout = circuit_breaker_timeout
        self._consecutive_failures = 0
        self._circuit_open_time: Optional[float] = None
        self._circuit_state = "closed"  # closed, open, half-open

    async def analyze_complexity(
        self, task_description: str, keyword_level: int = 2
    ) -> LocalModelAnalysis:
        """Analyze task complexity using local model with circuit breaker."""
        start_time = time.time()

        # Check circuit breaker state
        if self._circuit_state == "open":
            if (
                self._circuit_open_time
                and (time.time() - self._circuit_open_time)
                > self._circuit_breaker_timeout
            ):
                logger.info("Circuit breaker: transitioning to half-open")
                self._circuit_state = "half-open"
            else:
                return LocalModelAnalysis(
                    level=keyword_level,
                    confidence=0.3,
                    reason="Circuit breaker open, falling back to keyword level",
                    model_used=self._model,
                    latency_ms=(time.time() - start_time) * 1000,
                    fallback_to_keyword=True,
                )

        try:
            if not await self._check_ollama_available():
                self._record_failure()
                return LocalModelAnalysis(
                    level=keyword_level,
                    confidence=0.3,
                    reason="Ollama not available, falling back to keyword level",
                    model_used=self._model,
                    latency_ms=(time.time() - start_time) * 1000,
                    fallback_to_keyword=True,
                )

            prompt = self.COMPLEXITY_PROMPT.format(
                task_description=task_description, keyword_level=keyword_level
            )

            result = await self._call_ollama(prompt)
            latency_ms = (time.time() - start_time) * 1000

            if result:
                self._record_success()
                return LocalModelAnalysis(
                    level=result.get("level", keyword_level),
                    confidence=result.get("confidence", 0.5),
                    reason=result.get("reason", "Local model analysis"),
                    model_used=self._model,
                    latency_ms=latency_ms,
                )

            self._record_failure()
            return LocalModelAnalysis(
                level=keyword_level,
                confidence=0.3,
                reason="Local model returned invalid response",
                model_used=self._model,
                latency_ms=latency_ms,
                fallback_to_keyword=True,
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._record_failure()
            logger.warning(f"Local model analysis failed: {e}")
            return LocalModelAnalysis(
                level=keyword_level,
                confidence=0.3,
                reason=f"Local model analysis failed: {e}",
                model_used=self._model,
                latency_ms=latency_ms,
                fallback_to_keyword=True,
            )

    async def _check_ollama_available(self) -> bool:
        """Check if Ollama server is available."""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self._ollama_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=2),
                ) as response:
                    return response.status == 200
        except ImportError:
            try:
                import urllib.request

                req = urllib.request.Request(f"{self._ollama_url}/api/tags")
                with urllib.request.urlopen(req, timeout=2) as response:
                    return response.status == 200
            except Exception:
                return False
        except Exception:
            return False

    async def _call_ollama(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Call Ollama API with timeout."""
        try:
            import aiohttp

            payload = {"model": self._model, "prompt": prompt, "stream": False}
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self._ollama_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self._timeout_ms / 1000),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        response_text = data.get("response", "")
                        return self._parse_json_response(response_text)
                    return None
        except ImportError:
            try:
                import urllib.request

                payload = json.dumps(
                    {"model": self._model, "prompt": prompt, "stream": False}
                ).encode("utf-8")
                req = urllib.request.Request(
                    f"{self._ollama_url}/api/generate",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(
                    req, timeout=self._timeout_ms / 1000
                ) as response:
                    data = json.loads(response.read().decode("utf-8"))
                    response_text = data.get("response", "")
                    return self._parse_json_response(response_text)
            except Exception as e:
                logger.warning(f"urllib Ollama call failed: {e}")
                return None
        except asyncio.TimeoutError:
            logger.warning(f"Ollama call timed out after {self._timeout_ms}ms")
            return None
        except Exception as e:
            logger.warning(f"Ollama call failed: {e}")
            return None

    def _parse_json_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from model response."""
        try:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response_text[start:end]
                return json.loads(json_str)
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from response: {e}")
            return None

    def _record_success(self) -> None:
        """Record a successful Ollama call."""
        if self._circuit_state == "half-open":
            logger.info("Circuit breaker: transitioning to closed")
            self._circuit_state = "closed"
            self._consecutive_failures = 0
            self._circuit_open_time = None

    def _record_failure(self) -> None:
        """Record a failed Ollama call."""
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._circuit_breaker_threshold:
            if self._circuit_state != "open":
                logger.warning(
                    f"Circuit breaker: opening after {self._consecutive_failures} failures"
                )
                self._circuit_state = "open"
                self._circuit_open_time = time.time()


_local_analyzer: Optional[LocalModelAnalyzer] = None


def get_local_analyzer() -> LocalModelAnalyzer:
    """Get or create the global local model analyzer."""
    global _local_analyzer
    if _local_analyzer is None:
        _local_analyzer = LocalModelAnalyzer()
    return _local_analyzer


async def get_complexity_with_local_model(
    task_description: str, keyword_level: int = 2
) -> LocalModelAnalysis:
    """Combine keyword scoring with local model analysis for L3+ tasks."""
    if keyword_level < 3:
        return LocalModelAnalysis(
            level=keyword_level,
            confidence=0.8,
            reason="Keyword level below L3, using keyword score directly",
            model_used="",
            latency_ms=0,
        )

    analyzer = get_local_analyzer()
    return await analyzer.analyze_complexity(task_description, keyword_level)


if __name__ == "__main__":
    import sys

    async def demo():
        analyzer = get_local_analyzer()

        test_tasks = [
            "fix typo in variable name",
            "implement JWT authentication middleware",
            "redesign entire architecture",
        ]

        for task in test_tasks:
            print(f"\nAnalyzing: {task}")
            result = await analyzer.analyze_complexity(task, keyword_level=2)
            print(f"  Level: {result.level}, Confidence: {result.confidence}")
            print(f"  Reason: {result.reason}")
            print(f"  Model: {result.model_used}, Latency: {result.latency_ms:.0f}ms")
            print(f"  Circuit state: {analyzer._circuit_state}")

    asyncio.run(demo())
