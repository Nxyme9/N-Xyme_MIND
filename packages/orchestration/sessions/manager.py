"""Session Manager — Manage active sessions with cross-session knowledge transfer."""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Lazy import to avoid circular deps
_session_hook: Optional[Any] = None


def _get_session_hook():
    """Lazily load SessionLifecycleHook."""
    global _session_hook
    if _session_hook is None:
        try:
            from learning_engine import get_session_hook
            _session_hook = get_session_hook()
        except ImportError as e:
            logger.warning(f"Could not import SessionLifecycleHook: {e}")
            _session_hook = False  # Mark as failed
    return _session_hook if _session_hook else None


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

        # Call session hook at start
        hook = _get_session_hook()
        if hook:
            try:
                result = hook.on_session_start()
                logger.info(f"Session hook on_session_start: {result}")
            except Exception as e:
                logger.error(f"Error in on_session_start: {e}")

        return session_id

    def get(self, session_id: str) -> Dict:
        return self._sessions.get(session_id, {})

    def touch(self, session_id: str):
        if session_id in self._sessions:
            self._sessions[session_id]["last_active"] = time.time()

    def close(self, session_id: str) -> bool:
        if session_id in self._sessions:
            # Call session hook at end BEFORE removing
            hook = _get_session_hook()
            if hook:
                try:
                    result = hook.on_session_end(session_id)
                    logger.info(f"Session hook on_session_end: {result}")
                except Exception as e:
                    logger.error(f"Error in on_session_end: {e}")

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
            # Call session hook for each expired session
            hook = _get_session_hook()
            if hook:
                try:
                    hook.on_session_end(sid)
                except Exception as e:
                    logger.error(f"Error in on_session_end during cleanup: {e}")
            del self._sessions[sid]
        return len(expired)
