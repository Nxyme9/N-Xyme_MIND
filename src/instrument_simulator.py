"""Instrument Simulator — Virtual instruments"""

import logging, math
from typing import Dict, List

logger = logging.getLogger(__name__)


class InstrumentSimulator:
    NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

    def note_to_freq(self, note: str, octave: int = 4) -> float:
        idx = self.NOTES.index(note) if note in self.NOTES else 0
        return 440.0 * (2 ** ((idx - 9 + (octave - 4) * 12) / 12))

    def generate_note(
        self,
        note: str,
        octave: int,
        duration: float,
        instrument: str = "piano",
        sample_rate: int = 44100,
    ) -> List[float]:
        freq = self.note_to_freq(note, octave)
        samples = int(duration * sample_rate)
        t = [i / sample_rate for i in range(samples)]
        if instrument == "piano":
            wave = [math.sin(2 * math.pi * freq * ti) * math.exp(-ti * 3) for ti in t]
        elif instrument == "organ":
            wave = [
                0.5 * math.sin(2 * math.pi * freq * ti)
                + 0.3 * math.sin(4 * math.pi * freq * ti)
                + 0.2 * math.sin(6 * math.pi * freq * ti)
                for ti in t
            ]
        elif instrument == "bass":
            wave = [math.sin(2 * math.pi * freq * ti) * (1 - ti / duration) for ti in t]
        else:
            wave = [math.sin(2 * math.pi * freq * ti) for ti in t]
        return wave
