"""
Configuration Manager for The Catalyst

Manages loading, validation, and access to system configuration.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger("catalyst.config")


class ConfigManager:
    """
    Manages system configuration loading and access.

    Supports YAML and JSON configuration files with environment
    variable substitution.
    """

    def __init__(self, config_path: Path):
        """
        Initialize the configuration manager.

        Args:
            config_path: Path to configuration directory.
        """
        self._config_path = Path(config_path)
        self._configs: Dict[str, Any] = {}
        self._loaded = False

    async def load(self) -> None:
        """Load all configuration files."""
        if not self._config_path.exists():
            logger.warning(f"Config path does not exist: {self._config_path}")
            return

        # Load main config
        main_config = self._config_path / "opencode" / "opencode.json"
        if main_config.exists():
            self._configs["main"] = self._load_json(main_config)

        # Load agent configs
        agents_dir = self._config_path / "opencode" / "agents"
        if agents_dir.exists():
            self._configs["agents"] = {}
            for agent_file in agents_dir.glob("*.yaml"):
                agent_config = self._load_yaml(agent_file)
                if agent_config:
                    name = agent_config.get("name", agent_file.stem)
                    self._configs["agents"][name] = agent_config

        # Load permissions
        permissions_file = self._config_path / "opencode" / "permissions.json"
        if permissions_file.exists():
            self._configs["permissions"] = self._load_json(permissions_file)

        self._loaded = True
        logger.info(f"Loaded configuration from {self._config_path}")

    def _load_json(self, path: Path) -> Optional[Dict[str, Any]]:
        """Load a JSON configuration file."""
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load JSON config {path}: {e}")
            return None

    def _load_yaml(self, path: Path) -> Optional[Dict[str, Any]]:
        """Load a YAML configuration file."""
        try:
            with open(path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load YAML config {path}: {e}")
            return None

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key.

        Args:
            key: Dot-separated key path (e.g., 'agents.sisyphus.type')
            default: Default value if key not found.

        Returns:
            Configuration value or default.
        """
        parts = key.split(".")
        value = self._configs

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
                if value is None:
                    return default
            else:
                return default

        return value

    def get_all(self) -> Dict[str, Any]:
        """Get all configuration."""
        return self._configs.copy()

    def is_loaded(self) -> bool:
        """Check if configuration has been loaded."""
        return self._loaded

    def __repr__(self) -> str:
        return f"<ConfigManager path={self._config_path} loaded={self._loaded}>"
