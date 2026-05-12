from __future__ import annotations
import json
import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger("nxyme_dictate.history")

HISTORY_DIR = Path.home() / ".cache" / "nxyme-dictate" / "history"
MAX_HISTORY_SIZE = 1000


class TranscriptionHistory:
    def __init__(self, history_dir: Path = HISTORY_DIR, max_size: int = MAX_HISTORY_SIZE):
        self._dir = history_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._max_size = max_size
        self._current_file = self._dir / f"history_{datetime.now().strftime('%Y-%m-%d')}.jsonl"
        self._count = 0
        self._load_today_count()

    def _load_today_count(self):
        if self._current_file.exists():
            with open(self._current_file) as f:
                self._count = sum(1 for _ in f)

    def add(
        self,
        text: str,
        language: Optional[str] = None,
        model: Optional[str] = None,
        duration_ms: int = 0,
        word_count: int = 0,
        device: Optional[int] = None,
    ) -> str:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "text": text,
            "language": language,
            "model": model,
            "duration_ms": duration_ms,
            "word_count": word_count,
            "device": device,
        }

        with open(self._current_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

        self._count += 1
        entry_id = f"{datetime.now().strftime('%H%M%S')}-{self._count:04d}"

        if self._count >= self._max_size:
            self._cleanup_old()

        return entry_id

    def _cleanup_old(self):
        files = sorted(self._dir.glob("history_*.jsonl"))
        if len(files) > 7:
            for f in files[:-7]:
                try:
                    f.unlink()
                except OSError:
                    pass

    def get_recent(self, limit: int = 10) -> list[dict]:
        if not self._current_file.exists():
            return []
        results = []
        with open(self._current_file) as f:
            for line in f:
                try:
                    results.append(json.loads(line))
                    if len(results) >= limit:
                        break
                except json.JSONDecodeError:
                    continue
        return list(reversed(results))

    def search(self, query: str, limit: int = 20) -> list[dict]:
        results = []
        for f in sorted(self._dir.glob("history_*.jsonl"), reverse=True):
            with open(f) as fh:
                for line in fh:
                    try:
                        entry = json.loads(line)
                        if query.lower() in entry.get("text", "").lower():
                            results.append(entry)
                            if len(results) >= limit:
                                return results
                    except json.JSONDecodeError:
                        continue
        return results


_history: Optional[TranscriptionHistory] = None


def get_history() -> TranscriptionHistory:
    global _history
    if _history is None:
        _history = TranscriptionHistory()
    return _history
