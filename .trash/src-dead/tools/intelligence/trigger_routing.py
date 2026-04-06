"""Trigger-Based Routing Automation — Uses trigger patterns to automate routing decisions."""

import json
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("trigger-routing")


@dataclass
class RoutingTrigger:
    """A trigger that influences routing decisions."""
    name: str
    pattern: str
    level: Optional[int] = None
    agent: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0


@dataclass
class TriggerMatch:
    """A matched trigger with routing decision."""
    trigger: RoutingTrigger
    confidence: float
    reason: str


class TriggerBasedRouter:
    """Routes tasks using trigger pattern matching."""
    
    def __init__(self, trigger_config_path: Optional[str] = None):
        self._triggers: List[RoutingTrigger] = []
        if trigger_config_path:
            self.load_triggers(trigger_config_path)
    
    def load_triggers(self, config_path: str) -> bool:
        """Load trigger configuration from JSON file."""
        try:
            path = Path(config_path)
            if not path.exists():
                logger.warning(f"Trigger config not found: {config_path}")
                return False
            
            with open(path) as f:
                config = json.load(f)
            
            self._triggers = []
            
            raw_triggers = config.get("routing_triggers", config.get("triggers", {}))
            
            if isinstance(raw_triggers, list):
                trigger_list = raw_triggers
            elif isinstance(raw_triggers, dict):
                trigger_list = []
                for category, items in raw_triggers.items():
                    if isinstance(items, list):
                        for item in items:
                            item_copy = dict(item)
                            item_copy["category"] = category
                            trigger_list.append(item_copy)
            else:
                logger.warning(f"Unexpected triggers format: {type(raw_triggers)}")
                return False
            
            for trigger_data in trigger_list:
                pattern = trigger_data.get("pattern", "")
                if not pattern:
                    desc = trigger_data.get("description", "") or trigger_data.get("id", "")
                    pattern = desc.lower() if desc else ""
                
                trigger = RoutingTrigger(
                    name=trigger_data.get("id", trigger_data.get("name", "")),
                    pattern=pattern,
                    level=trigger_data.get("level"),
                    agent=trigger_data.get("agent"),
                    tags=trigger_data.get("tags", []) or [trigger_data.get("category", "")],
                    metadata=trigger_data.get("metadata", {}) or {
                        "action": trigger_data.get("action"),
                        "severity": trigger_data.get("severity"),
                        "source": trigger_data.get("source")
                    },
                    priority=trigger_data.get("priority", 0)
                )
                self._triggers.append(trigger)
            
            self._triggers.sort(key=lambda t: t.priority, reverse=True)
            
            logger.info(f"Loaded {len(self._triggers)} triggers from {config_path}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to load triggers: {e}")
            return False
    
    def match_trigger(self, task_description: str) -> Optional[TriggerMatch]:
        """Find the highest-priority trigger matching the task description."""
        task_lower = task_description.lower()
        
        for trigger in self._triggers:
            try:
                if re.search(trigger.pattern, task_lower, re.IGNORECASE):
                    confidence = self._calculate_confidence(trigger, task_description)
                    
                    return TriggerMatch(
                        trigger=trigger,
                        confidence=confidence,
                        reason=f"Trigger '{trigger.name}' matched pattern '{trigger.pattern}'"
                    )
            except re.error as e:
                logger.warning(f"Invalid regex in trigger '{trigger.name}': {e}")
                continue
        
        return None
    
    def get_routing_from_trigger(self, match: TriggerMatch) -> Dict[str, Any]:
        """Get routing decision from a trigger match."""
        routing = {
            "source": "trigger",
            "trigger_name": match.trigger.name,
            "confidence": match.confidence,
            "reason": match.reason,
            "tags": match.trigger.tags,
            "metadata": match.trigger.metadata
        }
        
        if match.trigger.level is not None:
            routing["recommended_level"] = match.trigger.level
        
        if match.trigger.agent is not None:
            routing["recommended_agent"] = match.trigger.agent
        
        return routing
    
    def _calculate_confidence(self, trigger: RoutingTrigger, task_description: str) -> float:
        """Calculate confidence score for a trigger match."""
        pattern_length = len(trigger.pattern)
        base_confidence = min(pattern_length / 50.0, 1.0)
        
        task_lower = task_description.lower()
        if trigger.pattern.lower() in task_lower:
            base_confidence = min(base_confidence + 0.3, 1.0)
        
        priority_boost = min(trigger.priority / 10.0, 0.2)
        
        return min(base_confidence + priority_boost, 1.0)
    
    def get_triggers(self) -> List[RoutingTrigger]:
        """Get all loaded triggers."""
        return self._triggers.copy()
    
    def add_trigger(self, trigger: RoutingTrigger) -> None:
        """Add a new trigger."""
        self._triggers.append(trigger)
        self._triggers.sort(key=lambda t: t.priority, reverse=True)
    
    def remove_trigger(self, name: str) -> bool:
        """Remove a trigger by name."""
        original_count = len(self._triggers)
        self._triggers = [t for t in self._triggers if t.name != name]
        return len(self._triggers) < original_count


_trigger_router: Optional[TriggerBasedRouter] = None

def get_trigger_router(config_path: Optional[str] = None) -> TriggerBasedRouter:
    """Get or create the global trigger router."""
    global _trigger_router
    if _trigger_router is None:
        _trigger_router = TriggerBasedRouter(config_path)
    return _trigger_router