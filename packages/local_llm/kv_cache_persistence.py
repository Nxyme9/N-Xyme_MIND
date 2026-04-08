#!/usr/bin/env python3
"""
KV Cache Persistence - Save/restore llama-cpp-python KV cache state

Based on research:
- llm.save_state() returns state object (includes KV cache)
- llm.load_state(state) restores state
- Supports cache_type and kv_cache_quantization params

Usage:
    from packages.local_llm.kv_cache_persistence import KVCacheManager

    manager = KVCacheManager()
    manager.save("session.bin")
    manager.load("session.bin")
"""

import logging
import pickle
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class KVCacheManager:
    """Manages KV cache state save/restore for GGUF models."""

    def __init__(self, cache_dir: str = "cache/kv_cache", max_states: int = 5):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_states = max_states
        self._current_state = None
        self._llm = None

    def attach_llm(self, llm) -> None:
        """Attach llama-cpp-python Llama instance."""
        self._llm = llm

    def save(self, filename: str = "session.bin") -> bool:
        """Save current KV cache state to disk.

        Args:
            filename: Name of cache file (default: session.bin)

        Returns:
            True if successful, False otherwise
        """
        if self._llm is None:
            logger.error("No LLM attached - call attach_llm() first")
            return False

        try:
            # Save state (includes KV cache, RNG, logits)
            state = self._llm.save_state()

            filepath = self.cache_dir / filename
            with open(filepath, "wb") as f:
                pickle.dump(state, f)

            # Cleanup old states
            self._cleanup_old_states()

            logger.info(f"KV cache saved to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to save KV cache: {e}")
            return False

    def load(self, filename: str = "session.bin") -> bool:
        """Load KV cache state from disk.

        Args:
            filename: Name of cache file to load

        Returns:
            True if successful, False otherwise
        """
        if self._llm is None:
            logger.error("No LLM attached - call attach_llm() first")
            return False

        filepath = self.cache_dir / filename

        if not filepath.exists():
            logger.warning(f"Cache file not found: {filepath}")
            return False

        try:
            with open(filepath, "rb") as f:
                state = pickle.load(f)

            self._llm.load_state(state)
            logger.info(f"KV cache loaded from {filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to load KV cache: {e}")
            return False

    def _cleanup_old_states(self) -> None:
        """Remove old cache states, keeping most recent."""
        states = sorted(self.cache_dir.glob("*.bin"))

        if len(states) > self.max_states:
            for old in states[: -self.max_states]:
                old.unlink()
                logger.debug(f"Removed old cache: {old}")

    def list_caches(self) -> list[str]:
        """List available cache files."""
        return [p.name for p in self.cache_dir.glob("*.bin")]

    def get_cache_path(self, filename: str = "session.bin") -> Path:
        """Get full path for cache file."""
        return self.cache_dir / filename


# Singleton
_cache_manager: Optional[KVCacheManager] = None


def get_kv_cache_manager() -> KVCacheManager:
    """Get singleton cache manager."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = KVCacheManager()
    return _cache_manager


# Convenience functions
def save_kv_cache(filename: str = "session.bin") -> bool:
    """Save current KV cache."""
    return get_kv_cache_manager().save(filename)


def load_kv_cache(filename: str = "session.bin") -> bool:
    """Load KV cache from file."""
    return get_kv_cache_manager().load(filename)


if __name__ == "__main__":
    # Test
    manager = KVCacheManager()
    print("Available caches:", manager.list_caches())
