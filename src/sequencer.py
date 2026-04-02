"""Sequencer — Step sequencer"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class Sequencer:
    def __init__(self, steps: int = 16, tracks: int = 4):
        self.steps = steps
        self.tracks = tracks
        self.grid = [[0] * steps for _ in range(tracks)]

    def set_step(self, track: int, step: int, value: int = 1):
        if 0 <= track < self.tracks and 0 <= step < self.steps:
            self.grid[track][step] = value

    def get_pattern(self) -> List[List[int]]:
        return self.grid

    def from_dict(self, pattern: Dict[str, List[int]]):
        for i, (name, steps) in enumerate(pattern.items()):
            if i < self.tracks:
                for j, val in enumerate(steps):
                    if j < self.steps:
                        self.grid[i][j] = val

    def clear(self):
        self.grid = [[0] * self.steps for _ in range(self.tracks)]
