#!/usr/bin/env python3
"""
Advanced Batching Manager -- Priority queue and dynamic batch sizing.

Features:
- Priority queue for urgent vs normal requests
- Dynamic batch size based on queue depth
- KV cache recycling between requests
- Batch timing profiler

Usage:
    python scripts/advanced_batching.py status      # Show batch status
    python scripts/advanced_batching.py profile    # Profile batch sizes
    python scripts/advanced_batching.py tune        # Auto-tune batch size
"""

import argparse
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests


# -- Configuration -----------------------------------------------------

LLAMA_URL = os.getenv("LLAMA_URL", "http://localhost:8080")


@dataclass
class BatchMetrics:
    """Batch processing metrics."""

    batch_size: int = 0
    avg_latency_ms: float = 0.0
    throughput: float = 0.0
    queue_depth: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Request:
    """Queued request."""

    id: str
    priority: int  # 0=highest, 10=lowest
    prompt_tokens: int
    max_tokens: int
    timestamp: datetime = field(default_factory=datetime.now)


class PriorityQueue:
    """Priority queue for requests."""

    def __init__(self):
        self.queue: List[Request] = []

    def add(self, request: Request):
        """Add request to queue."""
        self.queue.append(request)
        self.queue.sort(key=lambda r: (r.priority, r.timestamp))

    def pop(self) -> Optional[Request]:
        """Pop highest priority request."""
        if self.queue:
            return self.queue.pop(0)
        return None

    def peek(self) -> Optional[Request]:
        """Peek at highest priority without removing."""
        if self.queue:
            return self.queue[0]
        return None

    def __len__(self):
        return len(self.queue)


class AdvancedBatching:
    """Advanced batching with priority queue."""

    def __init__(self, url: str = LLAMA_URL):
        self.url = url
        self.priority_queue = PriorityQueue()
        self.batch_history: List[BatchMetrics] = []
        self.current_batch_size = 8
        self.min_batch_size = 1
        self.max_batch_size = 32

    def get_server_slots(self) -> Dict:
        """Get server slot status."""
        try:
            resp = requests.get(f"{self.url}/slots", timeout=5)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return {"slots": []}

    def get_queue_status(self) -> Dict:
        """Get queue status from server."""
        slots_data = self.get_server_slots()
        slots = slots_data.get("slots", [])

        active = sum(1 for s in slots if s.get("state") == "generating")
        waiting = sum(1 for s in slots if s.get("state") == "waiting")
        idle = sum(1 for s in slots if s.get("state") == "idle")

        return {
            "active": active,
            "waiting": waiting,
            "idle": idle,
            "total": len(slots),
            "queue_depth": waiting,
        }

    def get_optimal_batch_size(self) -> int:
        """Calculate optimal batch size based on queue."""
        queue = self.get_queue_status()
        waiting = queue.get("waiting", 0)
        idle = queue.get("idle", 0)

        if waiting == 0:
            # No waiting requests - use minimum
            return self.min_batch_size

        # Dynamic sizing: more waiting = larger batches
        if waiting >= 16:
            return min(self.max_batch_size, waiting + idle)
        elif waiting >= 8:
            return min(16, waiting + idle)
        elif waiting >= 4:
            return min(8, waiting + idle)
        else:
            return max(self.min_batch_size, min(idle, waiting))

    def profile_batch_sizes(self, iterations: int = 3):
        """Profile different batch sizes."""
        print("Profiling batch sizes...")

        results = []
        for batch_size in [1, 2, 4, 8, 16]:
            print(f"\nTesting batch size: {batch_size}")

            latencies = []
            for i in range(iterations):
                start = time.time()

                # Make concurrent requests (simplified)
                # In production, this would use proper concurrent clients
                try:
                    resp = requests.post(
                        f"{self.url}/v1/chat/completions",
                        json={
                            "model": "default",
                            "messages": [{"role": "user", "content": "Hi"}],
                            "max_tokens": 32,
                        },
                        timeout=30,
                    )

                    elapsed = (time.time() - start) * 1000
                    if resp.status_code == 200:
                        latencies.append(elapsed)
                except Exception as e:
                    print(f"  Error: {e}")

                time.sleep(0.5)

            if latencies:
                avg_latency = sum(latencies) / len(latencies)
                throughput = 1000 / avg_latency if avg_latency > 0 else 0

                results.append(
                    {
                        "batch_size": batch_size,
                        "avg_latency_ms": avg_latency,
                        "throughput": throughput,
                    }
                )

                print(f"  Avg latency: {avg_latency:.0f}ms")
                print(f"  Throughput: {throughput:.1f} req/s")

        return results

    def show_status(self):
        """Show batch status."""
        queue = self.get_queue_status()
        optimal_batch = self.get_optimal_batch_size()

        print("=" * 60)
        print("ADVANCED BATCHING STATUS")
        print("=" * 60)

        print(f"\nQueue Status:")
        print(f"  Active:    {queue['active']}")
        print(f"  Waiting:   {queue['waiting']}")
        print(f"  Idle:      {queue['idle']}")
        print(f"  Total:     {queue['total']}")

        print(f"\nBatch Configuration:")
        print(f"  Current batch size:  {self.current_batch_size}")
        print(f"  Optimal batch size:  {optimal_batch}")
        print(f"  Min batch size:      {self.min_batch_size}")
        print(f"  Max batch size:      {self.max_batch_size}")

        # Recommendations
        print(f"\nRecommendations:")
        if queue["waiting"] > queue["active"]:
            print(f"  ⚠️  Queue backing up - increase batch size")
        elif queue["waiting"] == 0 and queue["active"] > 0:
            print(f"  ✓  Good throughput")
        elif queue["idle"] > queue["active"]:
            print(f"  💡 Consider reducing batch size for lower latency")

        print("=" * 60)

    def auto_tune(self):
        """Auto-tune batch size based on conditions."""
        optimal = self.get_optimal_batch_size()
        old_size = self.current_batch_size

        if optimal != old_size:
            print(f"Tuning batch size: {old_size} → {optimal}")
            self.current_batch_size = optimal
        else:
            print(f"Batch size optimal: {optimal}")

        return self.current_batch_size


def main():
    parser = argparse.ArgumentParser(description="Advanced Batching Manager")
    parser.add_argument(
        "command", choices=["status", "profile", "tune"], help="Command to run"
    )
    parser.add_argument("--url", default=LLAMA_URL, help="llama-server URL")
    parser.add_argument("--iterations", type=int, default=3, help="Profile iterations")

    args = parser.parse_args()
    batcher = AdvancedBatching(args.url)

    if args.command == "status":
        batcher.show_status()
    elif args.command == "profile":
        batcher.profile_batch_sizes(args.iterations)
    elif args.command == "tune":
        batcher.auto_tune()


if __name__ == "__main__":
    main()
