"""Stereo Widener — Stereo width processing"""

import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class StereoWidener:
    def widen(
        self, left: List[float], right: List[float], width: float = 1.5
    ) -> Tuple[List[float], List[float]]:
        mid = [(l + r) / 2 for l, r in zip(left, right)]
        side = [(l - r) / 2 for l, r in zip(left, right)]
        widened_left = [m + s * width for m, s in zip(mid, side)]
        widened_right = [m - s * width for m, s in zip(mid, side)]
        return widened_left, widened_right
