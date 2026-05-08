# -*- coding: utf-8 -*-
"""ModelOrchestrator - Unified bulletproof local LLM engine.

This is the single entry point for all local LLM operations:
- Direct GGUF (no network overhead)
- Hot-swap models and LoRA adapters
- Auto-routing by complexity/task
- Training integration via Rosetta Stone Trainer

Usage:
    from packages.model_orchestrator import get_orchestrator

    orchestrator = get_orchestrator()
    response = orchestrator.generate("Hello!")

    # With adapter
    orchestrator.set_adapter("rosetta-lora")
    response = orchestrator.generate("search memory for security")
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
ADAPTERS_DIR = MODELS_DIR

logger = logging.getLogger("model_orchestrator")

# ============================================================================
# Imports from frankenstein_engine (existing, working)
# ============================================================================

from frankenstein_engine.engine import DirectLlamaClient
from frankenstein_engine.router import RouterBrain
from frankenstein_engine.adapters import (
    ADAPTERS as FRANKENSTEIN_ADAPTERS,
    get_adapter_path,
    load_adapter,
    unload_adapter,
    get_current_adapter,
    set_current_adapter,
    validate_adapter,
)
from frankenstein_engine import config as frankenstein_config
from frankenstein_engine.health import HealthMonitor

# ============================================================================
# Exceptions
# ============================================================================


class ModelOrchestratorError(Exception):
    """Base exception for orchestrator errors."""

    pass


class ModelLoadError(ModelOrchestratorError):
    """Failed to load model."""

    pass


class AdapterLoadError(ModelOrchestratorError):
    """Failed to load adapter."""

    pass


class RoutingError(ModelOrchestratorError):
    """Failed to route request."""

    pass


# ============================================================================
# Model Manager - Direct GGUF with hot-swap
# ============================================================================


class ModelManager:
    """Direct GGUF model management - no network overhead.

    Wraps DirectLlamaClient with:
    - Hot-swap model switching
    - VRAM tracking
    - HTTP fallback
    """

    def __init__(
        self,
        default_model: str = None,
        n_gpu_layers: int = 99,
        n_ctx: int = 32768,
        n_threads: int = 16,
    ):
        """Initialize model manager.

        Args:
            default_model: Model name (without .gguf)
            n_gpu_layers: GPU layers (-1 = all, 99 = all for llama-cpp)
            n_ctx: Context size
            n_threads: CPU threads
        """
        self.default_model = default_model or frankenstein_config.DEFAULT_MODEL
        self.n_gpu_layers = n_gpu_layers
        self.n_ctx = n_ctx
        self.n_threads = n_threads

        self._client: Optional[DirectLlamaClient] = None
        self._current_model: Optional[str] = None

        logger.info(f"ModelManager initialized with model={self.default_model}")

    def _ensure_client(
        self, model: str = None, adapter_name: str = None
    ) -> DirectLlamaClient:
        """Ensure client is loaded with correct model/adapter."""
        target_model = model or self.default_model

        # Check if we need to reload
        needs_reload = (
            self._client is None
            or self._current_model != target_model
            or get_current_adapter() != adapter_name
        )

        if needs_reload:
            logger.info(f"Loading model: {target_model} (adapter: {adapter_name})")

            # Build kwargs
            kwargs = {
                "model_path": str(MODELS_DIR / f"{target_model}.gguf"),
                "n_gpu_layers": self.n_gpu_layers,
                "n_ctx": self.n_ctx,
                "n_threads": self.n_threads,
            }

            # Add adapter if specified
            if adapter_name:
                if not validate_adapter(adapter_name):
                    raise AdapterLoadError(f"Invalid adapter: {adapter_name}")
                adapter_path = get_adapter_path(adapter_name)
                kwargs["lora_path"] = str(adapter_path)
                set_current_adapter(adapter_name)

            self._client = DirectLlamaClient(**kwargs)
            self._current_model = target_model
            logger.info(f"Model loaded: {target_model}")

        return self._client

    def generate(
        self,
        prompt: str,
        model: str = None,
        adapter: str = None,
        temperature: float = 0.3,
        max_tokens: int = 512,
        **kwargs,
    ) -> str:
        """Generate text with direct GGUF.

        Args:
            prompt: User prompt
            model: Override default model
            adapter: LoRA adapter name
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            **kwargs: Additional llama-cpp params

        Returns:
            Generated text
        """
        client = self._ensure_client(model, adapter)

        try:
            response = client.generate(
                prompt=prompt, temperature=temperature, max_tokens=max_tokens, **kwargs
            )
            return response
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            # TODO: HTTP fallback to localhost:8088
            raise

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        adapter: str = None,
        **kwargs,
    ) -> Dict[str, str]:
        """Chat completion with direct GGUF.

        Args:
            messages: [{"role": "user", "content": "..."}]
            model: Override default model
            adapter: LoRA adapter name

        Returns:
            {"role": "assistant", "content": "..."}
        """
        client = self._ensure_client(model, adapter)
        return client.chat(messages, **kwargs)

    def swap_model(self, new_model: str):
        """Hot-swap to different model (keeps VRAM, reloads weights).

        Args:
            new_model: New model name (without .gguf)
        """
        logger.info(f"Swapping model: {self._current_model} -> {new_model}")
        self._client = None
        self._current_model = new_model
        # Actual load happens on next generate

    def get_current_model(self) -> Optional[str]:
        """Get current model name."""
        return self._current_model

    def get_vram_usage(self) -> Dict[str, Any]:
        """Get VRAM usage info."""
        # TODO: Implement via nvidia-smi or pynvml
        return {"estimated_mb": 0, "available_mb": 0}


# ============================================================================
# Adapter Registry - Hot-swappable LoRA adapters
# ============================================================================


class AdapterRegistry:
    """LoRA adapter registry with hot-swap support.

    Wraps frankenstein_engine.adapters with additional features:
    - Auto-discovery
    - Scale factor control
    - Adapter-specific configs
    """

    def __init__(self, adapters_dir: Path = None):
        """Initialize adapter registry.

        Args:
            adapters_dir: Directory containing LoRA adapters
        """
        self.adapters_dir = adapters_dir or ADAPTERS_DIR
        self._adapters = dict(FRANKENSTEIN_ADAPTERS)

    def discover(self) -> List[str]:
        """Discover available adapters in directory.

        Returns:
            List of adapter names
        """
        # Scan for adapter files
        discovered = []
        for name, path in self._adapters.items():
            full_path = self.adapters_dir / path
            if full_path.exists():
                discovered.append(name)
            else:
                logger.warning(f"Adapter not found: {full_path}")
        return discovered

    def list_all(self) -> Dict[str, bool]:
        """List all registered adapters with availability.

        Returns:
            {adapter_name: is_available}
        """
        result = {}
        for name, path in self._adapters.items():
            full_path = self.adapters_dir / path
            result[name] = full_path.exists()
        return result

    def load(self, name: str, scale: float = 1.0) -> Path:
        """Load adapter (hot-swap).

        Args:
            name: Adapter name
            scale: LoRA scaling factor

        Returns:
            Path to adapter file
        """
        if name not in self._adapters:
            raise AdapterLoadError(f"Unknown adapter: {name}")

        adapter_path = load_adapter(name)
        logger.info(f"Loaded adapter: {name} (scale={scale})")
        return adapter_path

    def unload(self):
        """Unload current adapter."""
        unload_adapter()
        logger.info("Adapter unloaded")

    def get_active(self) -> Optional[str]:
        """Get currently active adapter."""
        return get_current_adapter()


# ============================================================================
# Request Router - Consolidated routing
# ============================================================================


class RequestRouter:
    """Consolidated request router.

    Combines:
    - Complexity-based routing (from RouterBrain)
    - Task classification
    - Remote fallback decision
    """

    # Model selection by complexity
    COMPLEXITY_MODELS = {
        "simple": "qwen2.5-0.5b-instruct-q4_k_m",
        "medium": "qwen2.5-coder-7b-q4_k_m",
        "complex": "qwen2.5-coder-7b-q4_k_m",  # Could fallback to remote
    }

    def __init__(self, model_manager: ModelManager):
        """Initialize request router.

        Args:
            model_manager: ModelManager instance
        """
        self._model_manager = model_manager
        self._router_brain = RouterBrain()

    def route(self, prompt: str, context: Dict = None) -> Dict[str, Any]:
        """Route prompt to optimal model/adapter.

        Args:
            prompt: User prompt
            context: Optional context dict

        Returns:
            {
                "model": str,
                "adapter": str or None,
                "complexity": "simple|medium|complex",
                "method": "local|remote",
                "categories": [str],
            }
        """
        # Use RouterBrain for complexity analysis
        result = self._router_brain.route(prompt)

        complexity = result.get("complexity", "medium")
        categories = result.get("categories", ["general"])

        # Select model by complexity
        model = self.COMPLEXITY_MODELS.get(
            complexity, self._model_manager.default_model
        )

        # Select adapter by task/category
        adapter = self._get_adapter_for_task(categories)

        # Determine if remote needed (for future)
        method = "local"  # Currently always local

        return {
            "model": model,
            "adapter": adapter,
            "complexity": complexity,
            "method": method,
            "categories": categories,
        }

    def _get_adapter_for_task(self, categories: List[str]) -> Optional[str]:
        """Get adapter for task categories.

        Args:
            categories: Detected categories

        Returns:
            Adapter name or None
        """
        # Map categories to adapters
        category_adapter_map = {
            "coding": "rosetta-lora",
            "reasoning": "rosetta-lora",
            "analysis": "rosetta-lora",
            "creative": None,
            "math": None,
            "summarization": "fast-explore-lora",
        }

        for cat in categories:
            if cat in category_adapter_map:
                adapter = category_adapter_map[cat]
                if adapter and validate_adapter(adapter):
                    return adapter
        return None


# ============================================================================
# ModelOrchestrator - Main unified API
# ============================================================================


class ModelOrchestrator:
    """Unified API for all local LLM operations.

    Single entry point that combines:
    - ModelManager (direct GGUF)
    - AdapterRegistry (LoRA hot-swap)
    - RequestRouter (auto-routing)
    - HealthMonitor (system health)
    """

    def __init__(self, config: Dict = None):
        """Initialize orchestrator.

        Args:
            config: Optional config dict
        """
        config = config or {}

        # Initialize components
        self._model_manager = ModelManager(
            default_model=config.get("default_model"),
            n_ctx=config.get("n_ctx", 32768),
            n_threads=config.get("n_threads", 16),
        )
        self._adapter_registry = AdapterRegistry()
        self._request_router = RequestRouter(self._model_manager)
        self._health_monitor = HealthMonitor()

        logger.info("ModelOrchestrator initialized")

    def generate(
        self,
        prompt: str,
        model: str = None,
        adapter: str = None,
        auto_route: bool = True,
        **kwargs,
    ) -> str:
        """Generate text with auto-routing.

        Args:
            prompt: User prompt
            model: Force specific model
            adapter: Force specific adapter
            auto_route: Use routing decision
            **kwargs: Generation params

        Returns:
            Generated text
        """
        # Auto-route if enabled
        if auto_route and not model:
            routing = self._route(prompt)
            model = routing["model"]
            adapter = adapter or routing["adapter"]

        return self._model_manager.generate(
            prompt=prompt, model=model, adapter=adapter, **kwargs
        )

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        adapter: str = None,
        auto_route: bool = True,
        **kwargs,
    ) -> Dict[str, str]:
        """Chat completion with auto-routing.

        Args:
            messages: [{"role": "user", "content": "..."}]
            model: Force specific model
            adapter: Force specific adapter
            auto_route: Use routing decision

        Returns:
            {"role": "assistant", "content": "..."}
        """
        if auto_route and not model:
            # Use first user message for routing
            user_msg = next((m["content"] for m in messages if m["role"] == "user"), "")
            routing = self._route(user_msg)
            model = routing["model"]
            adapter = adapter or routing["adapter"]

        return self._model_manager.chat(
            messages=messages, model=model, adapter=adapter, **kwargs
        )

    def route(self, prompt: str) -> Dict[str, Any]:
        """Route prompt without generating.

        Args:
            prompt: User prompt

        Returns:
            Routing decision dict
        """
        return self._route(prompt)

    def _route(self, prompt: str) -> Dict[str, Any]:
        """Internal routing helper."""
        return self._request_router.route(prompt)

    def set_adapter(self, adapter_name: str, scale: float = 1.0):
        """Set active LoRA adapter (hot-swap).

        Args:
            adapter_name: Adapter name
            scale: LoRA scaling factor
        """
        self._adapter_registry.load(adapter_name, scale)

    def unset_adapter(self):
        """Unload current adapter."""
        self._adapter_registry.unload()

    def list_adapters(self) -> Dict[str, bool]:
        """List available adapters."""
        return self._adapter_registry.list_all()

    def set_model(self, model_name: str):
        """Switch base model.

        Args:
            model_name: Model name (without .gguf)
        """
        self._model_manager.swap_model(model_name)

    def get_health(self) -> Dict[str, Any]:
        """Get system health status.

        Returns:
            Health status dict
        """
        return self._health_monitor.show_status()

    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status.

        Returns:
            Full status dict
        """
        return {
            "model": self._model_manager.get_current_model(),
            "adapter": self._adapter_registry.get_active(),
            "adapters": self.list_adapters(),
            "health": self.get_health(),
        }


