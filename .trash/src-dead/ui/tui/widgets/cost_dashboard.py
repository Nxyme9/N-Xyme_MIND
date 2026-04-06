#!/usr/bin/env python3
"""
CostDashboard - Cost and usage tracking widget

T4.3 from dashboard-v2-plan.md:
- Display token usage by agent
- Show API costs and budget
- Track daily/weekly/monthly usage trends
"""

from typing import Optional
from datetime import datetime, timedelta
from textual.reactive import reactive
from textual.widget import Widget


class CostDashboard(Widget):
    """ASCII cost and usage dashboard."""

    # Reactive data
    daily_costs = reactive([])
    agent_costs = reactive({})
    budget_limit = reactive(100.0)  # Default budget
    current_spend = reactive(0.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def set_data(
        self, daily_costs: list, agent_costs: dict, budget: float, current: float
    ) -> None:
        """Set cost data.

        Args:
            daily_costs: List of daily cost entries
            agent_costs: Dict of agent name -> cost
            budget_limit: Monthly budget limit
            current_spend: Current spend amount
        """
        self.daily_costs = daily_costs
        self.agent_costs = agent_costs
        self.budget_limit = budget
        self.current_spend = current
        self.refresh()

    def render(self) -> str:
        """Render ASCII cost dashboard."""
        lines = ["COST DASHBOARD", "═" * 40, ""]

        # Budget overview
        budget_used = (
            (self.current_spend / self.budget_limit * 100)
            if self.budget_limit > 0
            else 0
        )
        remaining = self.budget_limit - self.current_spend

        lines.append(f"Budget: ${self.budget_limit:.2f}/month")
        lines.append(f"Spend:  ${self.current_spend:.2f} ({budget_used:.0f}%)")
        lines.append(f"Left:   ${remaining:.2f}")

        # Budget bar
        bar_filled = min(int(budget_used / 5), 20)
        bar = "█" * bar_filled + "░" * (20 - bar_filled)
        lines.append(f"[{bar}]")
        lines.append("")

        # Agent costs
        if self.agent_costs:
            lines.append("┌─ AGENT COSTS ─┐")
            sorted_agents = sorted(
                self.agent_costs.items(), key=lambda x: x[1], reverse=True
            )
            for agent, cost in sorted_agents[:8]:
                pct = (cost / self.current_spend * 100) if self.current_spend > 0 else 0
                bar_len = int(pct / 5)
                bar = "▓" * bar_len + "░" * (20 - bar_len)
                lines.append(f"  {agent:<12} ${cost:>6.2f} [{bar}]")
            lines.append("")

        # Daily trend (last 7 days)
        if self.daily_costs:
            lines.append("┌─ DAILY TREND ─┐")
            for day in self.daily_costs[-7:]:
                date = day.get("date", "?")[:5]  # Just MM-DD
                cost = day.get("cost", 0)
                # Simple sparkline using unicode
                if cost < 5:
                    trend = "░"
                elif cost < 15:
                    trend = "▒"
                elif cost < 30:
                    trend = "▓"
                else:
                    trend = "█"
                lines.append(f"  {date} ${cost:>5.2f} {trend}")
        else:
            lines.append("[dim]No daily cost data[/]")

        return "\n".join(lines)


class UsageStats(Widget):
    """Simple usage statistics display."""

    tokens_used = reactive(0)
    tokens_limit = reactive(0)
    api_calls = reactive(0)
    avg_latency = reactive(0.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def set_stats(self, tokens: int, limit: int, calls: int, latency: float) -> None:
        """Set usage stats."""
        self.tokens_used = tokens
        self.tokens_limit = limit
        self.api_calls = calls
        self.avg_latency = latency
        self.refresh()

    def render(self) -> str:
        """Render usage stats."""
        token_pct = (
            (self.tokens_used / self.tokens_limit * 100) if self.tokens_limit > 0 else 0
        )

        return f"""USAGE STATS
══════════════

Tokens: {self.tokens_used:,} / {self.tokens_limit:,} ({token_pct:.0f}%)
  API Calls: {self.api_calls:,}
  Avg Latency: {self.avg_latency:.2f}s"""
