"""Feature Flags — On/off/percentage feature toggles"""

import logging, random
from typing import Any, Dict

logger = logging.getLogger(__name__)


class FeatureFlags:
    def __init__(self):
        self._flags: Dict[str, dict] = {}

    def set_flag(
        self, name: str, enabled: bool = True, percentage: int = 100, metadata: dict = None
    ):
        self._flags[name] = {
            "enabled": enabled,
            "percentage": percentage,
            "metadata": metadata or {},
        }

    def is_enabled(self, name: str, user_id: str = None) -> bool:
        flag = self._flags.get(name)
        if not flag or not flag["enabled"]:
            return False
        if flag["percentage"] >= 100:
            return True
        if user_id:
            hash_val = hash(f"{name}:{user_id}") % 100
            return hash_val < flag["percentage"]
        return random.randint(0, 99) < flag["percentage"]

    def get_all(self) -> Dict:
        return self._flags.copy()

    def delete(self, name: str) -> bool:
        if name in self._flags:
            del self._flags[name]
            return True
        return False
