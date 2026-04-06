"""Memory Core Configuration — Centralized configuration for memory_core package.

This module provides a single source of truth for all memory system parameters,
replacing scattered hardcoded values across the codebase.

Supported override sources (in order of precedence):
1. Environment variables (prefixed with MEMORY_)
2. JSON config file (path via MEMORY_CONFIG_PATH or default)
3. YAML config file (path via MEMORY_CONFIG_PATH or default)
4. Hardcoded defaults

Usage:
    from memory_core.config import get_config, MemoryCoreConfig

    config = get_config()
    print(f"RRF k value: {config.rrf_k}")

    # Access nested config
    db_config = get_config().database
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)

# Project root detection
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = PROJECT_ROOT / "context" / "memory" / "mind_from_mind.db"


# =============================================================================
# Dataclasses for Configuration Sections
# =============================================================================


@dataclass
class DatabaseConfig:
    """Database configuration."""

    path: str = "context/memory/mind_from_mind.db"
    connection_timeout_ms: int = 30000
    busy_timeout_ms: int = 5000
    wal_mode: bool = True
    pool_size: int = 5
    check_same_thread: bool = False


@dataclass
class RetrievalConfig:
    """Retrieval pipeline configuration."""

    # RRF Fusion
    rrf_k: int = 35

    # Trust-aware reranking
    trust_weight: float = 0.3

    # MMR (Maximal Marginal Relevance) reranking
    mmr_lambda: float = 0.5

    # Default retrieval parameters
    default_top_k: int = 10
    semantic_weight: float = 0.5
    keyword_weight: float = 0.5

    # Feedback threshold for weight adjustment
    feedback_threshold: int = 100


@dataclass
class PipelineConfig:
    """Retrieval pipeline stage configuration."""

    # Query analysis
    enable_query_analysis: bool = True

    # Cross-encoder reranking
    enable_cross_encoder: bool = True

    # MMR reranking
    enable_mmr_rerank: bool = True

    # Latency thresholds (ms)
    query_analysis_timeout_ms: float = 50.0
    retrieve_timeout_ms: float = 500.0
    rerank_timeout_ms: float = 200.0


@dataclass
class CognitiveConfig:
    """Cognitive engine configuration."""

    # Forgetting / Decay
    decay_enabled: bool = True
    decay_threshold: float = 0.3

    # Trust
    trust_initial: float = 0.5
    trust_verification_boost: float = 0.1
    trust_decay_days: int = 1

    # Reconsolidation
    conflict_detection_enabled: bool = True
    similarity_threshold: float = 0.85

    # Priority
    priority_update_on_access: bool = True


@dataclass
class VectorStoreConfig:
    """Vector store configuration."""

    embedding_dimension: int = 384
    index_type: str = "hnsw"
    m: int = 16
    ef_construction: int = 200
    ef_search: int = 50


@dataclass
class Config:
    """Main memory_core configuration container."""

    # Database
    database: DatabaseConfig = field(default_factory=DatabaseConfig)

    # Retrieval
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)

    # Pipeline
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)

    # Cognitive engines
    cognitive: CognitiveConfig = field(default_factory=CognitiveConfig)

    # Vector store
    vector_store: VectorStoreConfig = field(default_factory=VectorStoreConfig)

    # Environment
    env_prefix: str = "MEMORY_"


# =============================================================================
# Configuration Loading
# =============================================================================


def _get_env_prefix() -> str:
    """Get environment variable prefix."""
    return os.environ.get("MEMORY_ENV_PREFIX", "MEMORY_")


def _load_from_file(config_path: Optional[Path]) -> dict:
    """Load configuration from JSON or YAML file."""
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


def _apply_env_overrides(config: dict, prefix: str = "MEMORY_") -> dict:
    """Apply environment variable overrides to config dict.

    Environment variables are parsed with the prefix and nested keys:
    MEMORY_DATABASE_PATH -> database.path
    MEMORY_RETRIEVAL_RRF_K -> retrieval.rrf_k
    MEMORY_RRF_K -> retrieval.rrf_k (also supports flat keys)
    """
    env_mappings = {
        # Database
        "DATABASE_PATH": ("database", "path"),
        "DB_PATH": ("database", "path"),
        "DATABASE_TIMEOUT": ("database", "connection_timeout_ms"),
        "DB_TIMEOUT_MS": ("database", "connection_timeout_ms"),
        "DATABASE_POOL_SIZE": ("database", "pool_size"),
        # Retrieval
        "RRF_K": ("retrieval", "rrf_k"),
        "RETRIEVAL_RRF_K": ("retrieval", "rrf_k"),
        "TRUST_WEIGHT": ("retrieval", "trust_weight"),
        "RETRIEVAL_TRUST_WEIGHT": ("retrieval", "trust_weight"),
        "MMR_LAMBDA": ("retrieval", "mmr_lambda"),
        "RETRIEVAL_MMR_LAMBDA": ("retrieval", "mmr_lambda"),
        "DEFAULT_TOP_K": ("retrieval", "default_top_k"),
        "RETRIEVAL_DEFAULT_TOP_K": ("retrieval", "default_top_k"),
        "SEMANTIC_WEIGHT": ("retrieval", "semantic_weight"),
        "KEYWORD_WEIGHT": ("retrieval", "keyword_weight"),
        "FEEDBACK_THRESHOLD": ("retrieval", "feedback_threshold"),
        # Pipeline
        "QUERY_ANALYSIS_ENABLED": ("pipeline", "enable_query_analysis"),
        "CROSS_ENCODER_ENABLED": ("pipeline", "enable_cross_encoder"),
        "MMR_ENABLED": ("pipeline", "enable_mmr_rerank"),
        "QUERY_ANALYSIS_TIMEOUT_MS": ("pipeline", "query_analysis_timeout_ms"),
        "RETRIEVE_TIMEOUT_MS": ("pipeline", "retrieve_timeout_ms"),
        "RERANK_TIMEOUT_MS": ("pipeline", "rerank_timeout_ms"),
        # Cognitive
        "DECAY_ENABLED": ("cognitive", "decay_enabled"),
        "DECAY_THRESHOLD": ("cognitive", "decay_threshold"),
        "TRUST_INITIAL": ("cognitive", "trust_initial"),
        "TRUST_VERIFICATION_BOOST": ("cognitive", "trust_verification_boost"),
        "TRUST_DECAY_DAYS": ("cognitive", "trust_decay_days"),
        "CONFLICT_DETECTION_ENABLED": ("cognitive", "conflict_detection_enabled"),
        "SIMILARITY_THRESHOLD": ("cognitive", "similarity_threshold"),
        # Vector store
        "EMBEDDING_DIMENSION": ("vector_store", "embedding_dimension"),
        "INDEX_TYPE": ("vector_store", "index_type"),
        "HNSW_M": ("vector_store", "m"),
        "HNSW_EF_CONSTRUCTION": ("vector_store", "ef_construction"),
        "HNSW_EF_SEARCH": ("vector_store", "ef_search"),
    }

    for env_var, (section, key) in env_mappings.items():
        full_key = prefix + env_var
        if full_key in os.environ:
            val = os.environ[full_key]
            # Type inference
            if section not in config:
                config[section] = {}

            # Try to convert to appropriate type
            if val.lower() in ("true", "false"):
                config[section][key] = val.lower() == "true"
            elif val.isdigit():
                config[section][key] = int(val)
            elif val.replace(".", "").isdigit():
                config[section][key] = float(val)
            else:
                config[section][key] = val

    return config


def _dict_to_config(d: dict) -> Config:
    """Convert dict to Config dataclass."""
    db_config = DatabaseConfig(**d.get("database", {}))
    retrieval_config = RetrievalConfig(**d.get("retrieval", {}))
    pipeline_config = PipelineConfig(**d.get("pipeline", {}))
    cognitive_config = CognitiveConfig(**d.get("cognitive", {}))
    vector_store_config = VectorStoreConfig(**d.get("vector_store", {}))

    return Config(
        database=db_config,
        retrieval=retrieval_config,
        pipeline=pipeline_config,
        cognitive=cognitive_config,
        vector_store=vector_store_config,
    )


def _config_to_dict(config: Config) -> dict:
    """Convert Config dataclass to dict."""
    return {
        "database": {
            "path": config.database.path,
            "connection_timeout_ms": config.database.connection_timeout_ms,
            "busy_timeout_ms": config.database.busy_timeout_ms,
            "wal_mode": config.database.wal_mode,
            "pool_size": config.database.pool_size,
            "check_same_thread": config.database.check_same_thread,
        },
        "retrieval": {
            "rrf_k": config.retrieval.rrf_k,
            "trust_weight": config.retrieval.trust_weight,
            "mmr_lambda": config.retrieval.mmr_lambda,
            "default_top_k": config.retrieval.default_top_k,
            "semantic_weight": config.retrieval.semantic_weight,
            "keyword_weight": config.retrieval.keyword_weight,
            "feedback_threshold": config.retrieval.feedback_threshold,
        },
        "pipeline": {
            "enable_query_analysis": config.pipeline.enable_query_analysis,
            "enable_cross_encoder": config.pipeline.enable_cross_encoder,
            "enable_mmr_rerank": config.pipeline.enable_mmr_rerank,
            "query_analysis_timeout_ms": config.pipeline.query_analysis_timeout_ms,
            "retrieve_timeout_ms": config.pipeline.retrieve_timeout_ms,
            "rerank_timeout_ms": config.pipeline.rerank_timeout_ms,
        },
        "cognitive": {
            "decay_enabled": config.cognitive.decay_enabled,
            "decay_threshold": config.cognitive.decay_threshold,
            "trust_initial": config.cognitive.trust_initial,
            "trust_verification_boost": config.cognitive.trust_verification_boost,
            "trust_decay_days": config.cognitive.trust_decay_days,
            "conflict_detection_enabled": config.cognitive.conflict_detection_enabled,
            "similarity_threshold": config.cognitive.similarity_threshold,
        },
        "vector_store": {
            "embedding_dimension": config.vector_store.embedding_dimension,
            "index_type": config.vector_store.index_type,
            "m": config.vector_store.m,
            "ef_construction": config.vector_store.ef_construction,
            "ef_search": config.vector_store.ef_search,
        },
    }


# =============================================================================
# Module-Level API
# =============================================================================

_config_cache: Optional[Config] = None


def get_config(force_reload: bool = False) -> Config:
    """Get the current memory_core configuration.

    Args:
        force_reload: If True, bypass cache and reload from sources.

    Returns:
        Config dataclass with all memory_core settings.

    Example:
        >>> from memory_core.config import get_config
        >>> config = get_config()
        >>> print(f"RRF k: {config.retrieval.rrf_k}")
        >>> print(f"DB path: {config.database.path}")
    """
    global _config_cache

    if _config_cache is not None and not force_reload:
        return _config_cache

    # Start with defaults as dict
    config_dict = _config_to_dict(Config())

    # Load from file (if specified)
    config_path_str = os.environ.get("MEMORY_CONFIG_PATH")
    if config_path_str:
        config_path = Path(config_path_str)
        file_config = _load_from_file(config_path)
        if file_config:
            # Deep merge
            for section, values in file_config.items():
                if section in config_dict and isinstance(values, dict):
                    config_dict[section].update(values)
                else:
                    config_dict[section] = values

    # Apply environment overrides
    prefix = _get_env_prefix()
    config_dict = _apply_env_overrides(config_dict, prefix)

    # Convert to dataclass
    _config_cache = _dict_to_config(config_dict)

    # Resolve relative paths
    if (
        _config_cache.database.path
        and not Path(_config_cache.database.path).is_absolute()
    ):
        _config_cache.database.path = str(PROJECT_ROOT / _config_cache.database.path)

    logger.debug(
        f"Loaded memory_core config: DB={_config_cache.database.path}, RRF_k={_config_cache.retrieval.rrf_k}"
    )

    return _config_cache


def update_config(updates: dict) -> Config:
    """Update configuration with new values.

    Args:
        updates: Dict with section.key nested values or flat keys.

    Returns:
        Updated Config dataclass.

    Example:
        >>> from memory_core.config import update_config
        >>> config = update_config({"retrieval": {"rrf_k": 50}})
        >>> config = update_config({"RRF_K": 50})  # Also supports env-style keys
    """
    global _config_cache

    current = get_config()
    current_dict = _config_to_dict(current)

    # Apply updates
    for key, value in updates.items():
        if isinstance(value, dict):
            if key in current_dict:
                current_dict[key].update(value)
            else:
                current_dict[key] = value
        else:
            # Flat key - try to find the right section
            found = False
            for section, section_values in current_dict.items():
                if key.lower() in [k.lower() for k in section_values]:
                    for k, v in section_values.items():
                        if k.lower() == key.lower():
                            current_dict[section][k] = value
                            found = True
                            break
                if found:
                    break

    # Re-apply env overrides after update
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

    # Database validation
    if config.database.connection_timeout_ms <= 0:
        errors.append("database.connection_timeout_ms must be positive")
    if config.database.pool_size <= 0:
        errors.append("database.pool_size must be positive")

    # Retrieval validation
    if not 1 <= config.retrieval.rrf_k <= 1000:
        errors.append("retrieval.rrf_k must be between 1 and 1000")
    if not 0.0 <= config.retrieval.trust_weight <= 1.0:
        errors.append("retrieval.trust_weight must be between 0.0 and 1.0")
    if not 0.0 <= config.retrieval.mmr_lambda <= 1.0:
        errors.append("retrieval.mmr_lambda must be between 0.0 and 1.0")
    if not 1 <= config.retrieval.default_top_k <= 100:
        errors.append("retrieval.default_top_k must be between 1 and 100")
    if not 0.0 <= config.retrieval.semantic_weight <= 1.0:
        errors.append("retrieval.semantic_weight must be between 0.0 and 1.0")
    if not 0.0 <= config.retrieval.keyword_weight <= 1.0:
        errors.append("retrieval.keyword_weight must be between 0.0 and 1.0")

    # Pipeline validation
    if config.pipeline.query_analysis_timeout_ms <= 0:
        errors.append("pipeline.query_analysis_timeout_ms must be positive")
    if config.pipeline.retrieve_timeout_ms <= 0:
        errors.append("pipeline.retrieve_timeout_ms must be positive")
    if config.pipeline.rerank_timeout_ms <= 0:
        errors.append("pipeline.rerank_timeout_ms must be positive")

    # Cognitive validation
    if not 0.0 <= config.cognitive.decay_threshold <= 1.0:
        errors.append("cognitive.decay_threshold must be between 0.0 and 1.0")
    if not 0.0 <= config.cognitive.trust_initial <= 1.0:
        errors.append("cognitive.trust_initial must be between 0.0 and 1.0")
    if not 0.0 <= config.cognitive.trust_verification_boost <= 1.0:
        errors.append("cognitive.trust_verification_boost must be between 0.0 and 1.0")
    if not 0.0 <= config.cognitive.similarity_threshold <= 1.0:
        errors.append("cognitive.similarity_threshold must be between 0.0 and 1.0")

    # Vector store validation
    if config.vector_store.embedding_dimension <= 0:
        errors.append("vector_store.embedding_dimension must be positive")
    if config.vector_store.index_type not in ("hnsw", "flat", "ivf"):
        errors.append(f"vector_store.index_type must be one of: hnsw, flat, ivf")
    if config.vector_store.m <= 0:
        errors.append("vector_store.m must be positive")
    if config.vector_store.ef_construction <= 0:
        errors.append("vector_store.ef_construction must be positive")
    if config.vector_store.ef_search <= 0:
        errors.append("vector_store.ef_search must be positive")

    return len(errors) == 0, errors


def save_config(config: Optional[Config] = None, path: Optional[Path] = None) -> None:
    """Save configuration to file.

    Args:
        config: Config to save. If None, uses current config.
        path: Path to save to. If None, uses MEMORY_CONFIG_PATH env or default.
    """
    if config is None:
        config = get_config()

    if path is None:
        path_str = os.environ.get("MEMORY_CONFIG_PATH", "")
        if path_str:
            path = Path(path_str)
        else:
            path = PROJECT_ROOT / ".sisyphus" / "memory-config.json"

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    config_dict = _config_to_dict(config)

    with open(path, "w") as f:
        json.dump(config_dict, f, indent=2)

    logger.info(f"Saved memory_core config to {path}")


# =============================================================================
# Convenience Accessors
# =============================================================================


def get_rrf_k() -> int:
    """Get RRF k value."""
    return get_config().retrieval.rrf_k


def get_trust_weight() -> float:
    """Get trust weight for reranking."""
    return get_config().retrieval.trust_weight


def get_mmr_lambda() -> float:
    """Get MMR lambda for diversity reranking."""
    return get_config().retrieval.mmr_lambda


def get_db_path() -> str:
    """Get database path."""
    return get_config().database.path


def get_default_top_k() -> int:
    """Get default top-k for retrieval."""
    return get_config().retrieval.default_top_k


# =============================================================================
# Module Entry Point
# =============================================================================

if __name__ == "__main__":
    config = get_config()
    print("Memory Core Configuration")
    print("=" * 50)
    print(f"Database path: {config.database.path}")
    print(f"  Pool size: {config.database.pool_size}")
    print(f"  Timeout: {config.database.connection_timeout_ms}ms")
    print()
    print(f"Retrieval:")
    print(f"  RRF k: {config.retrieval.rrf_k}")
    print(f"  Trust weight: {config.retrieval.trust_weight}")
    print(f"  MMR lambda: {config.retrieval.mmr_lambda}")
    print(f"  Default top-k: {config.retrieval.default_top_k}")
    print()
    print(f"Cognitive:")
    print(f"  Decay enabled: {config.cognitive.decay_enabled}")
    print(f"  Trust initial: {config.cognitive.trust_initial}")
    print(f"  Similarity threshold: {config.cognitive.similarity_threshold}")
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
    env_vars = [k for k in os.environ if k.startswith("MEMORY_")]
    if env_vars:
        print(f"\nEnvironment overrides ({len(env_vars)}):")
        for var in env_vars[:10]:
            print(f"  {var}={os.environ[var]}")
        if len(env_vars) > 10:
            print(f"  ... and {len(env_vars) - 10} more")
