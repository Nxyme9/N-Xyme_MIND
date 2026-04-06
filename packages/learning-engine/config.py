"""Learning Engine Configuration — Centralized configuration for learning_engine package.

This module provides a single source of truth for all learning system parameters,
including Q-Learning, reward weights, routing, and outcome logging.

Supported override sources (in order of precedence):
1. Environment variables (prefixed with LEARNING_)
2. JSON config file (path via LEARNING_CONFIG_PATH or default)
3. Hardcoded defaults

Usage:
    from learning_engine.config import get_config, LearningEngineConfig
    
    config = get_config()
    print(f"Q-Learning alpha: {config.q_learning.alpha}")
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Project root detection
PROJECT_ROOT = Path(__file__).resolve().parents[2]


# =============================================================================
# Dataclasses for Configuration Sections
# =============================================================================

@dataclass
class QLearningConfig:
    """Q-Learning reinforcement learning configuration."""
    
    # Learning parameters
    alpha: float = 0.1  # Learning rate
    gamma: float = 0.9  # Discount factor
    epsilon: float = 0.1  # Exploration rate (epsilon-greedy)
    
    # EWC (Elastic Weight Consolidation) for continual learning
    ewc_lambda: float = 0.01  # EWC regularization strength
    ewc_task_interval: int = 10  # Apply EWC penalty every N tasks


@dataclass
class BanditConfig:
    """Multi-armed bandit configuration."""
    
    epsilon: float = 0.1  # Exploration rate
    ucb_c: float = 2.0  # UCB exploration constant
    strategy: str = "epsilon"  # "epsilon", "ucb", or "thompson"
    min_pulls_before_selection: int = 0  # Arms with 0 pulls get priority


@dataclass
class RewardConfig:
    """Reward computation configuration."""
    
    # Base rewards
    base_success: float = 1.0
    base_failure: float = -1.0
    
    # Latency penalty
    latency_threshold_ms: float = 100.0
    latency_penalty_per_ms: float = 0.001
    baseline_latency_ms: float = 500.0
    
    # Quality bonus
    quality_bonus_threshold: float = 0.8
    quality_bonus_value: float = 0.5
    
    # Exploration bonus
    exploration_bonus: float = 0.1
    
    # Cost weight
    baseline_cost: float = 0.01


@dataclass
class RoutingConfig:
    """Routing/agent selection configuration."""
    
    # EMA weights for routing decisions
    ema_alpha: float = 0.1  # Learning rate for EMA
    
    # Latency scoring
    latency_cap_ms: float = 10000.0  # Cap latency at 10s for normalization
    latency_weight: float = 0.3  # Weight for latency in scoring
    
    # Success rate thresholds
    min_sample_size: int = 3  # Minimum tasks before considering agent
    min_success_rate_for_recommendation: float = 0.70  # 70% minimum


@dataclass
class ABTestConfig:
    """A/B testing configuration."""
    
    min_sample_size: int = 100
    significance_level: float = 0.05  # 95% confidence


@dataclass
class DatabaseConfig:
    """Database configuration for learning_engine."""
    
    # Main outcome database
    outcomes_db_path: str = ".sisyphus/outcomes.db"
    
    # Routing learning database
    routing_db_path: str = ".sisyphus/routing_learning.db"
    
    # Skill registry database
    skills_db_path: str = "skills.db"
    
    # Prompt evolution database
    prompts_db_path: str = "prompts.db"
    
    # Self-learning database (for self_learning.py)
    self_learning_db_path: str = "learning.db"
    
    # Connection settings
    connection_timeout_ms: int = 30000
    busy_timeout_ms: int = 5000
    pool_size: int = 5


@dataclass
class EventBusConfig:
    """Event bus configuration."""
    
    flush_threshold: int = 100
    flush_interval_seconds: float = 30.0


@dataclass
class SkillLifecycleConfig:
    """Skill lifecycle management configuration."""
    
    # Success rate thresholds for skill recommendations
    min_success_rate_for_good: float = 0.80
    min_invocations_for_good: int = 10
    
    max_failure_rate_for_acceptable: float = 0.50
    max_invocations_before_flag: int = 20


@dataclass
class AnalyticsConfig:
    """Analytics and metrics configuration."""
    
    enabled: bool = True
    record_detailed_latency: bool = True


@dataclass
class Config:
    """Main learning_engine configuration container."""
    
    q_learning: QLearningConfig = field(default_factory=QLearningConfig)
    bandit: BanditConfig = field(default_factory=BanditConfig)
    reward: RewardConfig = field(default_factory=RewardConfig)
    routing: RoutingConfig = field(default_factory=RoutingConfig)
    ab_test: ABTestConfig = field(default_factory=ABTestConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    event_bus: EventBusConfig = field(default_factory=EventBusConfig)
    skill_lifecycle: SkillLifecycleConfig = field(default_factory=SkillLifecycleConfig)
    analytics: AnalyticsConfig = field(default_factory=AnalyticsConfig)
    
    env_prefix: str = "LEARNING_"


# =============================================================================
# Configuration Loading
# =============================================================================

def _get_env_prefix() -> str:
    """Get environment variable prefix."""
    return os.environ.get("LEARNING_ENV_PREFIX", "LEARNING_")


def _load_from_file(config_path: Optional[Path]) -> dict:
    """Load configuration from JSON file."""
    if not config_path or not config_path.exists():
        return {}
    
    try:
        with open(config_path) as f:
            if config_path.suffix in (".yaml", ".yml"):
                import yaml
                return yaml.safe_load(f) or {}
            elif config_path.suffix == ".json":
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load config from {config_path}: {e}")
    
    return {}


def _apply_env_overrides(config: dict, prefix: str = "LEARNING_") -> dict:
    """Apply environment variable overrides to config dict."""
    
    env_mappings = {
        # Q-Learning
        "Q_ALPHA": ("q_learning", "alpha"),
        "Q_LEARNING_ALPHA": ("q_learning", "alpha"),
        "Q_GAMMA": ("q_learning", "gamma"),
        "Q_LEARNING_GAMMA": ("q_learning", "gamma"),
        "Q_EPSILON": ("q_learning", "epsilon"),
        "Q_LEARNING_EPSILON": ("q_learning", "epsilon"),
        "EWC_LAMBDA": ("q_learning", "ewc_lambda"),
        
        # Bandit
        "BANDIT_EPSILON": ("bandit", "epsilon"),
        "BANDIT_UCB_C": ("bandit", "ucb_c"),
        "BANDIT_STRATEGY": ("bandit", "strategy"),
        
        # Reward
        "BASE_SUCCESS": ("reward", "base_success"),
        "BASE_FAILURE": ("reward", "base_failure"),
        "LATENCY_THRESHOLD_MS": ("reward", "latency_threshold_ms"),
        "LATENCY_PENALTY_PER_MS": ("reward", "latency_penalty_per_ms"),
        "BASELINE_LATENCY_MS": ("reward", "baseline_latency_ms"),
        "QUALITY_BONUS_THRESHOLD": ("reward", "quality_bonus_threshold"),
        "QUALITY_BONUS_VALUE": ("reward", "quality_bonus_value"),
        "EXPLORATION_BONUS": ("reward", "exploration_bonus"),
        "BASELINE_COST": ("reward", "baseline_cost"),
        
        # Routing
        "ROUTING_EMA_ALPHA": ("routing", "ema_alpha"),
        "LATENCY_CAP_MS": ("routing", "latency_cap_ms"),
        "LATENCY_WEIGHT": ("routing", "latency_weight"),
        "MIN_SAMPLE_SIZE": ("routing", "min_sample_size"),
        "MIN_SUCCESS_RATE": ("routing", "min_success_rate_for_recommendation"),
        
        # A/B Testing
        "AB_TEST_MIN_SAMPLE": ("ab_test", "min_sample_size"),
        "AB_TEST_SIG_LEVEL": ("ab_test", "significance_level"),
        
        # Database paths
        "OUTCOMES_DB_PATH": ("database", "outcomes_db_path"),
        "ROUTING_DB_PATH": ("database", "routing_db_path"),
        "SKILLS_DB_PATH": ("database", "skills_db_path"),
        "PROMPTS_DB_PATH": ("database", "prompts_db_path"),
        "SELF_LEARNING_DB_PATH": ("database", "self_learning_db_path"),
        "DB_TIMEOUT_MS": ("database", "connection_timeout_ms"),
        "DB_BUSY_TIMEOUT_MS": ("database", "busy_timeout_ms"),
        
        # Event bus
        "EVENT_FLUSH_THRESHOLD": ("event_bus", "flush_threshold"),
        "EVENT_FLUSH_INTERVAL": ("event_bus", "flush_interval_seconds"),
        
        # Skill lifecycle
        "SKILL_MIN_SUCCESS_RATE": ("skill_lifecycle", "min_success_rate_for_good"),
        "SKILL_MIN_INVOCATIONS": ("skill_lifecycle", "min_invocations_for_good"),
        "SKILL_MAX_FAILURE_RATE": ("skill_lifecycle", "max_failure_rate_for_acceptable"),
        "SKILL_MAX_INVOCATIONS": ("skill_lifecycle", "max_invocations_before_flag"),
    }
    
    for env_var, (section, key) in env_mappings.items():
        full_key = prefix + env_var
        if full_key in os.environ:
            val = os.environ[full_key]
            if section not in config:
                config[section] = {}
            
            # Type inference
            if val.lower() in ("true", "false"):
                config[section][key] = val.lower() == "true"
            elif val.isdigit():
                config[section][key] = int(val)
            elif val.replace(".", "").replace("-", "").isdigit():
                config[section][key] = float(val)
            else:
                config[section][key] = val
    
    return config


def _dict_to_config(d: dict) -> Config:
    """Convert dict to Config dataclass."""
    return Config(
        q_learning=QLearningConfig(**d.get("q_learning", {})),
        bandit=BanditConfig(**d.get("bandit", {})),
        reward=RewardConfig(**d.get("reward", {})),
        routing=RoutingConfig(**d.get("routing", {})),
        ab_test=ABTestConfig(**d.get("ab_test", {})),
        database=DatabaseConfig(**d.get("database", {})),
        event_bus=EventBusConfig(**d.get("event_bus", {})),
        skill_lifecycle=SkillLifecycleConfig(**d.get("skill_lifecycle", {})),
        analytics=AnalyticsConfig(**d.get("analytics", {})),
    )


def _config_to_dict(config: Config) -> dict:
    """Convert Config dataclass to dict."""
    return {
        "q_learning": {
            "alpha": config.q_learning.alpha,
            "gamma": config.q_learning.gamma,
            "epsilon": config.q_learning.epsilon,
            "ewc_lambda": config.q_learning.ewc_lambda,
            "ewc_task_interval": config.q_learning.ewc_task_interval,
        },
        "bandit": {
            "epsilon": config.bandit.epsilon,
            "ucb_c": config.bandit.ucb_c,
            "strategy": config.bandit.strategy,
            "min_pulls_before_selection": config.bandit.min_pulls_before_selection,
        },
        "reward": {
            "base_success": config.reward.base_success,
            "base_failure": config.reward.base_failure,
            "latency_threshold_ms": config.reward.latency_threshold_ms,
            "latency_penalty_per_ms": config.reward.latency_penalty_per_ms,
            "baseline_latency_ms": config.reward.baseline_latency_ms,
            "quality_bonus_threshold": config.reward.quality_bonus_threshold,
            "quality_bonus_value": config.reward.quality_bonus_value,
            "exploration_bonus": config.reward.exploration_bonus,
            "baseline_cost": config.reward.baseline_cost,
        },
        "routing": {
            "ema_alpha": config.routing.ema_alpha,
            "latency_cap_ms": config.routing.latency_cap_ms,
            "latency_weight": config.routing.latency_weight,
            "min_sample_size": config.routing.min_sample_size,
            "min_success_rate_for_recommendation": config.routing.min_success_rate_for_recommendation,
        },
        "ab_test": {
            "min_sample_size": config.ab_test.min_sample_size,
            "significance_level": config.ab_test.significance_level,
        },
        "database": {
            "outcomes_db_path": config.database.outcomes_db_path,
            "routing_db_path": config.database.routing_db_path,
            "skills_db_path": config.database.skills_db_path,
            "prompts_db_path": config.database.prompts_db_path,
            "self_learning_db_path": config.database.self_learning_db_path,
            "connection_timeout_ms": config.database.connection_timeout_ms,
            "busy_timeout_ms": config.database.busy_timeout_ms,
            "pool_size": config.database.pool_size,
        },
        "event_bus": {
            "flush_threshold": config.event_bus.flush_threshold,
            "flush_interval_seconds": config.event_bus.flush_interval_seconds,
        },
        "skill_lifecycle": {
            "min_success_rate_for_good": config.skill_lifecycle.min_success_rate_for_good,
            "min_invocations_for_good": config.skill_lifecycle.min_invocations_for_good,
            "max_failure_rate_for_acceptable": config.skill_lifecycle.max_failure_rate_for_acceptable,
            "max_invocations_before_flag": config.skill_lifecycle.max_invocations_before_flag,
        },
        "analytics": {
            "enabled": config.analytics.enabled,
            "record_detailed_latency": config.analytics.record_detailed_latency,
        },
    }


# =============================================================================
# Module-Level API
# =============================================================================

_config_cache: Optional[Config] = None


def get_config(force_reload: bool = False) -> Config:
    """Get the current learning_engine configuration.
    
    Args:
        force_reload: If True, bypass cache and reload from sources.
    
    Returns:
        Config dataclass with all learning_engine settings.
    
    Example:
        >>> from learning_engine.config import get_config
        >>> config = get_config()
        >>> print(f"Q alpha: {config.q_learning.alpha}")
        >>> print(f"Latency threshold: {config.reward.latency_threshold_ms}")
    """
    global _config_cache
    
    if _config_cache is not None and not force_reload:
        return _config_cache
    
    config_dict = _config_to_dict(Config())
    
    # Load from file
    config_path_str = os.environ.get("LEARNING_CONFIG_PATH")
    if config_path_str:
        config_path = Path(config_path_str)
        file_config = _load_from_file(config_path)
        if file_config:
            for section, values in file_config.items():
                if section in config_dict and isinstance(values, dict):
                    config_dict[section].update(values)
                else:
                    config_dict[section] = values
    
    # Apply environment overrides
    prefix = _get_env_prefix()
    config_dict = _apply_env_overrides(config_dict, prefix)
    
    _config_cache = _dict_to_config(config_dict)
    
    # Resolve relative paths
    for attr in ["outcomes_db_path", "routing_db_path", "skills_db_path", 
                 "prompts_db_path", "self_learning_db_path"]:
        db_path = getattr(_config_cache.database, attr)
        if db_path and not Path(db_path).is_absolute():
            setattr(_config_cache.database, attr, str(PROJECT_ROOT / db_path))
    
    logger.debug(f"Loaded learning_engine config: Q(alpha={_config_cache.q_learning.alpha}, "
                f"gamma={_config_cache.q_learning.gamma}, epsilon={_config_cache.q_learning.epsilon})")
    
    return _config_cache


def update_config(updates: dict) -> Config:
    """Update configuration with new values.
    
    Args:
        updates: Dict with nested section values.
    
    Returns:
        Updated Config dataclass.
    """
    global _config_cache
    
    current = get_config()
    current_dict = _config_to_dict(current)
    
    for key, value in updates.items():
        if isinstance(value, dict):
            if key in current_dict:
                current_dict[key].update(value)
            else:
                current_dict[key] = value
    
    prefix = _get_env_prefix()
    current_dict = _apply_env_overrides(current_dict, prefix)
    
    _config_cache = _dict_to_config(current_dict)
    return _config_cache


def reset_config() -> None:
    """Reset the cached configuration."""
    global _config_cache
    _config_cache = None


def validate_config(config: Optional[Config] = None) -> tuple[bool, list[str]]:
    """Validate configuration values.
    
    Args:
        config: Config to validate. If None, uses current config.
    
    Returns:
        Tuple of (is_valid, list of validation errors).
    """
    if config is None:
        config = get_config()
    
    errors = []
    
    # Q-Learning validation
    if not 0.0 < config.q_learning.alpha <= 1.0:
        errors.append("q_learning.alpha must be between 0.0 and 1.0")
    if not 0.0 <= config.q_learning.gamma <= 1.0:
        errors.append("q_learning.gamma must be between 0.0 and 1.0")
    if not 0.0 <= config.q_learning.epsilon <= 1.0:
        errors.append("q_learning.epsilon must be between 0.0 and 1.0")
    if not 0.0 <= config.q_learning.ewc_lambda <= 1.0:
        errors.append("q_learning.ewc_lambda must be between 0.0 and 1.0")
    
    # Bandit validation
    if not 0.0 <= config.bandit.epsilon <= 1.0:
        errors.append("bandit.epsilon must be between 0.0 and 1.0")
    if config.bandit.ucb_c <= 0:
        errors.append("bandit.ucb_c must be positive")
    if config.bandit.strategy not in ("epsilon", "ucb", "thompson"):
        errors.append("bandit.strategy must be epsilon, ucb, or thompson")
    
    # Reward validation
    if not -1.0 <= config.reward.base_failure <= 0:
        errors.append("reward.base_failure must be between -1.0 and 0")
    if not 0 <= config.reward.base_success <= 1.0:
        errors.append("reward.base_success must be between 0 and 1.0")
    if config.reward.latency_threshold_ms <= 0:
        errors.append("reward.latency_threshold_ms must be positive")
    if config.reward.latency_penalty_per_ms <= 0:
        errors.append("reward.latency_penalty_per_ms must be positive")
    if not 0.0 <= config.reward.quality_bonus_threshold <= 1.0:
        errors.append("reward.quality_bonus_threshold must be between 0.0 and 1.0")
    if not 0.0 <= config.reward.quality_bonus_value <= 1.0:
        errors.append("reward.quality_bonus_value must be between 0.0 and 1.0")
    
    # Routing validation
    if not 0.0 < config.routing.ema_alpha <= 1.0:
        errors.append("routing.ema_alpha must be between 0.0 and 1.0")
    if not 0.0 <= config.routing.latency_weight <= 1.0:
        errors.append("routing.latency_weight must be between 0.0 and 1.0")
    if config.routing.min_sample_size <= 0:
        errors.append("routing.min_sample_size must be positive")
    if not 0.0 <= config.routing.min_success_rate_for_recommendation <= 1.0:
        errors.append("routing.min_success_rate_for_recommendation must be between 0.0 and 1.0")
    
    # A/B Test validation
    if config.ab_test.min_sample_size <= 0:
        errors.append("ab_test.min_sample_size must be positive")
    if not 0.0 < config.ab_test.significance_level <= 0.5:
        errors.append("ab_test.significance_level must be between 0.0 and 0.5")
    
    # Database validation
    if config.database.connection_timeout_ms <= 0:
        errors.append("database.connection_timeout_ms must be positive")
    if config.database.busy_timeout_ms <= 0:
        errors.append("database.busy_timeout_ms must be positive")
    if config.database.pool_size <= 0:
        errors.append("database.pool_size must be positive")
    
    # Event bus validation
    if config.event_bus.flush_threshold <= 0:
        errors.append("event_bus.flush_threshold must be positive")
    if config.event_bus.flush_interval_seconds <= 0:
        errors.append("event_bus.flush_interval_seconds must be positive")
    
    # Skill lifecycle validation
    if not 0.0 <= config.skill_lifecycle.min_success_rate_for_good <= 1.0:
        errors.append("skill_lifecycle.min_success_rate_for_good must be between 0.0 and 1.0")
    if config.skill_lifecycle.min_invocations_for_good <= 0:
        errors.append("skill_lifecycle.min_invocations_for_good must be positive")
    if not 0.0 <= config.skill_lifecycle.max_failure_rate_for_acceptable <= 1.0:
        errors.append("skill_lifecycle.max_failure_rate_for_acceptable must be between 0.0 and 1.0")
    if config.skill_lifecycle.max_invocations_before_flag <= 0:
        errors.append("skill_lifecycle.max_invocations_before_flag must be positive")
    
    return len(errors) == 0, errors


def save_config(config: Optional[Config] = None, path: Optional[Path] = None) -> None:
    """Save configuration to file."""
    if config is None:
        config = get_config()
    
    if path is None:
        path_str = os.environ.get("LEARNING_CONFIG_PATH", "")
        if path_str:
            path = Path(path_str)
        else:
            path = PROJECT_ROOT / ".sisyphus" / "learning-config.json"
    
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    config_dict = _config_to_dict(config)
    
    with open(path, "w") as f:
        json.dump(config_dict, f, indent=2)
    
    logger.info(f"Saved learning_engine config to {path}")


# =============================================================================
# Convenience Accessors
# =============================================================================

def get_q_learning_params() -> tuple[float, float, float]:
    """Get Q-Learning alpha, gamma, epsilon."""
    config = get_config()
    return config.q_learning.alpha, config.q_learning.gamma, config.q_learning.epsilon


def get_latency_threshold() -> float:
    """Get latency threshold for reward penalty."""
    return get_config().reward.latency_threshold_ms


def get_outcomes_db_path() -> str:
    """Get outcomes database path."""
    return get_config().database.outcomes_db_path


def get_routing_db_path() -> str:
    """Get routing learning database path."""
    return get_config().database.routing_db_path


# =============================================================================
# Module Entry Point
# =============================================================================

if __name__ == "__main__":
    config = get_config()
    print("Learning Engine Configuration")
    print("=" * 50)
    print(f"Q-Learning: alpha={config.q_learning.alpha}, gamma={config.q_learning.gamma}, "
          f"epsilon={config.q_learning.epsilon}")
    print(f"  EWC lambda: {config.q_learning.ewc_lambda}")
    print()
    print(f"Reward:")
    print(f"  Base success: {config.reward.base_success}")
    print(f"  Base failure: {config.reward.base_failure}")
    print(f"  Latency threshold: {config.reward.latency_threshold_ms}ms")
    print(f"  Latency penalty: {config.reward.latency_penalty_per_ms}/ms")
    print(f"  Quality bonus: threshold={config.reward.quality_bonus_threshold}, "
          f"value={config.reward.quality_bonus_value}")
    print()
    print(f"Routing:")
    print(f"  EMA alpha: {config.routing.ema_alpha}")
    print(f"  Min sample size: {config.routing.min_sample_size}")
    print(f"  Min success rate: {config.routing.min_success_rate_for_recommendation}")
    print()
    print(f"Database paths:")
    print(f"  Outcomes: {config.database.outcomes_db_path}")
    print(f"  Routing: {config.database.routing_db_path}")
    print(f"  Skills: {config.database.skills_db_path}")
    print()
    
    # Validate
    is_valid, errors = validate_config(config)
    if is_valid:
        print("✓ Configuration is valid")
    else:
        print("✗ Validation errors:")
        for error in errors:
            print(f"  - {error}")
    
    # Check environment overrides
    env_vars = [k for k in os.environ if k.startswith("LEARNING_")]
    if env_vars:
        print(f"\nEnvironment overrides ({len(env_vars)}):")
        for var in env_vars[:10]:
            print(f"  {var}={os.environ[var]}")
        if len(env_vars) > 10:
            print(f"  ... and {len(env_vars) - 10} more")
