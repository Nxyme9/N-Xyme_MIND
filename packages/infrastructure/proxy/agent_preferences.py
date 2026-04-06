"""Per-Agent Model Preferences — Each agent can have preferred models."""

import threading
from typing import Dict, List, Optional


class AgentPreferences:
    def __init__(self):
        self._lock = threading.Lock()
        # Default preferences based on agent role - CLOUD FIRST, LOCAL AS FALLBACK
        self._preferences: Dict[str, dict] = {
            "sisyphus": {
                "preferred_models": ["mimo-v2-pro", "minimax-m2.5"],
                "avoid_models": [],
            },
            "prometheus": {
                "preferred_models": ["mimo-v2-pro", "minimax-m2.5"],
                "avoid_models": [],
            },
            "oracle": {
                "preferred_models": ["mimo-v2-pro", "minimax-m2.5"],
                "avoid_models": [],
            },
            "metis": {
                "preferred_models": ["mimo-v2-pro", "minimax-m2.5"],
                "avoid_models": [],
            },
            "momus": {
                "preferred_models": ["mimo-v2-pro", "minimax-m2.5"],
                "avoid_models": [],
            },
            "hephaestus": {
                "preferred_models": ["mimo-v2-pro", "minimax-m2.5"],
                "avoid_models": [],
            },
            "atlas": {
                "preferred_models": ["mimo-v2-pro", "minimax-m2.5"],
                "avoid_models": [],
            },
            "explore": {
                "preferred_models": ["minimax-m2.5", "mimo-v2-pro"],
                "avoid_models": [],
            },
            "librarian": {
                "preferred_models": ["minimax-m2.5", "mimo-v2-pro"],
                "avoid_models": [],
            },
            "sisyphus-junior": {
                "preferred_models": ["minimax-m2.5"],
                "avoid_models": [],
            },
            "multimodal-looker": {
                "preferred_models": ["mimo-v2-omni", "gemini-2.5-flash"],
                "avoid_models": [],
            },
        }
        # Per-session overrides
        self._session_overrides: Dict[str, Dict[str, list]] = {}
        # Track session last-access time for cleanup
        self._session_access_time: Dict[str, float] = {}
        self._max_sessions = 100  # Max sessions to track before cleanup
        self._cleanup_threshold = 0.8  # Cleanup when 80% of max

    def _cleanup_old_sessions(self, current_time: float) -> None:
        """Remove old session overrides to prevent memory leak."""
        if len(self._session_overrides) < self._max_sessions * self._cleanup_threshold:
            return
        
        # Remove sessions not accessed in >1 hour
        cutoff = current_time - 3600
        to_remove = [
            sid for sid, last_access in self._session_access_time.items()
            if last_access < cutoff
        ]
        for sid in to_remove:
            self._session_overrides.pop(sid, None)
            self._session_access_time.pop(sid, None)

    def get_preferred_models(self, agent_type: str, session_id: str = "") -> List[str]:
        """Get preferred models for an agent, with session overrides."""
        with self._lock:
            prefs = self._preferences.get(
                agent_type, {"preferred_models": ["mimo-v2-pro"], "avoid_models": []}
            )
            preferred = list(prefs["preferred_models"])
            # Apply session overrides
            if session_id and session_id in self._session_overrides:
                preferred = self._session_overrides[session_id].get(
                    "preferred", preferred
                )
            return preferred

    def get_avoided_models(self, agent_type: str) -> List[str]:
        """Get models to avoid for an agent."""
        with self._lock:
            return list(self._preferences.get(agent_type, {}).get("avoid_models", []))

    def set_session_override(
        self, session_id: str, preferred: list[str] | None = None, avoid: list[str] | None = None
    ) -> None:
        """Set model preferences for a specific session."""
        import time
        with self._lock:
            # Trigger cleanup if needed
            self._cleanup_old_sessions(time.time())
            
            if session_id not in self._session_overrides:
                self._session_overrides[session_id] = {}
                self._session_access_time[session_id] = time.time()
            if preferred:
                self._session_overrides[session_id]["preferred"] = preferred
                self._session_access_time[session_id] = time.time()
            if avoid:
                self._session_overrides[session_id]["avoid"] = avoid
                self._session_access_time[session_id] = time.time()

    def update_preferences(
        self, agent_type: str, preferred: list[str] | None = None, avoid: list[str] | None = None
    ) -> None:
        """Update default preferences for an agent."""
        with self._lock:
            if agent_type not in self._preferences:
                self._preferences[agent_type] = {
                    "preferred_models": [],
                    "avoid_models": [],
                }
            if preferred:
                self._preferences[agent_type]["preferred_models"] = preferred
            if avoid:
                self._preferences[agent_type]["avoid_models"] = avoid


# Global instance
agent_preferences = AgentPreferences()
