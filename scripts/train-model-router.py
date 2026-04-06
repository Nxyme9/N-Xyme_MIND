#!/usr/bin/env python3
"""
Model Router Training Loop — Realistic capability-based training with convergence.

Generates synthetic routing data based on actual model capability matrices,
then optimizes weights to learn which models excel at which task categories.

Usage:
    python3 scripts/train-model-router.py [--duration 3600 --batch 500 --interval 60]
    python3 scripts/train-model-router.py --quick  # 30-second smoke test

The training loop:
1. Generates task prompts per category (coding, reasoning, creative, math, analysis, summarization)
2. Simulates each model's performance based on MODEL_CAPABILITIES with realistic noise
3. Records outcomes to the learning engine SQLite database
4. Optimizes weights every N iterations
5. Tracks convergence: stops when weight changes < threshold for 3 consecutive rounds
"""

import sys
import os
import json
import time
import random
import argparse
import sqlite3
import math
from pathlib import Path
from collections import defaultdict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from packages.intelligent_router_mcp import (
    Router,
    MODEL_CAPABILITIES,
    CATEGORY_KEYWORDS,
    TrainingSimulator,
)

# ============================================================================
# REALISTIC TRAINING DATA
# ============================================================================

# Realistic task prompts per category — used to generate meaningful routing data
TRAINING_PROMPTS = {
    "coding": [
        "implement a binary search tree with insert, delete, and find operations",
        "write a REST API endpoint with authentication and rate limiting",
        "fix the memory leak in the WebSocket connection handler",
        "refactor the monolithic service into microservices with gRPC",
        "add unit tests for the payment processing module",
        "implement JWT token refresh with sliding expiration",
        "write a SQL query to find duplicate records across 3 tables",
        "create a middleware for request validation using Zod schemas",
        "debug the race condition in the concurrent file processor",
        "implement a caching layer with Redis and TTL eviction",
        "write a GraphQL resolver with DataLoader batching",
        "create a Kubernetes deployment config with health checks",
        "implement OAuth2 PKCE flow for a SPA application",
        "write a data pipeline with Apache Airflow DAGs",
        "fix the N+1 query problem in the ORM relationship",
    ],
    "reasoning": [
        "analyze why our API response times increased 300% after deployment",
        "compare microservices vs monolith for a team of 15 developers",
        "evaluate the security implications of storing tokens in localStorage",
        "explain the tradeoffs between eventual and strong consistency",
        "what are the implications of switching from PostgreSQL to MongoDB",
        "analyze the root cause of cascading failures in our service mesh",
        "compare REST vs GraphQL vs gRPC for our use case",
        "evaluate whether we should build or buy our auth system",
        "analyze the cost-benefit of migrating to serverless architecture",
        "what are the risks of deploying on Friday afternoon",
    ],
    "creative": [
        "write a compelling product description for our AI coding assistant",
        "compose a technical blog post about our architecture decisions",
        "draft an RFC for introducing a new design system",
        "create a narrative explaining our company's technical vision",
        "write user-facing documentation for our new API",
        "compose a release notes summary for non-technical stakeholders",
        "draft a post-mortem for the recent outage",
        "write a tutorial on setting up our development environment",
    ],
    "math": [
        "calculate the probability of hash collision for 10M entries",
        "solve the recurrence relation T(n) = 2T(n/2) + n",
        "compute the Big-O complexity of this nested loop algorithm",
        "calculate the optimal batch size given memory constraints",
        "solve the system of equations for load balancer distribution",
        "compute the entropy of our password generation algorithm",
        "calculate the expected latency for a 3-tier caching system",
    ],
    "analysis": [
        "review the authentication flow for security vulnerabilities",
        "audit our dependency tree for known CVEs",
        "assess the performance bottlenecks in our database queries",
        "analyze the code coverage report and identify gaps",
        "evaluate the test suite for flaky tests",
        "review the API design for REST compliance",
        "analyze the memory usage patterns in our application",
        "audit our CI/CD pipeline for security best practices",
    ],
    "summarization": [
        "summarize the key changes in this 200-file pull request",
        "give me the tl;dr of this 50-page technical specification",
        "condense these meeting notes into action items",
        "summarize the error logs from the last 24 hours",
        "provide an overview of our current technical debt",
        "brief me on the status of all open issues",
    ],
}

