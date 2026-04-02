"""Noise Gate — Silence below threshold"""

import logging
from typing import List

logger = logging.getLogger(__name__)


class NoiseGate:
    def apply(
        self,
        samples: List[float],
        threshold_db: float = -40.0,
        attack_ms: float = 1.0,
        release_ms: float = 100.0,
        sample_rate: int = 44100,
    ) -> List[float]:
        threshold = 10 ** (threshold_db / 20)
        output = []
        gate_open = True
        for sample in samples:
            abs_sample = abs(sample)
            if abs_sample < threshold:
                gate_open = False
            else:
                gate_open = True
            output.append(sample if gate_open else 0.0)
        return output
