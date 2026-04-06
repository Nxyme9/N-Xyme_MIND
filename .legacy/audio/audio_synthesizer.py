"""Audio Synthesizer — Generate tones"""

import math, logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class AudioSynthesizer:
    def generate_tone(
        self, frequency: float, duration: float, sample_rate: int = 44100, waveform: str = "sine"
    ) -> List[float]:
        samples = int(duration * sample_rate)
        t = [i / sample_rate for i in range(samples)]
        if waveform == "sine":
            return [math.sin(2 * math.pi * frequency * ti) for ti in t]
        elif waveform == "square":
            return [1.0 if math.sin(2 * math.pi * frequency * ti) > 0 else -1.0 for ti in t]
        elif waveform == "sawtooth":
            return [2.0 * (ti * frequency - math.floor(0.5 + ti * frequency)) for ti in t]
        elif waveform == "triangle":
            return [4.0 * abs(ti * frequency - math.floor(ti * frequency + 0.5)) - 1.0 for ti in t]
        return [0.0] * samples

    def generate_chord(
        self, root_freq: float, intervals: List[int], duration: float, sample_rate: int = 44100
    ) -> List[float]:
        import numpy as np

        chord = np.zeros(int(duration * sample_rate))
        for interval in intervals:
            freq = root_freq * (2 ** (interval / 12))
            tone = np.array(self.generate_tone(freq, duration, sample_rate))
            chord[: len(tone)] += tone
        return (chord / len(intervals)).tolist()
