#!/usr/bin/env python3
"""Benchmarks for agent handoff primitives (Phase 2.1).

Benchmarks verify:
- Handoff operation performance (1000 iterations)
- Guardrails validation performance
- Context serialization performance
"""

import sys
import os
import time
import json
import statistics
from typing import List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

# Add packages to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import handoff module directly to avoid packages.infrastructure dependency
import datetime


# Define the classes directly (mirroring handoff.py for isolated testing)
class HandoffStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class HandoffRequest:
    source_agent: str
    target_agent: str
    context: Dict[str, Any]
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.utcnow)

    def validate(self) -> List[str]:
        errors = []
        if not self.source_agent:
            errors.append("source_agent is required")
        if not self.target_agent:
            errors.append("target_agent is required")
        if self.source_agent == self.target_agent:
            errors.append("source_agent and target_agent must be different")
        if not self.context:
            errors.append("context cannot be empty")
        if not self.reason:
            errors.append("reason is required")
        return errors


@dataclass
class HandoffResponse:
    success: bool
    status: HandoffStatus
    transferred_context: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None
    guardrails_passed: bool = True
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.utcnow)

    @classmethod
    def approved(cls, transferred_context: Dict[str, Any], result: Any = None):
        return cls(
            success=True,
            status=HandoffStatus.COMPLETED,
            transferred_context=transferred_context,
            result=result,
            guardrails_passed=True,
        )

    @classmethod
    def blocked(cls, reason: str, transferred_context: Dict[str, Any] = None):
        return cls(
            success=False,
            status=HandoffStatus.BLOCKED,
            transferred_context=transferred_context or {},
            error=reason,
            guardrails_passed=False,
        )

    @classmethod
    def failed(cls, error: str, transferred_context: Dict[str, Any] = None):
        return cls(
            success=False,
            status=HandoffStatus.FAILED,
            transferred_context=transferred_context or {},
            error=error,
            guardrails_passed=True,
        )


class Guardrails:
    def __init__(self):
        self._rules: Dict[str, Callable[[HandoffRequest], bool]] = {}
        self._rule_descriptions: Dict[str, str] = {}
        self._enabled: Dict[str, bool] = {}
        self._register_default_rules()

    def _register_default_rules(self):
        self.add_rule(
            "different_agents",
            lambda r: r.source_agent != r.target_agent,
            "Source and target agents must be different",
        )
        self.add_rule(
            "non_empty_context", lambda r: bool(r.context), "Context cannot be empty"
        )
        self.add_rule(
            "has_reason", lambda r: bool(r.reason), "Handoff reason is required"
        )

    def add_rule(
        self, name: str, check: Callable[[HandoffRequest], bool], description: str = ""
    ):
        self._rules[name] = check
        self._rule_descriptions[name] = description
        self._enabled[name] = True

    def remove_rule(self, name: str) -> bool:
        if name in self._rules:
            del self._rules[name]
            del self._rule_descriptions[name]
            if name in self._enabled:
                del self._enabled[name]
            return True
        return False

    def enable_rule(self, name: str) -> bool:
        if name in self._enabled:
            self._enabled[name] = True
            return True
        return False

    def disable_rule(self, name: str) -> bool:
        if name in self._enabled:
            self._enabled[name] = False
            return True
        return False

    def check_handoff(self, request: HandoffRequest) -> tuple[bool, List[str]]:
        errors = []
        for name, check in self._rules.items():
            if not self._enabled.get(name, True):
                continue
            try:
                if not check(request):
                    desc = self._rule_descriptions.get(name, f"Rule {name} failed")
                    errors.append(desc)
            except Exception as e:
                errors.append(f"Rule '{name}' evaluation error: {e}")
        passed = len(errors) == 0
        return passed, errors

    def get_rules(self) -> Dict[str, Dict[str, Any]]:
        return {
            name: {
                "enabled": self._enabled.get(name, True),
                "description": self._rule_descriptions.get(name, ""),
            }
            for name in self._rules
        }


