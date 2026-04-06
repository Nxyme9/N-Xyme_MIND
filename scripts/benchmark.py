#!/usr/bin/env python3
"""N-Xyme_MIND Performance Benchmarks
=====================================
Comprehensive benchmark suite for MCP servers and core systems.

Measures:
1. MCP Server Startup Time - import and initialize each custom MCP
2. MCP Tool Response Time - latency for calling each tool
3. Memory System Query - unified memory search performance
4. VPN Rotator - config listing performance
5. Trigger Engine - action execution performance

Each test runs 5 times with detailed statistics.
"""

import importlib
import json
import os
import random
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List

# Add project paths
PROJECT_ROOT = Path(os.environ.get("NX_MIND_PROJECT_DIR", Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "athena-context-mcp"))
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "nx-mind-mcp"))
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "trigger-guardian-mcp"))

# Benchmark configuration
NUM_ITERATIONS = 5
BENCHMARK_OUTPUT = PROJECT_ROOT / "benchmark_results.json"


class BenchmarkResult:
    """Container for benchmark results."""
    
    def __init__(self, name: str):
        self.name = name
        self.times: List[float] = []
    
    def add_time(self, ms: float):
        self.times.append(ms)
    
    @property
    def mean(self) -> float:
        return statistics.mean(self.times) if self.times else 0.0
    
    @property
    def min(self) -> float:
        return min(self.times) if self.times else 0.0
    
    @property
    def max(self) -> float:
        return max(self.times) if self.times else 0.0
    
    @property
    def stdev(self) -> float:
        return statistics.stdev(self.times) if len(self.times) > 1 else 0.0
    
    @property
    def ops_per_sec(self) -> float:
        return 1000.0 / self.mean if self.mean > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "mean_ms": round(self.mean, 3),
            "min_ms": round(self.min, 3),
            "max_ms": round(self.max, 3),
            "stdev_ms": round(self.stdev, 3),
            "ops_per_sec": round(self.ops_per_sec, 2),
            "iterations": len(self.times),
            "raw_times_ms": [round(t, 3) for t in self.times]
        }


def format_result(result: BenchmarkResult) -> str:
    """Format benchmark result for display."""
    return (
        f"  {result.name}:\n"
        f"    Mean:   {result.mean:8.3f} ms\n"
        f"    Min:    {result.min:8.3f} ms\n"
        f"    Max:    {result.max:8.3f} ms\n"
        f"    StdDev: {result.stdev:8.3f} ms\n"
        f"    Ops/s:  {result.ops_per_sec:8.2f}\n"
    )


def benchmark_mcp_startup() -> List[BenchmarkResult]:
    """Benchmark MCP server startup time (import + initialization)."""
    print("\n[1] MCP Server Startup Time")
    print("-" * 50)
    
    results = []
    
    mcp_packages = [
        ("athena-context-mcp", "athena_context_mcp"),
        ("nx-mind-mcp", "nx_mind_mcp"),
        ("trigger-guardian-mcp", "trigger_guardian_mcp"),
    ]
    
    for pkg_name, module_name in mcp_packages:
        result = BenchmarkResult(f"import_{pkg_name}")
        
        for _ in range(NUM_ITERATIONS):
            # Clear any cached modules
            mods_to_remove = [k for k in sys.modules.keys() if module_name in k]
            for m in mods_to_remove:
                del sys.modules[m]
            
            start = time.perf_counter()
            
            # Import the module
            try:
                importlib.import_module(module_name)
            except Exception as e:
                print(f"  Warning: Failed to import {module_name}: {e}")
                continue
            
            end = time.perf_counter()
            result.add_time((end - start) * 1000)
        
        results.append(result)
        print(format_result(result))
    
    return results


