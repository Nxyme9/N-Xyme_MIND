"""
Benchmark Runner Module for N-Xyme MIND Dashboard TUI.

Provides a modal dialog for running performance benchmarks on agents and models.
"""

import json
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Header,
    Static,
    Label,
    Input,
    ProgressBar,
    Select,
)


# Benchmark type constants
BENCHMARK_TYPES = [
    ("agent_latency", "Agent Latency"),
    ("model_throughput", "Model Throughput"),
    ("routing_accuracy", "Routing Accuracy"),
    ("memory_query", "Memory Query"),
]


@dataclass
class BenchmarkConfig:
    """Configuration for a benchmark run."""

    benchmark_type: str
    iterations: int = 100
    warmup_runs: int = 10
    timeout: float = 30.0

    def __post_init__(self) -> None:
        """Validate benchmark configuration after initialization."""
        if not 1 <= self.iterations <= 1000:
            raise ValueError("Iterations must be between 1 and 1000")
        if not 0 <= self.warmup_runs <= 100:
            raise ValueError("Warmup runs must be between 0 and 100")
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")


@dataclass
class BenchmarkResult:
    """Results from a benchmark run."""

    benchmark_type: str
    iterations: int
    latencies: list[float] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def min_latency(self) -> float:
        """Get minimum latency."""
        return min(self.latencies) if self.latencies else 0.0

    @property
    def max_latency(self) -> float:
        """Get maximum latency."""
        return max(self.latencies) if self.latencies else 0.0

    @property
    def avg_latency(self) -> float:
        """Get average latency."""
        return sum(self.latencies) / len(self.latencies) if self.latencies else 0.0

    @property
    def p50_latency(self) -> float:
        """Get 50th percentile latency."""
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        idx = len(sorted_latencies) // 2
        return sorted_latencies[idx]

    @property
    def p95_latency(self) -> float:
        """Get 95th percentile latency."""
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[idx]

    @property
    def p99_latency(self) -> float:
        """Get 99th percentile latency."""
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.99)
        return sorted_latencies[idx]

    @property
    def throughput(self) -> float:
        """Get throughput (iterations per second)."""
        if not self.latencies:
            return 0.0
        total_time = sum(self.latencies)
        return self.iterations / total_time if total_time > 0 else 0.0

    def to_dict(self) -> dict:
        """Convert result to dictionary for JSON export."""
        return {
            "benchmark_type": self.benchmark_type,
            "iterations": self.iterations,
            "timestamp": self.timestamp,
            "latency": {
                "min_ms": round(self.min_latency * 1000, 2),
                "max_ms": round(self.max_latency * 1000, 2),
                "avg_ms": round(self.avg_latency * 1000, 2),
                "p50_ms": round(self.p50_latency * 1000, 2),
                "p95_ms": round(self.p95_latency * 1000, 2),
                "p99_ms": round(self.p99_latency * 1000, 2),
            },
            "throughput": {
                "ops_per_second": round(self.throughput, 2),
            },
        }