class HandoffManager:
    def __init__(
        self,
        guardrails: Optional[Guardrails] = None,
        known_agents: Optional[set] = None,
    ):
        self.guardrails = guardrails or Guardrails()
        self.known_agents = known_agents or {
            "sisyphus",
            "hephaestus",
            "oracle",
            "explore",
            "librarian",
            "momus",
            "metis",
            "prometheus",
            "atlas",
            "sisyphus-junior",
            "multimodal-looker",
        }
        self._handoff_history: List[HandoffResponse] = []

    def execute_handoff(self, request: HandoffRequest) -> HandoffResponse:
        validation_errors = request.validate()
        if validation_errors:
            error_msg = "; ".join(validation_errors)
            return HandoffResponse.failed(error_msg)

        guardrails_passed, guardrail_errors = self.guardrails.check_handoff(request)
        if not guardrails_passed:
            error_msg = "; ".join(guardrail_errors)
            return HandoffResponse.blocked(error_msg, request.context)

        transferred_context = self._prepare_context(request)
        response = HandoffResponse.approved(transferred_context)
        self._handoff_history.append(response)
        return response

    def _prepare_context(self, request: HandoffRequest) -> Dict[str, Any]:
        transferred = {
            "session_state": request.context.get("session_state", {}),
            "conversation_history": request.context.get("conversation_history", []),
            "tool_access": request.context.get("tool_access", []),
            "agent_state": request.context.get("agent_state", {}),
            "metadata": {
                "source_agent": request.source_agent,
                "target_agent": request.target_agent,
                "handoff_reason": request.reason,
                "timestamp": request.timestamp.isoformat(),
            },
        }
        additional = request.context.get("additional", {})
        if additional:
            transferred["additional"] = additional
        return transferred

    def get_history(self) -> List[HandoffResponse]:
        return self._handoff_history.copy()

    def clear_history(self) -> None:
        self._handoff_history.clear()


def create_handoff(
    source: str, target: str, context: Dict[str, Any], reason: str
) -> HandoffResponse:
    request = HandoffRequest(
        source_agent=source, target_agent=target, context=context, reason=reason
    )
    manager = HandoffManager()
    return manager.execute_handoff(request)


def benchmark_handoff_operation(iterations: int = 1000) -> Dict[str, Any]:
    """Benchmark complete handoff operation.

    Args:
        iterations: Number of handoff operations to run

    Returns:
        Dict with benchmark results
    """
    print(f"\n{'=' * 60}")
    print(f"Benchmark: Handoff Operation ({iterations} iterations)")
    print(f"{'=' * 60}")

    manager = HandoffManager()

    # Sample context for handoff
    context = {
        "session_state": {"session_id": "bench_session", "user_id": "user123"},
        "conversation_history": [
            {"role": "user", "content": f"Message {i}"} for i in range(10)
        ],
        "tool_access": ["read", "write", "edit", "grep", "glob"],
        "agent_state": {"current_step": 5, "tokens_used": 1000},
        "additional": {"metadata": "additional data"},
    }

    times: List[float] = []

    for i in range(iterations):
        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="hephaestus",
            context=context,
            reason=f"Benchmark iteration {i}",
        )

        start = time.perf_counter()
        response = manager.execute_handoff(request)
        end = time.perf_counter()

        times.append(end - start)

        # Verify success
        assert response.success is True, f"Handoff failed at iteration {i}"

    # Calculate statistics
    avg_time = statistics.mean(times)
    min_time = min(times)
    max_time = max(times)
    median_time = statistics.median(times)
    std_dev = statistics.stdev(times) if len(times) > 1 else 0

    # Operations per second
    ops_per_sec = iterations / sum(times)

    results = {
        "iterations": iterations,
        "avg_time_ms": avg_time * 1000,
        "min_time_ms": min_time * 1000,
        "max_time_ms": max_time * 1000,
        "median_time_ms": median_time * 1000,
        "std_dev_ms": std_dev * 1000,
        "ops_per_second": ops_per_sec,
        "total_time_sec": sum(times),
    }

    print(f"Results:")
    print(f"  Iterations:      {iterations}")
    print(f"  Avg time:       {results['avg_time_ms']:.4f} ms")
    print(f"  Min time:       {results['min_time_ms']:.4f} ms")
    print(f"  Max time:       {results['max_time_ms']:.4f} ms")
    print(f"  Median time:    {results['median_time_ms']:.4f} ms")
    print(f"  Std dev:        {results['std_dev_ms']:.4f} ms")
    print(f"  Ops/second:     {results['ops_per_second']:.2f}")
    print(f"  Total time:     {results['total_time_sec']:.4f} sec")

    return results


