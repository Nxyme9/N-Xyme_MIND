"""Session Archiver — Archive old sessions"""

import json, logging, time
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class SessionArchiver:
    def __init__(self, archive_dir: str = "data/archives"):
        self.archive_dir = Path(archive_dir)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def archive(self, session_data: Dict, session_id: str = None) -> str:
        session_id = session_id or f"session_{int(time.time())}"
        path = self.archive_dir / f"{session_id}.json"
        path.write_text(json.dumps(session_data, indent=2, default=str), encoding="utf-8")
        logger.info(f"SessionArchiver: Archived {session_id}")
        return str(path)

    def load(self, session_id: str) -> Dict:
        path = self.archive_dir / f"{session_id}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    def list_archived(self) -> List[str]:
        return [f.stem for f in self.archive_dir.glob("*.json")]

    def search(self, query: str) -> List[Dict]:
        results = []
        for f in self.archive_dir.glob("*.json"):
            content = f.read_text(encoding="utf-8")
            if query.lower() in content.lower():
                results.append({"session": f.stem, "found": True})
        return results
