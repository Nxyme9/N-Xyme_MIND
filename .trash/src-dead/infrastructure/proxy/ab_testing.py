"""A/B Testing Framework — Compare routing strategies."""

import hashlib
import random
import time
import threading
from typing import Dict, List, Optional


class ABTest:
    def __init__(self, name: str, variants: List[str], traffic_split: List[float] = None):
        self.name = name
        self.variants = variants
        self.traffic_split = traffic_split or [1.0 / len(variants)] * len(variants)
        self._results: Dict[str, dict] = {v: {"success": 0, "failure": 0, "total_latency": 0.0} for v in variants}
        self._lock = threading.Lock()

    def assign_variant(self, user_id: str) -> str:
        """Assign a variant based on traffic split."""
        h = int(hashlib.md5(f"{self.name}:{user_id}".encode()).hexdigest(), 16)
        threshold = (h % 10000) / 10000.0
        cumulative = 0.0
        for i, split in enumerate(self.traffic_split):
            cumulative += split
            if threshold < cumulative:
                return self.variants[i]
        return self.variants[-1]

    def record_result(self, variant: str, success: bool, latency_ms: float) -> None:
        with self._lock:
            if variant in self._results:
                self._results[variant]["success" if success else "failure"] += 1
                self._results[variant]["total_latency"] += latency_ms

    def get_results(self) -> dict:
        with self._lock:
            results = {}
            for variant, data in self._results.items():
                total = data["success"] + data["failure"]
                results[variant] = {
                    "total": total,
                    "success_rate": round(data["success"] / total, 3) if total > 0 else 0,
                    "avg_latency_ms": round(data["total_latency"] / total, 1) if total > 0 else 0,
                }
            return results


class ABTestingFramework:
    def __init__(self):
        self._tests: Dict[str, ABTest] = {}
        self._lock = threading.Lock()

    def create_test(self, name: str, variants: List[str], traffic_split: List[float] = None) -> ABTest:
        with self._lock:
            test = ABTest(name, variants, traffic_split)
            self._tests[name] = test
            return test

    def get_test(self, name: str) -> Optional[ABTest]:
        return self._tests.get(name)

    def get_all_results(self) -> dict:
        return {name: test.get_results() for name, test in self._tests.items()}


# Global instance
ab_testing = ABTestingFramework()