def benchmark_guardrails_validation(iterations: int = 1000) -> Dict[str, Any]:
    """Benchmark guardrails validation performance.

    Args:
        iterations: Number of validation checks to run

    Returns:
        Dict with benchmark results
    """
    print(f"\n{'=' * 60}")
    print(f"Benchmark: Guardrails Validation ({iterations} iterations)")
    print(f"{'=' * 60}")

    guardrails = Guardrails()

    # Add custom rules for more realistic benchmark
    guardrails.add_rule(
        "custom_rule_1",
        lambda r: r.target_agent not in ["blocked"],
        "Custom rule 1",
    )
    guardrails.add_rule(
        "custom_rule_2",
        lambda r: len(r.context) > 0,
        "Custom rule 2",
    )
    guardrails.add_rule(
        "custom_rule_3",
        lambda r: "task" in r.context,
        "Custom rule 3",
    )

    request = HandoffRequest(
        source_agent="sisyphus",
        target_agent="hephaestus",
        context={"task": "benchmark test", "data": "value"},
        reason="Benchmark validation",
    )

    times: List[float] = []

    for i in range(iterations):
        start = time.perf_counter()
        passed, errors = guardrails.check_handoff(request)
        end = time.perf_counter()

        times.append(end - start)

        # Verify correctness
        assert passed is True, f"Validation failed at iteration {i}: {errors}"

    # Calculate statistics
    avg_time = statistics.mean(times)
    min_time = min(times)
    max_time = max(times)
    median_time = statistics.median(times)
    std_dev = statistics.stdev(times) if len(times) > 1 else 0

    ops_per_sec = iterations / sum(times)

    results = {
        "iterations": iterations,
        "rules_count": len(guardrails.get_rules()),
        "avg_time_ms": avg_time * 1000,
        "min_time_ms": min_time * 1000,
        "max_time_ms": max_time * 1000,
        "median_time_ms": median_time * 1000,
        "std_dev_ms": std_dev * 1000,
        "ops_per_second": ops_per_sec,
        "total_time_sec": sum(times),
    }

    print(f"Results:")
    print(f"  Iterations:      {iterations}")
    print(f"  Rules count:    {results['rules_count']}")
    print(f"  Avg time:       {results['avg_time_ms']:.4f} ms")
    print(f"  Min time:       {results['min_time_ms']:.4f} ms")
    print(f"  Max time:       {results['max_time_ms']:.4f} ms")
    print(f"  Median time:    {results['median_time_ms']:.4f} ms")
    print(f"  Std dev:        {results['std_dev_ms']:.4f} ms")
    print(f"  Ops/second:     {results['ops_per_second']:.2f}")
    print(f"  Total time:     {results['total_time_sec']:.4f} sec")

    return results


