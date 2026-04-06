"""Performance regression tests based on benchmark baselines."""

import json
import os
import time
import pytest

BENCHMARK_FILE = os.path.join(
    os.path.dirname(__file__), "..", "..", "benchmark-results.json"
)
REGRESSION_TOLERANCE = 1.2  # 20% tolerance


def load_baselines():
    """Load benchmark baselines from benchmark-results.json."""
    if not os.path.exists(BENCHMARK_FILE):
        pytest.skip("benchmark-results.json not found")
    with open(BENCHMARK_FILE) as f:
        data = json.load(f)
    baselines = {}
    for result in data.get("results", []):
        baselines[result["name"]] = result["latency"]["mean_ms"]
    return baselines


def measure_latency(func, iterations=50):
    """Measure mean latency of a function in milliseconds."""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        end = time.perf_counter()
        times.append((end - start) * 1000)
    return sum(times) / len(times)


class TestModelRoutingPerformance:
    """Performance regression tests for model routing."""

    def test_model_config_loading_no_regression(self):
        """Model config loading should not regress beyond 20%."""
        baselines = load_baselines()
        baseline_ms = baselines.get("model_config_loading", 0.0016)

        def load_config():
            from bin.model_config import ModelConfig

            ModelConfig()

        current_ms = measure_latency(load_config, iterations=100)
        assert current_ms < baseline_ms * REGRESSION_TOLERANCE, (
            f"Model config loading regressed: {current_ms:.4f}ms > {baseline_ms * REGRESSION_TOLERANCE:.4f}ms"
        )

    def test_model_selection_no_regression(self):
        """Model selection should not regress beyond 20%."""
        baselines = load_baselines()
        baseline_ms = baselines.get("model_selection", 0.0023)

        def select_model():
            from bin.model_selector import ModelSelector

            selector = ModelSelector()
            selector.route("test task")

        current_ms = measure_latency(select_model, iterations=100)
        assert current_ms < baseline_ms * REGRESSION_TOLERANCE, (
            f"Model selection regressed: {current_ms:.4f}ms > {baseline_ms * REGRESSION_TOLERANCE:.4f}ms"
        )

    def test_model_routing_no_regression(self):
        """Model routing should not regress beyond 20%."""
        baselines = load_baselines()
        baseline_ms = baselines.get("model_routing", 0.6945)

        def route_task():
            from bin.model_router import ModelRouter

            router = ModelRouter()
            router.route_task("test task")

        current_ms = measure_latency(route_task, iterations=50)
        assert current_ms < baseline_ms * REGRESSION_TOLERANCE, (
            f"Model routing regressed: {current_ms:.4f}ms > {baseline_ms * REGRESSION_TOLERANCE:.4f}ms"
        )

    def test_prompt_cache_no_regression(self):
        """Prompt cache operations should not regress beyond 20%."""
        baselines = load_baselines()
        baseline_ms = baselines.get("prompt_cache", 0.0661)

        def cache_operation():
            from bin.prompt_cache import PromptCache

            cache = PromptCache()
            cache.get("test-key")

        current_ms = measure_latency(cache_operation, iterations=100)
        assert current_ms < baseline_ms * REGRESSION_TOLERANCE, (
            f"Prompt cache regressed: {current_ms:.4f}ms > {baseline_ms * REGRESSION_TOLERANCE:.4f}ms"
        )
