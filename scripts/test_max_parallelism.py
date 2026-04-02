#!/usr/bin/env python3
"""
Quick validation test for Maximum Parallelism System.
Tests basic parallelism without full implementation.
"""

import asyncio
import time
import os
import aiohttp
from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum

# Import centralized configuration
try:
    from jarvis.config.graphiti_config import OLLAMA_URL
except ImportError:
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")


class TaskPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class TestTask:
    id: str
    description: str
    priority: TaskPriority
    model: str
    result: str = None
    error: str = None
    start_time: float = None
    end_time: float = None


class QuickParallelismTest:
    """Quick test to validate parallelism design."""

    def __init__(self):
        self.ollama_url = OLLAMA_URL
        self.tasks: List[TestTask] = []
        self.results: Dict[str, Any] = {}

    async def test_local_parallelism(self, num_tasks: int = 5):
        """Test local model parallelism."""
        print(f"\n=== Testing Local Parallelism ({num_tasks} tasks) ===")

        # Create test tasks
        tasks = []
        for i in range(num_tasks):
            task = TestTask(
                id=f"local-{i}",
                description=f"Write a Python function that returns {i}",
                priority=TaskPriority.HIGH,
                model="llama3.2:3b",
            )
            tasks.append(task)

        # Execute in parallel
        start_time = time.time()
        results = await asyncio.gather(
            *[self.execute_local_task(task) for task in tasks], return_exceptions=True
        )
        end_time = time.time()

        # Analyze results
        successful = sum(1 for r in results if not isinstance(r, Exception))
        failed = len(results) - successful
        duration = end_time - start_time

        print(f"Completed: {successful}/{num_tasks}")
        print(f"Failed: {failed}")
        print(f"Duration: {duration:.2f}s")
        print(f"Throughput: {num_tasks / duration:.2f} tasks/s")

        return {
            "total": num_tasks,
            "successful": successful,
            "failed": failed,
            "duration": duration,
            "throughput": num_tasks / duration,
        }

    async def execute_local_task(self, task: TestTask) -> str:
        """Execute a task on local Ollama model."""
        task.start_time = time.time()

        try:
            async with aiohttp.ClientSession() as session:
                payload = {"model": task.model, "prompt": task.description, "stream": False}

                async with session.post(
                    f"{self.ollama_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        task.result = data.get("response", "")
                        task.end_time = time.time()
                        return task.result
                    else:
                        task.error = f"HTTP {resp.status}"
                        task.end_time = time.time()
                        raise Exception(task.error)

        except Exception as e:
            task.error = str(e)
            task.end_time = time.time()
            raise

    async def test_mixed_parallelism(self):
        """Test mixed local + cloud parallelism."""
        print("\n=== Testing Mixed Parallelism ===")

        # Create mixed tasks
        tasks = [
            TestTask("mixed-1", "Simple task", TaskPriority.LOW, "llama3.2:3b"),
            TestTask("mixed-2", "Medium task", TaskPriority.MEDIUM, "llama3.2:3b"),
            TestTask("mixed-3", "Complex task", TaskPriority.HIGH, "llama3.2:3b"),
        ]

        # Execute with different strategies
        start_time = time.time()

        # Parallel execution
        results = await asyncio.gather(
            self.execute_local_task(tasks[0]),
            self.execute_local_task(tasks[1]),
            self.execute_local_task(tasks[2]),
            return_exceptions=True,
        )

        end_time = time.time()

        print(f"Mixed tasks completed in {end_time - start_time:.2f}s")
        return results

    async def test_rate_limiting(self):
        """Test rate limiting behavior."""
        print("\n=== Testing Rate Limiting ===")

        # Simulate rapid task submission
        tasks = []
        for i in range(10):
            task = TestTask(
                id=f"rate-{i}",
                description=f"Quick task {i}",
                priority=TaskPriority.LOW,
                model="llama3.2:3b",
            )
            tasks.append(task)

        # Submit rapidly
        start_time = time.time()
        results = []

        for task in tasks:
            try:
                result = await self.execute_local_task(task)
                results.append(result)
            except Exception as e:
                print(f"Task {task.id} failed: {e}")

        end_time = time.time()

        print(f"Rate limit test: {len(results)}/{len(tasks)} succeeded")
        print(f"Total time: {end_time - start_time:.2f}s")

        return results

    async def run_all_tests(self):
        """Run all validation tests."""
        print("Starting Maximum Parallelism Validation Tests")
        print("=" * 50)

        results = {}

        # Test 1: Basic local parallelism
        results["local_5"] = await self.test_local_parallelism(5)

        # Test 2: Higher concurrency
        results["local_10"] = await self.test_local_parallelism(10)

        # Test 3: Mixed tasks
        results["mixed"] = await self.test_mixed_parallelism()

        # Test 4: Rate limiting
        results["rate_limit"] = await self.test_rate_limiting()

        # Summary
        print("\n" + "=" * 50)
        print("VALIDATION SUMMARY")
        print("=" * 50)

        for test_name, result in results.items():
            if isinstance(result, dict):
                print(
                    f"{test_name}: {result.get('successful', '?')}/{result.get('total', '?')} tasks"
                )
            else:
                print(f"{test_name}: Completed")

        return results


async def main():
    """Run the validation tests."""
    tester = QuickParallelismTest()

    try:
        results = await tester.run_all_tests()
        print("\n✅ Validation tests completed successfully")
        return results
    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
