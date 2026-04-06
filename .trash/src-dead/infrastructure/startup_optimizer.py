"""Startup Optimizer — Optimize system startup"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class StartupOptimizer:
    def __init__(self):
        self._checks: List[dict] = []

    def add_check(self, name: str, check_fn, fix_fn=None):
        self._checks.append({"name": name, "check": check_fn, "fix": fix_fn})

    def run_checks(self, auto_fix: bool = False) -> Dict:
        results = {"passed": [], "failed": [], "fixed": []}
        for check in self._checks:
            try:
                if check["check"]():
                    results["passed"].append(check["name"])
                else:
                    results["failed"].append(check["name"])
                    if auto_fix and check["fix"]:
                        check["fix"]()
                        results["fixed"].append(check["name"])
            except Exception as e:
                results["failed"].append(f"{check['name']}: {e}")
        return results
