"""Drum Machine — Drum pattern generation"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

PATTERNS = {
    "basic": {
        "kick": [1, 0, 0, 0, 1, 0, 0, 0],
        "snare": [0, 0, 1, 0, 0, 0, 1, 0],
        "hihat": [1, 1, 1, 1, 1, 1, 1, 1],
    },
    "hiphop": {
        "kick": [1, 0, 0, 0, 0, 0, 1, 0],
        "snare": [0, 0, 1, 0, 0, 0, 1, 0],
        "hihat": [1, 0, 1, 0, 1, 0, 1, 0],
    },
    "rock": {
        "kick": [1, 0, 0, 1, 0, 0, 1, 0],
        "snare": [0, 0, 1, 0, 0, 0, 1, 0],
        "hihat": [1, 1, 1, 1, 1, 1, 1, 1],
    },
    "techno": {
        "kick": [1, 0, 0, 0, 1, 0, 0, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 0],
        "hihat": [0, 1, 0, 1, 0, 1, 0, 1],
    },
}


class DrumMachine:
    def get_pattern(self, name: str, bars: int = 4) -> Dict:
        pattern = PATTERNS.get(name, PATTERNS["basic"])
        extended = {}
        for drum, hits in pattern.items():
            extended[drum] = hits * bars
        return {
            "name": name,
            "bars": bars,
            "steps": len(extended.get("kick", [])),
            "pattern": extended,
        }

    def list_patterns(self) -> List[str]:
        return list(PATTERNS.keys())
