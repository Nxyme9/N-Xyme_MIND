"""Session Manager — Manage active sessions"""

import logging, time, uuid
from typing import Dict, List

logger = logging.getLogger(__name__)


class SessionManager:
    def __init__(self):
        self._sessions: Dict[str, dict] = {}

    def create(self, name: str = None, metadata: dict = None) -> str:
        session_id = str(uuid.uuid4())[:8]
        self._sessions[session_id] = {
            "id": session_id,
            "name": name or session_id,
            "created": time.time(),
            "last_active": time.time(),
            "metadata": metadata or {},
        }
        logger.info(f"SessionManager: Created {session_id}")
        return session_id

    def get(self, session_id: str) -> Dict:
        return self._sessions.get(session_id, {})

    def touch(self, session_id: str):
        if session_id in self._sessions:
            self._sessions[session_id]["last_active"] = time.time()

    def close(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def list_active(self, max_age_seconds: float = 3600) -> List[Dict]:
        now = time.time()
        return [s for s in self._sessions.values() if now - s["last_active"] < max_age_seconds]

    def cleanup(self, max_age_seconds: float = 86400):
        now = time.time()
        expired = [
            sid for sid, s in self._sessions.items() if now - s["last_active"] > max_age_seconds
        ]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)