def benchmark_context_serialization(iterations: int = 1000) -> Dict[str, Any]:
    """Benchmark context serialization performance.

    Args:
        iterations: Number of serializations to run

    Returns:
        Dict with benchmark results
    """
    print(f"\n{'=' * 60}")
    print(f"Benchmark: Context Serialization ({iterations} iterations)")
    print(f"{'=' * 60}")

    # Large context for serialization test
    context = {
        "session_state": {
            "session_id": "bench_session_" * 10,
            "user_id": "user123",
            "metadata": {f"key_{i}": f"value_{i}" for i in range(100)},
        },
        "conversation_history": [
            {
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"This is message number {i} with some content to make it realistic"
                * 10,
            }
            for i in range(100)
        ],
        "tool_access": ["read", "write", "edit", "grep", "glob", "lsp", "bash"] * 10,
        "agent_state": {
            "current_step": 5,
            "tokens_used": 10000,
            "memory_used": 500,
        },
        "additional": {f"key_{i}": f"value_{i}" for i in range(50)},
    }

    request = HandoffRequest(
        source_agent="sisyphus",
        target_agent="hephaestus",
        context=context,
        reason="Benchmark context serialization",
    )

    manager = HandoffManager()

    times: List[float] = []
    json_sizes: List[int] = []

    for i in range(iterations):
        # Measure context preparation
        start = time.perf_counter()
        transferred = manager._prepare_context(request)

        # Measure JSON serialization
        json_str = json.dumps(transferred)
        json_sizes.append(len(json_str))

        end = time.perf_counter()
        times.append(end - start)

    # Calculate statistics
    avg_time = statistics.mean(times)
    min_time = min(times)
    max_time = max(times)
    median_time = statistics.median(times)
    std_dev = statistics.stdev(times) if len(times) > 1 else 0

    avg_json_size = statistics.mean(json_sizes)

    results = {
        "iterations": iterations,
        "avg_time_ms": avg_time * 1000,
        "min_time_ms": min_time * 1000,
        "max_time_ms": max_time * 1000,
        "median_time_ms": median_time * 1000,
        "std_dev_ms": std_dev * 1000,
        "avg_json_size_bytes": avg_json_size,
        "total_time_sec": sum(times),
    }

    print(f"Results:")
    print(f"  Iterations:      {iterations}")
    print(f"  Avg time:       {results['avg_time_ms']:.4f} ms")
    print(f"  Min time:       {results['min_time_ms']:.4f} ms")
    print(f"  Max time:       {results['max_time_ms']:.4f} ms")
    print(f"  Median time:    {results['median_time_ms']:.4f} ms")
    print(f"  Std dev:        {results['std_dev_ms']:.4f} ms")
    print(f"  Avg JSON size:  {results['avg_json_size_bytes']:,} bytes")
    print(f"  Total time:     {results['total_time_sec']:.4f} sec")

    return results


def benchmark_guardrails_with_many_rules(iterations: int = 1000) -> Dict[str, Any]:
    """Benchmark guardrails with many rules.

    Args:
        iterations: Number of validation checks to run

    Returns:
        Dict with benchmark results
    """
    print(f"\n{'=' * 60}")
    print(f"Benchmark: Guardrails with Many Rules ({iterations} iterations)")
    print(f"{'=' * 60}")

    guardrails = Guardrails()

    # Add 20 custom rules
    for i in range(20):
        guardrails.add_rule(
            f"rule_{i}",
            lambda r, idx=i: idx < 10 or r.target_agent != "test",
            f"Custom rule {i}",
        )

    request = HandoffRequest(
        source_agent="sisyphus",
        target_agent="hephaestus",
        context={"task": "benchmark", "data": "value"},
        reason="Benchmark many rules",
    )

    times: List[float] = []

    for i in range(iterations):
        start = time.perf_counter()
        passed, errors = guardrails.check_handoff(request)
        end = time.perf_counter()

        times.append(end - start)

    # Calculate statistics
    avg_time = statistics.mean(times)
    min_time = min(times)
    max_time = max(times)
    median_time = statistics.median(times)
    std_dev = statistics.stdev(times) if len(times) > 1 else 0

    rules_count = len(guardrails.get_rules())

    results = {
        "iterations": iterations,
        "rules_count": rules_count,
        "avg_time_ms": avg_time * 1000,
        "min_time_ms": min_time * 1000,
        "max_time_ms": max_time * 1000,
        "median_time_ms": median_time * 1000,
        "std_dev_ms": std_dev * 1000,
        "total_time_sec": sum(times),
    }

    print(f"Results:")
    print(f"  Iterations:      {iterations}")
    print(f"  Rules count:    {results['rules_count']}")
    print(f"  Avg time:       {results['avg_time_ms']:.4f} ms")
    print(f"  Min time:       {results['min_time_ms']:.4f} ms")
    print(f"  Max time:       {results['max_time_ms']:.4f} ms")
    print(f"  Median time:    {results['median_time_ms']:.4f} ms")
    print(f"  Std dev:        {results['std_dev_ms']:.4f} ms")
    print(f"  Total time:     {results['total_time_sec']:.4f} sec")

    return results


