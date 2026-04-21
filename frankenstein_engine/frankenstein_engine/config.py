# -*- coding: utf-8 -*-
"""Frankenstein Engine - Industry-standard configuration with validation."""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FrankensteinConfig(BaseSettings):
    """Frankenstein Engine configuration with environment variable support.

    All settings can be overridden via environment variables or .env file.
    Uses Pydantic for validation and type checking.
    """

    model_config = SettingsConfigDict(
        env_prefix="FRANKENSTEIN_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra env vars
    )

    # Paths
    models_dir: Path = Field(default=Path("models"), description="Directory containing GGUF models")

    # Ports
    llama_server_port: int = Field(default=8080, description="GGUF llama-server port")
    ollama_fallback_port: int = Field(default=11434, description="Ollama fallback port")

    # Default models
    default_model: str = Field(
        default="qwen2.5-coder-7b-q4_k_m", description="Primary reasoning model"
    )
    rosetta_model: str = Field(
        default="qwen2.5-0.5b-instruct-q4_k_m", description="Fast model for simple tasks"
    )
    embed_model: str = Field(default="nomic-embed-text-v1.5-Q4_K_M", description="Embedding model")

    # Inference settings (OPTIMIZED for RTX 3080 Ti 12.5GB)
    n_gpu_layers: int = Field(default=-1, description="GPU layers (-1 = all to GPU, 0 = CPU only)")
    n_ctx: int = Field(default=8192, description="Context window size (4096->8192)")
    n_ctx_large: int = Field(default=131072, description="Large context window")
    n_threads: int = Field(default=16, description="CPU threads (8->16 for 7800X3D)")
    n_batch: int = Field(default=512, description="Batch size (512 for throughput)")
    n_keep: int = Field(default=256, description="Keep tokens (128->256)")
    n_threads_batch: int = Field(default=16, description="Threads for batch processing")

    # Timeout settings (ms)
    default_timeout_ms: int = Field(default=30000, description="Default inference timeout")
    embedding_timeout_ms: int = Field(default=10000, description="Embedding timeout")

    # Routing
    complexity_threshold_simple: int = Field(default=100, description="Simple task char threshold")
    complexity_threshold_medium: int = Field(default=500, description="Medium task char threshold")
    circuit_breaker_threshold: int = Field(default=3, description="Failures before circuit opens")
    circuit_breaker_timeout: float = Field(
        default=60.0, description="Circuit breaker reset timeout"
    )

    # Health monitoring
    health_check_interval: float = Field(
        default=30.0, description="Health check interval (seconds)"
    )
    health_check_timeout: int = Field(default=10, description="Health check timeout (seconds)")
    health_threshold_ratio: float = Field(
        default=0.7, description="Min healthy ratio for degradation"
    )

    # GPU thresholds (configurable)
    gpu_temp_threshold: int = Field(default=85, description="GPU temperature threshold (C)")
    gpu_vram_threshold_mb: int = Field(default=11000, description="VRAM threshold (MB)")
    system_mem_threshold: float = Field(default=0.9, description="System memory threshold")

    # Feature flags
    enable_rosetta_fast_mode: bool = Field(
        default=True, description="Enable fast mode for simple tasks"
    )
    enable_embeddings: bool = Field(default=True, description="Enable embedding generation")
    enable_health_monitoring: bool = Field(default=True, description="Enable health monitoring")
    enable_circuit_breaker: bool = Field(default=True, description="Enable circuit breaker")
    prefer_gguf_over_ollama: bool = Field(default=True, description="Prefer GGUF over Ollama")
    auto_fallback: bool = Field(default=True, description="Auto fallback on failure")
    enable_rag: bool = Field(default=True, description="Enable RAG context injection")
    use_direct_mode: bool = Field(
        default=False, description="Use direct GGUF (bypass proxy on 8080)"
    )
    direct_mode_port: int = Field(default=8090, description="Port for direct GGUF mode")
    enable_rag_cache: bool = Field(
        default=True, description="Cache RAG results for repeated queries"
    )

    # LoRA Adapters
    default_adapter: Optional[str] = Field(default=None, description="Default adapter name")
    adapters_dir: Path = Field(default=Path("adapters"), description="LoRA adapters directory")

    # Default adapter per agent type
    adapter_for_explore: Optional[str] = Field(
        default=None, description="Adapter for explore agent"
    )
    adapter_for_implement: Optional[str] = Field(
        default=None, description="Adapter for implement agent"
    )
    adapter_for_review: Optional[str] = Field(default=None, description="Adapter for review agent")
    adapter_for_benchmark: Optional[str] = Field(
        default=None, description="Adapter for benchmark agent"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json/text)")


