"""Collaboration — Real-time collaboration support"""

import logging, time, uuid
from typing import Dict, List

logger = logging.getLogger(__name__)


class CollaborationSession:
    MAX_HISTORY = 5000

    def __init__(self, session_id: str | None = None):
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.participants: Dict[str, dict] = {}
        self.cursors: Dict[str, dict] = {}
        self.history: List[dict] = []

    def join(self, user_id: str, name: str):
        self.participants[user_id] = {"name": name, "joined": time.time()}
        logger.info(f"Collaboration: {name} joined session {self.session_id}")

    def leave(self, user_id: str):
        if user_id in self.participants:
            del self.participants[user_id]
            self.cursors.pop(user_id, None)

    def update_cursor(self, user_id: str, x: float, y: float):
        self.cursors[user_id] = {"x": x, "y": y, "time": time.time()}

    def broadcast(self, user_id: str, action: str, data: dict):
        event = {"user": user_id, "action": action, "data": data, "time": time.time()}
        self.history.append(event)
        if len(self.history) > self.MAX_HISTORY:
            self.history = self.history[-self.MAX_HISTORY :]

    def get_participants(self) -> List[dict]:
        return [{"id": uid, **info} for uid, info in self.participants.items()]