def benchmark_blocking_vs_passing(iterations: int = 1000) -> Dict[str, Any]:
    """Benchmark comparison of blocking vs passing handoffs.

    Args:
        iterations: Number of iterations to run

    Returns:
        Dict with benchmark results
    """
    print(f"\n{'=' * 60}")
    print(f"Benchmark: Blocking vs Passing ({iterations} iterations each)")
    print(f"{'=' * 60}")

    # Test 1: Passing handoffs
    guardrails_passing = Guardrails()
    manager_passing = HandoffManager(guardrails=guardrails_passing)

    request_passing = HandoffRequest(
        source_agent="sisyphus",
        target_agent="hephaestus",
        context={"task": "test"},
        reason="Test",
    )

    passing_times: List[float] = []
    for i in range(iterations):
        start = time.perf_counter()
        response = manager_passing.execute_handoff(request_passing)
        end = time.perf_counter()

        passing_times.append(end - start)
        assert response.success is True

    # Test 2: Blocking handoffs
    guardrails_blocking = Guardrails()
    guardrails_blocking.add_rule("always_block", lambda r: False, "Always blocks")
    manager_blocking = HandoffManager(guardrails=guardrails_blocking)

    request_blocking = HandoffRequest(
        source_agent="sisyphus",
        target_agent="hephaestus",
        context={"task": "test"},
        reason="Test",
    )

    blocking_times: List[float] = []
    for i in range(iterations):
        start = time.perf_counter()
        response = manager_blocking.execute_handoff(request_blocking)
        end = time.perf_counter()

        blocking_times.append(end - start)
        assert response.success is False

    results = {
        "iterations": iterations,
        "passing": {
            "avg_time_ms": statistics.mean(passing_times) * 1000,
            "total_time_sec": sum(passing_times),
        },
        "blocking": {
            "avg_time_ms": statistics.mean(blocking_times) * 1000,
            "total_time_sec": sum(blocking_times),
        },
        "overhead_ms": (
            statistics.mean(blocking_times) - statistics.mean(passing_times)
        )
        * 1000,
    }

    print(f"Results:")
    print(f"  Passing avg time:  {results['passing']['avg_time_ms']:.4f} ms")
    print(f"  Blocking avg time: {results['blocking']['avg_time_ms']:.4f} ms")
    print(f"  Overhead:          {results['overhead_ms']:.4f} ms")

    return results


def run_all_benchmarks() -> Dict[str, Any]:
    """Run all benchmarks and return combined results."""
    print("\n" + "=" * 60)
    print("HANDOFF BENCHMARKS - PHASE 2.1")
    print("=" * 60)

    all_results = {}

    # Run all benchmarks
    all_results["handoff_operation"] = benchmark_handoff_operation(1000)
    all_results["guardrails_validation"] = benchmark_guardrails_validation(1000)
    all_results["context_serialization"] = benchmark_context_serialization(1000)
    all_results["many_rules"] = benchmark_guardrails_with_many_rules(1000)
    all_results["blocking_vs_passing"] = benchmark_blocking_vs_passing(1000)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(
        f"  Handoff operation:    {all_results['handoff_operation']['ops_per_second']:.2f} ops/sec"
    )
    print(
        f"  Guardrails validation: {all_results['guardrails_validation']['ops_per_second']:.2f} ops/sec"
    )
    print(
        f"  Context serialization: {all_results['context_serialization']['avg_time_ms']:.4f} ms/op"
    )
    print(
        f"  Many rules:            {all_results['many_rules']['avg_time_ms']:.4f} ms/op"
    )
    print(
        f"  Blocking overhead:     {all_results['blocking_vs_passing']['overhead_ms']:.4f} ms"
    )

    return all_results


if __name__ == "__main__":
    results = run_all_benchmarks()
