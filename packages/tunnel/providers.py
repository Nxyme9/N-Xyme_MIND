"""
Tunnel Provider Interface - Pluggable provider abstraction
=========================================================

Abstract base class for tunnel providers. Enables:
- Easy addition of new providers
- Consistent interface across providers
- Provider-specific optimization

Usage:
    from packages.tunnel.providers import ProviderInterface, OpenCodeZenProvider

    # Use a provider
    provider = OpenCodeZenProvider()
    response = await provider.chat(model, messages)
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, AsyncIterator

logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    """Configuration for a provider."""

    name: str
    enabled: bool = True
    max_concurrent: int = 10
    rate_limit_rpm: int = 60
    token_limit_tpm: int = 100000
    timeout_seconds: float = 30.0
    retry_on_429: bool = True
    max_retries: int = 3


@dataclass
class ChatMessage:
    """Chat message structure."""

    role: str
    content: str


@dataclass
class ChatResponse:
    """Response from a provider."""

    success: bool
    content: str = ""
    model: str = ""
    tokens: int = 0
    latency_ms: float = 0.0
    error: Optional[str] = None
    raw_response: Dict = field(default_factory=dict)


class ProviderInterface(ABC):
    """
    Abstract base class for tunnel providers.

    All providers must implement this interface.
    """

    def __init__(self, config: Optional[ProviderConfig] = None):
        self.config = config or ProviderConfig(name=self.__class__.__name__)
        self._initialized = False
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0,
            "avg_latency_ms": 0.0,
        }

    @abstractmethod
    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        **kwargs,
    ) -> ChatResponse:
        """
        Send a chat request to the provider.

        Args:
            model: Model identifier
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional provider-specific parameters

        Returns:
            ChatResponse with success status and response content
        """
        pass

    @abstractmethod
    async def stream_chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        **kwargs,
    ) -> AsyncIterator[str]:
        """
        Stream chat response from the provider.

        Args:
            model: Model identifier
            messages: List of message dicts
            **kwargs: Additional parameters

        Yields:
            Text chunks as they arrive
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if provider is healthy.

        Returns:
            True if provider is reachable and operational
        """
        pass

    @abstractmethod
    async def initialize(self):
        """Initialize provider resources."""
        self._initialized = True

    @abstractmethod
    async def cleanup(self):
        """Cleanup provider resources."""
        self._initialized = False

    def get_stats(self) -> Dict[str, Any]:
        """Get provider statistics."""
        return {
            "provider": self.config.name,
            "enabled": self.config.enabled,
            "initialized": self._initialized,
            **self._stats,
        }

    def record_success(self, tokens: int, latency_ms: float):
        """Record successful request."""
        self._stats["total_requests"] += 1
        self._stats["successful_requests"] += 1
        self._stats["total_tokens"] += tokens

        # Update avg latency
        total = self._stats["successful_requests"]
        current_avg = self._stats["avg_latency_ms"]
        self._stats["avg_latency_ms"] = (current_avg * (total - 1) + latency_ms) / total

    def record_failure(self):
        """Record failed request."""
        self._stats["total_requests"] += 1
        self._stats["failed_requests"] += 1


class OpenCodeProvider(ProviderInterface):
    """
    OpenCode provider - uses OpenCode API directly.

    No API key needed, IP-based rate limiting.
    """

    BASE_URL = "https://opencode.ai/api/v1"

    def __init__(self, config: Optional[ProviderConfig] = None):
        super().__init__(config or ProviderConfig(name="opencode"))
        self._session: Optional[Any] = None

    async def initialize(self):
        """Initialize HTTP session."""
        import aiohttp

        self._session = aiohttp.ClientSession()
        self._initialized = True
        logger.info("[OpenCodeProvider] Initialized")

    async def cleanup(self):
        """Cleanup HTTP session."""
        if self._session:
            await self._session.close()
        self._initialized = False

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        **kwargs,
    ) -> ChatResponse:
        """Send chat request to OpenCode."""
        if not self._initialized:
            await self.initialize()

        start = time.time()

        try:
            import aiohttp

            url = f"{self.BASE_URL}/chat/completions"
            payload = {
                "model": model,
                "messages": messages,
                **kwargs,
            }

            async with self._session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(seconds=self.config.timeout_seconds),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = (
                        data.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )
                    tokens = data.get("usage", {}).get("total_tokens", 0)
                    latency_ms = (time.time() - start) * 1000

                    self.record_success(tokens, latency_ms)
                    return ChatResponse(
                        success=True,
                        content=content,
                        model=model,
                        tokens=tokens,
                        latency_ms=latency_ms,
                        raw_response=data,
                    )
                elif resp.status == 429:
                    self.record_failure()
                    return ChatResponse(
                        success=False,
                        error="Rate limited",
                    )
                else:
                    self.record_failure()
                    return ChatResponse(
                        success=False,
                        error=f"HTTP {resp.status}",
                    )

        except asyncio.TimeoutError:
            self.record_failure()
            return ChatResponse(success=False, error="Timeout")
        except Exception as e:
            self.record_failure()
            return ChatResponse(success=False, error=str(e))

    async def stream_chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream chat from OpenCode."""
        if not self._initialized:
            await self.initialize()


        url = f"{self.BASE_URL}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            **kwargs,
        }

        async with self._session.post(url, json=payload) as resp:
            async for line in resp.content:
                if line:
                    yield line.decode("utf-8")

    async def health_check(self) -> bool:
        """Check OpenCode health."""
        try:
            import aiohttp

            async with self._session.get(
                f"{self.BASE_URL}/models", timeout=aiohttp.ClientTimeout(seconds=5)
            ) as resp:
                return resp.status == 200
        except Exception:
            return False


