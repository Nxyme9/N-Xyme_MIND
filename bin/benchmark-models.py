#!/usr/bin/env python3
"""Comprehensive benchmark suite for model configuration scripts.

Measures latency, throughput, and cost for all model configuration scripts.
Collects real performance data for validation of optimization claims.

Usage:
    python3 bin/benchmark-models.py --runs 1000 --all
    python3 bin/benchmark-models.py --runs 100 --config
    python3 bin/benchmark-models.py --runs 100 --selector --output json
"""

import argparse
import json
import os
import random
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

import tracemalloc
tracemalloc.start()


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run."""

    name: str
    iterations: int
    latencies: list[float] = field(default_factory=list)
    memory_before: int = 0
    memory_after: int = 0
    metadata: dict = field(default_factory=dict)

    @property
    def mean(self) -> float:
        return statistics.mean(self.latencies) if self.latencies else 0.0

    @property
    def std(self) -> float:
        return statistics.stdev(self.latencies) if len(self.latencies) > 1 else 0.0

    @property
    def p50(self) -> float:
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.50)
        return sorted_latencies[idx]

    @property
    def p95(self) -> float:
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[idx]

    @property
    def p99(self) -> float:
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.99)
        return sorted_latencies[idx]

    @property
    def throughput(self) -> float:
        total_time = sum(self.latencies)
        return self.iterations / total_time if total_time > 0 else 0.0

    @property
    def memory_delta(self) -> int:
        return self.memory_after - self.memory_before

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "iterations": self.iterations,
            "latency": {
                "mean_ms": round(self.mean * 1000, 4),
                "std_ms": round(self.std * 1000, 4),
                "p50_ms": round(self.p50 * 1000, 4),
                "p95_ms": round(self.p95 * 1000, 4),
                "p99_ms": round(self.p99 * 1000, 4),
            },
            "throughput": {
                "ops_per_sec": round(self.throughput, 2),
            },
            "memory": {
                "before_bytes": self.memory_before,
                "after_bytes": self.memory_after,
                "delta_bytes": self.memory_delta,
            },
            "metadata": self.metadata,
        }


class BenchmarkSuite:
    """Comprehensive benchmark suite for model configuration scripts."""

    SAMPLE_TASKS = [
        "Write a function to calculate fibonacci",
        "Explain what is a closure in programming",
        "Debug this code that throws an error",
        "Design a new feature for user authentication",
        "Refactor this class for better performance",
        "Create a REST API endpoint handler",
        "Review this code for security issues",
        "Optimize this database query",
        "Add unit tests for this module",
        "Implement a caching mechanism",
        "Fix the memory leak in this function",
        "Build a scalable architecture",
        "Integrate with external API",
        "Write documentation for this module",
        "Analyze the performance bottleneck",
        "Create a data structure for LRU cache",
        "Implement binary search algorithm",
        "Design a system for rate limiting",
        "Build a middleware component",
        "Refactor to use async/await",
    ] * 5

    def __init__(self, iterations: int = 1000):
        self.iterations = iterations
        self.results: list[BenchmarkResult] = []
        self.process = psutil.Process() if PSUTIL_AVAILABLE else None

    def get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        if self.process is not None:
            return self.process.memory_info().rss
        # Fallback to tracemalloc
        current, _ = tracemalloc.get_traced_memory()
        return current

    def run_benchmark(
        self,
        name: str,
        func: Callable[[], Any],
        metadata: Optional[dict] = None,
    ) -> BenchmarkResult:
        """Run a benchmark with timing measurements."""
        result = BenchmarkResult(
            name=name,
            iterations=self.iterations,
            metadata=metadata or {},
        )

        result.memory_before = self.get_memory_usage()

        for _ in range(self.iterations):
            start = time.perf_counter()
            func()
            end = time.perf_counter()
            result.latencies.append(end - start)

        result.memory_after = self.get_memory_usage()

        self.results.append(result)
        return result

    def benchmark_config_loading(self) -> BenchmarkResult:
        """Benchmark ModelConfig loading performance."""
        sys.path.insert(0, str(Path(__file__).parent))
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "model_config", Path(__file__).parent / "model_config.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        ModelConfig = module.ModelConfig

        def load_config():
            config = ModelConfig()
            _ = config.get_model("coding")
            return config

        metadata = {
            "description": "Measure time to load ModelConfig and get model",
            "module": "model_config.py",
        }

        return self.run_benchmark(
            name="model_config_loading",
            func=load_config,
            metadata=metadata,
        )

    def benchmark_model_selection(self) -> BenchmarkResult:
        """Benchmark model-selector.py routing performance."""
        sys.path.insert(0, str(Path(__file__).parent))
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "model_selector", Path(__file__).parent / "model-selector.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        detect_complexity = module.detect_complexity
        MODELS = module.MODELS

        tasks = random.sample(self.SAMPLE_TASKS, min(100, len(self.SAMPLE_TASKS)))

        def select_model():
            task = random.choice(tasks)
            complexity = detect_complexity(task)
            model = MODELS[complexity]
            return model

        metadata = {
            "description": "Measure time for model-selector.py to route tasks",
            "module": "model-selector.py",
            "num_tasks": len(tasks),
        }

        return self.run_benchmark(
            name="model_selection",
            func=select_model,
            metadata=metadata,
        )

    def benchmark_model_routing(self) -> BenchmarkResult:
        """Benchmark model-router.py routing performance."""
        sys.path.insert(0, str(Path(__file__).parent))
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "model_router", Path(__file__).parent / "model-router.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        ModelRouter = module.ModelRouter

        router = ModelRouter()
        tasks = random.sample(self.SAMPLE_TASKS, min(100, len(self.SAMPLE_TASKS)))

        def route_task():
            task = random.choice(tasks)
            result = router.route(task)
            return result

        metadata = {
            "description": "Measure time for model-router.py to route tasks",
            "module": "model-router.py",
            "num_tasks": len(tasks),
        }

        return self.run_benchmark(
            name="model_routing",
            func=route_task,
            metadata=metadata,
        )

    def benchmark_prompt_cache(self) -> BenchmarkResult:
        """Benchmark prompt cache hit/miss performance."""
        sys.path.insert(0, str(Path(__file__).parent))
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "prompt_cache", Path(__file__).parent / "prompt-cache.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        PromptCache = module.PromptCache

        cache = PromptCache(cache_dir="/tmp/benchmark_cache", max_size=1000)
        cache.clear()

        test_prompts = [
            "Write a function to calculate fibonacci numbers",
            "Explain what is a closure in programming",
            "Debug this code that throws an error",
            "Design a new feature for user authentication",
            "Refactor this class for better performance",
        ]

        for i, prompt in enumerate(test_prompts):
            cache.put(prompt, f"Response {i}")

        hit_count = 0
        miss_count = 0

        def cache_operation():
            nonlocal hit_count, miss_count
            prompt = random.choice(test_prompts)
            result = cache.get(prompt)
            if result is not None:
                hit_count += 1
            else:
                miss_count += 1
            return result

        metadata = {
            "description": "Measure hit/miss latency for cache operations",
            "module": "prompt-cache.py",
            "cache_size": len(test_prompts),
        }

        result = self.run_benchmark(
            name="prompt_cache",
            func=cache_operation,
            metadata=metadata,
        )

        total = hit_count + miss_count
        hit_rate = (hit_count / total * 100) if total > 0 else 0
        result.metadata["hit_rate"] = round(hit_rate, 2)

        cache.clear()

        return result

    def benchmark_fallback_chain(self) -> BenchmarkResult:
        """Benchmark fallback chain performance with mocks."""
        sys.path.insert(0, str(Path(__file__).parent))
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "model_fallback", Path(__file__).parent / "model-fallback.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        ModelFallback = module.ModelFallback
        PRIORITY_MODELS = module.PRIORITY_MODELS

        class MockModelFallback(ModelFallback):
            """Mock fallback that simulates API calls."""

            def call_model(self, model: str, prompt: str) -> dict:
                time.sleep(random.uniform(0.001, 0.005))
                return {"success": True, "response": "Mock response", "model": model}

        fallback = MockModelFallback()

        def call_with_fallback():
            result = fallback.call_with_fallback("test prompt")
            return result

        metadata = {
            "description": "Measure time for each tier in fallback chain",
            "module": "model-fallback.py",
            "num_tiers": len(PRIORITY_MODELS),
            "models": PRIORITY_MODELS[:3],
        }

        return self.run_benchmark(
            name="fallback_chain",
            func=call_with_fallback,
            metadata=metadata,
        )

    def benchmark_local_router_classification(self) -> BenchmarkResult:
        """Benchmark local-router.py classification latency."""
        sys.path.insert(0, str(Path(__file__).parent))
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "local_router", Path(__file__).parent / "local-router.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        LocalRouter = module.LocalRouter

        router = LocalRouter()
        tasks = random.sample(self.SAMPLE_TASKS, min(100, len(self.SAMPLE_TASKS)))

        def classify_task():
            task = random.choice(tasks)
            return router.classify(task)

        metadata = {
            "description": "Measure classification latency for local-router.py",
            "module": "local-router.py",
            "num_tasks": len(tasks),
        }

        return self.run_benchmark(
            name="local_router_classification",
            func=classify_task,
            metadata=metadata,
        )

    def benchmark_local_pipeline_single_step(self) -> BenchmarkResult:
        """Benchmark local-pipeline.py single-step latency."""
        sys.path.insert(0, str(Path(__file__).parent))
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "local_pipeline", Path(__file__).parent / "local-pipeline.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        PipelineRunner = module.PipelineRunner

        class MockLocalRouter:
            def __init__(self):
                self.default_model = "llama3.2:3b"
            def generate(self, prompt, model=None, timeout=120.0):
                time.sleep(random.uniform(0.001, 0.005))
                return {"success": True, "response": "Mock response for: " + prompt[:50]}

        runner = PipelineRunner(local_router=MockLocalRouter())

        test_steps = [
            {"task": "Summarize this text", "model": "llama3.2:3b"},
            {"task": "Explain what a closure is", "model": "llama3.2:3b"},
            {"task": "Write a hello world function", "model": "llama3.2:3b"},
        ]

        def execute_single_step():
            step = random.choice(test_steps)
            return runner.execute_step(step, {"previous_output": None})

        metadata = {
            "description": "Measure single-step execution latency for local-pipeline.py (mocked)",
            "module": "local-pipeline.py",
            "num_steps": len(test_steps),
        }

        return self.run_benchmark(
            name="local_pipeline_single_step",
            func=execute_single_step,
            metadata=metadata,
        )

    def benchmark_local_chain_escalation(self) -> BenchmarkResult:
        """Benchmark local-chain.py escalation latency."""
        sys.path.insert(0, str(Path(__file__).parent))
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "local_router_module", Path(__file__).parent / "local-router.py"
        )
        router_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(router_module)
        LocalRouter = router_module.LocalRouter

        spec = importlib.util.spec_from_file_location(
            "local_chain", Path(__file__).parent / "local-chain.py"
        )
        chain_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(chain_module)
        ChainOrchestrator = chain_module.ChainOrchestrator

        class MockLocalRouter:
            def is_local_available(self, timeout=2.0):
                return True

        orchestrator = ChainOrchestrator(local_router=MockLocalRouter(), quality_threshold=0.7)

        test_prompts = [
            "Write a function to calculate fibonacci numbers",
            "Explain what is a closure in programming",
            "Debug this code that throws an error",
        ]

        def execute_with_escalation():
            prompt = random.choice(test_prompts)
            return orchestrator.execute_with_escalation(prompt=prompt, max_retries=1)

        metadata = {
            "description": "Measure escalation latency for local-chain.py (mocked)",
            "module": "local-chain.py",
            "num_prompts": len(test_prompts),
        }

        return self.run_benchmark(
            name="local_chain_escalation",
            func=execute_with_escalation,
            metadata=metadata,
        )

    def run_all(self) -> list[BenchmarkResult]:
        """Run all benchmarks."""
        self.results = []

        print("Running Model Config Loading benchmark...")
        self.benchmark_config_loading()

        print("Running Model Selection benchmark...")
        self.benchmark_model_selection()

        print("Running Model Routing benchmark...")
        self.benchmark_model_routing()

        print("Running Prompt Cache benchmark...")
        self.benchmark_prompt_cache()

        print("Running Fallback Chain benchmark...")
        self.benchmark_fallback_chain()

        print("Running Local Router Classification benchmark...")
        self.benchmark_local_router_classification()

        print("Running Local Pipeline Single-Step benchmark...")
        self.benchmark_local_pipeline_single_step()

        print("Running Local Chain Escalation benchmark...")
        self.benchmark_local_chain_escalation()

        return self.results

    def format_table(self) -> str:
        """Format results as a pretty table."""
        if not self.results:
            return "No results to display."

        lines = []
        lines.append("\n" + "=" * 100)
        lines.append("BENCHMARK RESULTS")
        lines.append("=" * 100)
        lines.append(f"Timestamp: {datetime.now().isoformat()}")
        lines.append(f"Total Iterations per benchmark: {self.iterations}")
        lines.append("=" * 100)

        lines.append("\n{:<35} {:>12} {:>12} {:>12} {:>12} {:>12}".format(
            "BENCHMARK", "MEAN (ms)", "P50 (ms)", "P95 (ms)", "P99 (ms)", "OPS/SEC"
        ))
        lines.append("-" * 100)

        for result in self.results:
            lines.append(
                "{:<35} {:>12.4f} {:>12.4f} {:>12.4f} {:>12.4f} {:>12.2f}".format(
                    result.name,
                    result.mean * 1000,
                    result.p50 * 1000,
                    result.p95 * 1000,
                    result.p99 * 1000,
                    result.throughput,
                )
            )

        lines.append("\n" + "=" * 100)
        lines.append("\nLOCAL vs CLOUD LATENCY COMPARISON")
        lines.append("=" * 100)

        local_benchmarks = [r for r in self.results if "local_" in r.name]
        cloud_benchmarks = [r for r in self.results if "local_" not in r.name]

        if local_benchmarks:
            local_mean = statistics.mean(r.mean for r in local_benchmarks)
            lines.append(f"Local Mean Latency:  {local_mean * 1000:.4f} ms")
            lines.append(f"Local Benchmarks:    {len(local_benchmarks)}")
            for r in local_benchmarks:
                lines.append(f"  - {r.name}: {r.mean * 1000:.4f} ms")

        if cloud_benchmarks:
            cloud_mean = statistics.mean(r.mean for r in cloud_benchmarks)
            lines.append(f"\nCloud Mean Latency:  {cloud_mean * 1000:.4f} ms")
            lines.append(f"Cloud Benchmarks:    {len(cloud_benchmarks)}")
            for r in cloud_benchmarks:
                lines.append(f"  - {r.name}: {r.mean * 1000:.4f} ms")

        if local_benchmarks and cloud_benchmarks:
            local_mean = statistics.mean(r.mean for r in local_benchmarks)
            cloud_mean = statistics.mean(r.mean for r in cloud_benchmarks)
            if cloud_mean > 0:
                speedup = cloud_mean / local_mean
                lines.append(f"\nLocal is {speedup:.2f}x {'faster' if speedup > 1 else 'slower'} than cloud")

        lines.append("\n" + "=" * 100)

        lines.append("\nDETAILED BENCHMARK RESULTS")
        lines.append("=" * 100)

        for result in self.results:
            lines.append(f"\n{result.name.upper()}")
            lines.append("-" * 60)
            lines.append(f"  Iterations:     {result.iterations}")
            lines.append(f"  Mean Latency:   {result.mean * 1000:.4f} ms")
            lines.append(f"  Std Dev:        {result.std * 1000:.4f} ms")
            lines.append(f"  P50 Latency:    {result.p50 * 1000:.4f} ms")
            lines.append(f"  P95 Latency:    {result.p95 * 1000:.4f} ms")
            lines.append(f"  P99 Latency:    {result.p99 * 1000:.4f} ms")
            lines.append(f"  Throughput:     {result.throughput:.2f} ops/sec")

            if result.memory_delta != 0:
                lines.append(f"  Memory Delta:   {result.memory_delta / 1024:.2f} KB")

            if result.metadata:
                for key, value in result.metadata.items():
                    lines.append(f"  {key}:     {value}")

        lines.append("\n" + "=" * 100)

    def to_json(self) -> dict:
        """Convert all results to JSON-serializable dictionary."""
        return {
            "timestamp": datetime.now().isoformat(),
            "iterations": self.iterations,
            "results": [r.to_dict() for r in self.results],
        }


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Comprehensive benchmark suite for model configuration scripts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 bin/benchmark-models.py --runs 1000 --all
  python3 bin/benchmark-models.py --runs 100 --config
  python3 bin/benchmark-models.py --runs 100 --selector --router
  python3 bin/benchmark-models.py --runs 500 --cache --output json
        """,
    )

    parser.add_argument(
        "--runs",
        type=int,
        default=1000,
        help="Number of iterations for each benchmark (default: 1000)",
    )

    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all benchmarks",
    )

    parser.add_argument(
        "--config",
        action="store_true",
        help="Run ModelConfig loading benchmark",
    )

    parser.add_argument(
        "--selector",
        action="store_true",
        help="Run model selector benchmark",
    )

    parser.add_argument(
        "--router",
        action="store_true",
        help="Run model router benchmark",
    )

    parser.add_argument(
        "--cache",
        action="store_true",
        help="Run prompt cache benchmark",
    )

    parser.add_argument(
        "--fallback",
        action="store_true",
        help="Run fallback chain benchmark",
    )

    parser.add_argument(
        "--local-router",
        action="store_true",
        help="Run local router classification benchmark",
    )

    parser.add_argument(
        "--local-pipeline",
        action="store_true",
        help="Run local pipeline single-step benchmark",
    )

    parser.add_argument(
        "--local-chain",
        action="store_true",
        help="Run local chain escalation benchmark",
    )

    parser.add_argument(
        "--output-file",
        type=str,
        default="benchmark-results.json",
        help="Output JSON file path (default: benchmark-results.json)",
    )
    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    if not any(
        [
            args.all, args.config, args.selector, args.router, args.cache,
            args.fallback, args.local_router, args.local_pipeline, args.local_chain,
        ]
    ):
        print("Error: Please specify at least one benchmark to run or use --all")
        print("Use --help for more information.")
        return 1

    if args.runs < 1:
        print("Error: --runs must be at least 1")
        return 1

    suite = BenchmarkSuite(iterations=args.runs)

    print(f"Running benchmarks with {args.runs} iterations...")

    if args.all:
        suite.run_all()
    else:
        if args.config:
            print("Running Model Config Loading benchmark...")
            suite.benchmark_config_loading()

        if args.selector:
            print("Running Model Selection benchmark...")
            suite.benchmark_model_selection()

        if args.router:
            print("Running Model Routing benchmark...")
            suite.benchmark_model_routing()

        if args.cache:
            print("Running Prompt Cache benchmark...")
            suite.benchmark_prompt_cache()

        if args.fallback:
            print("Running Fallback Chain benchmark...")
            suite.benchmark_fallback_chain()

        if args.local_router:
            print("Running Local Router Classification benchmark...")
            suite.benchmark_local_router_classification()

        if args.local_pipeline:
            print("Running Local Pipeline Single-Step benchmark...")
            suite.benchmark_local_pipeline_single_step()

        if args.local_chain:
            print("Running Local Chain Escalation benchmark...")
            suite.benchmark_local_chain_escalation()
    if args.output == "json":
        output_data = suite.to_json()
        output_path = Path(args.output_file)
        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\nResults written to {output_path}")
    else:
        print(suite.format_table())

    return 0


if __name__ == "__main__":
    sys.exit(main())