def benchmark_mcp_tools() -> List[BenchmarkResult]:
    """Benchmark MCP tool response time."""
    print("\n[2] MCP Tool Response Time")
    print("-" * 50)
    
    results = []
    
    # Test trigger-guardian-mcp tools (most lightweight)
    from trigger_guardian_mcp import _registry
    
    tool_tests = [
        ("register_trigger", lambda: _registry.register(
            phrase=f"/test-{random.randint(1000, 9999)}",
            description="test",
            handler="callback",
            handler_target="test",
            pattern_type="exact"
        )),
        ("list_triggers", lambda: _registry.list_all()),
        ("check_trigger", lambda: _registry.check(f"/test-{random.randint(1, 100)}")),
        ("get_handlers", lambda: _registry.get_handlers("/start-work")),
    ]
    
    for tool_name, tool_func in tool_tests:
        result = BenchmarkResult(f"tool_{tool_name}")
        
        for _ in range(NUM_ITERATIONS):
            start = time.perf_counter()
            try:
                tool_func()
            except Exception as e:
                print(f"  Warning: {tool_name} failed: {e}")
                continue
            end = time.perf_counter()
            result.add_time((end - start) * 1000)
        
        results.append(result)
        print(format_result(result))
    
    return results


def benchmark_memory_query() -> List[BenchmarkResult]:
    """Benchmark memory system query performance."""
    print("\n[3] Memory System Query")
    print("-" * 50)
    
    results = []
    
    # Test memory bank file reads
    memory_files = [
        "activeContext.md",
        "productContext.md",
        "userContext.md",
        "constraints.md",
    ]
    
    memory_bank_path = PROJECT_ROOT / ".context" / "memory_bank"
    
    for mem_file in memory_files:
        result = BenchmarkResult(f"read_{mem_file.replace('.md', '')}")
        file_path = memory_bank_path / mem_file
        
        if not file_path.exists():
            print(f"  Skipping {mem_file}: not found")
            continue
        
        for _ in range(NUM_ITERATIONS):
            start = time.perf_counter()
            try:
                content = file_path.read_text(encoding="utf-8")
                # Simulate basic parsing
                if content.startswith("---"):
                    _ = content.split("---", 2)
            except Exception as e:
                print(f"  Warning: {mem_file} failed: {e}")
                continue
            end = time.perf_counter()
            result.add_time((end - start) * 1000)
        
        results.append(result)
        print(format_result(result))
    
    # Test JSON file reads
    json_files = [
        ".context/mind-state.json",
    ]
    
    for json_file in json_files:
        result = BenchmarkResult(f"read_json_{json_file.split('/')[-1].replace('.json', '')}")
        file_path = PROJECT_ROOT / json_file
        
        if not file_path.exists():
            print(f"  Skipping {json_file}: not found")
            continue
        
        for _ in range(NUM_ITERATIONS):
            start = time.perf_counter()
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"  Warning: {json_file} failed: {e}")
                continue
            end = time.perf_counter()
            result.add_time((end - start) * 1000)
        
        results.append(result)
        print(format_result(result))
    
    return results


def benchmark_vpn_rotator() -> List[BenchmarkResult]:
    """Benchmark VPN rotator config listing."""
    print("\n[4] VPN Rotator Config Listing")
    print("-" * 50)
    
    results = []
    
    result = BenchmarkResult("list_vpn_configs")
    
    vpn_providers_path = PROJECT_ROOT / "vpn" / "providers"
    
    for _ in range(NUM_ITERATIONS):
        start = time.perf_counter()
        
        configs = []
        try:
            for provider_dir in sorted(vpn_providers_path.iterdir()):
                if not provider_dir.is_dir() or provider_dir.name.startswith("_"):
                    continue
                
                configs_dir = provider_dir / "configs"
                conf_files = list(configs_dir.glob("*.conf")) if configs_dir.exists() else []
                configs.append({
                    "provider": provider_dir.name,
                    "count": len(conf_files)
                })
        except Exception as e:
            print(f"  Warning: VPN listing failed: {e}")
            continue
        
        end = time.perf_counter()
        result.add_time((end - start) * 1000)
    
    results.append(result)
    print(format_result(result))
    
    return results


