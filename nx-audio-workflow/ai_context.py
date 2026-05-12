#!/usr/bin/env python3
"""
AI Context System for N-Xyme Audio Workflow
Tracks project state, learns user preferences, suggests next actions
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

# Import N-Xyme memory system
try:
    from nx_brain_memory_search_memories import search_memories
    from nx_brain_memory_memory_write import memory_write
    from nx_brain_context_get_active_context import get_active_context
    NXMEMORY_AVAILABLE = True
except ImportError:
    NXMEMORY_AVAILABLE = False
    print("Warning: N-Xyme memory system not available")


class AudioContextSystem:
    """Context system for AI audio workflow"""
    
    def __init__(self, project_path: str = None):
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self.context_file = self.project_path / ".nx-audio-context.json"
        self.state = self._load_state()
        self.history = []
        
    def _load_state(self) -> Dict:
        """Load existing project state"""
        if self.context_file.exists():
            try:
                with open(self.context_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Default state
        return {
            "project": {
                "name": "Untitled",
                "tempo": 120,
                "key": "C major",
                "time_signature": "4/4",
                "tracks": [],
                "created": datetime.now().isoformat(),
                "last_modified": None
            },
            "preferences": {
                "default_plugins": ["EQ+", "Compressor+", "Reverb+"],
                "routing_style": "bus-based",
                "favorite_buses": ["Drums", "Vocals", "Instruments"],
                "default_bpm": 120,
                "default_key": "C major"
            },
            "history": []
        }
    
    def _save_state(self):
        """Save current state to file"""
        self.state["project"]["last_modified"] = datetime.now().isoformat()
        with open(self.context_file, 'w') as f:
            json.dump(self.state, f, indent=2)
        
        # Also save to N-Xyme memory if available
        if NXMEMORY_AVAILABLE:
            try:
                memory_write(
                    content=json.dumps(self.state),
                    kind="semantic",
                    scope="project",
                    tags=["audio", "context", "project_state"]
                )
            except:
                pass
    
    def update_project_state(self, **kwargs):
        """Update project state with new values"""
        for key, value in kwargs.items():
            if key in self.state["project"]:
                self.state["project"][key] = value
        
        self._save_state()
        return self.state["project"]
    
    def add_track(self, track_name: str, track_type: str = "Audio") -> Dict:
        """Add a track to the project"""
        track = {
            "name": track_name,
            "type": track_type,
            "created": datetime.now().isoformat(),
            "armed": False,
            "muted": False,
            "volume": 0.0,
            "pan": 0.0
        }
        
        self.state["project"]["tracks"].append(track)
        self._log_action("add_track", {"track": track})
        self._save_state()
        
        return track
    
    def set_tempo(self, bpm: int) -> Dict:
        """Set project tempo"""
        self.state["project"]["tempo"] = bpm
        self._log_action("set_tempo", {"bpm": bpm})
        self._save_state()
        return {"tempo": bpm}
    
    def set_key(self, key: str) -> Dict:
        """Set project key"""
        self.state["project"]["key"] = key
        self._log_action("set_key", {"key": key})
        self._save_state()
        return {"key": key}
    
    def learn_preference(self, key: str, value: Any):
        """Learn user preference from behavior"""
        if key in self.state["preferences"]:
            # If it's a list, append; otherwise overwrite
            if isinstance(self.state["preferences"][key], list):
                if value not in self.state["preferences"][key]:
                    self.state["preferences"][key].append(value)
            else:
                self.state["preferences"][key] = value
        else:
            self.state["preferences"][key] = value
        
        self._log_action("learn_preference", {"key": key, "value": value})
        self._save_state()
    
    def get_preferences(self) -> Dict:
        """Get current user preferences"""
        # Try to get from N-Xyme memory first
        if NXMEMORY_AVAILABLE:
            try:
                results = search_memories("user preferences audio workflow")
                if results and "results" in results:
                    for r in results["results"]:
                        if "preference" in r.get("content", "").lower():
                            # Merge with local preferences
                            pass
            except:
                pass
        
        return self.state["preferences"]
    
    def suggest_next_actions(self, limit: int = 5) -> List[Dict]:
        """Suggest next actions based on history and current state"""
        suggestions = []
        project = self.state["project"]
        prefs = self.state["preferences"]
        
        # Rule-based suggestions
        if not project["tracks"]:
            suggestions.append({
                "action": "start_recording_session",
                "priority": "high",
                "reason": "No tracks in project yet"
            })
        
        if project["tracks"] and len(project["tracks"]) < 3:
            suggestions.append({
                "action": "create_beat_template",
                "priority": "medium",
                "reason": "Add a beat to build arrangement"
            })
        
        # Check if vocals exist but no vocal chain
        vocal_tracks = [t for t in project["tracks"] if "vocal" in t["name"].lower()]
        if vocal_tracks and not self._has_plugin_chain(vocal_tracks[0], ["Compressor+", "EQ+"]):
            suggestions.append({
                "action": "add_vocals_chain",
                "priority": "high",
                "reason": "Vocals detected without processing chain"
            })
        
        # Suggest based on history patterns
        if len(self.history) > 0:
            last_action = self.history[-1] if self.history else None
            if last_action:
                if last_action["action"] == "add_track":
                    suggestions.append({
                            "action": "add_reverb",
                            "priority": "low",
                            "reason": "Last action was adding track, consider adding reverb"
                        })
        
        # Default suggestions
        suggestions.append({
            "action": "mix_session",
            "priority": "low",
            "reason": "Auto-route tracks to buses for better organization"
        })
        
        return suggestions[:limit]
    
    def _has_plugin_chain(self, track: Dict, plugins: List[str]) -> bool:
        """Check if track has specific plugins"""
        # In real implementation, would check Bitwig device list
        return False
    
    def _log_action(self, action: str, details: Dict):
        """Log an action to history"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details
        }
        self.history.append(entry)
        self.state["history"].append(entry)
        
        # Keep only last 100 actions
        if len(self.history) > 100:
            self.history = self.history[-100:]
        if len(self.state["history"]) > 100:
            self.state["history"] = self.state["history"][-100:]
    
    def get_context_for_ai(self) -> str:
        """Generate context string for AI interpretation"""
        project = self.state["project"]
        prefs = self.state["preferences"]
        
        context = "Current Project State:\n"
        context += f"- Name: {project['name']}\n"
        context += f"- Tempo: {project['tempo']} BPM\n"
        context += f"- Key: {project['key']}\n"
        context += f"- Time Sig: {project['time_signature']}\n"
        context += f"- Tracks: {len(project['tracks'])} tracks\n"
        
        if project["tracks"]:
            context += "\nTrack List:\n"
            for i, track in enumerate(project["tracks"], 1):
                context += f"  {i}. {track['name']} ({track['type']})\n"
        
        context += "\nUser Preferences:\n"
        context += f"- Routing Style: {prefs['routing_style']}\n"
        context += f"- Favorite Buses: {', '.join(prefs['favorite_buses'])}"
        context += f"- Default Plugins: {', '.join(prefs['default_plugins'])}"
        
        if self.history:
            context += "\n\nRecent Actions:\n"
            for entry in self.history[-5:]:
                context += f"  - {entry['action']} at {entry['timestamp']}\n"
        
        return context
    
    def recall_similar_workflows(self, current_action: str) -> List[Dict]:
        """Recall similar workflows from memory"""
        if not NXMEMORY_AVAILABLE:
            return []
        
        try:
            results = search_memories(f"workflow {current_action}")
            if results and "results" in results:
                return results["results"][:5]
        except:
            pass
        
        return []
    
    def get_full_context(self) -> Dict:
        """Get complete context dictionary"""
        return {
            "project": self.state["project"],
            "preferences": self.state["preferences"],
            "history": self.history[-10:],
            "suggestions": self.suggest_next_actions()
        }


if __name__ == "__main__":
    # Demo usage
    context = AudioContextSystem()
    
    print("=== Initial State ===")
    print(json.dumps(context.get_full_context(), indent=2))
    
    print("\n=== Updating State ===")
    context.update_project_state(name="My First Track", tempo=140, key="A minor")
    context.add_track("Drum Machine", "Instrument")
    context.add_track("Vocals", "Audio")
    
    print("\n=== Suggestions ===")
    for s in context.suggest_next_actions():
        print(f"  - [{s['priority']}] {s['action']}: {s['reason']}")
    
    print("\n=== AI Context ===")
    print(context.get_context_for_ai())
