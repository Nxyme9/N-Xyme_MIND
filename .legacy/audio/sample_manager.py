"""Sample Manager — Audio sample library"""

import json, logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class SampleManager:
    def __init__(self, sample_dir: str = "data/samples"):
        self.sample_dir = Path(sample_dir)
        self.sample_dir.mkdir(parents=True, exist_ok=True)
        self._index: Dict[str, dict] = {}
        self._load_index()

    def _load_index(self):
        index_file = self.sample_dir / "index.json"
        if index_file.exists():
            self._index = json.loads(index_file.read_text(encoding="utf-8"))

    def _save_index(self):
        (self.sample_dir / "index.json").write_text(
            json.dumps(self._index, indent=2), encoding="utf-8"
        )

    def add(self, name: str, path: str, tags: List[str] = None, bpm: float = None, key: str = None):
        self._index[name] = {"path": path, "tags": tags or [], "bpm": bpm, "key": key}
        self._save_index()

    def search(self, query: str = None, tags: List[str] = None, bpm: float = None) -> List[Dict]:
        results = []
        for name, info in self._index.items():
            if query and query.lower() not in name.lower():
                continue
            if tags and not any(t in info["tags"] for t in tags):
                continue
            if bpm and info.get("bpm") and abs(info["bpm"] - bpm) > 5:
                continue
            results.append({"name": name, **info})
        return results

    def list_all(self) -> List[str]:
        return list(self._index.keys())
