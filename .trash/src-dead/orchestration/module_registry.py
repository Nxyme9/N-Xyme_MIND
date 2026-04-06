"""Module Registry — Dynamic module discovery and registration"""

import importlib, logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ModuleRegistry:
    def __init__(self):
        self._modules: Dict[str, dict] = {}

    def register(self, name: str, module_path: str, description: str = "", version: str = "1.0.0"):
        self._modules[name] = {
            "path": module_path,
            "description": description,
            "version": version,
            "loaded": False,
            "instance": None,
        }
        logger.info(f"ModuleRegistry: Registered '{name}'")

    def load(self, name: str) -> Any:
        if name not in self._modules:
            raise ValueError(f"Module '{name}' not registered")
        if self._modules[name]["loaded"]:
            return self._modules[name]["instance"]
        try:
            module = importlib.import_module(self._modules[name]["path"])
            self._modules[name]["instance"] = module
            self._modules[name]["loaded"] = True
            return module
        except Exception as e:
            logger.error(f"ModuleRegistry: Failed to load '{name}': {e}")
            raise

    def get(self, name: str) -> Dict:
        return self._modules.get(name, {})

    def list_all(self) -> List[str]:
        return list(self._modules.keys())

    def list_loaded(self) -> List[str]:
        return [name for name, info in self._modules.items() if info["loaded"]]
