"""Agent Card Registry - A2A-compliant agent discovery and registry."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AgentCardRegistry:
    """A2A-compliant agent card registry for agent discovery."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "context/memory/agent_cards.json"
        self.cards: Dict[str, Dict[str, Any]] = {}
        self._load_cards()
    
    def _load_cards(self):
        """Load agent cards from config file."""
        path = Path(self.config_path)
        if path.exists():
            try:
                with open(path) as f:
                    self.cards = json.load(f)
                logger.info(f"✅ Loaded {len(self.cards)} agent cards")
            except Exception as e:
                logger.warning(f"❌ Failed to load agent cards: {e}")
                self.cards = {}
        else:
            # Create default cards
            self._create_default_cards()
    
    def _create_default_cards(self):
        """Create default agent cards for known agents."""
        self.cards = {
            "sisyphus": {
                "name": "Sisyphus",
                "description": "Primary orchestrator agent",
                "capabilities": ["orchestration", "delegation", "planning"],
                "endpoints": {"default": "local"},
                "default_input_modes": ["text"],
                "default_output_modes": ["text"],
            },
            "prometheus": {
                "name": "Prometheus",
                "description": "Planning and architecture agent",
                "capabilities": ["planning", "architecture", "design"],
                "endpoints": {"default": "local"},
                "default_input_modes": ["text"],
                "default_output_modes": ["text"],
            },
            "hephaestus": {
                "name": "Hephaestus",
                "description": "Implementation and coding agent",
                "capabilities": ["coding", "implementation", "debugging"],
                "endpoints": {"default": "local"},
                "default_input_modes": ["text"],
                "default_output_modes": ["text"],
            },
            "oracle": {
                "name": "Oracle",
                "description": "Architecture review and guidance agent",
                "capabilities": ["review", "architecture", "guidance"],
                "endpoints": {"default": "local"},
                "default_input_modes": ["text"],
                "default_output_modes": ["text"],
            },
        }
        self._save_cards()
    
    def _save_cards(self):
        """Save agent cards to config file."""
        try:
            path = Path(self.config_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                json.dump(self.cards, f, indent=2)
        except Exception as e:
            logger.warning(f"❌ Failed to save agent cards: {e}")
    
    def register_agent(self, name: str, card: Dict[str, Any]):
        """Register a new agent card."""
        self.cards[name] = card
        self._save_cards()
        logger.info(f"✅ Registered agent: {name}")
    
    def get_agent(self, name: str) -> Optional[Dict[str, Any]]:
        """Get agent card by name."""
        return self.cards.get(name)
    
    def discover_agents(self, capabilities: Optional[List[str]] = None) -> List[str]:
        """Discover agents by capabilities."""
        if not capabilities:
            return list(self.cards.keys())
        
        matching = []
        for name, card in self.cards.items():
            agent_caps = card.get("capabilities", [])
            if any(cap in agent_caps for cap in capabilities):
                matching.append(name)
        return matching
    
    def get_all_agents(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered agents."""
        return self.cards.copy()
    
    def get_status(self) -> Dict[str, Any]:
        """Get registry status."""
        return {
            "total_agents": len(self.cards),
            "agents": list(self.cards.keys()),
        }


# Global registry instance
_registry = None


def get_agent_registry() -> AgentCardRegistry:
    """Get or create the global agent registry."""
    global _registry
    if _registry is None:
        _registry = AgentCardRegistry()
    return _registry