# Global config instance
_config: Optional[FrankensteinConfig] = None


def get_config() -> FrankensteinConfig:
    """Get or create global config instance (lazy-loaded)."""
    global _config
    if _config is None:
        _config = FrankensteinConfig()
    return _config


def reload_config() -> FrankensteinConfig:
    """Reload config (useful for testing)."""
    global _config
    _config = FrankensteinConfig()
    return _config


# ============================================================================
# Convenience accessors (backward compatible module-level constants)
# ============================================================================
# These functions provide backward-compatible access like config.LLAMA_SERVER_URL


def _LLAMA_SERVER_PORT() -> int:
    return get_config().llama_server_port


def _OLLAMA_FALLBACK_PORT() -> int:
    return get_config().ollama_fallback_port


def _LLAMA_SERVER_URL() -> str:
    return f"http://localhost:{get_config().llama_server_port}"


def _OLLAMA_URL() -> str:
    return f"http://localhost:{get_config().ollama_fallback_port}"


def _DEFAULT_MODEL() -> str:
    return get_config().default_model


def _ROSETTA_MODEL() -> str:
    return get_config().rosetta_model


def _EMBED_MODEL() -> str:
    return get_config().embed_model


def _DEFAULT_N_GPU_LAYERS() -> int:
    return get_config().n_gpu_layers


def _DEFAULT_N_CTX() -> int:
    return get_config().n_ctx


def _DEFAULT_N_CTX_LARGE() -> int:
    return get_config().n_ctx_large


def _DEFAULT_N_THREADS() -> int:
    return get_config().n_threads


def _DEFAULT_N_BATCH() -> int:
    return get_config().n_batch


def _DEFAULT_N_KEEP() -> int:
    return get_config().n_keep


def _DEFAULT_TIMEOUT_MS() -> int:
    return get_config().default_timeout_ms


def _EMBEDDING_TIMEOUT_MS() -> int:
    return get_config().embedding_timeout_ms


def _COMPLEXITY_THRESHOLD_SIMPLE() -> int:
    return get_config().complexity_threshold_simple


def _COMPLEXITY_THRESHOLD_MEDIUM() -> int:
    return get_config().complexity_threshold_medium


def _CIRCUIT_BREAKER_THRESHOLD() -> int:
    return get_config().circuit_breaker_threshold


def _CIRCUIT_BREAKER_TIMEOUT() -> float:
    return get_config().circuit_breaker_timeout


def _HEALTH_CHECK_INTERVAL() -> float:
    return get_config().health_check_interval


def _HEALTH_CHECK_TIMEOUT() -> int:
    return get_config().health_check_timeout


def _ENABLE_ROSETTA_FAST_MODE() -> bool:
    return get_config().enable_rosetta_fast_mode


def _ENABLE_EMBEDDINGS() -> bool:
    return get_config().enable_embeddings


def _ENABLE_HEALTH_MONITORING() -> bool:
    return get_config().enable_health_monitoring


def _ENABLE_CIRCUIT_BREAKER() -> bool:
    return get_config().enable_circuit_breaker


