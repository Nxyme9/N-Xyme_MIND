"""Dynamic Trigger Generation

Automatically creates triggers from successful routing patterns.
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from collections import Counter

logger = logging.getLogger("dynamic-triggers")


class DynamicTriggerGenerator:
    """Generates triggers from historical routing patterns."""
    
    def __init__(self, store=None):
        self._store = store
        self._min_occurrences = 3  # Minimum occurrences to create a trigger
        self._min_success_rate = 0.7  # Minimum success rate for a trigger
    
    def set_store(self, store):
        """Set the SQLite store for historical data."""
        self._store = store
    
    def analyze_patterns(self) -> List[Dict[str, Any]]:
        """Analyze historical data to find patterns for new triggers."""
        if not self._store:
            return []
        
        outcomes = self._store.get_outcomes(limit=1000)
        
        # Group successful outcomes by agent and level
        agent_patterns = {}
        for outcome in outcomes:
            if not outcome.get('success'):
                continue
            
            desc = outcome.get('task_description', '').lower()
            agent = outcome.get('agent', 'unknown')
            level = outcome.get('level', 2)
            
            # Extract key phrases
            phrases = self._extract_phrases(desc)
            
            for phrase in phrases:
                key = f"{agent}_{phrase}"
                if key not in agent_patterns:
                    agent_patterns[key] = {
                        'phrase': phrase,
                        'agent': agent,
                        'level': level,
                        'count': 0,
                        'success': 0
                    }
                agent_patterns[key]['count'] += 1
                agent_patterns[key]['success'] += 1
        
        # Filter patterns that meet thresholds
        candidates = []
        for key, data in agent_patterns.items():
            if data['count'] >= self._min_occurrences:
                success_rate = data['success'] / data['count']
                if success_rate >= self._min_success_rate:
                    candidates.append({
                        'phrase': data['phrase'],
                        'agent': data['agent'],
                        'level': data['level'],
                        'count': data['count'],
                        'success_rate': success_rate
                    })
        
        # Sort by count and success rate
        candidates.sort(key=lambda x: (x['count'], x['success_rate']), reverse=True)
        
        return candidates
    
    def generate_triggers(self, candidates: List[Dict[str, Any]], max_new: int = 5) -> List[Dict[str, Any]]:
        """Generate new triggers from candidates."""
        # Load existing triggers
        triggers_file = Path('.sisyphus/routing-triggers.json')
        if triggers_file.exists():
            with open(triggers_file) as f:
                config = json.load(f)
            existing_phrases = set()
            for trigger in config.get('routing_triggers', []):
                # Extract key phrases from existing patterns
                patterns = trigger.get('pattern', '').split('|')
                for pattern in patterns:
                    # Clean up regex
                    clean = re.sub(r'[.*?+^${}()|[\]\\]', '', pattern).strip()
                    if clean:
                        existing_phrases.add(clean.lower())
        else:
            existing_phrases = set()
            config = {'routing_triggers': []}
        
        # Generate new triggers (avoid duplicates)
        new_triggers = []
        for candidate in candidates:
            phrase = candidate['phrase']
            if phrase.lower() not in existing_phrases and len(new_triggers) < max_new:
                priority = int(candidate['success_rate'] * 10)
                new_triggers.append({
                    'name': f"auto-{phrase.replace(' ', '-')[:20]}",
                    'pattern': phrase,
                    'level': candidate['level'],
                    'agent': candidate['agent'],
                    'priority': priority
                })
                existing_phrases.add(phrase.lower())
        
        return new_triggers
    
    def apply_triggers(self, new_triggers: List[Dict[str, Any]]) -> int:
        """Apply new triggers to the routing config."""
        if not new_triggers:
            return 0
        
        triggers_file = Path('.sisyphus/routing-triggers.json')
        if triggers_file.exists():
            with open(triggers_file) as f:
                config = json.load(f)
        else:
            config = {'routing_triggers': []}
        
        # Add new triggers
        existing_names = {t['name'] for t in config.get('routing_triggers', [])}
        added = 0
        for trigger in new_triggers:
            if trigger['name'] not in existing_names:
                config['routing_triggers'].append(trigger)
                added += 1
                logger.info(f"Added trigger: {trigger['name']} -> {trigger['agent']} (L{trigger['level']})")
        
        if added > 0:
            with open(triggers_file, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info(f"Applied {added} new triggers")
        
        return added
    
    def _extract_phrases(self, text: str) -> List[str]:
        """Extract meaningful phrases from text."""
        # Common task patterns
        patterns = [
            r'fix\s+\w+\s+in\s+\w+',
            r'add\s+\w+\s+(?:to|for)\s+\w+',
            r'update\s+\w+\s+(?:to|for)\s+\w+',
            r'create\s+\w+\s+(?:for|with)\s+\w+',
            r'implement\s+\w+\s+(?:for|with)\s+\w+',
            r'refactor\s+\w+',
            r'optimize\s+\w+',
            r'debug\s+\w+',
            r'review\s+\w+',
            r'test\s+\w+',
        ]
        
        phrases = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            phrases.extend(matches)
        
        # If no patterns matched, extract key words
        if not phrases:
            words = re.findall(r'\b[a-z]{3,}\b', text.lower())
            stop_words = {'the', 'and', 'for', 'with', 'this', 'that', 'from', 'have', 'been', 'were', 'will', 'would', 'could', 'should'}
            key_words = [w for w in words if w not in stop_words]
            if len(key_words) >= 2:
                phrases.append(' '.join(key_words[:3]))
        
        return phrases


# Global generator instance
_generator = None

def get_trigger_generator() -> DynamicTriggerGenerator:
    """Get or create the global trigger generator."""
    global _generator
    if _generator is None:
        _generator = DynamicTriggerGenerator()
    return _generator
