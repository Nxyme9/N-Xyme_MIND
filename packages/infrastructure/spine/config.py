"""Spine Configuration — Dataclass for Golden Spine execution path."""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SpineConfig:
    """Configuration for Golden Spine AI model serving.

    This is the isolated execution path for AI model serving with:
    - Primary and fallback models
    - Ollama server binding
    - Circuit breaker settings for fault tolerance
    - Retry configuration

    Attributes:
        model_path: Primary model to serve (default: qwen2.5-coder:7b)
        fallback_models: List of fallback models in priority order
        bind_host: Host to bind Ollama server (default: 127.0.0.1)
        port: Port for Ollama server (default: 11434)
        ctx: Context window size (default: 8192)
        gpu_layers: Number of GPU layers to use (-1 = all, default: -1)
        failure_threshold: Circuit breaker failure threshold (default: 3)
        reset_timeout: Circuit breaker reset timeout in seconds (default: 60.0)
        max_retries: Maximum retry attempts (default: 3)
    """

    model_path: str = "qwen2.5-coder:7b"
    fallback_models: list[str] = field(default_factory=lambda: ["llama3.2:3b"])
    bind_host: str = "127.0.0.1"
    port: int = 11434
    ctx: int = 8192
    gpu_layers: int = -1
    failure_threshold: int = 3
    reset_timeout: float = 60.0
    max_retries: int = 3

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "model_path": self.model_path,
            "fallback_models": self.fallback_models,
            "bind_host": self.bind_host,
            "port": self.port,
            "ctx": self.ctx,
            "gpu_layers": self.gpu_layers,
            "failure_threshold": self.failure_threshold,
            "reset_timeout": self.reset_timeout,
            "max_retries": self.max_retries,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SpineConfig":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


# Lazy import types for run record
def _get_run_record():
    """Lazy import RunRecord to avoid circular imports."""
    from dataclasses import dataclass, field
    from typing import List, Optional
    from datetime import datetime

    @dataclass
    class RunRecord:
        """Record of a single spine execution run.

        Tracks model invocation, timing, and outcome for monitoring.
        """

        run_id: str
        timestamp: datetime = field(default_factory=datetime.now)
        model: str = ""
        success: bool = False
        latency_ms: float = 0.0
        error: Optional[str] = None
        fallback_used: bool = False
        fallback_chain: List[str] = field(default_factory=list)

        def to_dict(self) -> dict:
            return {
                "run_id": self.run_id,
                "timestamp": self.timestamp.isoformat(),
                "model": self.model,
                "success": self.success,
                "latency_ms": self.latency_ms,
                "error": self.error,
                "fallback_used": self.fallback_used,
                "fallback_chain": self.fallback_chain,
            }

    return RunRecord


def _get_golden_spine():
    """Lazy import GoldenSpine to avoid circular imports."""
    try:
        from .golden_spine import GoldenSpine

        return GoldenSpine
    except ImportError:
        # GoldenSpine not yet implemented - return placeholder
        return None


# Public lazy imports
def get_run_record():
    """Get RunRecord class (lazy import)."""
    return _get_run_record()


def get_golden_spine():
    """Get GoldenSpine class (lazy import)."""
    return _get_golden_spine()