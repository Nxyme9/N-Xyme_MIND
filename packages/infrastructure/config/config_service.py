"""Config Service — Central configuration management"""

import json, logging, os
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ConfigService:
    def __init__(self, config_file: str = "data/config.json"):
        self.config_file = Path(config_file)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self._config: Dict = {}
        self._load()

    def _load(self):
        if self.config_file.exists():
            self._config = json.loads(self.config_file.read_text(encoding="utf-8"))

    def _save(self):
        self.config_file.write_text(json.dumps(self._config, indent=2), encoding="utf-8")

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any):
        keys = key.split(".")
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        self._save()
