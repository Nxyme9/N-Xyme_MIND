"""
Chart widgets for Textual TUI.

Provides LineChart, BarChart, and Sparkline widgets for data visualization.
"""

from typing import Optional

from textual.widget import Widget
from textual.widgets import Static


class LineChart(Static):
    """
    ASCII line chart widget.
    
    Displays a line chart using ASCII/Unicode characters with proper scaling.
    """
    
    def __init__(self, *args, **kwargs) -> None:
        """Initialize the LineChart widget."""
        super().__init__(*args, **kwargs)
        self._data: list[float] = []
        self._color: str = "cyan"
        self._labels: list[str] = []
    
    def set_data(self, data: list[float]) -> None:
        """
        Set the data for the chart.
        
        Args:
            data: List of float values to plot.
        """
        self._data = data or []
        self.refresh()
    
    def set_color(self, color: str) -> None:
        """
        Set the chart color.
        
        Args:
            color: Textual color name (e.g., "cyan", "green", "red").
        """
        self._color = color
        self.refresh()
    
    def set_labels(self, labels: list[str]) -> None:
        """
        Set the x-axis labels.
        
        Args:
            labels: List of label strings for x-axis.
        """
        self._labels = labels or []
        self.refresh()
    
    def render(self) -> str:
        """Render the line chart."""
        if not self._data:
            return "[dim]No data[/dim]"
        
        # Get available width
        width = max(self.size.width - 2, 10)
        if width < 10:
            return "[dim]Too narrow[/dim]"
        
        # Normalize data to fit in height (default 8 rows)
        height = 8
        min_val = min(self._data)
        max_val = max(self._data)
        data_range = max_val - min_val if max_val != min_val else 1
        
        # Sample data points to fit width
        num_points = min(len(self._data), width)
        step = len(self._data) // num_points if num_points > 1 else 1
        sampled = self._data[::step][:num_points]
        
        # Build the chart
        lines = []
        for row in range(height, 0, -1):
            threshold = min_val + (data_range * row / height)
            line_chars = []
            for val in sampled:
                if val >= threshold:
                    line_chars.append("●")
                else:
                    line_chars.append(" ")
            lines.append("│ " + "".join(line_chars))
        
        # Add baseline
        baseline = "├" + "─" * len(sampled)
        lines.append(baseline)
        
        # Add labels if provided
        if self._labels and len(sampled) > 0:
            label_step = max(1, len(self._labels) // len(sampled))
            label_chars = []
            for i in range(len(sampled)):
                idx = i * label_step
                if idx < len(self._labels):
                    label_chars.append(self._labels[idx][:1])
                else:
                    label_chars.append(" ")
            lines.append("  " + "".join(label_chars))
        
        return f"[{self._color}]" + "\n".join(lines) + "[/]"


class BarChart(Static):
    """
    ASCII horizontal bar chart widget.
    
    Displays a horizontal bar chart using ASCII/Unicode characters.
    """
    
    def __init__(self, *args, **kwargs) -> None:
        """Initialize the BarChart widget."""
        super().__init__(*args, **kwargs)
        self._data: list[float] = []
        self._color: str = "green"
        self._labels: list[str] = []
    
    def set_data(self, data: list[float]) -> None:
        """
        Set the data for the chart.
        
        Args:
            data: List of float values to plot.
        """
        self._data = data or []
        self.refresh()
    
    def set_color(self, color: str) -> None:
        """
        Set the chart color.
        
        Args:
            color: Textual color name (e.g., "cyan", "green", "red").
        """
        self._color = color
        self.refresh()
    
    def set_labels(self, labels: list[str]) -> None:
        """
        Set the labels for bars.
        
        Args:
            labels: List of label strings for each bar.
        """
        self._labels = labels or []
        self.refresh()
    
    def render(self) -> str:
        """Render the bar chart."""
        if not self._data:
            return "[dim]No data[/dim]"
        
        # Get available width
        width = max(self.size.width - 15, 20)
        if width < 10:
            return "[dim]Too narrow[/dim]"
        
        # Find max value for scaling
        max_val = max(self._data) if self._data else 1
        if max_val == 0:
            max_val = 1
        
        # Build the chart
        lines = []
        for i, value in enumerate(self._data):
            # Calculate bar length
            bar_length = int((value / max_val) * width)
            bar_length = min(bar_length, width)
            
            # Get label
            label = self._labels[i] if i < len(self._labels) else f"Item {i+1}"
            label = label[:10].ljust(10)
            
            # Create bar
            bar = "█" * bar_length
            value_str = f"{value:.1f}"[:6].rjust(6)
            lines.append(f"{label} │[{self._color}]{bar}[/] {value_str}")
        
        return "\n".join(lines)


class Sparkline(Static):
    """
    Compact inline sparkline widget.
    
    Renders a compact sparkline using Unicode box-drawing characters.
    """
    
    def __init__(self, *args, **kwargs) -> None:
        """Initialize the Sparkline widget."""
        super().__init__(*args, **kwargs)
        self._data: list[float] = []
        self._color: str = "cyan"
    
    def set_data(self, data: list[float]) -> None:
        """
        Set the data for the sparkline.
        
        Args:
            data: List of float values to plot.
        """
        self._data = data or []
        self.refresh()
    
    def set_color(self, color: str) -> None:
        """
        Set the sparkline color.
        
        Args:
            color: Textual color name (e.g., "cyan", "green", "red").
        """
        self._color = color
        self.refresh()
    
    def render(self) -> str:
        """Render the sparkline."""
        if not self._data:
            return "[dim]──[/dim]"
        
        # Unicode block characters for sparkline levels
        blocks = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
        
        # Calculate min/max for scaling
        min_val = min(self._data)
        max_val = max(self._data)
        data_range = max_val - min_val if max_val != min_val else 1
        
        # Generate sparkline
        spark = []
        for val in self._data:
            # Normalize to 0-7 range
            level = int(((val - min_val) / data_range) * 7)
            level = max(0, min(7, level))
            spark.append(blocks[level])
        
        return f"[{self._color}]{''.join(spark)}[/]"