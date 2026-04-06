#!/usr/bin/env python3
"""
Scan Configuration — Configuration system for drive scanning.

Provides:
- load_config(config_path): Load configuration from JSON file
- save_config(config, config_path): Save configuration to JSON file
- get_config(): Get current configuration (lazy-loaded)
- update_config(updates): Merge updates into current configuration

Configuration sources (in order of precedence):
1. Environment variables (highest)
2. JSON config file
3. Default values (lowest)

Environment variables:
- SCAN_DRIVES: Comma-separated list of drive paths
- SCAN_INCLUDE_EXTENSIONS: Comma-separated file extensions to include
- SCAN_EXCLUDE_DIRS: Comma-separated directory names to exclude
- SCAN_MAX_FILE_SIZE: Maximum file size in bytes
- SCAN_BATCH_SIZE: Number of files to process in a batch
- SCAN_MAX_WORKERS: Maximum worker threads
- SCAN_OLLAMA_MODEL: Ollama embedding model
- SCAN_CHUNK_SIZE: Text chunk size for embeddings
- SCAN_CHUNK_OVERlap: Text chunk overlap
- SCAN_DB_PATH: Path to file registry database
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# Default configuration values
DEFAULT_CONFIG: Dict[str, Any] = {
    "drives": [
        os.environ.get("NX_DRIVE_LIBRARY", "/mnt/Library"),
        "/mnt/WIN_LIBRARY",
        "/mnt/NXYME_CORE",
        "/mnt/NXYME_IMAGES",
        "/mnt/backup",
    ],
    "include_extensions": [
        ".py",
        ".js",
        ".ts",
        ".md",
        ".txt",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".pdf",
        ".docx",
        ".rst",
        ".sh",
        ".bash",
    ],
    "exclude_dirs": [
        "node_modules",
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "dist",
        "build",
        "target",
        ".cache",
    ],
    "max_file_size": 10485760,  # 10MB
    "batch_size": 100,
    "max_workers": {"extraction": 16, "embedding": 4},
    "ollama_model": "nomic-embed-text",
    "chunk_size": 512,
    "chunk_overlap": 50,
    "db_path": "context/memory/file_registry.db",
}

# Environment variable to config key mapping
ENV_OVERRIDES: Dict[str, str] = {
    "SCAN_DRIVES": "drives",
    "SCAN_INCLUDE_EXTENSIONS": "include_extensions",
    "SCAN_EXCLUDE_DIRS": "exclude_dirs",
    "SCAN_MAX_FILE_SIZE": "max_file_size",
    "SCAN_BATCH_SIZE": "batch_size",
    "SCAN_MAX_WORKERS_EXTRACTION": "max_workers.extraction",
    "SCAN_MAX_WORKERS_EMBEDDING": "max_workers.embedding",
    "SCAN_MAX_WORKERS": "max_workers",
    "SCAN_OLLAMA_MODEL": "ollama_model",
    "SCAN_CHUNK_SIZE": "chunk_size",
    "SCAN_CHUNK_OVERLAP": "chunk_overlap",
    "SCAN_DB_PATH": "db_path",
}

# Module-level cached configuration
_config_cache: Optional[Dict[str, Any]] = None


def _get_config_file_path(config_path: Optional[str] = None) -> Path:
    """Get the configuration file path.

    Args:
        config_path: Optional custom config path. If not provided, defaults to
                    .sisyphus/scan-config.json in project root.

    Returns:
        Path to the config file
    """
    if config_path:
        return Path(config_path)

    # Default: project root/.sisyphus/scan-config.json
    project_root = Path(__file__).parent.parent.parent
    return project_root / ".sisyphus" / "scan-config.json"


def _parse_env_value(key: str, value: str) -> Any:
    """Parse environment variable value to appropriate type.

    Args:
        key: Configuration key
        value: String value from environment variable

    Returns:
        Parsed value of appropriate type
    """
    # Handle nested keys like "max_workers.extraction"
    if "." in key:
        # For nested keys, return string - will be handled by update logic
        return value

    # List values (comma-separated)
    if key in ["drives", "include_extensions", "exclude_dirs"]:
        return [item.strip() for item in value.split(",") if item.strip()]

    # Integer values
    if key in ["max_file_size", "batch_size", "chunk_size", "chunk_overlap"]:
        try:
            return int(value)
        except ValueError:
            return DEFAULT_CONFIG.get(key)

    # String values (default)
    return value


def _apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply environment variable overrides to configuration.

    Args:
        config: Base configuration dictionary

    Returns:
        Configuration with environment overrides applied
    """
    result = config.copy()

    for env_key, config_key in ENV_OVERRIDES.items():
        env_value = os.environ.get(env_key)
        if env_value is None:
            continue

        parsed_value = _parse_env_value(config_key, env_value)

        # Handle nested keys like "max_workers.extraction"
        if "." in config_key:
            main_key, sub_key = config_key.split(".", 1)
            if main_key in result and isinstance(result[main_key], dict):
                try:
                    result[main_key][sub_key] = int(env_value)
                except ValueError:
                    result[main_key][sub_key] = parsed_value
        else:
            result[config_key] = parsed_value

    return result


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from JSON file.

    Loads configuration from the specified JSON file, falling back to defaults
    if the file doesn't exist. Environment variables always override file values.

    Args:
        config_path: Optional path to config JSON file. If not provided,
                    defaults to .sisyphus/scan-config.json in project root.

    Returns:
        Configuration dictionary with all settings
    """
    global _config_cache

    config_file = _get_config_file_path(config_path)

    # Start with defaults
    config = DEFAULT_CONFIG.copy()

    # Try to load from file
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                file_config = json.load(f)
                # Merge file config with defaults
                config = _merge_config(config, file_config)
        except (json.JSONDecodeError, IOError) as e:
            # Log warning but continue with defaults
            import logging

            logging.getLogger(__name__).warning(
                f"Failed to load config from {config_file}: {e}"
            )

    # Apply environment variable overrides (highest precedence)
    config = _apply_env_overrides(config)

    # Cache the result
    _config_cache = config

    return config


def _merge_config(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge update dict into base config.

    Args:
        base: Base configuration dictionary
        updates: Updates to merge in

    Returns:
        Merged configuration dictionary
    """
    result = base.copy()

    for key, value in updates.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_config(result[key], value)
        else:
            result[key] = value

    return result