def _PREFER_GGUF_OVER_OLLAMA() -> bool:
    return get_config().prefer_gguf_over_ollama


def _AUTO_FALLBACK() -> bool:
    return get_config().auto_fallback


def _ENABLE_RAG() -> bool:
    return get_config().enable_rag


def _DEFAULT_N_THREADS_BATCH() -> int:
    return get_config().n_threads_batch


# For backward compatibility, create module-level aliases
# These will be imported by other modules as frankenstein_engine.config.LLAMA_SERVER_URL
# Use simple properties that delegate to get_config() for dynamic updates


def _make_property(name: str):
    """Create a property that delegates to get_config()."""

    def getter(self):
        return getattr(get_config(), name)

    return property(getter)


# Create properties that delegate to get_config() - these work as module-level values
# When imported, they evaluate lazily
class _ConfigProxy:
    """Proxy class for module-level config access."""

    @property
    def LLAMA_SERVER_PORT(self) -> int:
        return get_config().llama_server_port

    @property
    def OLLAMA_FALLBACK_PORT(self) -> int:
        return get_config().ollama_fallback_port

    @property
    def LLAMA_SERVER_URL(self) -> str:
        return f"http://localhost:{get_config().llama_server_port}"

    @property
    def OLLAMA_URL(self) -> str:
        return f"http://localhost:{get_config().ollama_fallback_port}"

    @property
    def DEFAULT_MODEL(self) -> str:
        return get_config().default_model

    @property
    def ROSETTA_MODEL(self) -> str:
        return get_config().rosetta_model

    @property
    def EMBED_MODEL(self) -> str:
        return get_config().embed_model

    @property
    def DEFAULT_N_GPU_LAYERS(self) -> int:
        return get_config().n_gpu_layers

    @property
    def DEFAULT_N_CTX(self) -> int:
        return get_config().n_ctx

    @property
    def DEFAULT_N_CTX_LARGE(self) -> int:
        return get_config().n_ctx_large

    @property
    def DEFAULT_N_THREADS(self) -> int:
        return get_config().n_threads

    @property
    def DEFAULT_N_BATCH(self) -> int:
        return get_config().n_batch

    @property
    def DEFAULT_N_KEEP(self) -> int:
        return get_config().n_keep

    @property
    def DEFAULT_TIMEOUT_MS(self) -> int:
        return get_config().default_timeout_ms

    @property
    def EMBEDDING_TIMEOUT_MS(self) -> int:
        return get_config().embedding_timeout_ms

    @property
    def COMPLEXITY_THRESHOLD_SIMPLE(self) -> int:
        return get_config().complexity_threshold_simple

    @property
    def COMPLEXITY_THRESHOLD_MEDIUM(self) -> int:
        return get_config().complexity_threshold_medium

    @property
    def CIRCUIT_BREAKER_THRESHOLD(self) -> int:
        return get_config().circuit_breaker_threshold

    @property
    def CIRCUIT_BREAKER_TIMEOUT(self) -> float:
        return get_config().circuit_breaker_timeout

    @property
    def HEALTH_CHECK_INTERVAL(self) -> float:
        return get_config().health_check_interval

    @property
    def HEALTH_CHECK_TIMEOUT(self) -> int:
        return get_config().health_check_timeout

    @property
    def ENABLE_ROSETTA_FAST_MODE(self) -> bool:
        return get_config().enable_rosetta_fast_mode

    @property
    def ENABLE_EMBEDDINGS(self) -> bool:
        return get_config().enable_embeddings

    @property
    def ENABLE_HEALTH_MONITORING(self) -> bool:
        return get_config().enable_health_monitoring

    @property
    def ENABLE_CIRCUIT_BREAKER(self) -> bool:
        return get_config().enable_circuit_breaker

    @property
    def PREFER_GGUF_OVER_OLLAMA(self) -> bool:
        return get_config().prefer_gguf_over_ollama

    @property
    def AUTO_FALLBACK(self) -> bool:
        return get_config().auto_fallback

    @property
    def ENABLE_RAG(self) -> bool:
        return get_config().enable_rag

    @property
    def DEFAULT_N_THREADS_BATCH(self) -> int:
        return get_config().n_threads_batch


