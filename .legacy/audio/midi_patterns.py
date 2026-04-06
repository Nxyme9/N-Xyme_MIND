"""MIDI Patterns — MIDI pattern generation"""

import logging, random
from typing import Dict, List

logger = logging.getLogger(__name__)


class MIDIPatterns:
    def generate_scale(self, root: int = 60, scale: str = "major", octaves: int = 2) -> List[int]:
        SCALES = {
            "major": [0, 2, 4, 5, 7, 9, 11],
            "minor": [0, 2, 3, 5, 7, 8, 10],
            "pentatonic": [0, 2, 4, 7, 9],
            "blues": [0, 3, 5, 6, 7, 10],
        }
        intervals = SCALES.get(scale, SCALES["major"])
        notes = []
        for octave in range(octaves):
            for interval in intervals:
                notes.append(root + interval + octave * 12)
        return notes

    def generate_arpeggio(
        self, chord: List[int], pattern: str = "up", length: int = 16
    ) -> List[int]:
        if pattern == "up":
            seq = chord * (length // len(chord) + 1)
        elif pattern == "down":
            seq = list(reversed(chord)) * (length // len(chord) + 1)
        else:
            seq = [random.choice(chord) for _ in range(length)]
        return seq[:length]

    def generate_chord(self, root: int, intervals: List[int]) -> List[int]:
        return [root + i for i in intervals]
