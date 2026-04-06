"""Routing Context Injector

Generates routing context to inject into system prompts.
This gives the cloud model visibility into routing decisions.
"""

import json
from pathlib import Path
from typing import Dict, Any


def generate_routing_context() -> str:
    """Generate routing context string for system prompt injection."""
    context_parts = []
    
    # 1. Current routing stats
    outcomes_file = Path('.sisyphus/outcomes.jsonl')
    if outcomes_file.exists():
        with open(outcomes_file) as f:
            lines = [l for l in f if l.strip()]
        total = len(lines)
        context_parts.append(f"## Routing Statistics\n- Total delegations: {total}")
        
        # Calculate success rate
        success = 0
        for line in lines:
            try:
                data = json.loads(line)
                if data.get('success'):
                    success += 1
            except (json.JSONDecodeError, KeyError):
                pass
        rate = (success / total * 100) if total > 0 else 0
        context_parts.append(f"- Overall success rate: {rate:.0f}%")
    
    # 2. Top performing agents
    weights_file = Path('.sisyphus/routing-weights.json')
    if weights_file.exists():
        with open(weights_file) as f:
            weights = json.load(f)
        
        # Sort by success rate
        agents = []
        for name, data in weights.items():
            if data.get('total_tasks', 0) > 0:
                agents.append((name, data.get('success_rate', 0), data.get('total_tasks', 0)))
        
        agents.sort(key=lambda x: (x[1], x[2]), reverse=True)
        
        if agents:
            context_parts.append("\n## Agent Performance")
            for name, rate, tasks in agents[:5]:
                context_parts.append(f"- {name}: {rate:.0%} success ({tasks} tasks)")
    
    # 3. Available triggers
    triggers_file = Path('.sisyphus/routing-triggers.json')
    if triggers_file.exists():
        with open(triggers_file) as f:
            config = json.load(f)
        triggers = config.get('routing_triggers', [])
        context_parts.append(f"\n## Routing Triggers\n- {len(triggers)} patterns configured")
        context_parts.append("- When you delegate, the system auto-routes based on task description")
    
    # 4. Routing instructions
    context_parts.append("\n## Delegation Instructions")
    context_parts.append("- Use `route_task` MCP tool to get routing recommendations")
    context_parts.append("- Use `record_delegation_outcome` to log task outcomes")
    context_parts.append("- The system will auto-route delegation tool calls")
    
    return "\n".join(context_parts)


if __name__ == "__main__":
    print(generate_routing_context())
