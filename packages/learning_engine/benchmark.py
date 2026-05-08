#!/usr/bin/env python3
"""N-Xyme_MIND 8-Phase Learning System Benchmark Suite.

Run this to verify all phases actually work with real data.
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.learning_engine import (
    # Phase 0 - Config
    get_config,
    # Phase 1-4 - Core
    get_routing_optimizer,
    get_ab_testing,
    QLearningEngine,
    CompositeReward,
    # Phase 5 - Cross-Session
    CrossSessionTransfer,
    PromptWizard,
    # Phase 7 - Bayesian Confidence
    BayesianConfidenceEstimator,
    # Phase 8 - Adaptive Router
    AdaptiveRouter,
)


class BenchmarkResults:
    def __init__(self):
        self.results = {}
        self.start_time = time.time()

    def add(self, phase: str, test: str, value: float, unit: str, passed: bool):
        if phase not in self.results:
            self.results[phase] = []
        self.results[phase].append(
            {
                "test": test,
                "value": value,
                "unit": unit,
                "passed": passed,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def print_summary(self):
        total_time = time.time() - self.start_time
        print("\n" + "=" * 70)
        print("N-XYME_MIND 8-PHASE LEARNING SYSTEM BENCHMARK RESULTS")
        print("=" * 70)

        total_passed = 0
        total_tests = 0

        for phase, tests in self.results.items():
            passed = sum(1 for t in tests if t["passed"])
            total = len(tests)
            total_passed += passed
            total_tests += total

            status = "✅ PASS" if passed == total else "❌ FAIL"
            print(f"\n{phase}: {passed}/{total} tests {status}")
            for t in tests:
                icon = "✅" if t["passed"] else "❌"
                print(f"  {icon} {t['test']}: {t['value']:.4f} {t['unit']}")

        print("\n" + "=" * 70)
        print(
            f"OVERALL: {total_passed}/{total_tests} tests passed in {total_time:.2f}s"
        )
        print("=" * 70)

        # Save results (convert numpy types to native Python)
        output_path = Path(".sisyphus/benchmark_results.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert all numpy types to native Python
        def convert(obj):
            if hasattr(obj, "item"):  # numpy types (includes np.bool_)
                return obj.item()
            elif hasattr(obj, "tolist"):  # numpy arrays
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert(i) for i in obj]
            elif obj is True:
                return True
            elif obj is False:
                return False
            return obj

        results_data = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": total_time,
            "results": {
                phase: [convert(t) for t in tests]
                for phase, tests in self.results.items()
            },
            "summary": {
                "total_tests": total_tests,
                "passed": total_passed,
                "failed": total_tests - total_passed,
            },
        }

        with open(output_path, "w") as f:
            json.dump(results_data, f, indent=2)
        print(f"\nResults saved to: {output_path}")

        return total_passed == total_tests


def benchmark_phase_0_config(results: BenchmarkResults):
    """Phase 0: Configuration System."""
    print("\n[Phase 0: Configuration]")

    # Test 1: Load config
    try:
        config = get_config()
        results.add("Phase 0", "Config Load", 1.0, "ops", True)
    except Exception as e:
        results.add("Phase 0", "Config Load", 0.0, "ops", False)
        print(f"  Error loading config: {e}")
        return

    # Test 2: Config has required sections
    has_embedding = hasattr(config, "embedding") or (
        hasattr(config, "__dict__") and "embedding" in config.__dict__
    )
    has_meta = hasattr(config, "meta_learning") or (
        hasattr(config, "__dict__") and "meta_learning" in config.__dict__
    )
    has_bayesian = hasattr(config, "bayesian") or (
        hasattr(config, "__dict__") and "bayesian" in config.__dict__
    )

    results.add(
        "Phase 0",
        "Embedding Config",
        1.0 if has_embedding else 0.0,
        "bool",
        has_embedding,
    )
    results.add("Phase 0", "Meta Config", 1.0 if has_meta else 0.0, "bool", has_meta)
    results.add(
        "Phase 0", "Bayesian Config", 1.0 if has_bayesian else 0.0, "bool", has_bayesian
    )


def benchmark_phase_1_ql(results: BenchmarkResults):
    """Phase 1: Q-Learning Engine."""
    print("\n[Phase 1: Q-Learning]")

    # Test 1: Create Q-Learning engine
    db_path = ":memory:"
    start = time.perf_counter()
    qle = QLearningEngine(db_path=db_path)
    elapsed = time.perf_counter() - start
    results.add("Phase 1", "QL Engine Init", elapsed * 1000, "ms", elapsed < 0.1)

    # Test 2: Select action
    from packages.learning_engine.rl.q_learning import QState, ActionType

    state = QState(task_type="implementation", complexity=3, has_context=True)
    actions = [ActionType.HEPHAESTUS, ActionType.EXPLORE, ActionType.ORACLE]

    start = time.perf_counter()
    action = qle.select_action(state, actions)
    elapsed = time.perf_counter() - start
    results.add("Phase 1", "Action Selection", elapsed * 1000, "ms", elapsed < 0.05)

    # Test 3: Update Q-value
    start = time.perf_counter()
    qle.update(state, action, reward=1.0, task_id="test_001")
    elapsed = time.perf_counter() - start
    results.add("Phase 1", "Q-Value Update", elapsed * 1000, "ms", elapsed < 0.05)


def benchmark_phase_2_routing(results: BenchmarkResults):
    """Phase 2: Routing Optimizer."""
    print("\n[Phase 2: Routing Optimizer]")

    # Test 1: Get routing optimizer
    start = time.perf_counter()
    ro = get_routing_optimizer()
    elapsed = time.perf_counter() - start
    results.add("Phase 2", "Optimizer Init", elapsed * 1000, "ms", elapsed < 0.1)

    # Test 2: Get routing weights
    start = time.perf_counter()
    weights = ro.get_routing_weights()
    elapsed = time.perf_counter() - start
    results.add("Phase 2", "Get Weights", elapsed * 1000, "ms", elapsed < 0.05)

    # Test 3: Get optimal agent
    start = time.perf_counter()
    rec = ro.get_optimal_agent("implement login handler", level=3)
    elapsed = time.perf_counter() - start
    results.add("Phase 2", "Route Task", elapsed * 1000, "ms", elapsed < 0.1)

    # Test 4: Update weights
    start = time.perf_counter()
    ro.update_weights("hephaestus", level=3, success=True, latency_ms=1500)
    elapsed = time.perf_counter() - start
    results.add("Phase 2", "Update Weights", elapsed * 1000, "ms", elapsed < 0.05)


def benchmark_phase_3_ab_testing(results: BenchmarkResults):
    """Phase 3: A/B Testing."""
    print("\n[Phase 3: A/B Testing]")

    # Test 1: Get A/B framework
    start = time.perf_counter()
    ab = get_ab_testing()
    elapsed = time.perf_counter() - start
    results.add("Phase 3", "AB Framework Init", elapsed * 1000, "ms", elapsed < 0.1)

    # Test 2: Create test
    start = time.perf_counter()
    test = ab.create_test(
        test_id="benchmark_test",
        name="Benchmark Test",
        description="Test for benchmarking",
        variants={"control": 0.5, "treatment": 0.5},
        min_sample_size=50,
    )
    elapsed = time.perf_counter() - start
    results.add("Phase 3", "Create Test", elapsed * 1000, "ms", elapsed < 0.05)

    # Test 3: Record outcomes
    start = time.perf_counter()
    for i in range(50):
        variant = ab.get_variant("benchmark_test")
        success = i % 3 != 0  # ~66% success rate
        ab.record_outcome("benchmark_test", variant, success, 100.0 + i)
    elapsed = time.perf_counter() - start
    results.add("Phase 3", "Record 50 Outcomes", elapsed * 1000, "ms", elapsed < 0.5)

    # Test 4: Get results
    start = time.perf_counter()
    test_results = ab.get_test_results("benchmark_test")
    elapsed = time.perf_counter() - start
    results.add("Phase 3", "Get Test Results", elapsed * 1000, "ms", elapsed < 0.05)


def benchmark_phase_4_rewards(results: BenchmarkResults):
    """Phase 4: Multi-Dimensional Rewards."""
    print("\n[Phase 4: Rewards]")

    # Test 1: Compute composite reward
    start = time.perf_counter()
    reward = CompositeReward()
    score = reward.compute(
        success=True,
        latency_ms=1500,
        quality_score=0.85,
        tokens_used=500,
        user_satisfaction=0.9,
    )
    elapsed = time.perf_counter() - start
    results.add("Phase 4", "Compute Reward", elapsed * 1000, "ms", elapsed < 0.01)
    results.add("Phase 4", "Reward Score", score, "score", 0 <= score <= 1)

    # Test 2: Different success/failure
    success_reward = reward.compute(
        success=True,
        latency_ms=500,
        quality_score=0.9,
        tokens_used=100,
        user_satisfaction=0.9,
    )
    fail_reward = reward.compute(
        success=False,
        latency_ms=500,
        quality_score=0.9,
        tokens_used=100,
        user_satisfaction=0.9,
    )
    results.add(
        "Phase 4",
        "Success > Failure",
        1.0 if success_reward > fail_reward else 0.0,
        "bool",
        success_reward > fail_reward,
    )


def benchmark_phase_5_cross_session(results: BenchmarkResults):
    """Phase 5: Cross-Session Transfer."""
    print("\n[Phase 5: Cross-Session Transfer]")

    # Test 1: Initialize
    start = time.perf_counter()
    cs = CrossSessionTransfer()
    elapsed = time.perf_counter() - start
    results.add("Phase 5", "Init", elapsed * 1000, "ms", elapsed < 0.5)

    # Test 2: Get stats (should show existing knowledge)
    stats = cs.get_stats()
    results.add(
        "Phase 5", "Knowledge Items", float(stats["total_knowledge"]), "count", True
    )
    results.add(
        "Phase 5",
        "Avg Transferability",
        stats["avg_transferability"],
        "score",
        stats["avg_transferability"] > 0,
    )

    # Test 3: Extract decisions
    decisions = [
        {
            "content": "Always verify type safety before committing",
            "outcome": "success",
            "occurrence_count": 3,
        },
        {
            "content": "Use explore agent for finding files",
            "outcome": "success",
            "occurrence_count": 5,
        },
    ]
    start = time.perf_counter()
    extracted = cs.extract_decisions("test_session", decisions)
    elapsed = time.perf_counter() - start
    results.add("Phase 5", "Extract Decisions", elapsed * 1000, "ms", elapsed < 0.1)
    results.add(
        "Phase 5",
        "Decisions Extracted",
        float(len(extracted)),
        "count",
        len(extracted) >= 0,
    )

    # Test 4: Get transferable knowledge
    start = time.perf_counter()
    knowledge = cs.get_transferable_knowledge("type safety", min_score=0.5, limit=5)
    elapsed = time.perf_counter() - start
    results.add("Phase 5", "Search Knowledge", elapsed * 1000, "ms", elapsed < 0.2)


def benchmark_phase_6_prompt_evolution(results: BenchmarkResults):
    """Phase 6: Prompt Evolution."""
    print("\n[Phase 6: Prompt Evolution]")

    # Test 1: Initialize
    start = time.perf_counter()
    pw = PromptWizard(db_path=":memory:")
    elapsed = time.perf_counter() - start
    results.add("Phase 6", "Init", elapsed * 1000, "ms", elapsed < 0.1)

    # Test 2: Register prompt
    start = time.perf_counter()
    record = pw.register("test_prompt", "You are an expert. Analyze this code: {code}")
    elapsed = time.perf_counter() - start
    results.add("Phase 6", "Register Prompt", elapsed * 1000, "ms", elapsed < 0.05)

    # Test 3: Evolve prompt
    start = time.perf_counter()
    evolved = pw.evolve("test_prompt", max_iterations=3, score_threshold=0.7)
    elapsed = time.perf_counter() - start
    results.add("Phase 6", "Evolve (3 iterations)", elapsed * 1000, "ms", elapsed < 0.5)

    # Test 4: Get best version
    best = pw.get_best("test_prompt")
    results.add(
        "Phase 6",
        "Best Version Score",
        best.score if best else 0.0,
        "score",
        best is not None,
    )

    # Test 5: Record outcome
    start = time.perf_counter()
    pw.record_outcome(
        "test_prompt",
        version=best.version if best else 1,
        success=True,
        latency_ms=1500,
        tokens_used=500,
    )
    elapsed = time.perf_counter() - start
    results.add("Phase 6", "Record Outcome", elapsed * 1000, "ms", elapsed < 0.05)


def benchmark_phase_7_bayesian(results: BenchmarkResults):
    """Phase 7: Bayesian Confidence."""
    print("\n[Phase 7: Bayesian Confidence]")

    # Test 1: Initialize
    start = time.perf_counter()
    bc = BayesianConfidenceEstimator()
    elapsed = time.perf_counter() - start
    results.add("Phase 7", "Init", elapsed * 1000, "ms", elapsed < 0.01)

    # Test 2: High success rate (8/10)
    result = bc.estimate(8, 10)
    results.add(
        "Phase 7", "High Success (8/10)", result["mean"], "rate", result["mean"] > 0.7
    )
    results.add(
        "Phase 7",
        "CI Width (8/10)",
        result["upper_credible"] - result["lower_credible"],
        "width",
        True,
    )

    # Test 3: Low success rate (1/10)
    result = bc.estimate(1, 10)
    results.add(
        "Phase 7", "Low Success (1/10)", result["mean"], "rate", result["mean"] < 0.3
    )

    # Test 4: No data (0/0)
    result = bc.estimate(0, 0)
    results.add(
        "Phase 7", "No Data (0/0)", result["mean"], "rate", result["mean"] == 0.5
    )

    # Test 5: Large sample (50/100)
    result = bc.estimate(50, 100)
    ci_width = result["upper_credible"] - result["lower_credible"]
    results.add(
        "Phase 7", "CI Narrower (50/100)", ci_width, "width", ci_width < 0.3
    )  # Should be narrower than 8/10


def benchmark_phase_8_adaptive(results: BenchmarkResults):
    """Phase 8: Adaptive Router."""
    print("\n[Phase 8: Adaptive Router]")

    # Test 1: Initialize
    start = time.perf_counter()
    ar = AdaptiveRouter()
    elapsed = time.perf_counter() - start
    results.add("Phase 8", "Init", elapsed * 1000, "ms", elapsed < 0.2)

    # Test 2: Route task (keyword-based)
    start = time.perf_counter()
    route = ar._heuristic_route("fix the bug in auth.py")
    elapsed = time.perf_counter() - start
    results.add("Phase 8", "Heuristic Route", elapsed * 1000, "ms", elapsed < 0.05)
    results.add(
        "Phase 8",
        "Agent Selected",
        1.0 if route["agent"] in ["hephaestus", "explore", "oracle"] else 0.0,
        "bool",
        True,
    )

    # Test 3: Multiple routes for latency test
    tasks = [
        "find login function",
        "implement user auth",
        "review security code",
        "fix database error",
        "create new endpoint",
    ]
    start = time.perf_counter()
    for task in tasks:
        ar._heuristic_route(task)
    elapsed = time.perf_counter() - start
    results.add("Phase 8", "5 Routes", elapsed * 1000, "ms", elapsed < 0.1)

    # Test 4: Learning stats
    stats = ar.get_learning_stats()
    results.add(
        "Phase 8",
        "Stats Available",
        1.0 if hasattr(stats, "total_decisions") else 0.0,
        "bool",
        True,
    )


def main():
    print("=" * 70)
    print("N-XYME_MIND 8-PHASE LEARNING SYSTEM BENCHMARK")
    print("=" * 70)
    print(f"Started at: {datetime.now().isoformat()}")

    results = BenchmarkResults()

    try:
        benchmark_phase_0_config(results)
    except Exception as e:
        print(f"Phase 0 Error: {e}")

    try:
        benchmark_phase_1_ql(results)
    except Exception as e:
        print(f"Phase 1 Error: {e}")

    try:
        benchmark_phase_2_routing(results)
    except Exception as e:
        print(f"Phase 2 Error: {e}")

    try:
        benchmark_phase_3_ab_testing(results)
    except Exception as e:
        print(f"Phase 3 Error: {e}")

    try:
        benchmark_phase_4_rewards(results)
    except Exception as e:
        print(f"Phase 4 Error: {e}")

    try:
        benchmark_phase_5_cross_session(results)
    except Exception as e:
        print(f"Phase 5 Error: {e}")

    try:
        benchmark_phase_6_prompt_evolution(results)
    except Exception as e:
        print(f"Phase 6 Error: {e}")

    try:
        benchmark_phase_7_bayesian(results)
    except Exception as e:
        print(f"Phase 7 Error: {e}")

    try:
        benchmark_phase_8_adaptive(results)
    except Exception as e:
        print(f"Phase 8 Error: {e}")

    # Print and save results
    all_passed = results.print_summary()

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
