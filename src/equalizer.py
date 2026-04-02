"""Equalizer — Graphic EQ simulation"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

BANDS = [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]


class Equalizer:
    def __init__(self):
        self.gains: Dict[int, float] = {freq: 0.0 for freq in BANDS}

    def set_gain(self, freq: int, gain_db: float):
        if freq in self.gains:
            self.gains[freq] = max(-12.0, min(12.0, gain_db))

    def get_gains(self) -> Dict[int, float]:
        return self.gains.copy()

    def apply(self, samples: List[float], sample_rate: int = 44100) -> List[float]:
        try:
            import numpy as np
            from scipy import signal

            output = np.array(samples)
            for freq, gain_db in self.gains.items():
                if gain_db == 0:
                    continue
                gain = 10 ** (gain_db / 20)
                nyquist = sample_rate / 2
                if freq >= nyquist:
                    continue
                low = max(20, freq / 1.5) / nyquist
                high = min(nyquist - 1, freq * 1.5) / nyquist
                b, a = signal.butter(2, [low, high], btype="band")
                filtered = signal.filtfilt(b, a, output)
                output += filtered * (gain - 1)
            return output.tolist()
        except ImportError:
            logger.warning("scipy not installed, returning original")
            return samples