def benchmark_trigger_engine() -> List[BenchmarkResult]:
    """Benchmark trigger engine action execution."""
    print("\n[5] Trigger Engine Action Execution")
    print("-" * 50)
    
    results = []
    
    # Import trigger engine
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    from trigger_engine import ACTION_REGISTRY, TriggerEngine
    
    # Benchmark each action
    action_tests = [
        ("clean_stale_sessions", lambda ctx: ACTION_REGISTRY["clean_stale_sessions"](ctx)),
        ("clear_db_lock", lambda ctx: ACTION_REGISTRY["clear_db_lock"](ctx)),
        ("force_gc", lambda ctx: ACTION_REGISTRY["force_garbage_collection"](ctx)),
    ]
    
    for action_name, action_func in action_tests:
        result = BenchmarkResult(f"trigger_{action_name}")
        context = {}  # Empty context for benchmark
        
        for _ in range(NUM_ITERATIONS):
            start = time.perf_counter()
            try:
                action_func(context)
            except Exception as e:
                # Some actions may fail due to missing files - that's OK
                pass
            end = time.perf_counter()
            result.add_time((end - start) * 1000)
        
        results.append(result)
        print(format_result(result))
    
    # Benchmark TriggerEngine.evaluate
    engine_result = BenchmarkResult("trigger_engine_evaluate")
    
    for _ in range(NUM_ITERATIONS):
        engine = TriggerEngine()
        
        # Add some test triggers
        for i in range(5):
            engine.add(
                name=f"test_trigger_{i}",
                condition=lambda ctx: True,
                action=lambda ctx: None
            )
        
        start = time.perf_counter()
        try:
            engine.evaluate({})
        except Exception as e:
            pass
        end = time.perf_counter()
        engine_result.add_time((end - start) * 1000)
    
    results.append(engine_result)
    print(format_result(engine_result))
    
    return results


def save_results(all_results: List[BenchmarkResult]):
    """Save benchmark results to JSON file."""
    output = {
        "timestamp": datetime.now().isoformat(),
        "iterations": NUM_ITERATIONS,
        "results": [r.to_dict() for r in all_results]
    }
    
    BENCHMARK_OUTPUT.write_text(
        json.dumps(output, indent=2),
        encoding="utf-8"
    )
    
    print(f"\n{'=' * 60}")
    print(f"Results saved to: {BENCHMARK_OUTPUT}")


def main():
    """Run all benchmarks."""
    print("=" * 60)
    print("N-Xyme_MIND Performance Benchmarks")
    print("=" * 60)
    print(f"Project: {PROJECT_ROOT}")
    print(f"Iterations per test: {NUM_ITERATIONS}")
    print(f"Started: {datetime.now().isoformat()}")
    
    all_results = []
    
    # Run all benchmarks
    all_results.extend(benchmark_mcp_startup())
    all_results.extend(benchmark_mcp_tools())
    all_results.extend(benchmark_memory_query())
    all_results.extend(benchmark_vpn_rotator())
    all_results.extend(benchmark_trigger_engine())
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    # Group by category
    categories = {
        "MCP Startup": [],
        "MCP Tools": [],
        "Memory Query": [],
        "VPN Rotator": [],
        "Trigger Engine": [],
    }
    
    for r in all_results:
        if r.name.startswith("import_"):
            categories["MCP Startup"].append(r)
        elif r.name.startswith("tool_"):
            categories["MCP Tools"].append(r)
        elif r.name.startswith("read_"):
            categories["Memory Query"].append(r)
        elif r.name.startswith("list_vpn"):
            categories["VPN Rotator"].append(r)
        elif r.name.startswith("trigger_"):
            categories["Trigger Engine"].append(r)
    
    for cat_name, cat_results in categories.items():
        if cat_results:
            avg_mean = statistics.mean([r.mean for r in cat_results])
            avg_ops = statistics.mean([r.ops_per_sec for r in cat_results])
            print(f"{cat_name:20s} | Avg: {avg_mean:8.3f} ms | Ops/s: {avg_ops:10.2f}")
    
    # Save results
    save_results(all_results)
    
    print(f"\nCompleted: {datetime.now().isoformat()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
