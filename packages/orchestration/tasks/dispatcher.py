"""Task Dispatcher — Merged parallel dispatcher and executor."""

import asyncio
import concurrent.futures
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class DispatchResult:
    """Result from a dispatched task."""
    name: str
    status: str = "pass"
    result: Any = None
    error: str = ""
    duration_ms: float = 0.0


@dataclass
class ParallelResult:
    """Result from parallel execution."""
    agent: str
    result: Any
    score: float = 0.0
    error: str = ""


class Dispatcher:
    """Task dispatcher with parallel execution support."""

    def __init__(self, timeout: int = 30, max_concurrent: int = 3):
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

    def dispatch_parallel(self, checks: List[Dict]) -> List[DispatchResult]:
        """Run multiple checks in parallel. Returns list of results."""
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(checks)) as executor:
            futures = {}
            for check in checks:
                name = check.get("name", "unknown")
                fn = check["fn"]
                args = check.get("args", [])
                futures[executor.submit(self._run, name, fn, args)] = name
            for future in concurrent.futures.as_completed(futures, timeout=self.timeout):
                name = futures[future]
                try:
                    results.append(future.result(timeout=self.timeout))
                except concurrent.futures.TimeoutError:
                    results.append(DispatchResult(name=name, status="timeout", duration_ms=self.timeout * 1000))
                except Exception as e:
                    results.append(DispatchResult(name=name, status="error", error=str(e), duration_ms=0))
        return results

    def _run(self, name: str, fn: Callable, args: List) -> DispatchResult:
        start = time.perf_counter()
        try:
            result = fn(*args)
            duration = round((time.perf_counter() - start) * 1000, 2)
            if isinstance(result, dict):
                result = DispatchResult(
                    name=result.get("name", name),
                    status=result.get("status", "pass"),
                    result=result.get("result"),
                    duration_ms=duration,
                )
            return DispatchResult(name=name, status="pass", result=result, duration_ms=duration)
        except Exception as e:
            return DispatchResult(
                name=name, status="error", error=str(e),
                duration_ms=round((time.perf_counter() - start) * 1000, 2)
            )

    async def execute_parallel(
        self, tasks: List[Dict], executor_fn: Callable
    ) -> List[ParallelResult]:
        """Execute tasks in parallel with async."""
        async def run_one(task: Dict) -> ParallelResult:
            async with self._semaphore:
                try:
                    result = await executor_fn(task)
                    return ParallelResult(
                        agent=task.get("agent", "unknown"),
                        result=result,
                        score=self._score_result(result),
                    )
                except Exception as e:
                    return ParallelResult(
                        agent=task.get("agent", "unknown"),
                        result=None,
                        error=str(e),
                    )

        return await asyncio.gather(*[run_one(t) for t in tasks])

    def select_best(self, results: List[ParallelResult]) -> ParallelResult:
        """Select the best result from a list."""
        valid = [r for r in results if r.result is not None]
        if not valid:
            return results[0] if results else ParallelResult(agent="none", result=None)
        return max(valid, key=lambda r: r.score)

    def _score_result(self, result: Any) -> float:
        """Score a result for selection."""
        if result is None:
            return 0.0
        if isinstance(result, str):
            score = min(len(result) / 500, 2.0)
            if "error" in result.lower():
                score *= 0.5
            return score
        if isinstance(result, dict):
            if result.get("status") == "success":
                return 1.0
            if result.get("status") == "blocked":
                return 0.3
        return 0.5


# Global dispatcher instance
_dispatcher: Optional[Dispatcher] = None


def get_dispatcher(timeout: int = 30, max_concurrent: int = 3) -> Dispatcher:
    """Get or create the global dispatcher."""
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = Dispatcher(timeout, max_concurrent)
    return _dispatcher