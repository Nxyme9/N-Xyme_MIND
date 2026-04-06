#!/usr/bin/env python3
"""
Intelligent Router Training Script

Intensive training loop that runs continuously to optimize the intelligent router's
model weights. Generates synthetic training data with realistic distribution and
updates weights after each cycle.

Usage:
    python3 bin/train_router.py                    # Default: 10 cycles, 500 samples each
    python3 bin/train_router.py --cycles 5         # 5 cycles
    python3 bin/train_router.py --samples 1000     # 1000 samples per cycle
    python3 bin/train_router.py --duration 30     # Run for 30 minutes
"""

import sys
import os
import time
import json
import random
import argparse
from typing import Dict, List, Any, Optional

# Add project root to path
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Import from intelligent_router_mcp
from packages.intelligent_router_mcp import (
    Router,
    LearningEngine,
    TrainingSimulator,
    MODEL_CAPABILITIES,
)


# ============================================================================
# CATEGORY-SPECIFIC PROMPT TEMPLATES
# ============================================================================

CATEGORY_PROMPTS = {
    "coding": [
        "implement a function to sort a list of dictionaries",
        "fix the bug in the authentication API endpoint",
        "write unit tests for the user service module",
        "refactor the data processing pipeline for better performance",
        "add error handling to the payment service",
        "create a REST API endpoint for user registration",
        "implement JWT token validation middleware",
        "write a database migration script",
        "debug the memory leak in the background worker",
        "refactor the legacy authentication flow",
        "add caching layer to the product API",
        "implement rate limiting for public endpoints",
        "write a Python script to parse CSV files",
        "create a Docker container for the application",
        "implement file upload handler with validation",
    ],
    "reasoning": [
        "analyze why the system is slow under load",
        "compare these two architectural approaches",
        "evaluate the security implications of the design",
        "explain why we chose this architecture decision",
        "what are the tradeoffs between SQL and NoSQL",
        "analyze the performance bottlenecks in the pipeline",
        "evaluate the pros and cons of microservices",
        "explain the reasoning behind this algorithm choice",
        "compare synchronous vs asynchronous processing",
        "analyze the cost-benefit of caching strategies",
        "evaluate the scalability limitations",
        "explain why we need a message queue here",
        "analyze the failure modes of the system",
        "evaluate the test coverage strategy",
        "explain the rationale for this API design",
    ],
    "creative": [
        "write a short story about AI systems collaborating",
        "compose a poem about software development",
        "generate a creative product description",
        "draft an engaging introduction for a blog post",
        "create a narrative about the future of coding",
        "write a creative explanation of recursion",
        "compose a haiku about debugging",
        "generate an imaginative use case for AI",
        "write a creative analogy for API design",
        "draft a fun explanation of algorithms",
    ],
    "analysis": [
        "review the code for security vulnerabilities",
        "audit the authentication flow for gaps",
        "assess the performance bottlenecks",
        "analyze the data patterns in the logs",
        "evaluate the test coverage quality",
        "review the API for injection vulnerabilities",
        "audit the error handling strategy",
        "analyze the memory usage patterns",
        "evaluate the database query efficiency",
        "review the caching strategy effectiveness",
    ],
    "math": [
        "calculate the time complexity of this algorithm",
        "solve the equation for optimal batch size",
        "derive the formula for cache hit rate",
        "calculate the probability of collision",
        "compute the optimal buffer size",
        "solve for the minimum required capacity",
        "calculate the network latency distribution",
        "derive the throughput formula",
    ],
    "summarization": [
        "summarize the key points of this architecture",
        "provide a brief overview of the implementation",
        "condense the main findings into a tl;dr",
        "give an executive summary of the analysis",
        "summarize the bug report in few sentences",
    ],
}

# Category distribution weights
CATEGORY_DISTRIBUTION = {
    "coding": 0.40,  # 40%
    "reasoning": 0.25,  # 25%
    "analysis": 0.15,  # 15%
    "creative": 0.10,  # 10%
    "math": 0.05,  # 5%
    "summarization": 0.05,  # 5%
}


# ============================================================================
# ENHANCED TRAINING SIMULATOR
# ============================================================================


