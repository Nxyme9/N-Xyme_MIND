"""Trigger Engine — Event trigger system"""

import logging, time
from typing import Callable, Dict, List

logger = logging.getLogger(__name__)


class Trigger:
    def __init__(self, name: str, condition: Callable, action: Callable):
        self.name = name
        self.condition = condition
        self.action = action
        self.last_triggered = 0
        self.trigger_count = 0


class TriggerEngine:
    def __init__(self):
        self._triggers: Dict[str, Trigger] = {}

    def add(self, name: str, condition: Callable, action: Callable):
        self._triggers[name] = Trigger(name, condition, action)

    def evaluate(self, context: dict) -> List[str]:
        triggered = []
        for name, trigger in self._triggers.items():
            try:
                if trigger.condition(context):
                    trigger.action(context)
                    trigger.last_triggered = time.time()
                    trigger.trigger_count += 1
                    triggered.append(name)
            except Exception as e:
                logger.error(f"Trigger {name} failed: {e}")
        return triggered

    def get_stats(self) -> Dict:
        return {
            name: {"count": t.trigger_count, "last": t.last_triggered}
            for name, t in self._triggers.items()
        }
