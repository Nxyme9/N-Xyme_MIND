"""Compressor Simulator — Dynamic range compression"""

import logging
from typing import List

logger = logging.getLogger(__name__)


class CompressorSimulator:
    def apply(
        self,
        samples: List[float],
        threshold: float = -20.0,
        ratio: float = 4.0,
        attack_ms: float = 10.0,
        release_ms: float = 100.0,
        sample_rate: int = 44100,
    ) -> List[float]:
        import math

        threshold_linear = 10 ** (threshold / 20)
        output = []
        gain = 1.0
        for sample in samples:
            abs_sample = abs(sample)
            if abs_sample > threshold_linear:
                target_gain = (
                    threshold_linear / abs_sample + (1 - threshold_linear / abs_sample) / ratio
                )
            else:
                target_gain = 1.0
            if target_gain < gain:
                gain = target_gain
            else:
                gain += (target_gain - gain) * 0.01
            output.append(sample * gain)
        return output