# Realistic latency baselines per model (ms) — faster models get lower latency
MODEL_LATENCY_BASE = {
    "qwen3.6-plus": 800,
    "qwen3-coder": 600,
    "deepseek-r1": 1200,
    "minimax-m2.5": 400,
    "gemini-2.5-flash": 300,
}

# Local model baselines
LOCAL_MODEL_LATENCY_BASE = {
    "ollama/qwen2.5-coder:7b": 2500,
    "ollama/llama3.2:3b": 1500,
}

# Local model capabilities (lower than cloud)
LOCAL_MODEL_CAPABILITIES = {
    "ollama/qwen2.5-coder:7b": {
        "reasoning": 0.70,
        "coding": 0.82,
        "creative": 0.55,
        "math": 0.65,
        "analysis": 0.68,
        "summarization": 0.60,
        "context_window": 8192,
    },
    "ollama/llama3.2:3b": {
        "reasoning": 0.50,
        "coding": 0.55,
        "creative": 0.45,
        "math": 0.40,
        "analysis": 0.48,
        "summarization": 0.52,
        "context_window": 4096,
    },
}


# ============================================================================
# TRAINING ENGINE
# ============================================================================


class RealisticTrainer:
    """Generates realistic training data based on model capability matrices."""

    def __init__(self, router: Router):
        self.router = router
        self.all_models = {**MODEL_CAPABILITIES, **LOCAL_MODEL_CAPABILITIES}
        self.all_latency = {**MODEL_LATENCY_BASE, **LOCAL_MODEL_LATENCY_BASE}

    def simulate_model_response(self, model: str, category: str, prompt: str) -> dict:
        """
        Simulate a model's response to a task.

        Returns dict with:
        - success: bool (based on capability + noise)
        - quality: float 0-1 (capability score + small noise)
        - latency_ms: float (baseline + category modifier + noise)
        """
        caps = self.all_models.get(model, {})
        capability = caps.get(category, 0.5)

        # Success probability: capability-based with small noise (±5%)
        noise = random.uniform(-0.05, 0.05)
        success_prob = max(0.1, min(0.99, capability + noise))
        success = random.random() < success_prob

        # Quality: capability + tiny noise, clamped 0-1
        quality = max(0.0, min(1.0, capability + random.uniform(-0.03, 0.03)))

        # Latency: baseline + category modifier + noise
        base_latency = self.all_latency.get(model, 500)
        # Complex categories take longer
        category_modifier = {
            "coding": 1.2,
            "reasoning": 1.3,
            "math": 1.1,
            "analysis": 1.15,
            "creative": 0.9,
            "summarization": 0.8,
        }.get(category, 1.0)
        latency = base_latency * category_modifier * random.uniform(0.8, 1.4)

        return {
            "success": success,
            "quality": round(quality, 3),
            "latency_ms": round(latency, 1),
            "capability": capability,
        }

    def generate_batch(self, batch_size: int = 100) -> dict:
        """
        Generate a batch of realistic training samples.

        Each sample:
        1. Picks a random category and prompt
        2. Tests ALL models against that prompt
        3. Records outcomes to the learning engine

        Returns batch statistics.
        """
        categories = list(TRAINING_PROMPTS.keys())
        models = list(self.all_models.keys())

        results = defaultdict(
            lambda: {"success": 0, "total": 0, "quality": 0.0, "latency": 0.0}
        )

        for _ in range(batch_size):
            category = random.choice(categories)
            prompt = random.choice(TRAINING_PROMPTS[category])

            for model in models:
                sim = self.simulate_model_response(model, category, prompt)

                self.router.learning.record_outcome(
                    prompt_hash=hash(prompt[:50]),
                    categories=category,
                    complexity=random.choice(["simple", "medium", "complex"]),
                    model=model,
                    provider="ollama" if model.startswith("ollama") else "opencode",
                    ip="local" if model.startswith("ollama") else "cloud",
                    latency_ms=sim["latency_ms"],
                    success=sim["success"],
                )

                stats = results[model]
                stats["total"] += 1
                if sim["success"]:
                    stats["success"] += 1
                stats["quality"] += sim["quality"]
                stats["latency"] += sim["latency_ms"]

        # Compute averages
        summary = {}
        for model, stats in results.items():
            total = stats["total"]
            summary[model] = {
                "success_rate": round(stats["success"] / total, 3) if total else 0,
                "avg_quality": round(stats["quality"] / total, 3) if total else 0,
                "avg_latency_ms": round(stats["latency"] / total, 1) if total else 0,
                "samples": total,
            }

        return summary

    def optimize_and_report(self, iteration: int) -> dict:
        """Run optimization and return weight changes."""
        old_weights = dict(self.router._model_weights)
        result = self.router.optimize()
        new_weights = self.router._model_weights

        # Compute weight changes
        changes = {}
        for model in new_weights:
            old = old_weights.get(model, 0.5 / max(len(new_weights), 1))
            changes[model] = round(new_weights[model] - old, 4)

        return {
            "iteration": iteration,
            "weights": {k: round(v, 4) for k, v in new_weights.items()},
            "changes": changes,
            "total_outcomes": self.router.learning.get_stats()["total_requests"],
        }

    def check_convergence(
        self, recent_changes: list, threshold: float = 0.005, min_rounds: int = 5
    ) -> bool:
        """
        Check if weights have converged (changes < threshold for min_rounds consecutive rounds).
        """
        if len(recent_changes) < min_rounds:
            return False

        for changes in recent_changes[-min_rounds:]:
            max_change = max(abs(v) for v in changes.values()) if changes else 0
            if max_change > threshold:
                return False

        return True


