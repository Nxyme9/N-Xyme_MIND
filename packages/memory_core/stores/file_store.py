"""File Store — File-based episodic memory storage."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class FileStore:
    """File-based episodic memory store."""

    def __init__(self, storage_dir: str = "data/memories"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        results = []
        for mem_file in self.storage_dir.glob("*.json"):
            try:
                data = json.loads(mem_file.read_text())
                if query.lower() in data.get("content", "").lower():
                    results.append(data)
                    if len(results) >= limit:
                        break
            except Exception:
                continue
        return results

    def store(self, id: str, content: str, **kwargs) -> str:
        mem_file = self.storage_dir / f"{id}.json"
        mem_file.write_text(
            json.dumps({"id": id, "content": content, **kwargs}, indent=2)
        )
        return id

    def delete(self, id: str) -> bool:
        mem_file = self.storage_dir / f"{id}.json"
        if mem_file.exists():
            mem_file.unlink()
            return True
        return False

    def stats(self) -> Dict[str, Any]:
        return {"total_files": len(list(self.storage_dir.glob("*.json")))}


__all__ = ["FileStore"]
