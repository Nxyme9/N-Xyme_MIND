#!/usr/bin/env python3
"""
Activity Heatmap - Visualize agent activity patterns over time

T2.2 from dashboard-v2-plan.md:
- 24h activity by hour
- ASCII-based heatmap display
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class ActivityHeatmap:
    """Generate ASCII heatmap for agent activity."""
    
    HOURS = list(range(24))
    BLOCKS = ["░", "▒", "▓", "█"]  # Light to dark
    
    def __init__(self):
        # Activity data: agent_name -> {hour -> count}
        self._data: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
    
    def record_activity(self, agent: str, hour: int, count: int = 1) -> None:
        """Record activity for an agent at a specific hour."""
        self._data[agent][hour] += count
    
    def load_from_outcomes(self, outcomes_file: str = ".sisyphus/outcomes.jsonl") -> int:
        """Load activity data from outcomes.jsonl file."""
        import json
        from pathlib import Path
        
        count = 0
        path = Path(outcomes_file)
        if not path.exists():
            return 0
        
        for line in path.read_text().splitlines()[-1000:]:  # Last 1000 entries
            try:
                entry = json.loads(line)
                # Extract agent and timestamp
                agent = entry.get("agent", "unknown")
                timestamp = entry.get("timestamp", "")
                
                if timestamp and agent:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    hour = dt.hour
                    self.record_activity(agent, hour)
                    count += 1
            except Exception:
                continue
        
        return count
    
    def get_heatmap_row(self, agent: str) -> str:
        """Get heatmap row for a single agent."""
        if agent not in self._data:
            return "░" * 24
        
        hour_data = self._data[agent]
        max_count = max(hour_data.values()) if hour_data else 1
        
        row = ""
        for hour in self.HOURS:
            count = hour_data.get(hour, 0)
            if count == 0:
                row += "░"
            elif max_count > 0:
                # Calculate intensity
                intensity = count / max_count
                if intensity < 0.25:
                    row += "░"
                elif intensity < 0.5:
                    row += "▒"
                elif intensity < 0.75:
                    row += "▓"
                else:
                    row += "█"
        
        return row
    
    def render(self, agents: Optional[List[str]] = None) -> str:
        """Render the full heatmap."""
        if agents is None:
            agents = sorted(self._data.keys())
        
        if not agents:
            return "No activity data available"
        
        # Header row
        header = " " * 12 + "".join(f"{h:02d}" for h in self.HOURS)
        separator = "─" * 36
        
        lines = [header, separator]
        
        # Agent rows
        for agent in agents:
            row = self.get_heatmap_row(agent)
            # Truncate agent name to 10 chars
            name = agent[:10].ljust(10)
            lines.append(f"{name} │{row}│")
        
        return "\n".join(lines)
    
    def get_summary(self) -> Dict[str, int]:
        """Get summary statistics."""
        summary = {}
        for agent, hours in self._data.items():
            summary[agent] = sum(hours.values())
        return summary


def get_agent_activity() -> str:
    """Quick function to get agent activity heatmap."""
    heatmap = ActivityHeatmap()
    count = heatmap.load_from_outcomes()
    
    if count == 0:
        return "No recent activity"
    
    return heatmap.render()