# ============================================================================
# MAIN TRAINING LOOP
# ============================================================================


def run_training(
    duration_seconds: int = 3600,
    batch_size: int = 500,
    report_interval: int = 60,
    convergence_threshold: float = 0.005,
    convergence_rounds: int = 5,
    quick: bool = False,
):
    """
    Main training loop.

    Args:
        duration_seconds: How long to train (default 1 hour)
        batch_size: Samples per iteration
        report_interval: Seconds between progress reports
        convergence_threshold: Max weight change to consider converged
        convergence_rounds: Consecutive rounds below threshold to stop
        quick: If True, run 30-second smoke test
    """
    if quick:
        duration_seconds = 30
        batch_size = 200
        report_interval = 10

    print("=" * 70)
    print("MODEL ROUTER TRAINING LOOP")
    print("=" * 70)
    print(f"Duration: {duration_seconds}s ({duration_seconds / 60:.1f} min)")
    print(f"Batch size: {batch_size} samples/iteration")
    print(f"Report interval: {report_interval}s")
    print(f"Convergence: <{convergence_threshold} for {convergence_rounds} rounds")
    print()

    # Initialize router (fresh for clean training)
    from packages.intelligent_router_mcp import Router

    router = Router()

    # Clear previous outcomes for clean training
    conn = sqlite3.connect(router.learning.db_path)
    conn.execute("DELETE FROM outcomes")
    conn.execute("DELETE FROM model_performance")
    conn.commit()
    conn.close()
    print(f"Cleared previous training data. DB: {router.learning.db_path}")

    trainer = RealisticTrainer(router)

    start_time = time.time()
    iteration = 0
    total_samples = 0
    recent_changes = []
    converged = False

    print(
        f"\n{'Iter':>5} | {'Samples':>8} | {'Elapsed':>8} | {'Best Model':>20} | {'Best Wt':>7} | {'Status'}"
    )
    print("-" * 80)

    while True:
        elapsed = time.time() - start_time
        if elapsed >= duration_seconds:
            print(f"\n⏱️  Duration reached ({elapsed:.0f}s >= {duration_seconds}s)")
            break

        if converged:
            print(f"\n✅ Converged after {iteration} iterations")
            break

        iteration += 1

        # Generate batch
        batch_stats = trainer.generate_batch(batch_size)
        total_samples += batch_size

        # Optimize weights
        opt_result = trainer.optimize_and_report(iteration)
        recent_changes.append(opt_result["changes"])

        # Find best model
        weights = opt_result["weights"]
        if weights:
            best_model = max(weights, key=weights.get)
            best_weight = weights[best_model]
        else:
            best_model = "N/A"
            best_weight = 0

        # Report
        if (
            iteration % max(1, report_interval // 5) == 0
            or elapsed >= duration_seconds - 5
        ):
            max_change = (
                max(abs(v) for v in opt_result["changes"].values())
                if opt_result["changes"]
                else 0
            )
            status = f"Δ={max_change:.4f}"
            if len(recent_changes) >= convergence_rounds:
                status += f" ({len(recent_changes)} rounds)"

            print(
                f"{iteration:>5} | {total_samples:>8} | {elapsed:>7.0f}s | "
                f"{best_model:>20} | {best_weight:>7.3f} | {status}"
            )

        # Check convergence (only after enough data)
        if iteration >= 10:
            converged = trainer.check_convergence(
                recent_changes, convergence_threshold, convergence_rounds
            )

    # Final report
    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    print(f"Total iterations: {iteration}")
    print(f"Total samples: {total_samples}")
    print(f"Time elapsed: {elapsed:.1f}s")
    print(f"Converged: {'Yes' if converged else 'No (duration limit)'}")

    # Final weights
    print(f"\n{'Model':<30} {'Weight':>8} {'Rank':>5}")
    print("-" * 45)
    sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
    for rank, (model, weight) in enumerate(sorted_weights, 1):
        print(f"{model:<30} {weight:>8.4f} {rank:>5}")

    # Category-specific performance
    print(f"\nCategory-Specific Best Models:")
    print("-" * 45)
    for category in TRAINING_PROMPTS:
        # Query best model for this category
        conn = sqlite3.connect(router.learning.db_path)
        cursor = conn.execute(
            """SELECT selected_model, COUNT(*) as total, SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) as successes
            FROM outcomes WHERE categories=? GROUP BY selected_model ORDER BY successes DESC LIMIT 1""",
            (category,),
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            success_rate = row[2] / row[1] if row[1] else 0
            print(
                f"  {category:<15} → {row[0]:<25} ({success_rate:.1%} success, {row[1]} samples)"
            )

    # Save weights to file
    weights_file = Path(".sisyphus/model_weights.json")
    weights_file.parent.mkdir(parents=True, exist_ok=True)
    with open(weights_file, "w") as f:
        json.dump(
            {
                "weights": weights,
                "category_best": {},
                "trained_at": time.time(),
                "total_samples": total_samples,
                "iterations": iteration,
                "converged": converged,
            },
            f,
            indent=2,
        )

    # Save category-specific best models
    for category in TRAINING_PROMPTS:
        conn = sqlite3.connect(router.learning.db_path)
        cursor = conn.execute(
            """SELECT selected_model, COUNT(*) as total, SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) as successes
            FROM outcomes WHERE categories=? GROUP BY selected_model ORDER BY successes DESC""",
            (category,),
        )
        rows = cursor.fetchall()
        conn.close()
        if rows:
            best = rows[0]
            weights_file.parent.mkdir(parents=True, exist_ok=True)
            # Update the saved file with category data
            with open(weights_file) as f:
                data = json.load(f)
            data["category_best"][category] = {
                "model": best[0],
                "success_rate": best[2] / best[1] if best[1] else 0,
                "samples": best[1],
            }
            with open(weights_file, "w") as f:
                json.dump(data, f, indent=2)

    print(f"\nWeights saved to: {weights_file}")
    print(f"Training database: {router.learning.db_path}")

    return weights


# ============================================================================
# CLI
# ============================================================================


def main():
    parser = argparse.ArgumentParser(description="Train model router weights")
    parser.add_argument(
        "--duration",
        type=int,
        default=3600,
        help="Training duration in seconds (default: 3600 = 1 hour)",
    )
    parser.add_argument(
        "--batch", type=int, default=500, help="Batch size per iteration (default: 500)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Report interval in seconds (default: 60)",
    )
    parser.add_argument(
        "--convergence",
        type=float,
        default=0.005,
        help="Convergence threshold (default: 0.005)",
    )
    parser.add_argument("--quick", action="store_true", help="Run 30-second smoke test")
    args = parser.parse_args()

    run_training(
        duration_seconds=args.duration,
        batch_size=args.batch,
        report_interval=args.interval,
        convergence_threshold=args.convergence,
        quick=args.quick,
    )


if __name__ == "__main__":
    main()
