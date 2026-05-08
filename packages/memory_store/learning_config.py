"""Learning system configuration with feature flags and thresholds.

Core learning features (enabled, rerank, tempr) default to ON for
active self-learning. Advanced features (consolidate, forget) default
to OFF until tested. Config can be overridden via environment variables.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()

LEARNING_CONFIG_DEFAULTS = {
    # Master switches
    "enabled": True,  # Enable learning cycle
    "rerank_enabled": True,  # Enable preference-based reranking
    "consolidate_enabled": False,  # Keep OFF until consolidation is tested
    "forget_enabled": False,  # Keep OFF until forgetting is tested
    "tempr_enabled": True,  # Enable TEMPR multi-strategy retrieval
    # Thresholds
    "min_confidence": 0.8,
    "exploration_rate": 0.2,
    "consolidation_threshold": 0.95,
    # Timing
    "learning_cycle_minutes": 120,
    "feedback_ttl_days": 90,
    "mandatory_retention_days": 30,
    # Paths
    "db_path": str(PROJECT_ROOT / "context/memory/file_registry.db"),
    "config_path": str(PROJECT_ROOT / ".sisyphus/learning-config.json"),
    # Feature flags (all OFF by default for safe rollout)
    "singleton_enabled": True,  # T0.1-T0.2: Module-level singletons
    "health_metrics_enabled": True,  # T0.3: Real health metrics
    "recovery_enabled": False,  # T0.4: Auto-recovery (keep OFF until tested)
    "thread_safety_enabled": True,  # T0.5: Thread locks
    "signals_enabled": False,  # Phase 2: Signals taxonomy
    "event_bus_enabled": False,  # Phase 1: LearningEventBus
    "etgpo_enabled": False,  # Phase 3: ETGPO
    "evoskill_enabled": False,  # Phase 3: EvoSkill
}

_config_cache: Optional[dict] = None


def _merge_config(base: dict, updates: dict) -> dict:
    """Deep merge updates into base config."""
    result = base.copy()
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_config(result[key], value)
        else:
            result[key] = value
    return result


def _apply_env_overrides(config: dict) -> dict:
    """Apply environment variable overrides."""
    env_map = {
        "LEARNING_ENABLED": "enabled",
        "LEARNING_RERANK_ENABLED": "rerank_enabled",
        "LEARNING_CONSOLIDATE_ENABLED": "consolidate_enabled",
        "LEARNING_FORGET_ENABLED": "forget_enabled",
        "LEARNING_MIN_CONFIDENCE": "min_confidence",
        "LEARNING_EXPLORATION_RATE": "exploration_rate",
        "LEARNING_CONSOLIDATION_THRESHOLD": "consolidation_threshold",
        "LEARNING_CYCLE_MINUTES": "learning_cycle_minutes",
        "LEARNING_FEEDBACK_TTL_DAYS": "feedback_ttl_days",
    }
    for env_var, config_key in env_map.items():
        if env_var in os.environ:
            val = os.environ[env_var]
            # Convert to appropriate type
            if isinstance(config[config_key], bool):
                config[config_key] = val.lower() in ("true", "1", "yes")
            elif isinstance(config[config_key], (int, float)):
                config[config_key] = type(config[config_key])(val)
            else:
                config[config_key] = val
    return config


def load_config() -> dict:
    """Load configuration from file, merge with defaults."""
    config = LEARNING_CONFIG_DEFAULTS.copy()
    config_path = Path(config["config_path"])

    if config_path.exists():
        try:
            with open(config_path) as f:
                file_config = json.load(f)
            config = _merge_config(config, file_config)
            logger.info(f"Loaded learning config from {config_path}")
        except Exception as e:
            logger.warning(f"Failed to load learning config: {e}")

    config = _apply_env_overrides(config)
    return config


def save_config(config: Optional[dict] = None) -> None:
    """Save configuration to file."""
    if config is None:
        config = get_config()
    config_path = Path(config["config_path"])
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    logger.info(f"Saved learning config to {config_path}")


def get_config(key: Optional[str] = None) -> Any:
    """Get current configuration.

    Args:
        key: Optional specific key to retrieve. If None, returns full config.

    Returns:
        Current configuration dict, or specific value if key provided.
    """
    global _config_cache
    if _config_cache is None:
        _config_cache = load_config()

    if key is not None:
        return _config_cache.get(key)
    return _config_cache


def update_config(updates: dict) -> dict:
    """Merge updates into current configuration.

    Args:
        updates: Dictionary of config values to update.

    Returns:
        Updated configuration dictionary.
    """
    global _config_cache
    if _config_cache is None:
        _config_cache = load_config()

    _config_cache = _merge_config(_config_cache, updates)
    _config_cache = _apply_env_overrides(_config_cache)
    return _config_cache


def is_feature_enabled(feature_name: str) -> bool:
    """Check if a feature flag is enabled.

    Args:
        feature_name: Name of the feature flag (e.g., 'singleton_enabled').

    Returns:
        True if the feature is enabled, False otherwise.
    """
    config = get_config()
    return config.get(feature_name, False)


def reset_config() -> None:
    """Reset the cached configuration."""
    global _config_cache
    _config_cache = None


if __name__ == "__main__":
    config = get_config()
    logger.info("Learning Configuration:")
    logger.info(f"  Enabled: {config['enabled']}")
    logger.info(f"  Rerank enabled: {config['rerank_enabled']}")
    logger.info(f"  Consolidate enabled: {config['consolidate_enabled']}")
    logger.info(f"  Forget enabled: {config['forget_enabled']}")
    logger.info(f"  Min confidence: {config['min_confidence']}")
    logger.info(f"  Exploration rate: {config['exploration_rate']}")
    logger.info(f"  Consolidation threshold: {config['consolidation_threshold']}")
    logger.info(f"  Learning cycle: {config['learning_cycle_minutes']} minutes")
    logger.info(f"  Feedback TTL: {config['feedback_ttl_days']} days")
    logger.info(f"  Mandatory retention: {config['mandatory_retention_days']} days")
    logger.info(f"  DB path: {config['db_path']}")
    logger.info(f"  Config path: {config['config_path']}")
