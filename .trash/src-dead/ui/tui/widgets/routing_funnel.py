#!/usr/bin/env python3
"""
RoutingFunnel - ASCII visualization of request flow through intelligent router

T4.2 from dashboard-v2-plan.md:
- Show request flow through routing pipeline
- Display success rates at each stage
- Visualize funnel conversion
"""

from typing import Optional
from textual.reactive import reactive
from textual.widget import Widget


class RoutingFunnel(Widget):
    """Routing funnel visualization."""

    # Reactive data
    total_requests = reactive(0)
    stages = reactive([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def set_data(self, total: int, stages: list) -> None:
        """Set funnel data.

        Args:
            total: Total number of requests
            stages: List of dicts with 'name', 'count', 'rate'
        """
        self.total_requests = total
        self.stages = stages
        self.refresh()

    def render(self) -> str:
        """Render ASCII funnel."""
        if not self.total_requests:
            return "[dim]No routing data[/]"

        lines = ["ROUTING FUNNEL", "═" * 40, ""]
        lines.append(f"Requests: {self.total_requests:,}")

        max_count = max([s.get("count", 0) for s in self.stages], default=1)

        for stage in self.stages:
            name = stage.get("name", "?")
            count = stage.get("count", 0)
            rate = stage.get("rate", 0)

            # Calculate bar width proportional to count
            if max_count > 0:
                bar_width = int((count / max_count) * 20)
            else:
                bar_width = 0

            bar = "█" * bar_width + "░" * (20 - bar_width)

            lines.append(f"  │")
            lines.append(f"  ▼ {rate:3d}% [{bar}] {name}")
            lines.append(f"  │  {count:,} processed")

        # Summary
        success_count = self.stages[-1].get("count", 0) if self.stages else 0
        success_rate = (
            (success_count / self.total_requests * 100) if self.total_requests else 0
        )

        lines.extend(["", f"Success Rate: {success_rate:.0f}%"])

        return "\n".join(lines)


class SimpleRoutingStats(Widget):
    """Simple routing statistics display."""

    total_requests = reactive(0)
    success_count = reactive(0)
    avg_latency = reactive(0.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def set_stats(self, total: int, success: int, latency: float) -> None:
        """Set routing stats."""
        self.total_requests = total
        self.success_count = success
        self.avg_latency = latency
        self.refresh()

    def render(self) -> str:
        """Render stats."""
        success_rate = (
            (self.success_count / self.total_requests * 100)
            if self.total_requests
            else 0
        )

        return f"""ROUTING STATS
═══════════════════

Requests: {self.total_requests:,}
  Success: {self.success_count:,} ({success_rate:.0f}%)
   Failed: {self.total_requests - self.success_count:,}
Avg Latency: {self.avg_latency:.2f}s"""
