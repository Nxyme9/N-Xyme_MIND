"""Decision Tracker — Track architectural decisions"""

import json, logging, time
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class DecisionTracker:
    def __init__(self, storage_file: str = "data/decisions.json"):
        self.storage_file = Path(storage_file)
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        self._decisions: List[Dict] = []
        self._load()

    def _load(self):
        if self.storage_file.exists():
            self._decisions = json.loads(self.storage_file.read_text(encoding="utf-8"))

    def _save(self):
        self.storage_file.write_text(json.dumps(self._decisions, indent=2), encoding="utf-8")

    def record(
        self,
        title: str,
        context: str,
        decision: str,
        alternatives: List[str] = None,
        tags: List[str] = None,
    ):
        entry = {
            "title": title,
            "context": context,
            "decision": decision,
            "alternatives": alternatives or [],
            "tags": tags or [],
            "timestamp": time.time(),
        }
        self._decisions.append(entry)
        self._save()
        logger.info(f"DecisionTracker: Recorded '{title}'")

    def search(self, query: str) -> List[Dict]:
        return [
            d
            for d in self._decisions
            if query.lower() in d["title"].lower() or query.lower() in d["decision"].lower()
        ]

    def get_all(self) -> List[Dict]:
        return self._decisions

    def get_by_tag(self, tag: str) -> List[Dict]:
        return [d for d in self._decisions if tag in d.get("tags", [])]