class IntensiveTrainingSimulator:
    """Enhanced simulator with category-specific training and recency bias."""

    def __init__(self, learning: LearningEngine):
        self.learning = learning
        self._pending_outcomes: List[dict] = []
        self._outcomes_with_recency: List[tuple] = []  # (timestamp, outcome)

    def generate_category_samples(
        self,
        num_samples: int,
        category_distribution: Optional[Dict[str, float]] = None,
        recency_bias: bool = True,
    ) -> Dict[str, Any]:
        """Generate synthetic training data with specified category distribution."""
        if category_distribution is None:
            category_distribution = CATEGORY_DISTRIBUTION

        models = list(MODEL_CAPABILITIES.keys())
        results = []
        categories = list(category_distribution.keys())
        weights = list(category_distribution.values())

        for i in range(num_samples):
            # Select category based on distribution
            category = random.choices(categories, weights=weights, k=1)[0]
            prompt = random.choice(
                CATEGORY_PROMPTS.get(category, CATEGORY_PROMPTS["coding"])
            )
            model = random.choice(models)

            # Get model capabilities for this category
            caps = MODEL_CAPABILITIES.get(model, {})

            # Calculate success probability based on capability
            base_success = caps.get(category, 0.7)
            if category == "coding":
                base_success = caps.get("coding", 0.7)
            elif category == "reasoning":
                base_success = caps.get("reasoning", 0.7)
            elif category == "analysis":
                base_success = caps.get("analysis", 0.7)
            elif category == "creative":
                base_success = caps.get("creative", 0.7)

            # Add variance (±15%)
            success_prob = base_success + random.uniform(-0.15, 0.15)
            success = random.random() < success_prob

            # Simulate latency based on model capability
            base_latency = 400 + (1 - caps.get("coding", 0.5)) * 800
            latency = base_latency + random.uniform(-100, 200)

            # Store outcome with timestamp for recency bias
            timestamp = time.time()
            outcome = {
                "prompt_hash": hash(prompt[:50]),
                "categories": category,
                "complexity": random.choice(["simple", "medium", "complex"]),
                "model": model,
                "provider": "opencode",
                "ip": f"127.0.0.1:{random.randint(1080, 1087)}",
                "latency_ms": latency,
                "success": success,
            }

            self._outcomes_with_recency.append((timestamp, outcome))
            results.append(
                {
                    "prompt": prompt,
                    "category": category,
                    "model": model,
                    "success": success,
                    "latency": latency,
                }
            )

        return {
            "samples_generated": num_samples,
            "results": results[-5:],  # Last 5 for display
            "category_counts": self._count_categories(results),
        }

    def _count_categories(self, results: List[dict]) -> Dict[str, int]:
        """Count samples per category."""
        counts = {}
        for r in results:
            cat = r.get("category", "unknown")
            counts[cat] = counts.get(cat, 0) + 1
        return counts

    def flush_to_learning(self, apply_recency_bias: bool = True) -> int:
        """Flush pending outcomes to learning engine with optional recency bias."""
        if apply_recency_bias and self._outcomes_with_recency:
            # Apply recency bias: weight recent outcomes more heavily
            # We'll add duplicate entries for recent outcomes
            now = time.time()
            bias_window = 300  # 5 minutes
            recent_count = 0

            for timestamp, outcome in list(self._outcomes_with_recency):
                age = now - timestamp
                if age < bias_window:
                    # Recent: add with extra weight (re-record)
                    self.learning.record_outcome(
                        prompt_hash=outcome["prompt_hash"],
                        categories=outcome["categories"],
                        complexity=outcome["complexity"],
                        model=outcome["model"],
                        provider=outcome["provider"],
                        ip=outcome["ip"],
                        latency_ms=outcome["latency_ms"],
                        success=outcome["success"],
                    )
                    recent_count += 1

        # Flush all outcomes
        count = len(self._outcomes_with_recency)
        for _, outcome in self._outcomes_with_recency:
            self.learning.record_outcome(
                prompt_hash=outcome["prompt_hash"],
                categories=outcome["categories"],
                complexity=outcome["complexity"],
                model=outcome["model"],
                provider=outcome["provider"],
                ip=outcome["ip"],
                latency_ms=outcome["latency_ms"],
                success=outcome["success"],
            )

        self._outcomes_with_recency.clear()
        return count


