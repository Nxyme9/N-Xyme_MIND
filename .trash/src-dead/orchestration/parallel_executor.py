#!/usr/bin/env python3
"""Parallel Execution — GPU warp-style parallel agent dispatch"""

import asyncio
from typing import List, Dict, Callable, Any
from dataclasses import dataclass, field


@dataclass
class ParallelResult:
    agent: str
    result: Any
    score: float = 0.0
    error: str = ""


class ParallelExecutor:
    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def execute_parallel(self, tasks: List[Dict], executor_fn: Callable) -> List[ParallelResult]:
        async def run_one(task):
            async with self.semaphore:
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
        valid = [r for r in results if r.result is not None]
        if not valid:
            return results[0] if results else ParallelResult(agent="none", result=None)
        return max(valid, key=lambda r: r.score)

    def _score_result(self, result) -> float:
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


class EnsembleExecutor:
    def __init__(self, agents: List[str], max_concurrent: int = 3):
        self.agents = agents
        self.executor = ParallelExecutor(max_concurrent)

    async def execute(self, task: str, executor_fn: Callable) -> Dict:
        tasks = [{"agent": agent, "task": task} for agent in self.agents]
        results = await self.executor.execute_parallel(tasks, executor_fn)
        best = self.executor.select_best(results)

        return {
            "winner": best.agent,
            "result": best.result,
            "score": best.score,
            "all_results": [
                {"agent": r.agent, "score": r.score, "error": r.error}
                for r in results
            ],
        }
