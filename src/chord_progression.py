"""Chord Progression — Generate chord progressions"""

import random
from typing import List, Dict

PROGRESSIONS = {
    "pop": ["I", "V", "vi", "IV"],
    "jazz": ["ii", "V", "I", "vi"],
    "blues": ["I", "I", "I", "I", "IV", "IV", "I", "I", "V", "IV", "I", "V"],
    "electronic": ["i", "VI", "III", "VII"],
    "rock": ["I", "bVII", "IV", "I"],
}

NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
MAJOR_INTERVALS = [0, 2, 4, 5, 7, 9, 11]
MINOR_INTERVALS = [0, 2, 3, 5, 7, 8, 10]


class ChordProgression:
    def generate(self, key: str = "C", style: str = "pop", bars: int = 4) -> Dict:
        prog = PROGRESSIONS.get(style, PROGRESSIONS["pop"])
        key_idx = NOTES.index(key) if key in NOTES else 0
        chords = []
        for i in range(bars):
            degree = prog[i % len(prog)]
            interval = MAJOR_INTERVALS[
                int(
                    degree.replace("i", "1")
                    .replace("I", "1")
                    .replace("V", "5")
                    .replace("b", "")
                    .strip()
                )
                - 1
            ]
            if "b" in degree:
                interval -= 1
            if degree.islower():
                interval = MINOR_INTERVALS[
                    int(degree.replace("i", "1").replace("v", "5").strip()) - 1
                ]
            chord_note = NOTES[(key_idx + interval) % 12]
            chord_type = "m" if degree.islower() else ""
            chords.append(f"{chord_note}{chord_type}")
        return {"key": key, "style": style, "chords": chords, "bars": bars}
