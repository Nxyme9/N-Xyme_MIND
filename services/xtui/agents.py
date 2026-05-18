"""Agent definitions and management."""
import json, os

DEFAULT_AGENTS = [
    {"id": "catalyst", "name": "Catalyst", "mode": "primary", "model": "opencode/deepseek-v4-flash-free"},
    {"id": "hephaestus", "name": "Hephaestus - Builder", "mode": "primary", "model": "opencode/minimax-m2.5-free"},
    {"id": "atlas", "name": "Atlas - Plan Executor", "mode": "subagent"},
    {"id": "hermes", "name": "Hermes - Memory & Personal", "mode": "subagent"},
    {"id": "prometheus", "name": "Prometheus - Planner", "mode": "subagent"},
    {"id": "oracle", "name": "Oracle - Architecture", "mode": "subagent"},
    {"id": "explore", "name": "Explore - Search", "mode": "subagent", "model": "opencode/minimax-m2.5-free"},
    {"id": "momus", "name": "Momus - Critic", "mode": "subagent"},
    {"id": "librarian", "name": "Librarian - Research", "mode": "subagent"},
    {"id": "metis", "name": "Metis - Consultant", "mode": "subagent"},
    {"id": "phi4", "name": "Phi-4 Reasoner", "mode": "subagent"},
    {"id": "kairos", "name": "Kairos - Therapist", "mode": "subagent"},
    {"id": "jarvis", "name": "Jarvis - Assistant", "mode": "subagent"},
    {"id": "mrwhite", "name": "Mr. White - Chemistry", "mode": "subagent"},
    {"id": "architect", "name": "System Architect", "mode": "subagent"},
    {"id": "vision", "name": "Vision Analyst", "mode": "subagent"},
    {"id": "masterplan", "name": "Masterplan", "mode": "subagent"},
]

class AgentManager:
    def __init__(self, config_path=None):
        self.agents = DEFAULT_AGENTS.copy()
        self.current = self.agents[0]
        self._load_custom(config_path)
    
    def _load_custom(self, path):
        if not path:
            path = os.path.expanduser("~/.xtui/agents.json")
        try:
            with open(path) as f:
                custom = json.load(f)
                if isinstance(custom, list):
                    self.agents = custom
                elif isinstance(custom, dict):
                    ids = {a["id"] for a in self.agents}
                    for a in custom.get("agents", []):
                        if a["id"] in ids:
                            self.agents = [a if x["id"] == a["id"] else x for x in self.agents]
                        else:
                            self.agents.append(a)
                    if "default" in custom:
                        self.set(custom["default"])
        except:
            pass
    
    def list(self):
        return self.agents
    
    def get(self, identifier):
        if isinstance(identifier, int):
            if 0 <= identifier < len(self.agents):
                return self.agents[identifier]
            return None
        identifier = identifier.lower().strip()
        for a in self.agents:
            if a["id"] == identifier:
                return a
            if identifier in a["name"].lower():
                return a
        return None
    
    def set(self, identifier):
        a = self.get(identifier)
        if a:
            self.current = a
        return a
    
    def current_name(self):
        return self.current["name"]
    
    def current_id(self):
        return self.current["id"]
    
    def mode(self, name=None):
        a = self.get(name) if name else self.current
        return a.get("mode", "all") if a else "all"
