"""MIDI Learn — MIDI controller learning"""

import logging
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)


class MIDILearn:
    def __init__(self):
        self._mappings: Dict[int, dict] = {}
        self._learning = False
        self._learning_target = None

    def start_learn(self, target: str):
        self._learning = True
        self._learning_target = target
        logger.info(f"MIDILearn: Learning for {target}")

    def handle_midi(self, channel: int, value: int) -> Optional[str]:
        if self._learning and self._learning_target:
            self._mappings[channel] = {"target": self._learning_target, "value": value}
            self._learning = False
            target = self._learning_target
            self._learning_target = None
            logger.info(f"MIDILearn: Mapped CC{channel} to {target}")
            return target
        mapping = self._mappings.get(channel)
        if mapping:
            return mapping["target"]
        return None

    def get_mappings(self) -> Dict:
        return self._mappings.copy()

    def clear(self):
        self._mappings.clear()
