"""Token Estimation — Accurate token counting for all models.

Ported from ant-source-code-main/services/tokenEstimation.ts
Provides accurate token counting for local and cloud models.
Supports: OpenAI, Anthropic, Ollama, and local models.

Pattern: Uses tiktoken for OpenAI-compatible models, fallback to
character-based estimation for others. Integrates with cost_tracking.py
for real-time cost awareness.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Token estimation constants
CHARS_PER_TOKEN_APPROX = 4.0  # Average characters per token
CHARS_PER_TOKEN_CODE = 3.5  # Code is more token-efficient
CHARS_PER_TOKEN_PROSE = 4.5  # Prose is less token-efficient

# Model-specific tokenization overhead
MODEL_TOKEN_OVERHEAD = {
    # OpenAI models
    "gpt-4": 0.0,
    "gpt-4-turbo": 0.0,
    "gpt-3.5-turbo": 0.0,
    # Anthropic models
    "claude-3-opus": 0.0,
    "claude-3-sonnet": 0.0,
    "claude-3-haiku": 0.0,
    # OpenCode Zen models
    "opencode/qwen3.6-plus-free": 0.0,
    "opencode/qwen3.6-coder-free": 0.0,
    "opencode/qwen3.6-flash-free": 0.0,
    # Ollama models
    "llama-3.2-3b": 0.0,
    "llama-3.2-8b": 0.0,
    "mistral-7b": 0.0,
    "phi-3-mini": 0.0,
}

# Context window sizes (tokens)
MODEL_CONTEXT_WINDOWS = {
    # OpenAI
    "gpt-4": 8192,
    "gpt-4-turbo": 128000,
    "gpt-3.5-turbo": 16385,
    # Anthropic
    "claude-3-opus": 200000,
    "claude-3-sonnet": 200000,
    "claude-3-haiku": 200000,
    # OpenCode Zen
    "opencode/qwen3.6-plus-free": 32768,
    "opencode/qwen3.6-coder-free": 32768,
    "opencode/qwen3.6-flash-free": 32768,
    # Ollama
    "llama-3.2-3b": 131072,
    "llama-3.2-8b": 131072,
    "mistral-7b": 32768,
    "phi-3-mini": 128000,
}

# Cost per 1M tokens (USD)
MODEL_COSTS = {
    # OpenAI
    "gpt-4": {"input": 30.0, "output": 60.0},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
    # Anthropic
    "claude-3-opus": {"input": 15.0, "output": 75.0},
    "claude-3-sonnet": {"input": 3.0, "output": 15.0},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    # OpenCode Zen (free)
    "opencode/qwen3.6-plus-free": {"input": 0.0, "output": 0.0},
    "opencode/qwen3.6-coder-free": {"input": 0.0, "output": 0.0},
    "opencode/qwen3.6-flash-free": {"input": 0.0, "output": 0.0},
    # Ollama (local, free)
    "llama-3.2-3b": {"input": 0.0, "output": 0.0},
    "llama-3.2-8b": {"input": 0.0, "output": 0.0},
    "mistral-7b": {"input": 0.0, "output": 0.0},
    "phi-3-mini": {"input": 0.0, "output": 0.0},
}


@dataclass
class TokenCount:
    """Result of token counting."""

    input_tokens: int
    output_tokens: int
    total_tokens: int
    context_window: int
    context_usage_pct: float
    estimated_cost_usd: float
    model: str


@dataclass
class MessageTokenCount:
    """Token count for a single message."""

    role: str
    content: str
    tokens: int


class TokenEstimator:
    """Estimates token counts for various models."""

    def __init__(self):
        """Initialize token estimator."""
        self._tiktoken_encoders = {}

    def estimate_tokens(self, text: str, model: str | None = None) -> int:
        """Estimate token count for text.

        Args:
            text: Text to count tokens for.
            model: Model name (affects estimation accuracy).

        Returns:
            Estimated token count.
        """
        if not text:
            return 0

        # Try tiktoken if available (OpenAI-compatible models)
        if model and self._is_openai_compatible(model):
            try:
                return self._count_with_tiktoken(text, model)
            except Exception:
                pass  # Fallback to estimation

        # Use character-based estimation
        return self._estimate_by_chars(text, model)

    def _is_openai_compatible(self, model: str) -> bool:
        """Check if model is OpenAI-compatible."""
        return model.startswith(("gpt-", "o1", "o3"))

    def _count_with_tiktoken(self, text: str, model: str) -> int:
        """Count tokens using tiktoken library."""
        try:
            import tiktoken

            if model not in self._tiktoken_encoders:
                self._tiktoken_encoders[model] = tiktoken.encoding_for_model(model)
            encoder = self._tiktoken_encoders[model]
            return len(encoder.encode(text))
        except ImportError:
            raise RuntimeError("tiktoken not installed")
        except KeyError:
            # Model not supported by tiktoken
            return self._estimate_by_chars(text, model)

    def _estimate_by_chars(self, text: str, model: str | None = None) -> int:
        """Estimate tokens by character count.

        Uses different ratios for code vs prose.
        """
        if not text:
            return 0

        # Detect if text is code or prose
        is_code = self._is_code(text)
        chars_per_token = CHARS_PER_TOKEN_CODE if is_code else CHARS_PER_TOKEN_PROSE

        # Adjust for model if known
        if model and model in MODEL_TOKEN_OVERHEAD:
            overhead = MODEL_TOKEN_OVERHEAD[model]
            chars_per_token += overhead

        return max(1, int(len(text) / chars_per_token))

    def _is_code(self, text: str) -> bool:
        """Detect if text is code or prose."""
        # Simple heuristics
        code_indicators = [
            "def ",
            "class ",
            "import ",
            "from ",
            "function ",
            "const ",
            "let ",
            "var ",
            "if ",
            "else ",
            "for ",
            "while ",
            "return ",
            "async ",
            "await ",
            "=>",
            "{",
            "}",
            "(",
            ")",
            "[",
            "]",
        ]
        code_count = sum(1 for indicator in code_indicators if indicator in text)
        return code_count > 3

    def count_messages(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
    ) -> list[MessageTokenCount]:
        """Count tokens for a list of messages.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            model: Model name.

        Returns:
            List of MessageTokenCount objects.
        """
        results = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            tokens = self.estimate_tokens(content, model)
            results.append(
                MessageTokenCount(
                    role=role,
                    content=content,
                    tokens=tokens,
                )
            )
        return results

    def count_conversation(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
    ) -> TokenCount:
        """Count tokens for an entire conversation.

        Args:
            messages: List of message dicts.
            model: Model name.

        Returns:
            TokenCount with total counts and context usage.
        """
        if not model:
            model = "opencode/qwen3.6-plus-free"

        # Count input tokens (all messages except last)
        input_tokens = sum(
            self.estimate_tokens(msg.get("content", ""), model) for msg in messages[:-1]
        )

        # Count output tokens (last message)
        output_tokens = 0
        if messages:
            output_tokens = self.estimate_tokens(messages[-1].get("content", ""), model)

        total_tokens = input_tokens + output_tokens
        context_window = MODEL_CONTEXT_WINDOWS.get(model, 32768)
        context_usage_pct = (
            (total_tokens / context_window * 100) if context_window > 0 else 0
        )

        # Calculate cost
        costs = MODEL_COSTS.get(model, {"input": 0.0, "output": 0.0})
        estimated_cost = (input_tokens / 1_000_000) * costs["input"] + (
            output_tokens / 1_000_000
        ) * costs["output"]

        return TokenCount(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            context_window=context_window,
            context_usage_pct=round(context_usage_pct, 2),
            estimated_cost_usd=round(estimated_cost, 6),
            model=model,
        )

    def get_context_window(self, model: str) -> int:
        """Get context window size for model."""
        return MODEL_CONTEXT_WINDOWS.get(model, 32768)

    def get_cost_per_1m_tokens(self, model: str) -> dict[str, float]:
        """Get cost per 1M tokens for model."""
        return MODEL_COSTS.get(model, {"input": 0.0, "output": 0.0})

    def is_context_window_exceeded(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        threshold_pct: float = 90.0,
    ) -> bool:
        """Check if conversation is approaching context window limit.

        Args:
            messages: List of message dicts.
            model: Model name.
            threshold_pct: Warning threshold percentage.

        Returns:
            True if context window usage exceeds threshold.
        """
        count = self.count_conversation(messages, model)
        return count.context_usage_pct >= threshold_pct

    def suggest_compaction(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        target_pct: float = 70.0,
    ) -> list[int]:
        """Suggest which messages to compact to stay under target.

        Args:
            messages: List of message dicts.
            model: Model name.
            target_pct: Target context usage percentage.

        Returns:
            List of message indices to compact.
        """
        if not model:
            model = "opencode/qwen3.6-plus-free"

        count = self.count_conversation(messages, model)
        if count.context_usage_pct <= target_pct:
            return []  # No compaction needed

        # Calculate how many tokens to remove
        context_window = self.get_context_window(model)
        target_tokens = int(context_window * target_pct / 100)
        tokens_to_remove = count.total_tokens - target_tokens

        # Find longest messages to compact (excluding system prompt and last message)
        message_tokens = []
        for i, msg in enumerate(messages[:-1]):  # Exclude last message
            if msg.get("role") == "system":
                continue  # Don't compact system prompt
            tokens = self.estimate_tokens(msg.get("content", ""), model)
            message_tokens.append((i, tokens))

        # Sort by token count (longest first)
        message_tokens.sort(key=lambda x: x[1], reverse=True)

        # Select messages to compact
        indices_to_compact = []
        removed_tokens = 0
        for idx, tokens in message_tokens:
            indices_to_compact.append(idx)
            removed_tokens += tokens
            if removed_tokens >= tokens_to_remove:
                break

        return indices_to_compact


# Global singleton
_estimator = TokenEstimator()


def estimate_tokens(text: str, model: str | None = None) -> int:
    """Convenience function to estimate tokens."""
    return _estimator.estimate_tokens(text, model)


def count_conversation(
    messages: list[dict[str, str]],
    model: str | None = None,
) -> TokenCount:
    """Convenience function to count conversation tokens."""
    return _estimator.count_conversation(messages, model)


def is_context_window_exceeded(
    messages: list[dict[str, str]],
    model: str | None = None,
    threshold_pct: float = 90.0,
) -> bool:
    """Convenience function to check context window."""
    return _estimator.is_context_window_exceeded(messages, model, threshold_pct)


def suggest_compaction(
    messages: list[dict[str, str]],
    model: str | None = None,
    target_pct: float = 70.0,
) -> list[int]:
    """Convenience function to suggest compaction."""
    return _estimator.suggest_compaction(messages, model, target_pct)
