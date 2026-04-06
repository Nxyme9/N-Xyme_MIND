"""Export Service — Export data in various formats"""

import csv, json, logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ExportService:
    def to_json(self, data: Any, path: str):
        Path(path).write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def to_csv(self, data: List[Dict], path: str):
        if not data:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

    def to_markdown(self, data: List[Dict], path: str, title: str = "Export"):
        if not data:
            return
        lines = [f"# {title}\n"]
        headers = list(data[0].keys())
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for row in data:
            lines.append("| " + " | ".join(str(row.get(h, "")) for h in headers) + " |")
        Path(path).write_text("\n".join(lines), encoding="utf-8")
