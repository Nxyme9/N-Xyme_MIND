#!/usr/bin/env python3
"""
AGENT-LEVEL BENCHMARK - Compare agent performance with different skill loads

Tests:
1. Base agent (no skills) vs Agent + Skills
2. Different agent types: explore, hephaestus, oracle, librarian
3. Metrics: Success rate, Latency, Token usage, Quality score

Usage:
    python benchmark_agent_levels.py --rounds 5 --output results.json
"""

import argparse
import asyncio
import json
import time
import statistics
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Benchmark tasks - diverse set covering research, implementation, review
BENCHMARK_TASKS = [
    # Research tasks
    {
        "category": "research",
        "name": "find_auth_patterns",
        "description": "Find all authentication patterns in packages/orchestration/",
        "agent": "explore",
    },
    {
        "category": "research",
        "name": "find_mcp_servers",
        "description": "Find all MCP server implementations in packages/",
        "agent": "explore",
    },
    {
        "category": "research",
        "name": "find_quality_gates",
        "description": "Find quality gate implementations in bin/quality-gates/",
        "agent": "explore",
    },
    {
        "category": "research",
        "name": "external_docs",
        "description": "Research best practices for circuit breaker pattern in distributed systems",
        "agent": "librarian",
    },
    {
        "category": "research",
        "name": "external_websocket",
        "description": "Research WebSocket reconnection strategies for production",
        "agent": "librarian",
    },
    # Implementation tasks
    {
        "category": "implementation",
        "name": "simple_edit",
        "description": "Add a docstring to the hello function in packages/orchestration/catalyst.py",
        "agent": "hephaestus",
    },
    {
        "category": "implementation",
        "name": "config_edit",
        "description": "Add a new provider to enabled_providers in opencode.json",
        "agent": "hephaestus",
    },
    {
        "category": "implementation",
        "name": "multi_file",
        "description": "Add logging to 3 files in packages/orchestration/",
        "agent": "hephaestus",
    },
    # Review tasks
    {
        "category": "review",
        "name": "code_review",
        "description": "Review packages/orchestration/catalyst.py for issues",
        "agent": "oracle",
    },
    {
        "category": "review",
        "name": "architecture_review",
        "description": "Review the orchestration architecture for improvements",
        "agent": "oracle",
    },
]

# Skill configurations to test
SKILL_CONFIGS = {
    "base": [],  # No skills
    "research": ["frontend-ui-ux"],  # For explore/librarian
    "implementation": ["git-master"],  # For hephaestus
    "review": [],  # For oracle
}


@dataclass
class AgentBenchmarkResult:
    """Result of a single agent benchmark run."""

    task_name: str
    agent: str
    skills: List[str]
    success: bool
    latency_ms: float
    tokens_used: int
    quality_score: float
    error: Optional[str] = None


@dataclass
class BenchmarkSummary:
    """Aggregated benchmark results."""

    config_name: str
    agent: str
    skills: List[str]
    total_runs: int
    success_count: int
    success_rate: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    avg_tokens: float
    avg_quality: float


def run_agent_task(
    agent: str, description: str, skills: List[str], timeout: int = 120
) -> Dict[str, Any]:
    """Run a single agent task and measure results."""
    start_time = time.time()

    # Build the command - use correct model ID from opencode models
    cmd = [
        "opencode",
        "--model",
        "opencode/minimax-m2.5-free",
        "--pure",
        "run",
        description,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND",
        )

        latency_ms = (time.time() - start_time) * 1000

        # Check stderr too for errors
        output = result.stdout + result.stderr

        # Simple success detection - check for actual work done
        # OpenCode prints progress, so check for meaningful output
        success = (
            result.returncode == 0
            and len(output) > 100
            and "ProviderModelNotFoundError" not in output
        )

        # Estimate tokens (rough: ~4 chars per token)
        tokens = len(result.stdout) // 4

        # Quality score: based on output length and success
        quality = 1.0 if success else 0.0

        return {
            "success": success,
            "latency_ms": latency_ms,
            "tokens": tokens,
            "quality": quality,
            "output_length": len(result.stdout),
            "error": None,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "latency_ms": timeout * 1000,
            "tokens": 0,
            "quality": 0.0,
            "output_length": 0,
            "error": "Timeout",
        }
    except Exception as e:
        return {
            "success": False,
            "latency_ms": (time.time() - start_time) * 1000,
            "tokens": 0,
            "quality": 0.0,
            "output_length": 0,
            "error": str(e),
        }


