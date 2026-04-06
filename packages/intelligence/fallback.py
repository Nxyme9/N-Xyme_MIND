"""Fallback Chain

Implements automatic failover for model routing. When a model fails,
automatically try the next model in the chain until one succeeds or
all are exhausted.
"""

import time
import json
import logging
import threading
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
from dataclasses import dataclass, field

from .circuit_breaker import get_circuit_breaker_registry, CircuitState

logger = logging.getLogger("fallback-chain")


@dataclass
class FallbackResult:
    """Result of a fallback chain execution."""

    model: str = ""
    success: bool = False
    attempts: int = 0
    errors: List[tuple] = field(default_factory=list)
    latency_ms: float = 0.0
    fallback_path: List[str] = field(default_factory=list)


class FallbackChain:
    """Fallback chain for model routing with automatic failover."""

    def __init__(
        self,
        chain: List[str],
        config_path: str = "configs/model_router.json",
    ):
        """Initialize fallback chain.

        Args:
            chain: List of model names in fallback order
            config_path: Path to model router configuration
        """
        self.config_path = Path(config_path)
        self._chain: List[str] = list(chain)
        self._config = self._load_config()
        self._circuit_breaker_registry = get_circuit_breaker_registry(config_path)
        self._lock = threading.Lock()
        logger.info(f"Initialized fallback chain: {self._chain}")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON."""
        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading config: {e}")
        return {}

    def execute(self, task_callable: Callable[[str], Any]) -> FallbackResult:
        """Execute task with fallback chain.

        Args:
            task_callable: Function that takes model_name and returns result
                          or raises an exception

        Returns:
            FallbackResult with execution details
        """
        result = FallbackResult(fallback_path=list(self._chain))
        start_time = time.time()
        errors: List[tuple] = []
        last_successful_model = ""

        with self._lock:
            for model in self._chain:
                # Check circuit breaker first
                if not self._circuit_breaker_registry.can_execute(model):
                    state = self._circuit_breaker_registry.get_breaker(
                        model
                    ).get_state()
                    logger.info(
                        f"Skipping model '{model}' - circuit breaker is {state.value}"
                    )
                    result.fallback_path.append(f"{model}:skipped_circuit_open")
                    continue

                result.fallback_path.append(model)
                result.attempts += 1
                logger.info(f"Attempting model: {model}")

                try:
                    # Execute task with this model
                    task_callable(model)

                    # Record success in circuit breaker
                    self._circuit_breaker_registry.record_success(model)

                    result.model = model
                    result.success = True
                    last_successful_model = model
                    logger.info(f"Model '{model}' succeeded")
                    break

                except Exception as e:
                    error_msg = str(e)
                    logger.warning(f"Model '{model}' failed: {error_msg}")
                    errors.append((model, error_msg))

                    # Record failure in circuit breaker
                    self._circuit_breaker_registry.record_failure(model)
                    result.fallback_path[-1] = f"{model}:failed"

            # If no model succeeded, return failure result
            if not result.success:
                result.errors = errors
                logger.warning(f"All {len(errors)} models in fallback chain failed")

        result.latency_ms = (time.time() - start_time) * 1000
        return result

    def get_chain(self) -> List[str]:
        """Get current fallback chain order.

        Returns:
            List of model names in order
        """
        with self._lock:
            return list(self._chain)

    def get_available_models(self) -> List[str]:
        """Get models not blocked by circuit breaker.

        Returns:
            List of models that can execute
        """
        available = []
        with self._lock:
            for model in self._chain:
                if self._circuit_breaker_registry.can_execute(model):
                    available.append(model)
        return available

    def reorder_chain(self, new_order: List[str]) -> None:
        """Reorder the fallback chain.

        Args:
            new_order: New order of model names
        """
        with self._lock:
            # Validate all models are in the new order
            current_set = set(self._chain)
            new_set = set(new_order)

            if current_set != new_set:
                missing = current_set - new_set
                extra = new_set - current_set
                if missing:
                    logger.warning(f"Models missing from new order: {missing}")
                if extra:
                    logger.warning(f"Extra models in new order: {extra}")

            self._chain = list(new_order)
            logger.info(f"Reordered fallback chain: {self._chain}")

    def get_status(self) -> Dict[str, Any]:
        """Get status of fallback chain with circuit breaker states.

        Returns:
            Dictionary with chain status
        """
        with self._lock:
            chain_status = []
            for model in self._chain:
                breaker = self._circuit_breaker_registry.get_breaker(model)
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
                "chain": self._chain,
                "chain_status": chain_status,
                "available_models": self.get_available_models(),
                "total_models": len(self._chain),
            }


# Global registry for fallback chains
_chains: Dict[str, FallbackChain] = {}
_chains_lock = threading.Lock()


def get_fallback_chain(
    chain_name: str = "default",
    config_path: str = "configs/model_router.json",
) -> FallbackChain:
    """Get or create a named fallback chain.

    Args:
        chain_name: Name of the chain ('default', 'local-first', 'cloud-first')
        config_path: Path to model router configuration

    Returns:
        FallbackChain instance
    """
    # Load default chain from config
    config_path_obj = Path(config_path)
    default_chain = [
        "ollama/qwen2.5-coder:7b",
        "ollama/llama3.2:3b",
        "opencode/minimax-m2.5-free",
        "opencode/mimo-v2-pro-free",
    ]

    if config_path_obj.exists():
        try:
            with open(config_path_obj) as f:
                config = json.load(f)
                chain_config = config.get("fallback_chain", [])
                if chain_config:
                    default_chain = chain_config
        except Exception as e:
            logger.warning(f"Error loading fallback chain from config: {e}")

    # Predefined chain configurations
    chain_configs = {
        "default": default_chain,
        "local-first": [
            "ollama/qwen2.5-coder:7b",
            "ollama/llama3.2:3b",
            "opencode/minimax-m2.5-free",
            "opencode/mimo-v2-pro-free",
        ],
        "cloud-first": [
            "opencode/minimax-m2.5-free",
            "opencode/mimo-v2-pro-free",
            "ollama/qwen2.5-coder:7b",
            "ollama/llama3.2:3b",
        ],
    }

    # Get chain for name or use custom
    if chain_name in chain_configs:
        chain = chain_configs[chain_name]
    else:
        # Custom chain name - use default chain
        chain = default_chain
        logger.info(f"Unknown chain name '{chain_name}', using default chain")

    global _chains

    with _chains_lock:
        if chain_name not in _chains:
            _chains[chain_name] = FallbackChain(chain, config_path)
            logger.info(f"Created fallback chain '{chain_name}': {chain}")

        return _chains[chain_name]


def reset_fallback_chain(chain_name: str = "default") -> None:
    """Reset a specific fallback chain's circuit breakers.

    Args:
        chain_name: Name of the chain to reset
    """
    registry = get_circuit_breaker_registry()
    registry.reset_all()
    logger.info(f"Reset circuit breakers for chain '{chain_name}'")


def get_all_chain_status() -> Dict[str, Dict[str, Any]]:
    """Get status of all registered fallback chains.

    Returns:
        Dictionary mapping chain names to their status
    """
    with _chains_lock:
        return {name: chain.get_status() for name, chain in _chains.items()}
