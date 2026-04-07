"""Spine Fallback - Golden Spine Fallback Chain Wrapper.

Implements fallback execution for Golden Spine with circuit breaker integration.
Tries primary model first, falls back to secondary models on failure.
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from packages.intelligence.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
    get_circuit_breaker_registry,
)
from packages.intelligence.fallback import FallbackChain

logger = logging.getLogger("spine-fallback")


@dataclass
class SpineFallbackResult:
    """Result of SpineFallback execution."""

    success: bool = False
    model_used: str = ""
    latency_ms: float = 0.0
    error: Optional[str] = None
    fallback_path: List[str] = field(default_factory=list)


class SpineFallback:
    """Fallback wrapper for Golden Spine with circuit breaker integration.

    Executes prompts with automatic failover to fallback models.
    Integrates with persistent circuit breaker for failure detection.
    """

    def __init__(
        self,
        primary_model: str = "qwen2.5-coder:7b",
        fallback_models: Optional[List[str]] = None,
        config_path: str = "configs/model_router.json",
    ):
        """Initialize SpineFallback.

        Args:
            primary_model: Primary model to try first
            fallback_models: List of fallback models in order (default: ["llama3.2:3b"])
            config_path: Path to model router configuration
        """
        self.config_path = Path(config_path)
        self.primary_model = primary_model
        self.fallback_models = fallback_models or ["llama3.2:3b"]

        # Build complete chain: primary + fallbacks
        self._chain: List[str] = [self.primary_model] + self.fallback_models

        # Initialize circuit breaker registry
        self._circuit_registry = get_circuit_breaker_registry(config_path)

        # Create fallback chain using existing intelligence pattern
        self._fallback_chain = FallbackChain(self._chain, str(config_path))

        self._lock = threading.Lock()
        logger.info(f"Initialized SpineFallback: {self._chain}")

    def execute(
        self,
        prompt: str,
        model: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> SpineFallbackResult:
        """Execute prompt with fallback chain.

        Args:
            prompt: The prompt to send to the model
            model: Override model (uses primary if not specified)
            config: Additional configuration options

        Returns:
            SpineFallbackResult with execution details
        """
        result = SpineFallbackResult(fallback_path=list(self._chain))
        start_time = time.time()

        # Determine which models to try
        models_to_try: List[str] = []
        if model:
            models_to_try = [model]
        else:
            models_to_try = list(self._chain)

        logger.info(f"Executing fallback chain with models: {models_to_try}")

        with self._lock:
            for idx, model_name in enumerate(models_to_try):
                # Check circuit breaker
                if not self._circuit_registry.can_execute(model_name):
                    from packages.intelligence.circuit_breaker import CircuitState

                    breaker = self._circuit_registry.get_breaker(model_name)
                    state = breaker.get_state()
                    logger.info(
                        f"Skipping model '{model_name}' - circuit breaker is {state.value}"
                    )
                    result.fallback_path.append(f"{model_name}:skipped_circuit_open")
                    continue

                result.fallback_path.append(model_name)
                logger.info(f"Attempting model: {model_name}")

                try:
                    # Execute the prompt with this model
                    response = self._execute_model(model_name, prompt, config or {})

                    # Record success in circuit breaker
                    self._circuit_registry.record_success(model_name)

                    result.success = True
                    result.model_used = model_name
                    logger.info(f"Model '{model_name}' succeeded")
                    break

                except Exception as e:
                    error_msg = str(e)
                    logger.warning(f"Model '{model_name}' failed: {error_msg}")

                    # Record failure in circuit breaker
                    self._circuit_registry.record_failure(model_name)
                    result.fallback_path[-1] = f"{model_name}:failed"
                    result.error = error_msg

            # If no model succeeded
            if not result.success:
                logger.warning(
                    f"All {len(models_to_try)} models in fallback chain failed"
                )

        result.latency_ms = (time.time() - start_time) * 1000
        return result

    def _execute_model(
        self,
        model: str,
        prompt: str,
        config: Dict[str, Any],
    ) -> Any:
        """Execute prompt with a specific model.

        Args:
            model: Model name to use
            prompt: Prompt to send
            config: Configuration options

        Returns:
            Model response

        Raises:
            Exception: If model fails to produce a response
        """
        from packages.local_llm.ollama_client import LocalLLM

        # Determine base URL based on model provider
        if model.startswith("ollama/"):
            base_url = "http://localhost:11434"
            actual_model = model.replace("ollama/", "")
        elif model.startswith("opencode/"):
            # OpenCode models would use different client
            # For now, raise not implemented
            raise NotImplementedError(f"OpenCode models not yet implemented: {model}")
        else:
            # Assume Ollama for unknown providers
            base_url = "http://localhost:11434"
            actual_model = model

        # Create client and execute
        llm = LocalLLM(model=actual_model, base_url=base_url)

        messages = [{"role": "user", "content": prompt}]
        response = llm.chat(messages)

        # Check for error response
        if isinstance(response, dict):
            content = response.get("content", "")
            if content.startswith("Error:"):
                raise Exception(content)
            return response

        raise Exception(f"Unexpected response type: {type(response)}")

    def get_chain(self) -> List[str]:
        """Get current fallback chain order.

        Returns:
            List of model names in order
        """
        return list(self._chain)

    def get_available_models(self) -> List[str]:
        """Get models not blocked by circuit breaker.

        Returns:
            List of models that can execute
        """
        available = []
        with self._lock:
            for model in self._chain:
                if self._circuit_registry.can_execute(model):
                    available.append(model)
        return available

    def get_status(self) -> Dict[str, Any]:
        """Get status of fallback chain with circuit breaker states.

        Returns:
            Dictionary with chain status
        """
        with self._lock:
            chain_status = []
            for model in self._chain:
                breaker = self._circuit_registry.get_breaker(model)
                state_info = breaker.get_state_info()
                chain_status.append(
                    {
                        "model": model,
                        "circuit_state": state_info["state"],
                        "can_execute": state_info["can_execute"],
                        "failures": state_info["failures"],
                    }
                )

            return {
                "primary": self.primary_model,
                "fallbacks": self.fallback_models,
                "chain": self._chain,
                "chain_status": chain_status,
                "available_models": self.get_available_models(),
                "total_models": len(self._chain),
            }

    def reset_circuit_breakers(self) -> None:
        """Reset all circuit breakers for this fallback chain."""
        self._circuit_registry.reset_all()
        logger.info("Reset all circuit breakers for SpineFallback")


# Global instance
_fallback_instance: Optional[SpineFallback] = None
_fallback_lock = threading.Lock()


def get_spine_fallback(
    primary_model: str = "qwen2.5-coder:7b",
    fallback_models: Optional[List[str]] = None,
    config_path: str = "configs/model_router.json",
) -> SpineFallback:
    """Get or create the global SpineFallback instance.

    Args:
        primary_model: Primary model to try first
        fallback_models: List of fallback models
        config_path: Path to model router configuration

    Returns:
        SpineFallback instance
    """
    global _fallback_instance

    if fallback_models is None:
        fallback_models = ["llama3.2:3b"]

    with _fallback_lock:
        if _fallback_instance is None:
            _fallback_instance = SpineFallback(
                primary_model=primary_model,
                fallback_models=fallback_models,
                config_path=config_path,
            )
            logger.info(
                f"Created global SpineFallback: primary={primary_model}, fallbacks={fallback_models}"
            )

        return _fallback_instance


def reset_spine_fallback() -> None:
    """Reset the global SpineFallback instance."""
    global _fallback_instance

    with _fallback_lock:
        if _fallback_instance is not None:
            _fallback_instance.reset_circuit_breakers()
            _fallback_instance = None
            logger.info("Reset global SpineFallback instance")
