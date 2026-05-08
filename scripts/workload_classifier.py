#!/usr/bin/env python3
"""
Workload Classifier -- Auto-tunes llama.cpp based on request patterns.

Classifies requests as:
- throughput: High volume, batch processing
- latency: Low latency, single requests
- context: Long context, RAG workloads
- balanced: Mix of workloads

Usage:
    python scripts/workload_classifier.py status    # Show current classification
    python scripts/workload_classifier.py tune      # Apply auto-tune recommendations
    python scripts/workload_classifier.py monitor  # Monitor and classify in real-time
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests

# -- Configuration -----------------------------------------------------

LLAMA_URL = os.getenv("LLAMA_URL", "http://localhost:8080")
SAMPLE_WINDOW_SECONDS = 30
MIN_SAMPLES_FOR_CLASSIFICATION = 5

# Classification thresholds
CONTEXT_LENGTH_THRESHOLD = 2048  # Tokens
THROUGHPUT_THRESHOLD = 10  # Requests per minute
LATENCY_SENSITIVE_THRESHOLD = 0.3  # 30% of requests under 500ms


@dataclass
class RequestMetrics:
    """Metrics for a single request."""

    tokens_generated: int = 0
    prompt_tokens: int = 0
    latency_ms: float = 0.0
    context_length: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class WorkloadProfile:
    """Classified workload profile."""

    workload_type: str = "balanced"  # throughput, latency, context, balanced
    avg_context_length: int = 0
    avg_tokens_per_request: int = 0
    avg_latency_ms: float = 0.0
    requests_per_minute: float = 0.0
    confidence: float = 0.0
    sample_count: int = 0
    recommendation: str = ""
    flags: Dict[str, str] = field(default_factory=dict)


class WorkloadClassifier:
    """Classifies llama.cpp workload patterns."""

    def __init__(self, url: str = LLAMA_URL):
        self.url = url
        self.metrics: List[RequestMetrics] = []

    def get_server_metrics(self) -> Optional[Dict]:
        """Get metrics from llama-server."""
        try:
            resp = requests.get(f"{self.url}/metrics", timeout=5)
            if resp.status_code == 200:
                return self._parse_prometheus(resp.text)
        except Exception:
            pass
        return None

    def _parse_prometheus(self, text: str) -> Dict:
        """Parse Prometheus-style metrics."""
        metrics = {}
        for line in text.split("\n"):
            if line.startswith("#") or not line.strip():
                continue
            match = re.match(r"(\S+)\s+(.+)", line)
            if match:
                metrics[match.group(1)] = match.group(2)
        return metrics

    def get_recent_requests(self) -> List[RequestMetrics]:
        """Analyze recent requests from server logs."""
        # Try to get predictions metrics
        metrics = self.get_server_metrics()
        requests_data = []

        if metrics:
            # Extract available metrics
            prompt_toks = int(metrics.get("llama_batch_prompt_tokens_total", 0))
            eval_toks = int(metrics.get("llama_batch_eval_tokens_total", 0))

            if prompt_toks > 0 or eval_toks > 0:
                requests_data.append(
                    RequestMetrics(
                        tokens_generated=eval_toks,
                        prompt_tokens=prompt_toks,
                        context_length=prompt_toks,
                    )
                )

        return requests_data

    def classify(self) -> WorkloadProfile:
        """Classify the current workload."""
        # Get recent requests
        recent = self.get_recent_requests()

        if not recent:
            return WorkloadProfile(
                workload_type="balanced",
                recommendation="Insufficient data for classification",
                flags={"threads": "8", "flash_attn": "auto"},
            )

        # Calculate aggregates
        total_prompt = sum(r.prompt_tokens for r in recent)
        total_generated = sum(r.tokens_generated for r in recent)
        total_latency = sum(r.latency_ms for r in recent)

        avg_context = total_prompt / len(recent) if recent else 0
        avg_tokens = total_generated / len(recent) if recent else 0
        avg_latency = total_latency / len(recent) if recent and total_latency > 0 else 0

        # Classify based on context length
        if avg_context > CONTEXT_LENGTH_THRESHOLD:
            workload_type = "context"
            recommendation = "Enable flash attention, reduce threads"
            flags = {"flash-attn": "on", "threads": "4", "cb": "on"}
        # Classify based on throughput (approximation)
        elif avg_tokens > THROUGHPUT_THRESHOLD * 100:
            workload_type = "throughput"
            recommendation = "Maximize parallel slots, enable batch processing"
            flags = {"np": "16", "cb": "on", "threads": "8"}
        # Classify based on latency sensitivity
        elif avg_latency > 0 and avg_latency < 500:
            workload_type = "latency"
            recommendation = "Reduce threads, disable batch, enable flash attention"
            flags = {"threads": "4", "flash-attn": "on", "cb": "off"}
        else:
            workload_type = "balanced"
            recommendation = "Current settings optimal"
            flags = {"threads": "8", "flash-attn": "auto", "cb": "on"}

        confidence = min(1.0, len(recent) / MIN_SAMPLES_FOR_CLASSIFICATION)

        return WorkloadProfile(
            workload_type=workload_type,
            avg_context_length=int(avg_context),
            avg_tokens_per_request=int(avg_tokens),
            avg_latency_ms=int(avg_latency),
            requests_per_minute=len(recent) * 2,  # Approximate
            confidence=confidence,
            recommendation=recommendation,
            flags=flags,
            sample_count=len(recent),
        )

    def get_gpu_status(self) -> Optional[Dict]:
        """Get GPU status for workload decisions."""
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=memory.used,memory.total,temperature.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            used_mb, total_mb, temp = result.stdout.strip().split(", ")
            return {
                "used_gb": int(used_mb) / 1000,
                "total_gb": int(total_mb) / 1000,
                "temperature_c": int(temp),
            }
        except Exception:
            return None


def show_status(classifier: WorkloadClassifier):
    """Show current workload classification."""
    profile = classifier.classify()
    gpu = classifier.get_gpu_status()

    print("=" * 60)
    print("WORKLOAD CLASSIFICATION")
    print("=" * 60)
    print(f"Type:          {profile.workload_type.upper()}")
    print(f"Confidence:    {profile.confidence:.0%} ({profile.sample_count} samples)")
    print(f"Avg Context:   {profile.avg_context_length} tokens")
    print(f"Avg Output:    {profile.avg_tokens_per_request} tokens")
    print(f"Avg Latency:   {profile.avg_latency_ms} ms")

    if gpu:
        print(f"\nGPU Status:")
        print(f"  VRAM Used:   {gpu['used_gb']:.1f} GB / {gpu['total_gb']:.1f} GB")
        print(f"  Temperature: {gpu['temperature_c']}°C")

    print(f"\nRecommendation: {profile.recommendation}")
    print(f"\nSuggested Flags:")
    for k, v in profile.flags.items():
        print(f"  {k}: {v}")
    print("=" * 60)


def monitor_mode(classifier: WorkloadClassifier, interval: int = 10):
    """Monitor and classify in real-time."""
    print(f"Monitoring workload every {interval}s (Ctrl+C to stop)...")
    print("-" * 60)

    try:
        while True:
            profile = classifier.classify()
            gpu = classifier.get_gpu_status()

            timestamp = datetime.now().strftime("%H:%M:%S")
            vram = f"{gpu['used_gb']:.1f}GB" if gpu else "N/A"

            print(
                f"[{timestamp}] {profile.workload_type:10} | "
                f"ctx: {profile.avg_context_length:5} | "
                f"VRAM: {vram}"
            )

            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped monitoring.")


def apply_tuning(classifier: WorkloadClassifier):
    """Apply auto-tuning recommendations (placeholder for integration)."""
    profile = classifier.classify()

    print("Auto-tuning recommendations:")
    print(f"  Workload type: {profile.workload_type}")
    print(f"  Recommended flags: {profile.flags}")
    print("\nTo apply, update gguf_manager.sh or restart with new flags.")
    print("This is a read-only recommendation system.")


def main():
    parser = argparse.ArgumentParser(description="Workload Classifier for llama.cpp")
    parser.add_argument(
        "command", choices=["status", "tune", "monitor"], help="Command to run"
    )
    parser.add_argument("--url", default=LLAMA_URL, help="llama-server URL")
    parser.add_argument(
        "--interval", type=int, default=10, help="Monitoring interval in seconds"
    )

    args = parser.parse_args()
    classifier = WorkloadClassifier(args.url)

    if args.command == "status":
        show_status(classifier)
    elif args.command == "tune":
        apply_tuning(classifier)
    elif args.command == "monitor":
        monitor_mode(classifier, args.interval)


if __name__ == "__main__":
    main()
