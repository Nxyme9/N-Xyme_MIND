"""Lyrics Parser — LRC/SRT/VTT format parsing"""

import re, logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class LyricsParser:
    def parse_lrc(self, content: str) -> List[Dict]:
        pattern = r"\[(\d+):(\d+)\.(\d+)\](.*)"
        lyrics = []
        for match in re.finditer(pattern, content):
            minutes, seconds, centiseconds, text = match.groups()
            time = int(minutes) * 60 + int(seconds) + int(centiseconds) / 100
            lyrics.append({"time": round(time, 2), "text": text.strip()})
        return sorted(lyrics, key=lambda x: x["time"])

    def parse_srt(self, content: str) -> List[Dict]:
        blocks = content.strip().split("\n\n")
        lyrics = []
        for block in blocks:
            lines = block.strip().split("\n")
            if len(lines) >= 3:
                time_match = re.match(
                    r"(\d+):(\d+):(\d+),(\d+)\s*-->\s*(\d+):(\d+):(\d+),(\d+)", lines[1]
                )
                if time_match:
                    start = int(time_match[1]) * 3600 + int(time_match[2]) * 60 + int(time_match[3])
                    text = " ".join(lines[2:])
                    lyrics.append({"time": start, "text": text})
        return sorted(lyrics, key=lambda x: x["time"])

    def to_lrc(self, lyrics: List[Dict]) -> str:
        lines = []
        for item in lyrics:
            minutes = int(item["time"]) // 60
            seconds = int(item["time"]) % 60
            lines.append(f"[{minutes:02d}:{seconds:02d}.00]{item['text']}")
        return "\n".join(lines)
