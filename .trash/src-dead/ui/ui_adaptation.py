"""UI Adaptation — Real-time UI adaptation based on usage"""

import json, logging, time
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class UIAdaptation:
    def __init__(self, stats_file: str = "data/ui_stats.json"):
        self.stats_file = Path(stats_file)
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)
        self._usage: Dict[str, dict] = {}
        self._load()

    def _load(self):
        if self.stats_file.exists():
            self._usage = json.loads(self.stats_file.read_text(encoding="utf-8"))

    def _save(self):
        self.stats_file.write_text(json.dumps(self._usage, indent=2), encoding="utf-8")

    def record_usage(self, component: str, action: str = "click"):
        if component not in self._usage:
            self._usage[component] = {"clicks": 0, "last_used": 0}
        self._usage[component]["clicks"] += 1
        self._usage[component]["last_used"] = time.time()
        self._save()

    def get_frequently_used(self, limit: int = 10) -> List[str]:
        sorted_components = sorted(self._usage.items(), key=lambda x: x[1]["clicks"], reverse=True)
        return [name for name, _ in sorted_components[:limit]]

    def get_layout_suggestion(self) -> Dict:
        frequent = self.get_frequently_used(5)
        return {"suggested_order": frequent, "reason": "Based on usage frequency"}
