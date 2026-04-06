"""Config Manager — YAML/JSON config with env overrides"""

import json, logging, os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ConfigManager:
    def __init__(self, config_dir: str = "configs"):
        self.config_dir = Path(config_dir)
        self._cache: Dict[str, dict] = {}

    def load(self, name: str) -> Dict:
        if name in self._cache:
            return self._cache[name]
        for ext in [".json", ".yaml", ".yml"]:
            path = self.config_dir / f"{name}{ext}"
            if path.exists():
                if ext == ".json":
                    config = json.loads(path.read_text(encoding="utf-8"))
                else:
                    try:
                        import yaml

                        config = yaml.safe_load(path.read_text(encoding="utf-8"))
                    except ImportError:
                        config = json.loads(path.read_text(encoding="utf-8"))
                config = self._apply_env_overrides(config)
                self._cache[name] = config
                return config
        logger.warning(f"ConfigManager: {name} not found")
        return {}

    def _apply_env_overrides(self, config: Dict) -> Dict:
        for key, value in config.items():
            env_key = f"CONFIG_{key.upper()}"
            env_value = os.environ.get(env_key)
            if env_value is not None:
                config[key] = env_value
        return config

    def get(self, name: str, key: str, default: Any = None) -> Any:
        config = self.load(name)
        return config.get(key, default)