# Create singleton for module-level attribute access
_config_proxy = _ConfigProxy()


# For module-level constants that work with direct access like config.LLAMA_SERVER_URL
# Use __getattr__ for dynamic attribute resolution (Python 3.7+)
def __getattr__(name: str):
    """Module-level attribute access for backward compatibility."""
    # Handle lowercase attributes (embed_model -> EMBED_MODEL)
    if name == "embed_model":
        name = "EMBED_MODEL"
    elif name == "default_model":
        name = "DEFAULT_MODEL"
    elif name == "rosetta_model":
        name = "ROSETTA_MODEL"

    if hasattr(_config_proxy, name):
        return getattr(_config_proxy, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Simple function-based accessors for backward compatibility
# These are what most code actually uses
def _get_llama_server_port() -> int:
    return get_config().llama_server_port


def _get_ollama_fallback_port() -> int:
    return get_config().ollama_fallback_port


def _get_llama_server_url() -> str:
    return f"http://localhost:{get_config().llama_server_port}"


def _get_ollama_url() -> str:
    return f"http://localhost:{get_config().ollama_fallback_port}"


def _get_default_model() -> str:
    return get_config().default_model


def _get_rosetta_model() -> str:
    return get_config().rosetta_model


def _get_embed_model() -> str:
    return get_config().embed_model


def _get_default_n_gpu_layers() -> int:
    return get_config().n_gpu_layers


def _get_default_n_ctx() -> int:
    return get_config().n_ctx


def _get_default_n_ctx_large() -> int:
    return get_config().n_ctx_large


def _get_default_n_threads() -> int:
    return get_config().n_threads


def _get_default_n_batch() -> int:
    return get_config().n_batch


def _get_default_n_keep() -> int:
    return get_config().n_keep


def _get_default_timeout_ms() -> int:
    return get_config().default_timeout_ms


def _get_embedding_timeout_ms() -> int:
    return get_config().embedding_timeout_ms


def _get_complexity_threshold_simple() -> int:
    return get_config().complexity_threshold_simple


def _get_complexity_threshold_medium() -> int:
    return get_config().complexity_threshold_medium


def _get_circuit_breaker_threshold() -> int:
    return get_config().circuit_breaker_threshold


def _get_circuit_breaker_timeout() -> float:
    return get_config().circuit_breaker_timeout


def _get_health_check_interval() -> float:
    return get_config().health_check_interval


def _get_health_check_timeout() -> int:
    return get_config().health_check_timeout


def _get_enable_rosetta_fast_mode() -> bool:
    return get_config().enable_rosetta_fast_mode


def _get_enable_embeddings() -> bool:
    return get_config().enable_embeddings


def _get_enable_health_monitoring() -> bool:
    return get_config().enable_health_monitoring


def _get_enable_circuit_breaker() -> bool:
    return get_config().enable_circuit_breaker


def _get_prefer_gguf_over_ollama() -> bool:
    return get_config().prefer_gguf_over_ollama


def _get_auto_fallback() -> bool:
    return get_config().auto_fallback


def _get_enable_rag() -> bool:
    return get_config().enable_rag


def _get_default_n_threads_batch() -> int:
    return get_config().n_threads_batch


def get_project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent


def get_models_dir() -> Path:
    """Get models directory."""
    return get_config().models_dir


def get_model_path(model_name: str) -> Path:
    """Get full path to a GGUF model."""
    return get_models_dir() / f"{model_name}.gguf"


# Backward compatibility - expose models_dir as MODELS_DIR for direct_pipeline compatibility
MODELS_DIR = get_models_dir()
