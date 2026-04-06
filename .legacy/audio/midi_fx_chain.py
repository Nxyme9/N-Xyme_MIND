"""MIDI FX Chain — MIDI effects processing"""

import logging, random
from typing import Dict, List

logger = logging.getLogger(__name__)


class MIDIFXChain:
    def __init__(self):
        self._effects = []

    def add_effect(self, effect_type: str, params: dict = None):
        self._effects.append({"type": effect_type, "params": params or {}})

    def process(self, notes: List[Dict]) -> List[Dict]:
        output = notes
        for effect in self._effects:
            output = self._apply_effect(output, effect)
        return output

    def _apply_effect(self, notes: List[Dict], effect: dict) -> List[Dict]:
        if effect["type"] == "transpose":
            semitones = effect["params"].get("semitones", 0)
            return [{**n, "note": n.get("note", 60) + semitones} for n in notes]
        elif effect["type"] == "velocity_scale":
            factor = effect["params"].get("factor", 1.0)
            return [{**n, "velocity": min(127, int(n.get("velocity", 64) * factor))} for n in notes]
        elif effect["type"] == "humanize":
            amount = effect["params"].get("amount", 10)
            return [
                {**n, "time": n.get("time", 0) + random.randint(-amount, amount)} for n in notes
            ]
        return notes

    def clear(self):
        self._effects.clear()
