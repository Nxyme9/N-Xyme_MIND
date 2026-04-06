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
        self, session_id: str, preferred: List[str] = None, avoid: List[str] = None
    ) -> None:
        """Set model preferences for a specific session."""
        with self._lock:
            if session_id not in self._session_overrides:
                self._session_overrides[session_id] = {}
            if preferred:
                self._session_overrides[session_id]["preferred"] = preferred
            if avoid:
                self._session_overrides[session_id]["avoid"] = avoid

    def update_preferences(
        self, agent_type: str, preferred: List[str] = None, avoid: List[str] = None
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
