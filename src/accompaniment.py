"""Accompaniment — Auto-accompaniment generator"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class AccompanimentGenerator:
    def generate(self, key: str = "C", style: str = "pop", bars: int = 4, bpm: int = 120) -> Dict:
        from chord_progression import ChordProgression
        from drum_machine import DrumMachine

        chords = ChordProgression().generate(key, style, bars)
        drums = DrumMachine().get_pattern(style, bars)
        bass_notes = []
        for chord in chords["chords"]:
            bass_notes.append({"note": chord[0], "octave": 2, "duration": 60.0 / bpm * 4})
        return {
            "chords": chords,
            "drums": drums,
            "bass": bass_notes,
            "bpm": bpm,
            "bars": bars,
        }
