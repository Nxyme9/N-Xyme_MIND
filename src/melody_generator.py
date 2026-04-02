"""Melody Generator — AI melody generation"""

import random
from typing import Dict, List

SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "pentatonic": [0, 2, 4, 7, 9],
    "blues": [0, 3, 5, 6, 7, 10],
}

NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


class MelodyGenerator:
    def generate(self, key: str = "C", scale: str = "major", bars: int = 4, bpm: int = 120) -> Dict:
        intervals = SCALES.get(scale, SCALES["major"])
        key_idx = NOTES.index(key) if key in NOTES else 0
        notes = []
        beat_duration = 60.0 / bpm
        current_time = 0.0
        for i in range(bars * 4):
            interval = random.choice(intervals)
            octave = random.choice([0, 12])
            note_idx = (key_idx + interval + octave) % 12
            duration = random.choice([beat_duration, beat_duration * 0.5, beat_duration * 2])
            notes.append(
                {
                    "note": NOTES[note_idx],
                    "time": round(current_time, 3),
                    "duration": round(duration, 3),
                    "velocity": random.randint(60, 127),
                }
            )
            current_time += duration
        return {
            "key": key,
            "scale": scale,
            "bpm": bpm,
            "notes": notes,
            "total_duration": round(current_time, 2),
        }
