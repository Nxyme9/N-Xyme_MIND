#!/usr/bin/env python3
"""
SparklineWidget - Real-time trend visualization for dashboard metrics

T2.1 from dashboard-v2-plan.md:
- Track history (last 100 samples)
- Display as inline sparkline
- Color-coded based on trend
"""

from collections import deque
from typing import Optional

from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Sparkline as TextualSparkline


class MetricSparkline(Widget):
    """Real-time sparkline for dashboard metrics."""

    # Reactive data store
    data = reactive([])
    max_points = 100

    # Configuration
    min_value: Optional[float] = None
    max_value: Optional[float] = None

    def __init__(
        self,
        max_points: int = 100,
        min_color: str = "$error",
        max_color: str = "$success",
        gradient: Optional[tuple] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.max_points = max_points
        self.min_color = min_color
        self.max_color = max_color
        self.gradient = gradient or ("$error", "$warning", "$success")

        # Data storage using deque for efficient appends
        self._data: deque = deque(maxlen=max_points)

    def add_sample(self, value: float) -> None:
        """Add a new data point."""
        self._data.append(value)
        # Trigger reactivity - create new list to notify Textual
        self.data = list(self._data)

    def add_samples(self, values: list) -> None:
        """Add multiple data points at once."""
        for v in values:
            self._data.append(v)
        self.data = list(self._data)

    def clear(self) -> None:
        """Clear all data points."""
        self._data.clear()
        self.data = []

    def get_trend(self) -> str:
        """Get trend indicator based on recent changes."""
        if len(self._data) < 2:
            return "─"

        recent = list(self._data)[-5:]
        first = recent[0]
        last = recent[-1]

        if last > first * 1.1:
            return "↑"
        elif last < first * 0.9:
            return "↓"
        return "→"

    def get_avg(self) -> float:
        """Get average of current data."""
        if not self._data:
            return 0.0
        return sum(self._data) / len(self._data)


class MetricCard(Widget):
    """Card displaying a metric with optional sparkline."""

    label = reactive("")
    value = reactive(0)
    unit = reactive("")
    trend = reactive("─")
    sparkline_data = reactive([])

    def __init__(
        self,
        label: str = "",
        value: int = 0,
        unit: str = "",
        show_sparkline: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._label = label
        self._value = value
        self._unit = unit
        self._show_sparkline = show_sparkline

    def update(
        self, value: int, trend: str = "─", sparkline_data: Optional[list] = None
    ) -> None:
        """Update the card with new values."""
        self.value = value
        self.trend = trend
        if sparkline_data is not None:
            self.sparkline_data = sparkline_data


class StatusIndicator(Widget):
    """Light-style status indicator."""

    status = reactive("unknown")  # unknown, healthy, warning, error

    COLORS = {
        "unknown": "$text-muted",
        "healthy": "$success",
        "warning": "$warning",
        "error": "$error",
    }

    def __init__(self, status: str = "unknown", **kwargs):
        super().__init__(**kwargs)
        self.status = status

    def set_status(self, status: str) -> None:
        """Update status."""
        self.status = status
        self.refresh()

    def render(self) -> str:
        """Render the indicator."""
        color = self.COLORS.get(self.status, "$text-muted")
        symbols = {
            "unknown": "○",
            "healthy": "●",
            "warning": "◐",
            "error": "◉",
        }
        return f"[{color}]{symbols.get(self.status, '○')}[/]"


class ProgressRing(Widget):
    """Circular progress indicator."""

    progress = reactive(0.0)  # 0.0 to 1.0
    label = reactive("")

    def __init__(self, progress: float = 0.0, label: str = "", **kwargs):
        super().__init__(**kwargs)
        self.progress = progress
        self.label = label

    def set_progress(self, progress: float) -> None:
        """Set progress (0.0 to 1.0)."""
        self.progress = max(0.0, min(1.0, progress))

    def render(self) -> str:
        """Render the progress ring."""
        # Simple ASCII progress bar
        filled = int(self.progress * 10)
        bar = "█" * filled + "░" * (10 - filled)
        return f"[$primary]{bar}[/] {self.label}"


# T4.3: Cost & Usage Dashboard
from src.ui.tui.widgets.cost_dashboard import CostDashboard, UsageStats

# T4.4: Live Activity Feed
from src.ui.tui.widgets.activity_feed import ActivityFeed, LiveEventCounter, EventStream

# T4.1: Knowledge Graph Viewer
from src.ui.tui.widgets.kg_viewer import KnowledgeGraphViewer, AgentGraphViewer

# T4.2: Routing Funnel Visualization
from src.ui.tui.widgets.routing_funnel import RoutingFunnel, SimpleRoutingStats

# T4.5: Progress Indicators
from src.ui.tui.widgets.progress import StepProgress, CircularProgress

# T5.1-5.3: Theme, Performance, Error Handling
from src.ui.tui.widgets.enhancements import (
    ThemeEnhancer,
    PerformanceOptimizer,
    ErrorBoundary,
)


__all__ = [
    # T2.1-2.2: Core widgets
    "MetricSparkline",
    "MetricCard",
    "StatusIndicator",
    "ProgressRing",
    # T4.1: Knowledge Graph
    "KnowledgeGraphViewer",
    "AgentGraphViewer",
    # T4.2: Routing Funnel
    "RoutingFunnel",
    "SimpleRoutingStats",
    # T4.3: Cost Dashboard
    "CostDashboard",
    "UsageStats",
    # T4.4: Activity Feed
    "ActivityFeed",
    "LiveEventCounter",
    "EventStream",
    # T4.5: Progress Indicators
    "StepProgress",
    "CircularProgress",
    # T5.x: Enhancements
    "ThemeEnhancer",
    "PerformanceOptimizer",
    "ErrorBoundary",
]
