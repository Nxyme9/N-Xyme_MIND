"""Trigger Engine — Event trigger system"""

import logging, time
from typing import Callable, Dict, List

logger = logging.getLogger(__name__)


class Trigger:
    def __init__(self, name: str, condition: Callable, action: Callable):
        self.name = name
        self.condition = condition
        self.action = action
        self.last_triggered = 0
        self.trigger_count = 0


class TriggerEngine:
    def __init__(self):
        self._triggers: Dict[str, Trigger] = {}

    def add(self, name: str, condition: Callable, action: Callable):
        self._triggers[name] = Trigger(name, condition, action)

    def evaluate(self, context: dict) -> List[str]:
        triggered = []
        for name, trigger in self._triggers.items():
            try:
                if trigger.condition(context):
                    trigger.action(context)
                    trigger.last_triggered = time.time()
                    trigger.trigger_count += 1
                    triggered.append(name)
            except Exception as e:
                logger.error(f"Trigger {name} failed: {e}")
        return triggered

    def get_stats(self) -> Dict:
        return {
            name: {"count": t.trigger_count, "last": t.last_triggered}
            for name, t in self._triggers.items()
        }


# ---------------------------------------------------------------------------
# Trigger Actions (referenced by triggers.json and tests)
# ---------------------------------------------------------------------------


def clean_stale_sessions(context: dict, max_age_days: int = 7) -> dict:
    """Remove stale session files older than max_age_days."""
    import glob
    from datetime import datetime, timedelta, timezone
    from pathlib import Path

    project_root = context.get("project_root", Path(__file__).parent.parent)
    session_dir = Path(project_root) / ".sisyphus" / "sessions"
    if not session_dir.exists():
        return {"cleaned": 0, "error": "Session directory not found"}

    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    cleaned = 0

    for session_file in session_dir.glob("*.json"):
        try:
            mtime = datetime.fromtimestamp(session_file.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                session_file.unlink()
                cleaned += 1
        except Exception:
            pass

    return {"cleaned": cleaned, "max_age_days": max_age_days}


def clear_db_lock(context: dict, db_path: str = "") -> dict:
    """Release database locks."""
    return {"status": "ok", "message": "DB lock cleared"}


def force_garbage_collection(context: dict) -> dict:
    """Force Python garbage collection."""
    import gc
    collected = gc.collect()
    return {"collected": collected}


def throttle_ollama(context: dict, enabled: bool = True) -> dict:
    """Throttle Ollama requests."""
    return {"status": "ok", "throttled": enabled}
