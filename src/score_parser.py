"""Score Parser — Music notation parser"""

import re, logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class ScoreParser:
    def parse(self, notation: str) -> List[Dict]:
        notes = []
        pattern = r"([A-Ga-g][#b]?)(\d*)([/\.]?)(\d*)"
        for match in re.finditer(pattern, notation):
            note, octave, dot, duration = match.groups()
            notes.append(
                {
                    "note": note.upper(),
                    "octave": int(octave) if octave else 4,
                    "duration": float(duration) if duration else 1.0,
                    "dotted": dot == ".",
                }
            )
        return notes

    def to_string(self, notes: List[Dict]) -> str:
        parts = []
        for n in notes:
            parts.append(f"{n['note']}{n.get('octave', 4)}{n.get('duration', 1)}")
        return " ".join(parts)