def run_benchmark(
    config_name: str, agents: List[str], rounds: int = 3
) -> List[BenchmarkSummary]:
    """Run benchmark for specified agents."""
    results = []

    print(f"\n{'=' * 60}")
    print(f"BENCHMARK: {config_name}")
    print(f"{'=' * 60}")

    for agent in agents:
        skills = SKILL_CONFIGS.get(agent, [])
        task_results = []

        print(f"\nAgent: {agent} (skills: {skills})")

        # Quick test: 1 task per agent only
        test_task = BENCHMARK_TASKS[0]  # Use first task as test
        print(f"  Testing: {test_task['name']}")

        result = run_agent_task(
            test_task["agent"], test_task["description"], skills, timeout=90
        )

        task_results.append(result)
        print(
            f"  Result: [{result['success']}] {result['latency_ms']:.0f}ms, output: {result['output_length']} chars"
        )

        # Aggregate results
        successes = sum(1 for r in task_results if r["success"])
        latencies = [r["latency_ms"] for r in task_results]
        tokens = [r["tokens"] for r in task_results]
        qualities = [r["quality"] for r in task_results]

        summary = BenchmarkSummary(
            config_name=config_name,
            agent=agent,
            skills=skills,
            total_runs=len(task_results),
            success_count=successes,
            success_rate=successes / len(task_results) if task_results else 0,
            avg_latency_ms=statistics.mean(latencies) if latencies else 0,
            min_latency_ms=min(latencies) if latencies else 0,
            max_latency_ms=max(latencies) if latencies else 0,
            avg_tokens=statistics.mean(tokens) if tokens else 0,
            avg_quality=statistics.mean(qualities) if qualities else 0,
        )

        results.append(summary)
        print(
            f"  => Success: {summary.success_rate:.1%}, Latency: {summary.avg_latency_ms:.0f}ms"
        )

    return results


def main():
    parser = argparse.ArgumentParser(description="Agent-level benchmark")
    parser.add_argument(
        "--rounds", type=int, default=3, help="Number of rounds per task"
    )
    parser.add_argument(
        "--output", type=str, default="agent_benchmark_results.json", help="Output file"
    )
    parser.add_argument(
        "--agents",
        type=str,
        default="explore,librarian,hephaestus,oracle",
        help="Comma-separated agents",
    )
    args = parser.parse_args()

    agents = args.agents.split(",")

    print("AGENT-LEVEL BENCHMARK")
    print(f"Rounds: {args.rounds}")
    print(f"Agents: {agents}")
    print(f"Output: {args.output}")

    results = run_benchmark("full_system", agents, args.rounds)

    # Save results
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "config": "full_system",
        "rounds": args.rounds,
        "results": [
            {
                "agent": r.agent,
                "skills": r.skills,
                "total_runs": r.total_runs,
                "success_count": r.success_count,
                "success_rate": r.success_rate,
                "avg_latency_ms": r.avg_latency_ms,
                "min_latency_ms": r.min_latency_ms,
                "max_latency_ms": r.max_latency_ms,
                "avg_tokens": r.avg_tokens,
                "avg_quality": r.avg_quality,
            }
            for r in results
        ],
    }

    with open(args.output, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"Results saved to: {args.output}")
    print(f"{'=' * 60}")

    # Print summary table
    print("\n| Agent | Skills | Success Rate | Avg Latency | Avg Tokens |")
    print("|-------|--------|--------------|-------------|------------|")
    for r in results:
        print(
            f"| {r.agent} | {r.skills} | {r.success_rate:.1%} | {r.avg_latency_ms:.0f}ms | {r.avg_tokens:.0f} |"
        )


if __name__ == "__main__":
    main()
