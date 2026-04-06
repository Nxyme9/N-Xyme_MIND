"""
GPU VRAM Monitoring and Management Module.

Monitors GPU VRAM usage, enforces configurable limits, and makes
model loading/unloading decisions based on available memory.

Uses nvidia-smi CLI (no external GPU libraries required).

Usage:
    manager = VRAMManager(max_vram_gb=12.0, safety_margin_gb=1.0)
    status = manager.get_vram_usage()
    if manager.can_load_model(4.5):
        load_model("qwen2.5-coder:7b")
"""

from __future__ import annotations

import logging
import re
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .config import MODEL_SIZES, DEFAULT_MODEL_SIZE_GB

logger = logging.getLogger(__name__)

MB_TO_GB = 1024.0


MODEL_SIZES: Dict[str, float] = {
    "llama3.2:3b": 2.0,
    "llama3.2:1b": 0.7,
    "qwen2.5-coder:7b": 4.5,
    "qwen2.5-coder:14b": 9.0,
    "qwen3:8b": 5.2,
    "deepseek-r1:14b": 9.0,
    "llava:7b": 4.5,
}

DEFAULT_MODEL_SIZE_GB = 4.0

MB_TO_GB = 1024.0


@dataclass
class VRAMUsage:
    """Snapshot of GPU VRAM usage."""

    used_gb: float
    total_gb: float
    free_gb: float
    percent: float


class VRAMManagerError(Exception):
    """Raised when VRAM operations fail."""