# ============================================================================
# Global Singleton
# ============================================================================

_orchestrator: Optional[ModelOrchestrator] = None


def get_orchestrator(config: Dict = None) -> ModelOrchestrator:
    """Get or create global orchestrator instance.

    Args:
        config: Optional config

    Returns:
        ModelOrchestrator singleton
    """
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ModelOrchestrator(config)
    return _orchestrator


def reset_orchestrator():
    """Reset global orchestrator (for testing)."""
    global _orchestrator
    _orchestrator = None


# ============================================================================
# CLI Entry Point
# ============================================================================

if __name__ == "__main__":
    import sys

    orchestrator = get_orchestrator()

    if len(sys.argv) < 2:
        print("ModelOrchestrator CLI")
        print("Usage:")
        print("  generate <prompt>")
        print("  route <prompt>")
        print("  adapters")
        print("  status")
        sys.exit(1)

    command = sys.argv[1]

    if command == "generate":
        prompt = " ".join(sys.argv[2:])
        result = orchestrator.generate(prompt)
        print(result)

    elif command == "route":
        prompt = " ".join(sys.argv[2:])
        import json

        print(json.dumps(orchestrator.route(prompt), indent=2))

    elif command == "adapters":
        import json

        print(json.dumps(orchestrator.list_adapters(), indent=2))

    elif command == "status":
        import json

        print(json.dumps(orchestrator.get_status(), indent=2))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
