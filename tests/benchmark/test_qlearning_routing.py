#!/usr/bin/env python3
"""Benchmark Q-Learning routing vs old static routing."""

import time
import sys

sys.path.insert(0, ".")

# Benchmark 1: Agent selection (Q-Learning vs static)
print("=" * 60)
print("BENCHMARK: Q-Learning Routing")
print("=" * 60)

# Test different task complexities
tasks = [
    ("fix typo", 1),
    ("implement hello world", 2),
    ("add auth middleware with JWT", 3),
    ("design microservices architecture with monitoring", 5),
    ("implement full ML pipeline with training and inference", 5),
]

print("\n1. Task Complexity Classification")
print("-" * 40)
from packages.nx_routing import _compute_complexity

for task, expected in tasks:
    result = _compute_complexity(task)
    status = (
        "✓" if result.level == expected or abs(result.level - expected) <= 1 else "✗"
    )
    print(f'  {status} "{task[:40]}..." -> L{result.level} (expected L{expected})')

print("\n2. Q-Learning Agent Selection (1000 iterations)")
print("-" * 40)
from packages.nx_routing import _select_agent_qlearning

iterations = 1000
start = time.perf_counter()
for _ in range(iterations):
    for level in range(1, 6):
        agent, q = _select_agent_qlearning(level, "test task")
elapsed = time.perf_counter() - start
print(f"  {iterations * 5} selections in {elapsed:.3f}s")
print(f"  Average: {elapsed / (iterations * 5) * 1000:.2f}ms per selection")

print("\n3. Full Routing Pipeline (100 iterations)")
print("-" * 40)
from packages.nx_routing import route_task

iterations = 100
start = time.perf_counter()
for i in range(iterations):
    result = route_task(f"task {i}")
elapsed = time.perf_counter() - start
print(f"  {iterations} routes in {elapsed:.3f}s")
print(f"  Average: {elapsed / iterations * 1000:.2f}ms per route")

# Show distribution of selected agents
print("\n4. Agent Selection Distribution (500 routes)")
print("-" * 40)
from collections import Counter

agents = []
for _ in range(500):
    result = route_task("random task")
    agents.append(result.agent)

dist = Counter(agents)
for agent, count in sorted(dist.items(), key=lambda x: -x[1]):
    print(f"  {agent:15} {count:3} ({count / 5:.1f}%)")

print("\n5. Strategy Used")
print("-" * 40)
strategies = []
for _ in range(100):
    result = route_task("test")
    strategies.append(result.strategy)

strategy_dist = Counter(strategies)
for strategy, count in strategy_dist.items():
    print(f"  {strategy:15} {count:3} ({count}%)")

print("\n" + "=" * 60)
print("BENCHMARK COMPLETE")
print("=" * 60)

# Compare with old static approach
print("\n6. Comparison: Old static vs Q-Learning")
print("-" * 40)


# Old approach (static weights - no learning)
def old_static_route(task):
    task_lower = task.lower()
    if any(k in task_lower for k in ["fix", "typo", "simple", "quick"]):
        return "sisyphus-junior"
    elif any(k in task_lower for k in ["implement", "create", "add"]):
        return "hephaestus"
    elif any(k in task_lower for k in ["search", "find", "look"]):
        return "explore"
    elif any(k in task_lower for k in ["design", "architecture", "system"]):
        return "oracle"
    return "hephaestus"


iterations = 1000
start = time.perf_counter()
for _ in range(iterations):
    old_static_route("implement feature")
elapsed_old = time.perf_counter() - start

start = time.perf_counter()
for _ in range(iterations):
    route_task("implement feature")
elapsed_new = time.perf_counter() - start

print(f"  Old static:  {elapsed_old * 1000:.2f}ms for {iterations} routes")
print(f"  Q-Learning:  {elapsed_new * 1000:.2f}ms for {iterations} routes")
print(
    f"  Overhead:    {(elapsed_new / elapsed_old - 1) * 100:.1f}% (worth it for learning!)"
)