class VRAMManager:
    """
    Monitor GPU VRAM usage and make model loading decisions.

    Enforces a configurable VRAM limit with safety margin to prevent
    OOM crashes during model loading.

    Args:
        max_vram_gb: Maximum VRAM (GB) allowed before blocking loads.
        safety_margin_gb: Buffer (GB) subtracted from max to avoid edge cases.
        gpu_index: Which GPU to monitor (0 = first GPU).

    Raises:
        VRAMManagerError: If nvidia-smi is unavailable or returns invalid data.

    Example:
        >>> mgr = VRAMManager(max_vram_gb=12.0)
        >>> usage = mgr.get_vram_usage()
        >>> print(f"VRAM: {usage.used_gb:.1f} / {usage.total_gb:.1f} GB")
        >>> if mgr.can_load_model("qwen2.5-coder:7b"):
        ...     print("Model fits in VRAM")
    """

    def __init__(
        self,
        max_vram_gb: float = 12.0,
        safety_margin_gb: float = 1.0,
        gpu_index: int = 0,
    ) -> None:
        if max_vram_gb <= 0:
            raise VRAMManagerError("max_vram_gb must be positive")
        if safety_margin_gb < 0:
            raise VRAMManagerError("safety_margin_gb must be non-negative")
        if safety_margin_gb >= max_vram_gb:
            raise VRAMManagerError("safety_margin_gb must be less than max_vram_gb")

        self.max_vram_gb = max_vram_gb
        self.safety_margin_gb = safety_margin_gb
        self.gpu_index = gpu_index
        self._loaded_models: Dict[str, float] = {}
        self._last_query_time: float = 0
        self._cached_usage: Dict[str, float] = {}
        self._cache_ttl: float = 2.0
        self._lock = threading.Lock()

    def _run_nvidia_smi(self) -> str:
        """
        Run nvidia-smi and return raw output.

        Returns:
            Raw stdout from nvidia-smi.

        Raises:
            VRAMManagerError: If nvidia-smi fails or is not found.
        """
        cmd = [
            "nvidia-smi",
            f"--id={self.gpu_index}",
            "--query-gpu=memory.used,memory.total",
            "--format=csv,noheader,nounits",
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
        except FileNotFoundError:
            raise VRAMManagerError("nvidia-smi not found. Is NVIDIA driver installed?")
        except subprocess.TimeoutExpired:
            raise VRAMManagerError("nvidia-smi timed out after 10s")
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.strip()
            raise VRAMManagerError(f"nvidia-smi failed: {stderr}") from exc

        output = result.stdout.strip()
        if not output:
            raise VRAMManagerError("nvidia-smi returned empty output")
        return output

    def _parse_nvidia_smi(self, output: str) -> tuple[float, float]:
        """
        Parse nvidia-smi output into (used_mb, total_mb).

        Args:
            output: Raw nvidia-smi output string.

        Returns:
            Tuple of (used_mb, total_mb).

        Raises:
            VRAMManagerError: If output format is unexpected.
        """
        # Expected: "1234.5, 8192.0"
        parts = [p.strip() for p in output.split(",")]
        if len(parts) != 2:
            raise VRAMManagerError(
                f"Expected 2 values from nvidia-smi, got {len(parts)}: {output!r}"
            )

        try:
            used_mb = float(parts[0])
            total_mb = float(parts[1])
        except ValueError as exc:
            raise VRAMManagerError(
                f"Cannot parse nvidia-smi output as floats: {output!r}"
            ) from exc

        if total_mb <= 0:
            raise VRAMManagerError(f"Invalid total VRAM: {total_mb} MB")

        return used_mb, total_mb

    def get_vram_usage(self) -> Dict[str, float]:
        """
        Get current GPU VRAM usage.

        Returns:
            Dict with keys: used_gb, total_gb, free_gb, percent.

        Note:
            Returns all zeros if GPU is unavailable (no crash).
        """
        if time.monotonic() - self._last_query_time < self._cache_ttl and self._cached_usage:
            return dict(self._cached_usage)

        try:
            output = self._run_nvidia_smi()
            used_mb, total_mb = self._parse_nvidia_smi(output)
        except VRAMManagerError as exc:
            logger.warning("VRAM query failed: %s", exc)
            result = {"used_gb": 0.0, "total_gb": 0.0, "free_gb": 0.0, "percent": 0.0}
            self._cached_usage = result
            self._last_query_time = time.monotonic()
            return result

        used_gb = used_mb / MB_TO_GB
        total_gb = total_mb / MB_TO_GB
        free_gb = total_gb - used_gb
        percent = (used_gb / total_gb * 100.0) if total_gb > 0 else 0.0

        result = {
            "used_gb": round(used_gb, 2),
            "total_gb": round(total_gb, 2),
            "free_gb": round(free_gb, 2),
            "percent": round(percent, 1),
        }
        self._cached_usage = result
        self._last_query_time = time.monotonic()
        return result

    @property
    def has_gpu(self) -> bool:
        """
        Check if a GPU is available.

        Returns:
            True if nvidia-smi reports a GPU with non-zero total VRAM.
        """
        usage = self.get_vram_usage()
        return usage["total_gb"] > 0

    def can_load_model(self, model_size_gb: float) -> bool:
        """
        Check if a model can be loaded without exceeding the VRAM limit.

        The effective limit is (max_vram_gb - safety_margin_gb). A model
        can load only if current usage + model size <= effective limit.

        Args:
            model_size_gb: Expected VRAM footprint of the model in GB.
                Can be a float or a model name key from MODEL_SIZES.

        Returns:
            True if the model fits within the VRAM budget.

        Example:
            >>> mgr = VRAMManager()
            >>> mgr.can_load_model(4.5)  # direct size
            True
            >>> mgr.can_load_model("qwen2.5-coder:7b")  # lookup
            True
        """
        # Resolve model name to size
        if isinstance(model_size_gb, str):
            if model_size_gb not in MODEL_SIZES:
                logger.warning(
                    "Unknown model '%s' (not in MODEL_SIZES), using default %.1f GB",
                    model_size_gb,
                    DEFAULT_MODEL_SIZE_GB,
                )
                model_size_gb = DEFAULT_MODEL_SIZE_GB
            else:
                model_size_gb = MODEL_SIZES[model_size_gb]

        if model_size_gb <= 0:
            return False

        if not self.has_gpu:
            logger.warning("No GPU available — cannot load local models")
            return False

        usage = self.get_vram_usage()
        effective_limit = self.max_vram_gb - self.safety_margin_gb
        projected_usage = usage["used_gb"] + model_size_gb

        return projected_usage <= effective_limit

    def get_available_vram(self) -> float:
        """
        Get free VRAM in GB.

        Returns:
            Free VRAM in GB. Returns 0.0 if GPU is unavailable.
        """
        usage = self.get_vram_usage()
        return usage["free_gb"]

    def is_over_limit(self) -> bool:
        """
        Check if current VRAM usage exceeds the configured limit.

        The limit is (max_vram_gb - safety_margin_gb).

        Returns:
            True if usage is at or above the effective limit.
        """
        usage = self.get_vram_usage()
        effective_limit = self.max_vram_gb - self.safety_margin_gb
        return usage["used_gb"] >= effective_limit

    def get_models_to_unload(self, target_gb: float) -> List[str]:
        """
        Determine which loaded models to unload to free target_gb of VRAM.

        Uses a greedy strategy: unload largest models first to minimize
        the number of models removed.

        Args:
            target_gb: Amount of VRAM (GB) to free up.

        Returns:
            List of model names to unload, ordered largest-first.
            Empty list if no models are loaded or target is <= 0.

        Example:
            >>> mgr = VRAMManager()
            >>> mgr._loaded_models = {"model_a": 2.0, "model_b": 4.5, "model_c": 1.0}
            >>> mgr.get_models_to_unload(5.0)
            ['model_b', 'model_a']  # 4.5 + 2.0 = 6.5 >= 5.0
        """
        if target_gb <= 0 or not self._loaded_models:
            return []

        # Sort by size descending (unload largest first)
        sorted_models = sorted(
            self._loaded_models.items(), key=lambda x: x[1], reverse=True
        )

        to_unload: List[str] = []
        freed_gb = 0.0

        for model_name, model_size in sorted_models:
            if freed_gb >= target_gb:
                break
            to_unload.append(model_name)
            freed_gb += model_size

        return to_unload

    def register_loaded_model(self, name: str, size_gb: float) -> None:
        with self._lock:
            self._loaded_models[name] = size_gb
        logger.info("Registered loaded model: %s (%.1f GB)", name, size_gb)

    def unregister_loaded_model(self, name: str) -> Optional[float]:
        with self._lock:
            size = self._loaded_models.pop(name, None)
        if size is not None:
            logger.info("Unregistered model: %s (%.1f GB)", name, size)
        return size

    def get_loaded_models(self) -> Dict[str, float]:
        with self._lock:
            return dict(self._loaded_models)

    def get_vram_budget(self) -> Dict[str, float]:
        """
        Get a summary of the VRAM budget.

        Returns:
            Dict with keys: max_gb, safety_margin_gb, effective_limit_gb,
            used_gb, available_gb, headroom_gb.
        """
        usage = self.get_vram_usage()
        effective_limit = self.max_vram_gb - self.safety_margin_gb
        headroom = effective_limit - usage["used_gb"]

        return {
            "max_gb": self.max_vram_gb,
            "safety_margin_gb": self.safety_margin_gb,
            "effective_limit_gb": round(effective_limit, 2),
            "used_gb": usage["used_gb"],
            "available_gb": usage["free_gb"],
            "headroom_gb": round(headroom, 2),
        }

    def __repr__(self) -> str:
        return (
            f"VRAMManager(max_vram_gb={self.max_vram_gb}, "
            f"safety_margin_gb={self.safety_margin_gb})"
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print("=" * 50)
    print("GPU VRAM Manager — Status")
    print("=" * 50)

    manager = VRAMManager(max_vram_gb=12.0, safety_margin_gb=1.0)
    print(f"Config: {manager}")
    print()

    # VRAM usage
    usage = manager.get_vram_usage()
    if usage["total_gb"] > 0:
        print(
            f"VRAM Usage: {usage['used_gb']:.1f} / {usage['total_gb']:.1f} GB "
            f"({usage['percent']:.1f}%)"
        )
        print(f"Free: {usage['free_gb']:.1f} GB")
    else:
        print("VRAM: GPU not available or nvidia-smi not found")

    print()

    # Budget
    budget = manager.get_vram_budget()
    print("VRAM Budget:")
    print(f"  Max:            {budget['max_gb']:.1f} GB")
    print(f"  Safety Margin:  {budget['safety_margin_gb']:.1f} GB")
    print(f"  Effective Limit: {budget['effective_limit_gb']:.1f} GB")
    print(f"  Used:           {budget['used_gb']:.1f} GB")
    print(f"  Headroom:       {budget['headroom_gb']:.1f} GB")

    print()

    # Model capacity check
    print("Model Loading Capacity:")
    for model_name, model_size in sorted(MODEL_SIZES.items(), key=lambda x: x[1]):
        can_load = manager.can_load_model(model_size)
        status = "OK" if can_load else "NO"
        print(f"  [{status}] {model_name}: {model_size:.1f} GB")

    print()

    # Over-limit check
    over = manager.is_over_limit()
    print(f"Over Limit: {'YES ⚠️' if over else 'NO'}")

    print("=" * 50)