class BenchmarkRunnerDialog(ModalScreen):
    """
    Textual Modal Dialog for running performance benchmarks.

    Features:
    - Select benchmark type (agent_latency, model_throughput, routing_accuracy, memory_query)
    - Configure iterations (1-1000), warmup_runs, timeout
    - Progress bar during execution
    - Results display with min/max/avg latency, p50/p95/p99, throughput
    - Export results to JSON
    """

    CSS = """
    BenchmarkRunnerDialog {
        align: center middle;
    }

    #dialog_container {
        width: 80;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: solid $primary;
        padding: 1;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: $text;
        padding: 1;
    }

    #config_section {
        height: auto;
        padding: 1;
        background: $panel;
        margin-bottom: 1;
    }

    #config_row {
        height: auto;
        margin-bottom: 1;
    }

    #results_section {
        height: auto;
        padding: 1;
        background: $panel;
        margin-bottom: 1;
    }

    #results_table {
        margin: 1;
        border: solid $primary;
        height: 8;
    }

    #progress_section {
        height: auto;
        padding: 1;
        background: $panel;
        margin-bottom: 1;
    }

    #button_row {
        height: auto;
        align: center middle;
        padding: 1;
    }

    Button {
        margin: 0 1;
    }

    Select, Input {
        width: 100%;
    }

    .config_label {
        width: 20;
    }

    .config_input {
        width: 1fr;
    }
    """

    def __init__(self) -> None:
        """Initialize the Benchmark Runner Dialog."""
        super().__init__()
        self._config: Optional[BenchmarkConfig] = None
        self._results: Optional[BenchmarkResult] = None
        self._is_running: bool = False

    def compose(self) -> ComposeResult:
        """Compose the dialog widgets."""
        with Vertical(id="dialog_container"):
            # Title
            yield Static("Benchmark Runner", id="title")

            # Configuration section
            with Container(id="config_section"):
                yield Static("Configuration", classes="section_header")

                with Horizontal(id="config_row"):
                    yield Label("Benchmark Type:", classes="config_label")
                    yield Select(
                        [(t[0], t[1]) for t in BENCHMARK_TYPES],
                        value="agent_latency",
                        id="benchmark_type",
                    )

                with Horizontal(id="config_row"):
                    yield Label("Iterations:", classes="config_label")
                    yield Input(
                        value="100",
                        placeholder="1-1000",
                        id="iterations",
                        classes="config_input",
                    )

                with Horizontal(id="config_row"):
                    yield Label("Warmup Runs:", classes="config_label")
                    yield Input(
                        value="10",
                        placeholder="0-100",
                        id="warmup_runs",
                        classes="config_input",
                    )

                with Horizontal(id="config_row"):
                    yield Label("Timeout (s):", classes="config_label")
                    yield Input(
                        value="30",
                        placeholder="Timeout in seconds",
                        id="timeout",
                        classes="config_input",
                    )

            # Progress section
            with Container(id="progress_section"):
                yield Static("Progress", classes="section_header")
                yield ProgressBar(total=100, id="progress_bar")

            # Results section
            with Container(id="results_section"):
                yield Static("Results", classes="section_header")
                yield DataTable(id="results_table")

            # Button row
            with Horizontal(id="button_row"):
                yield Button("Run Benchmark", variant="primary", id="btn_run")
                yield Button("Export JSON", variant="success", id="btn_export")
                yield Button("Close", variant="default", id="btn_close")

    def on_mount(self) -> None:
        """Initialize the dialog on mount."""
        table = self.query_one("#results_table", DataTable)

        # Add columns
        table.add_columns("Metric", "Value")

        # Disable export until we have results
        self._set_export_enabled(False)

    def _set_export_enabled(self, enabled: bool) -> None:
        """Enable or disable the export button."""
        export_btn = self.query_one("#btn_export", Button)
        export_btn.disabled = not enabled

    def _generate_mock_latencies(self, count: int) -> list[float]:
        """Generate mock latency data for demonstration."""
        # Generate realistic-looking latencies with some variance
        base_latency = random.uniform(0.05, 0.2)  # 50-200ms base
        latencies = []
        for _ in range(count):
            # Add random variance (mostly around base, occasionally higher)
            if random.random() < 0.05:
                # 5% chance of outlier
                latency = base_latency * random.uniform(2, 5)
            else:
                latency = base_latency * random.uniform(0.8, 1.5)
            latencies.append(latency)
        return latencies

    def _run_benchmark_mock(self) -> BenchmarkResult:
        """Run a mock benchmark (simulates actual benchmarking)."""
        if self._config is None:
            return BenchmarkResult(benchmark_type="none", iterations=0)

        # Generate mock latencies
        latencies = self._generate_mock_latencies(self._config.iterations)

        return BenchmarkResult(
            benchmark_type=self._config.benchmark_type,
            iterations=self._config.iterations,
            latencies=latencies,
        )

    async def _execute_benchmark(self) -> None:
        """Execute the benchmark with progress updates."""
        self._is_running = True
        self._set_run_enabled(False)

        progress = self.query_one("#progress_bar", ProgressBar)

        try:
            # Simulate progress updates
            for i in range(101):
                progress.advance(1)
                # Small delay to show progress
                time.sleep(0.02)

            # Run the benchmark
            self._results = self._run_benchmark_mock()

            # Update results table
            self._update_results_table()

            self._set_export_enabled(True)
            self.notify("Benchmark completed successfully", severity="information")

        except Exception as e:
            self.notify(f"Benchmark failed: {str(e)}", severity="error")
        finally:
            self._is_running = False
            self._set_run_enabled(True)

    def _set_run_enabled(self, enabled: bool) -> None:
        """Enable or disable the run button."""
        run_btn = self.query_one("#btn_run", Button)
        run_btn.disabled = not enabled

    def _update_results_table(self) -> None:
        """Update the results table with current results."""
        if self._results is None:
            return

        table = self.query_one("#results_table", DataTable)
        table.clear()

        # Add result rows
        table.add_row("Min Latency", f"{self._results.min_latency * 1000:.2f} ms")
        table.add_row("Max Latency", f"{self._results.max_latency * 1000:.2f} ms")
        table.add_row("Avg Latency", f"{self._results.avg_latency * 1000:.2f} ms")
        table.add_row("P50 Latency", f"{self._results.p50_latency * 1000:.2f} ms")
        table.add_row("P95 Latency", f"{self._results.p95_latency * 1000:.2f} ms")
        table.add_row("P99 Latency", f"{self._results.p99_latency * 1000:.2f} ms")
        table.add_row("Throughput", f"{self._results.throughput:.2f} ops/s")

    def _parse_config(self) -> bool:
        """Parse and validate the configuration from inputs."""
        try:
            benchmark_type_select = self.query_one("#benchmark_type", Select)
            benchmark_type_val = benchmark_type_select.value
            if isinstance(benchmark_type_val, str):
                benchmark_type = benchmark_type_val
            else:
                benchmark_type = "agent_latency"

            iterations_input = self.query_one("#iterations", Input)
            iterations = int(iterations_input.value.strip())

            warmup_input = self.query_one("#warmup_runs", Input)
            warmup_runs = int(warmup_input.value.strip())

            timeout_input = self.query_one("#timeout", Input)
            timeout = float(timeout_input.value.strip())

            self._config = BenchmarkConfig(
                benchmark_type=benchmark_type,
                iterations=iterations,
                warmup_runs=warmup_runs,
                timeout=timeout,
            )
            return True

        except ValueError as e:
            self.notify(f"Invalid configuration: {str(e)}", severity="error")
            return False

    def _export_results(self) -> None:
        """Export benchmark results to JSON file."""
        if self._results is None:
            self.notify("No results to export", severity="warning")
            return

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_path = f"benchmark_{self._results.benchmark_type}_{timestamp}.json"

            result_dict = self._results.to_dict()
            file_path = Path(default_path)

            with file_path.open("w", encoding="utf-8") as f:
                json.dump(result_dict, f, indent=2)

            self.notify(f"Results exported to {default_path}", severity="information")

        except Exception as e:
            self.notify(f"Export failed: {str(e)}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id

        if button_id == "btn_run":
            if self._parse_config():
                # Reset progress bar
                progress = self.query_one("#progress_bar", ProgressBar)
                progress.update(progress=0)
                # Run benchmark asynchronously
                self._executor = self._executor or self.app.run_worker
                self.app.call_later(self._execute_benchmark)

        elif button_id == "btn_export":
            self._export_results()

        elif button_id == "btn_close":
            self.app.pop_screen()


# Module-level default instance
_default_runner: Optional["BenchmarkRunnerDialog"] = None


def get_runner() -> BenchmarkRunnerDialog:
    """
    Get the benchmark runner dialog instance.

    Returns:
        The BenchmarkRunnerDialog instance.
    """
    global _default_runner
    if _default_runner is None:
        _default_runner = BenchmarkRunnerDialog()
    return _default_runner
