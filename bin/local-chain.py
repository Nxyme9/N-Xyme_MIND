#!/usr/bin/env python3
"""Local Chain - Chain orchestrator for local→cloud escalation."""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional

import requests

LOCAL_TIMEOUT_SECONDS = 90
ERROR_KEYWORDS = [
    "error",
    "failed",
    "failure",
    "exception",
    "timeout",
    "unavailable",
    "cannot",
    "unable to",
    "not found",
    "connection refused",
    "internal server error",
    "503",
]


class ChainOrchestrator:
    """Orchestrator that tries local model first, escalates to cloud on failure."""

    def __init__(self, local_router=None, quality_threshold: float = 0.7):
        self.local_router = local_router
        self.quality_threshold = quality_threshold
        self.expected_length = 50

    def _score_quality(self, response: str, expected_length: int = None) -> float:
        """Score response quality using heuristics.

        Args:
            response: The model response to score
            expected_length: Expected minimum length (uses default if not provided)

        Returns:
            Quality score between 0.0 and 1.0
        """
        if expected_length:
            self.expected_length = expected_length

        if not response or not response.strip():
            return 0.0

        response_lower = response.lower()

        has_error = any(keyword in response_lower for keyword in ERROR_KEYWORDS)
        if has_error:
            return 0.2

        length_ratio = len(response.strip()) / self.expected_length
        if length_ratio < 0.5:
            return 0.3
        elif length_ratio < 1.0:
            return 0.6
        elif length_ratio < 2.0:
            return 0.85
        else:
            return 0.95

    def _simulate_local_execution(self, prompt: str) -> tuple[str, bool]:
        """Simulate local model execution.

        In production, this would call the local LLM.
        For now, simulates based on local availability.

        Args:
            prompt: The prompt to send to local model

        Returns:
            Tuple of (response, success)
        """
        if self.local_router and not self.local_router.is_local_available():
            return "", False

        return f"Local response to: {prompt[:50]}...", True

    def _simulate_cloud_escalation(self, prompt: str) -> str:
        """Simulate cloud model escalation.

        In production, this would call a cloud API.
        Currently simulates the escalation behavior.

        Args:
            prompt: The original prompt

        Returns:
            Simulated cloud response
        """
        return f"[CLOUD ESCALATED] Processed: {prompt[:50]}..."

    def execute_with_escalation(
        self,
        prompt: str,
        cloud_fallback: str = None,
        max_retries: int = 2,
    ) -> dict:
        """Execute prompt with local→cloud escalation.

        Args:
            prompt: The prompt to execute
            cloud_fallback: Optional cloud endpoint (not used in simulation)
            max_retries: Maximum number of local retries before escalation

        Returns:
            Dictionary with response, quality score, and escalation reason
        """
        escalation_reason = None
        response = ""
        quality_score = 0.0

        for attempt in range(max_retries + 1):
            try:
                start_time = time.time()

                response, success = self._simulate_local_execution(prompt)
                elapsed = time.time() - start_time

                if not success:
                    escalation_reason = "local_unavailable"
                    break

                if elapsed > LOCAL_TIMEOUT_SECONDS:
                    escalation_reason = "timeout"
                    break

                quality_score = self._score_quality(response)

                if quality_score < self.quality_threshold:
                    if attempt < max_retries:
                        continue
                    escalation_reason = "poor_quality"
                    break

                return {
                    "response": response,
                    "quality_score": quality_score,
                    "escalation_reason": None,
                    "attempts": attempt + 1,
                    "elapsed_seconds": elapsed,
                }

            except Exception as e:
                if attempt >= max_retries:
                    escalation_reason = "max_retries"
                    break
                continue

        if escalation_reason in [
            "local_unavailable",
            "timeout",
            "max_retries",
            "poor_quality",
        ]:
            cloud_response = self._simulate_cloud_escalation(prompt)
            return {
                "response": cloud_response,
                "quality_score": 0.9,
                "escalation_reason": escalation_reason,
                "attempts": max_retries + 1,
                "elapsed_seconds": 0.0,
            }

        return {
            "response": response,
            "quality_score": quality_score,
            "escalation_reason": escalation_reason,
            "attempts": max_retries + 1,
            "elapsed_seconds": 0.0,
        }


def main():
    parser = argparse.ArgumentParser(
        description="Local Chain - Chain orchestrator for local→cloud escalation"
    )
    parser.add_argument(
        "--prompt", type=str, required=True, help="Prompt to execute with escalation"
    )
    parser.add_argument(
        "--threshold", type=float, default=0.7, help="Quality threshold (0.0-1.0)"
    )
    parser.add_argument(
        "--max-retries", type=int, default=2, help="Maximum retries before escalation"
    )
    parser.add_argument(
        "--format", choices=["json", "text"], default="text", help="Output format"
    )

    args = parser.parse_args()

    bin_dir = Path(__file__).parent
    import importlib.util

    router_spec = importlib.util.spec_from_file_location(
        "local_router", bin_dir / "local-router.py"
    )
    router_module = importlib.util.module_from_spec(router_spec)
    router_spec.loader.exec_module(router_module)
    LocalRouter = router_module.LocalRouter

    router = LocalRouter()
    orchestrator = ChainOrchestrator(
        local_router=router,
        quality_threshold=args.threshold,
    )

    result = orchestrator.execute_with_escalation(
        prompt=args.prompt,
        max_retries=args.max_retries,
    )

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        if result["escalation_reason"]:
            print(f"[ESCALATED: {result['escalation_reason']}]")
        print(result["response"])
        print(f"Quality: {result['quality_score']:.2f}, Attempts: {result['attempts']}")

    sys.exit(0)


if __name__ == "__main__":
    main()
