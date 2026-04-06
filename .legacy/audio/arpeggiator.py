"""Arpeggiator — Arpeggio generator"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

PATTERNS = {
    "up": [0, 1, 2, 3],
    "down": [3, 2, 1, 0],
    "updown": [0, 1, 2, 3, 2, 1],
    "random": None,
}


class Arpeggiator:
    def generate(
        self, chord_notes: List[str], pattern: str = "up", octaves: int = 1, bpm: int = 120
    ) -> Dict:
        import random

        beat_duration = 60.0 / bpm
        pattern_steps = PATTERNS.get(pattern)
        if pattern_steps is None:
            pattern_steps = list(range(len(chord_notes)))
            random.shuffle(pattern_steps)
        sequence = []
        for octave in range(octaves):
            for step in pattern_steps:
                if step < len(chord_notes):
                    sequence.append(
                        {"note": chord_notes[step], "octave": octave + 4, "duration": beat_duration}
                    )
        return {
            "pattern": pattern,
            "notes": sequence,
            "total_duration": len(sequence) * beat_duration,
        }