# ============================================================================
# TRAINING LOOP
# ============================================================================


class RouterTrainingLoop:
    """Intensive training loop for the intelligent router."""

    def __init__(
        self,
        router: Router,
        samples_per_cycle: int = 500,
        total_cycles: int = 10,
        sleep_between_cycles: float = 2.0,
    ):
        self.router = router
        self.samples_per_cycle = samples_per_cycle
        self.total_cycles = total_cycles
        self.sleep_between_cycles = sleep_between_cycles
        self.simulator = IntensiveTrainingSimulator(router.learning)
        self._weight_history: List[Dict[str, float]] = []

    def run(self, duration_minutes: Optional[int] = None) -> Dict[str, Any]:
        """Run the training loop."""
        start_time = time.time()
        total_samples = 0

        print("=== Intelligent Router Training Loop ===")
        print(
            f"Duration: {'~' + str(duration_minutes) + ' minutes' if duration_minutes else '~1 hour (configurable)'}"
        )
        print(f"Samples per cycle: {self.samples_per_cycle}")
        print(f"Total cycles: {self.total_cycles}")
        print()

        # Determine number of cycles if duration specified
        cycles_to_run = self.total_cycles
        if duration_minutes:
            cycles_to_run = float("inf")  # Run until duration expires

        cycle = 0
        last_weights = {}

        while cycle < cycles_to_run:
            # Check duration limit
            if duration_minutes:
                elapsed = (time.time() - start_time) / 60
                if elapsed >= duration_minutes:
                    break

            cycle += 1

            # Generate training data
            gen_result = self.simulator.generate_category_samples(
                self.samples_per_cycle,
                CATEGORY_DISTRIBUTION,
                recency_bias=True,
            )

            # Flush to learning engine
            flushed = self.simulator.flush_to_learning(apply_recency_bias=True)
            total_samples += gen_result["samples_generated"]

            # Optimize weights
            opt_result = self.router.optimize()
            new_weights = opt_result.get("weights", {})

            # Track weight changes
            self._weight_history.append(new_weights.copy())

            # Calculate success rate from learning stats
            stats = self.router.learning.get_stats()
            success_rate = stats.get("success_rate", 0) * 100

            # Format weights for display
            if new_weights:
                weights_str = ", ".join(
                    [
                        f"{k}={v:.2f}"
                        for k, v in sorted(new_weights.items(), key=lambda x: -x[1])
                    ]
                )
            else:
                weights_str = "initializing..."

            # Print progress
            print(
                f"Cycle {cycle}/{self.total_cycles}: Generated {gen_result['samples_generated']} samples (total: {total_samples})"
            )
            print(f"  Weights: {weights_str}")
            print(f"  Success rate: {success_rate:.1f}%")
            print()

            # Sleep between cycles (simulate real usage)
            if cycle < self.total_cycles and not duration_minutes:
                time.sleep(self.sleep_between_cycles)

        # Final results
        return self._generate_final_report(total_samples, start_time)

    def _generate_final_report(
        self, total_samples: int, start_time: float
    ) -> Dict[str, Any]:
        """Generate final training report."""
        duration = time.time() - start_time

        # Get final weights
        final_weights = self.router._model_weights.copy()
        if not final_weights:
            opt_result = self.router.optimize()
            final_weights = opt_result.get("weights", {})

        # Get model performance
        model_perf = self.router.learning.get_all_model_performance()

        # Calculate weight changes
        weight_changes = {}
        if len(self._weight_history) >= 2:
            first = self._weight_history[0]
            last = self._weight_history[-1]
            for model in set(list(first.keys()) + list(last.keys())):
                first_val = first.get(model, 0)
                last_val = last.get(model, 0)
                weight_changes[model] = round(last_val - first_val, 3)

        # Print final report
        print("=== Training Complete ===")
        print(f"Duration: {duration:.1f} seconds ({duration / 60:.1f} minutes)")
        print(f"Total samples: {total_samples}")
        print()
        print("Final weights:")
        if final_weights:
            for model, weight in sorted(final_weights.items(), key=lambda x: -x[1]):
                change = weight_changes.get(model, 0)
                change_str = f" ({change:+.3f})" if change != 0 else ""
                print(f"  {model}: {weight:.3f}{change_str}")
        else:
            print("  (weights not yet optimized)")
        print()

        print("Model performance:")
        for model, perf in sorted(
            model_perf.items(), key=lambda x: -x[1].get("success_rate", 0)
        ):
            success_rate = perf.get("success_rate", 0) * 100
            avg_latency = perf.get("avg_latency_ms", 0)
            total_req = perf.get("total_requests", 0)
            print(
                f"  {model}: {success_rate:.1f}% success, {avg_latency:.0f}ms avg ({total_req} requests)"
            )

        print()
        print("=== Test Routing Decisions ===")

        # Run test routing decisions
        test_prompts = [
            ("implement a new API endpoint", "coding"),
            ("explain why the system is slow", "reasoning"),
            ("review the code for security", "analysis"),
            ("write a story about AI", "creative"),
            ("calculate the time complexity", "math"),
            ("summarize the main findings", "summarization"),
            ("fix the authentication bug", "coding"),
            ("compare microservices vs monolith", "reasoning"),
            ("audit the database queries", "analysis"),
            ("compose a poem", "creative"),
        ]

        # Repeat for 20 total decisions
        test_prompts = test_prompts * 2  # 10 * 2 = 20

        routing_results = []
        for i, (prompt, expected_cat) in enumerate(test_prompts[:20], 1):
            result = self.router.select_route(prompt, agent_type="test")
            routing_results.append(
                {
                    "prompt": prompt[:40] + "..." if len(prompt) > 40 else prompt,
                    "expected": expected_cat,
                    "selected": result.get("model"),
                    "reason": result.get("selection_reason"),
                }
            )
            print(
                f"  {i:2d}. [{expected_cat:8s}] '{prompt[:30]}...' -> {result.get('model')}"
            )

        # Save weights to JSON
        output_file = os.path.join(
            _project_root, "data", "intelligent_router", "trained_weights.json"
        )
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        save_data = {
            "timestamp": time.time(),
            "training_duration_seconds": duration,
            "total_samples": total_samples,
            "final_weights": final_weights,
            "weight_changes": weight_changes,
            "model_performance": {
                model: {
                    "success_rate": perf.get("success_rate", 0),
                    "avg_latency_ms": perf.get("avg_latency_ms", 0),
                    "total_requests": perf.get("total_requests", 0),
                }
                for model, perf in model_perf.items()
            },
            "test_routing_results": routing_results,
        }

        with open(output_file, "w") as f:
            json.dump(save_data, f, indent=2)

        print()
        print(f"Weights saved to: {output_file}")

        return {
            "duration_seconds": duration,
            "total_samples": total_samples,
            "final_weights": final_weights,
            "weight_changes": weight_changes,
            "model_performance": model_perf,
            "weights_saved_to": output_file,
        }


# ============================================================================
# MAIN
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Intensive training loop for intelligent router"
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=10,
        help="Number of training cycles (default: 10)",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=500,
        help="Samples per cycle (default: 500)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Run for N minutes instead of N cycles",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=2.0,
        help="Seconds between cycles (default: 2.0)",
    )

    args = parser.parse_args()

    print("Initializing router...")
    router = Router()
    print("Router initialized.")
    print()

    # Create and run training loop
    training_loop = RouterTrainingLoop(
        router=router,
        samples_per_cycle=args.samples,
        total_cycles=args.cycles
        if not args.duration
        else 999,  # High number if duration mode
        sleep_between_cycles=args.sleep,
    )

    result = training_loop.run(duration_minutes=args.duration)

    print()
    print("=== Training Summary ===")
    print(f"Samples processed: {result['total_samples']}")
    print(f"Duration: {result['duration_seconds']:.1f}s")
    print(f"Weights saved: {result.get('weights_saved_to', 'N/A')}")


if __name__ == "__main__":
    main()