def save_config(config: Dict[str, Any], config_path: Optional[str] = None) -> None:
    """Save configuration to JSON file.

    Saves the provided configuration to the specified JSON file.
    Creates parent directories if they don't exist.

    Args:
        config: Configuration dictionary to save
        config_path: Optional path to save config to. If not provided,
                    defaults to .sisyphus/scan-config.json in project root.

    Raises:
        IOError: If the config file cannot be written
    """
    config_file = _get_config_file_path(config_path)

    # Ensure parent directory exists
    config_file.parent.mkdir(parents=True, exist_ok=True)

    # Write config as JSON with indentation
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def get_config() -> Dict[str, Any]:
    """Get current configuration.

    Returns the cached configuration if available, otherwise loads it.
    This is a convenience function that lazily loads the configuration.

    Returns:
        Current configuration dictionary
    """
    global _config_cache

    if _config_cache is None:
        _config_cache = load_config()

    return _config_cache


def update_config(updates: Dict[str, Any]) -> Dict[str, Any]:
    """Merge updates into current configuration.

    Updates the cached configuration with the provided updates.
    This modifies the in-memory config and returns the updated version.

    Args:
        updates: Dictionary of config values to update

    Returns:
        Updated configuration dictionary
    """
    global _config_cache

    # Load if not already loaded
    if _config_cache is None:
        _config_cache = load_config()

    # Merge updates
    _config_cache = _merge_config(_config_cache, updates)

    # Re-apply environment variable overrides
    _config_cache = _apply_env_overrides(_config_cache)

    return _config_cache


def reset_config() -> None:
    """Reset the cached configuration.

    Clears the in-memory configuration cache, forcing a reload on next get_config() call.
    """
    global _config_cache
    _config_cache = None


if __name__ == "__main__":
    # Test the configuration system
    import sys

    config = get_config()

    print(f"Drives: {len(config['drives'])} paths")
    for drive in config["drives"]:
        print(f"  - {drive}")

    print(f"\nInclude extensions: {len(config['include_extensions'])} types")
    print(f"Exclude dirs: {len(config['exclude_dirs'])} dirs")
    print(
        f"Max file size: {config['max_file_size']:,} bytes ({config['max_file_size'] // 1048576}MB)"
    )
    print(f"Batch size: {config['batch_size']}")
    print(f"Max workers (extraction): {config['max_workers']['extraction']}")
    print(f"Max workers (embedding): {config['max_workers']['embedding']}")
    print(f"Ollama model: {config['ollama_model']}")
    print(f"Chunk size: {config['chunk_size']}")
    print(f"Chunk overlap: {config['chunk_overlap']}")
    print(f"DB path: {config['db_path']}")
