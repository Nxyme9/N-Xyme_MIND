"""Config file operations for N-Xyme MIND Dashboard.

Provides ConfigManager class for reading, writing, validating, and backing up
configuration files (JSON and YAML formats).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import yaml


class ConfigManager:
    """Manages configuration files for the N-Xyme MIND Dashboard.
    
    Supports both JSON and YAML configuration files with validation,
    backup, and restore capabilities.
    """
    
    def __init__(self, config_dir: Path | str | None = None) -> None:
        """Initialize ConfigManager.
        
        Args:
            config_dir: Optional config directory path. Defaults to src/dashboard/config.
        """
        if config_dir is None:
            self._config_dir = Path(__file__).parent / "config"
        else:
            self._config_dir = Path(config_dir)
        self._config_dir.mkdir(parents=True, exist_ok=True)
    
    def read_config(self, path: Path | str) -> dict[str, Any]:
        """Read configuration from JSON or YAML file.
        
        Args:
            path: Path to the configuration file.
            
        Returns:
            Dictionary containing the configuration data.
            
        Raises:
            FileNotFoundError: If the config file does not exist.
            ValueError: If the file format is not supported.
        """
        path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        
        suffix = path.suffix.lower()
        
        if suffix in (".json",):
            return json.loads(content)
        elif suffix in (".yaml", ".yml"):
            return yaml.safe_load(content) or {}
        else:
            raise ValueError(f"Unsupported config format: {suffix}")
    
    def write_config(self, path: Path | str, data: dict[str, Any]) -> bool:
        """Write configuration to JSON or YAML file.
        
        Creates a .bak backup before writing.
        
        Args:
            path: Path to the configuration file.
            data: Dictionary containing configuration data.
            
        Returns:
            True if successful, False otherwise.
        """
        path = Path(path)
        
        # Create backup before writing
        if path.exists():
            self.backup_config(path)
        
        suffix = path.suffix.lower()
        
        try:
            with open(path, "w", encoding="utf-8") as f:
                if suffix in (".json",):
                    json.dump(data, f, indent=2, ensure_ascii=False)
                elif suffix in (".yaml", ".yml"):
                    yaml.safe_dump(data, f, indent=2, allow_unicode=True, default_flow_style=False)
                else:
                    return False
            return True
        except Exception:
            return False
    
    def validate_config(self, path: Path | str) -> tuple[bool, list[str]]:
        """Validate configuration file syntax.
        
        Args:
            path: Path to the configuration file.
            
        Returns:
            Tuple of (valid, error_list). valid is True if no errors found.
        """
        path = Path(path)
        errors: list[str] = []
        
        if not path.exists():
            errors.append(f"Config file not found: {path}")
            return False, errors
        
        suffix = path.suffix.lower()
        
        if suffix not in (".json", ".yaml", ".yml"):
            errors.append(f"Unsupported config format: {suffix}")
            return False, errors
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            if suffix in (".json",):
                json.loads(content)
            elif suffix in (".yaml", ".yml"):
                yaml.safe_load(content)
            
            return True, []
        except json.JSONDecodeError as e:
            errors.append(f"JSON syntax error: {e}")
            return False, errors
        except yaml.YAMLError as e:
            errors.append(f"YAML syntax error: {e}")
            return False, errors
        except Exception as e:
            errors.append(f"Validation error: {e}")
            return False, errors
    
    def backup_config(self, path: Path | str) -> bool:
        """Create a .bak backup of the configuration file.
        
        Args:
            path: Path to the configuration file.
            
        Returns:
            True if backup created successfully, False otherwise.
        """
        path = Path(path)
        backup_path = path.with_suffix(path.suffix + ".bak")
        
        try:
            shutil.copy2(path, backup_path)
            return True
        except Exception:
            return False
    
    def restore_config(self, backup_path: Path | str) -> bool:
        """Restore configuration from a .bak backup file.
        
        Args:
            backup_path: Path to the backup file.
            
        Returns:
            True if restore successful, False otherwise.
        """
        backup_path = Path(backup_path)
        original_path = backup_path.with_suffix("")
        
        if not backup_path.exists():
            return False
        
        try:
            shutil.copy2(backup_path, original_path)
            return True
        except Exception:
            return False
    
    def get_config_dir(self) -> Path:
        """Get the configuration directory path.
        
        Returns:
            Path to the config directory.
        """
        return self._config_dir
