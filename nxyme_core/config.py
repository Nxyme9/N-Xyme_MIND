"""N-Xyme Configuration Schema — Validation for module configs."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class NXymeConfig:
    """Configuration for N-Xyme core and modules."""

    # Core settings
    log_level: str = "INFO"
    data_dir: Path = field(default_factory=lambda: Path.home() / ".nxyme")

    # Module settings
    modules: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Feature flags
    enable_memory: bool = True
    enable_learning: bool = True
    enable_orchestration: bool = True
    enable_intelligence: bool = True

    def __post_init__(self):
        """Ensure data directory exists."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        config = asdict(self)
        # Convert Path to string for JSON serialization
        config["data_dir"] = str(self.data_dir)
        return config

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "NXymeConfig":
        """Create from dictionary."""
        # Convert string back to Path
        if "data_dir" in config and isinstance(config["data_dir"], str):
            config["data_dir"] = Path(config["data_dir"])
        return cls(**config)

    @classmethod
    def from_file(cls, path: Path) -> "NXymeConfig":
        """Load configuration from JSON file."""
        with open(path) as f:
            return cls.from_dict(json.load(f))

    def to_file(self, path: Path) -> None:
        """Save configuration to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    def validate(self) -> tuple[bool, list[str]]:
        """Validate configuration.

        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors = []

        # Log level validation
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level not in valid_levels:
            errors.append(f"Invalid log_level: {self.log_level}")

        # Data directory must be writable
        if not self.data_dir.exists():
            try:
                self.data_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create data_dir: {e}")

        return (len(errors) == 0, errors)


class ModuleConfig:
    """Configuration for a specific module."""

    def __init__(self, name: str, enabled: bool = True, **kwargs):
        self.name = name
        self.enabled = enabled
        self._settings = kwargs

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting."""
        return self._settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a setting."""
        self._settings[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {"name": self.name, "enabled": self.enabled, **self._settings}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModuleConfig":
        """Create from dictionary."""
        name = data.pop("name")
        enabled = data.pop("enabled", True)
        return cls(name, enabled, **data)


def get_default_config() -> NXymeConfig:
    """Get default configuration."""
    return NXymeConfig()


def load_config(config_path: Optional[Path] = None) -> NXymeConfig:
    """Load configuration from file or return defaults."""
    if config_path and config_path.exists():
        try:
            return NXymeConfig.from_file(config_path)
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")

    return get_default_config()
