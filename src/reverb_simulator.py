"""Reverb Simulator — Simple reverb effect"""

import logging
from typing import List

logger = logging.getLogger(__name__)


class ReverbSimulator:
    def apply(
        self,
        samples: List[float],
        decay: float = 0.5,
        delay_ms: float = 50,
        sample_rate: int = 44100,
    ) -> List[float]:
        delay_samples = int(delay_ms * sample_rate / 1000)
        output = samples.copy()
        for i in range(delay_samples, len(output)):
            output[i] += output[i - delay_samples] * decay
        max_val = max(abs(s) for s in output) if output else 1.0
        return [s / max_val for s in output]