class OpenRouterProvider(ProviderInterface):
    """
    OpenRouter provider - uses NxRotator for 6-key rotation.
    """

    def __init__(self, config: Optional[ProviderConfig] = None):
        super().__init__(config or ProviderConfig(name="openrouter"))
        self._nx_rotator = None

    async def initialize(self):
        """Initialize NxRotator."""
        try:
            from nx_rotator.core.aggregator import NxRotator
            from nx_rotator.integration import get_rotator, is_enabled

            if is_enabled():
                self._nx_rotator = get_rotator()
                logger.info(
                    f"[OpenRouterProvider] Initialized with {len(self._nx_rotator.keys)} keys"
                )
        except ImportError:
            logger.warning("[OpenRouterProvider] NxRotator not available")

        self._initialized = True

    async def cleanup(self):
        """Cleanup."""
        self._initialized = False

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        **kwargs,
    ) -> ChatResponse:
        """Send chat via NxRotator."""
        if not self._initialized:
            await self.initialize()

        if not self._nx_rotator:
            return ChatResponse(success=False, error="NxRotator not available")

        start = time.time()

        try:
            result = await asyncio.to_thread(
                self._nx_rotator.race_chat,
                model,
                messages,
            )

            latency_ms = (time.time() - start) * 1000

            if result.success and result.response:
                self.record_success(result.tokens, latency_ms)
                content = (
                    result.response.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                return ChatResponse(
                    success=True,
                    content=content,
                    model=model,
                    tokens=result.tokens,
                    latency_ms=latency_ms,
                    raw_response=result.response,
                )
            else:
                self.record_failure()
                return ChatResponse(success=False, error=result.error)

        except Exception as e:
            self.record_failure()
            return ChatResponse(success=False, error=str(e))

    async def stream_chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream via NxRotator."""
        if not self._initialized:
            await self.initialize()

        result = await asyncio.to_thread(
            self._nx_rotator.stream_chat,
            model,
            messages,
        )

        for chunk in result:
            yield chunk

    async def health_check(self) -> bool:
        """Check NxRotator health."""
        return self._nx_rotator is not None and len(self._nx_rotator.keys) > 0


# Provider registry
PROVIDERS: Dict[str, type] = {
    "opencode": OpenCodeProvider,
    "openrouter": OpenRouterProvider,
    # Future providers (template stubs)
    # "google": GoogleProvider,
    # "groq": GroqProvider,
}


class GoogleProvider(ProviderInterface):
    """
    Google AI provider - Gemini API.

    Usage:
        provider = GoogleProvider()
        response = await provider.chat("gemini-2.0-flash", messages)
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, config: Optional[ProviderConfig] = None):
        super().__init__(config or ProviderConfig(name="google"))
        self._session: Optional[Any] = None
        self._api_key: Optional[str] = None

    def _load_api_key(self) -> str:
        """Load Google API key from environment."""
        import os

        return os.environ.get("GOOGLE_API_KEY", "")

    async def initialize(self):
        """Initialize HTTP session."""
        import aiohttp

        self._api_key = self._load_api_key()
        if not self._api_key:
            logger.warning("[GoogleProvider] No GOOGLE_API_KEY set")
        self._session = aiohttp.ClientSession()
        self._initialized = True
        logger.info("[GoogleProvider] Initialized")

    async def cleanup(self):
        """Cleanup HTTP session."""
        if self._session:
            await self._session.close()
        self._initialized = False

    async def chat(self, model: str, messages: List[Dict], **kwargs) -> ChatResponse:
        """Send chat request to Google."""
        if not self._initialized:
            await self.initialize()

        if not self._api_key:
            return ChatResponse(success=False, error="No API key")

        start = time.time()

        try:

            url = f"{self.BASE_URL}/models/{model}:generateContent"
            params = {"key": self._api_key}

            # Convert messages to Google format
            contents = []
            for msg in messages:
                contents.append(
                    {"role": msg["role"], "parts": [{"text": msg["content"]}]}
                )

            payload = {"contents": contents}
            if "max_tokens" in kwargs:
                payload["maxOutputTokens"] = kwargs["max_tokens"]
            if "temperature" in kwargs:
                payload["temperature"] = kwargs["temperature"]

            async with self._session.post(url, params=params, json=payload) as resp:
                latency_ms = (time.time() - start) * 1000

                if resp.status == 200:
                    data = await resp.json()
                    content = ""
                    if "candidates" in data and data["candidates"]:
                        candidate = data["candidates"][0]
                        if "content" in candidate and "parts" in candidate["content"]:
                            for part in candidate["content"]["parts"]:
                                content += part.get("text", "")

                    tokens = len(content.split())  # Approximate
                    self.record_success(tokens, latency_ms)
                    return ChatResponse(
                        success=True,
                        content=content,
                        model=model,
                        tokens=tokens,
                        latency_ms=latency_ms,
                        raw_response=data,
                    )
                else:
                    self.record_failure()
                    text = await resp.text()
                    return ChatResponse(
                        success=False, error=f"HTTP {resp.status}: {text[:200]}"
                    )
        except Exception as e:
            self.record_failure()
            return ChatResponse(success=False, error=str(e))

    async def stream_chat(
        self, model: str, messages: List[Dict], **kwargs
    ) -> AsyncIterator[str]:
        """Stream from Google (limited support)."""
        # Not fully implemented - would need server-sent events
        response = await self.chat(model, messages, **kwargs)
        if response.success:
            yield response.content

    async def health_check(self) -> bool:
        """Check Google API health."""
        return bool(self._api_key)


class GroqProvider(ProviderInterface):
    """
    Groq provider - Fast inference API.

    Usage:
        provider = GroqProvider()
        response = await provider.chat("llama-3.3-70b-versatile", messages)
    """

    BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(self, config: Optional[ProviderConfig] = None):
        super().__init__(config or ProviderConfig(name="groq"))
        self._session: Optional[Any] = None
        self._api_key: Optional[str] = None

    def _load_api_key(self) -> str:
        """Load Groq API key from environment."""
        import os

        return os.environ.get("GROQ_API_KEY", "")

    async def initialize(self):
        """Initialize HTTP session."""
        import aiohttp

        self._api_key = self._load_api_key()
        if not self._api_key:
            logger.warning("[GroqProvider] No GROQ_API_KEY set")
        self._session = aiohttp.ClientSession()
        self._initialized = True
        logger.info("[GroqProvider] Initialized")

    async def cleanup(self):
        """Cleanup HTTP session."""
        if self._session:
            await self._session.close()
        self._initialized = False

    async def chat(self, model: str, messages: List[Dict], **kwargs) -> ChatResponse:
        """Send chat request to Groq."""
        if not self._initialized:
            await self.initialize()

        if not self._api_key:
            return ChatResponse(success=False, error="No API key")

        start = time.time()

        try:

            url = f"{self.BASE_URL}/chat/completions"
            headers = {"Authorization": f"Bearer {self._api_key}"}

            payload = {
                "model": model,
                "messages": messages,
            }
            if "max_tokens" in kwargs:
                payload["max_tokens"] = kwargs["max_tokens"]
            if "temperature" in kwargs:
                payload["temperature"] = kwargs["temperature"]

            async with self._session.post(url, headers=headers, json=payload) as resp:
                latency_ms = (time.time() - start) * 1000

                if resp.status == 200:
                    data = await resp.json()
                    choice = data["choices"][0]
                    content = choice["message"]["content"]

                    usage = data.get("usage", {})
                    tokens = usage.get("total_tokens", len(content.split()))

                    self.record_success(tokens, latency_ms)
                    return ChatResponse(
                        success=True,
                        content=content,
                        model=model,
                        tokens=tokens,
                        latency_ms=latency_ms,
                        raw_response=data,
                    )
                else:
                    self.record_failure()
                    text = await resp.text()
                    return ChatResponse(
                        success=False, error=f"HTTP {resp.status}: {text[:200]}"
                    )
        except Exception as e:
            self.record_failure()
            return ChatResponse(success=False, error=str(e))

    async def stream_chat(
        self, model: str, messages: List[Dict], **kwargs
    ) -> AsyncIterator[str]:
        """Stream from Groq."""
        if not self._initialized:
            await self.initialize()

        if not self._api_key:
            return


        url = f"{self.BASE_URL}/chat/completions"
        headers = {"Authorization": f"Bearer {self._api_key}"}

        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        if "max_tokens" in kwargs:
            payload["max_tokens"] = kwargs["max_tokens"]

        try:
            async with self._session.post(url, headers=headers, json=payload) as resp:
                async for line in resp.content:
                    line = line.decode().strip()
                    if line.startswith("data: "):
                        if line == "data: [DONE]":
                            break
                        import json

                        try:
                            data = json.loads(line[6:])
                            if "choices" in data and data["choices"]:
                                delta = data["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                        except (json.JSONDecodeError, KeyError):
                            pass
        except Exception as e:
            yield f"[Error: {e}]"

    async def health_check(self) -> bool:
        """Check Groq API health."""
        return bool(self._api_key)


def get_provider(name: str, **kwargs) -> ProviderInterface:
    """Get a provider instance by name."""
    provider_class = PROVIDERS.get(name.lower())
    if not provider_class:
        raise ValueError(f"Unknown provider: {name}")
    return provider_class(**kwargs)


# Add additional providers to registry
PROVIDERS["google"] = GoogleProvider
PROVIDERS["groq"] = GroqProvider
