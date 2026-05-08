#!/usr/bin/env python3
"""
Optimization Profiler -- Speculative decoding, temperature, and top-p profiling.

Features:
- Temperature profiling per model
- Top-p (nucleus) sampling analysis
- Speculative decoding setup
- Optimal parameter recommendations

Usage:
    python scripts/optimization_profiler.py profile     # Run temperature profiling
    python scripts/optimization_profiler.py speculative # Setup speculative decoding
    python scripts/optimization_profiler.py recommend  # Get recommendations
"""

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests


# -- Configuration -----------------------------------------------------

LLAMA_URL = os.getenv("LLAMA_URL", "http://localhost:8080")


@dataclass
class GenerationParams:
    """Generation parameters."""

    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0


@dataclass
class ProfileResult:
    """Profile result for a parameter setting."""

    setting: str
    avg_latency_ms: float
    tokens_per_second: float
    unique_tokens: int
    quality_score: float  # Approximation


class OptimizationProfiler:
    """Optimization profiling for llama.cpp."""

    def __init__(self, url: str = LLAMA_URL):
        self.url = url
        self.test_prompt = "Write a short poem about a mountain."
        self.max_tokens = 64

    def generate_with_params(self, params: GenerationParams) -> Optional[Dict]:
        """Generate text with given parameters."""
        try:
            resp = requests.post(
                f"{self.url}/v1/chat/completions",
                json={
                    "model": "default",
                    "messages": [{"role": "user", "content": self.test_prompt}],
                    "max_tokens": self.max_tokens,
                    "temperature": params.temperature,
                    "top_p": params.top_p,
                    "top_k": params.top_k,
                    "repeat_penalty": params.repeat_penalty,
                },
                timeout=30,
            )

            if resp.status_code == 200:
                data = resp.json()
                return {
                    "text": data["choices"][0]["message"]["content"],
                    "usage": data.get("usage", {}),
                    "latency_ms": resp.elapsed.total_seconds() * 1000,
                }
        except Exception as e:
            print(f"Error: {e}")
        return None

    def profile_temperature(self) -> List[ProfileResult]:
        """Profile different temperature values."""
        print("Profiling temperature values...")

        temps = [0.0, 0.3, 0.5, 0.7, 1.0, 1.5]
        results = []

        for temp in temps:
            print(f"\nTesting temperature: {temp}")

            latencies = []
            token_counts = []
            texts = []

            for _ in range(3):
                params = GenerationParams(temperature=temp)
                result = self.generate_with_params(params)

                if result:
                    latencies.append(result["latency_ms"])
                    usage = result.get("usage", {})
                    tokens = usage.get("completion_tokens", 0)
                    token_counts.append(tokens)
                    texts.append(result["text"])

                time.sleep(0.5)

            if latencies:
                avg_latency = sum(latencies) / len(latencies)
                total_tokens = sum(token_counts)
                tps = (total_tokens / sum(latencies)) * 1000 if latencies else 0

                # Simple quality metric: uniqueness ratio
                unique = len(set("".join(texts)))
                total = sum(len(t) for t in texts)
                uniqueness = unique / total if total > 0 else 0

                results.append(
                    ProfileResult(
                        setting=f"temp={temp}",
                        avg_latency_ms=avg_latency,
                        tokens_per_second=tps,
                        unique_tokens=unique,
                        quality_score=uniqueness,
                    )
                )

                print(f"  Latency: {avg_latency:.0f}ms | TPS: {tps:.1f}")

        return results

    def profile_top_p(self) -> List[ProfileResult]:
        """Profile different top_p values."""
        print("Profiling top_p values...")

        top_ps = [0.5, 0.7, 0.8, 0.9, 0.95, 1.0]
        results = []

        for top_p in top_ps:
            print(f"\nTesting top_p: {top_p}")

            latencies = []
            token_counts = []

            for _ in range(3):
                params = GenerationParams(temperature=0.7, top_p=top_p)
                result = self.generate_with_params(params)

                if result:
                    latencies.append(result["latency_ms"])
                    usage = result.get("usage", {})
                    tokens = usage.get("completion_tokens", 0)
                    token_counts.append(tokens)

                time.sleep(0.5)

            if latencies:
                avg_latency = sum(latencies) / len(latencies)
                tps = (sum(token_counts) / sum(latencies)) * 1000 if latencies else 0

                results.append(
                    ProfileResult(
                        setting=f"top_p={top_p}",
                        avg_latency_ms=avg_latency,
                        tokens_per_second=tps,
                        unique_tokens=0,
                        quality_score=0,
                    )
                )

                print(f"  Latency: {avg_latency:.0f}ms | TPS: {tps:.1f}")

        return results

    def get_speculative_config(self) -> Dict:
        """Get speculative decoding configuration."""
        # Check llama-server capabilities
        try:
            resp = requests.get(f"{self.url}/metrics", timeout=5)
            # Look for speculative metrics
            has_speculative = "speculative" in resp.text.lower()

            if has_speculative:
                return {
                    "available": True,
                    "suggested_draft": "llama3.2:1b",  # Small draft model
                    "max_draft": 10,
                    "technique": "n-gram",
                }
        except:
            pass

        return {
            "available": False,
            "message": "Speculative decoding not available in this build",
            "suggestion": "Rebuild llama.cpp with speculative decoding support",
        }

    def show_recommendations(self):
        """Show optimization recommendations."""
        print("=" * 60)
        print("OPTIMIZATION RECOMMENDATIONS")
        print("=" * 60)

        # Get speculative config
        spec = self.get_speculative_config()

        print("\n📝 Speculative Decoding:")
        if spec["available"]:
            print(f"  ✅ Available")
            print(f"  Draft model: {spec.get('suggested_draft')}")
            print(f"  Max drafts: {spec.get('max_draft')}")
        else:
            print(f"  ❌ {spec.get('message')}")

        print("\n📝 Temperature Guide:")
        print(f"  0.0-0.3: Focused/deterministic (code, facts)")
        print(f"  0.5-0.7: Balanced (general use)")
        print(f"  0.8-1.0: Creative (stories, brainstorming)")

        print("\n📝 Top-p Guide:")
        print(f"  0.7-0.8: Focused output")
        print(f"  0.9: Balanced (default)")
        print(f"  0.95+: More diverse output")

        print("\n📝 Recommended Presets:")
        print(f"  Code generation: temperature=0.1, top_p=0.8")
        print(f"  Creative writing: temperature=0.8, top_p=0.95")
        print(f"  Summarization: temperature=0.3, top_p=0.9")
        print(f"  Chat: temperature=0.7, top_p=0.9")

        print("\n" + "=" * 60)

    def profile(self):
        """Run full profiling."""
        print("=" * 60)
        print("RUNNING OPTIMIZATION PROFILES")
        print("=" * 60)

        # Check server
        try:
            requests.get(f"{self.url}/health", timeout=5)
        except:
            print("❌ Server not running")
            return

        # Temperature profile
        print("\n" + "=" * 60)
        temp_results = self.profile_temperature()

        # Top-p profile
        print("\n" + "=" * 60)
        top_p_results = self.profile_top_p()

        # Summary
        print("\n" + "=" * 60)
        print("PROFILE SUMMARY")
        print("=" * 60)

        if temp_results:
            best_temp = min(temp_results, key=lambda r: r.avg_latency_ms)
            print(f"\nBest temperature (speed): {best_temp.setting}")

        if top_p_results:
            best_top_p = min(top_p_results, key=lambda r: r.avg_latency_ms)
            print(f"Best top_p (speed): {best_top_p.setting}")

        print("\nFor detailed recommendations, run:")
        print("  python scripts/optimization_profiler.py recommend")


def main():
    parser = argparse.ArgumentParser(description="Optimization Profiler")
    parser.add_argument(
        "command",
        choices=["profile", "speculative", "recommend"],
        help="Command to run",
    )
    parser.add_argument("--url", default=LLAMA_URL, help="llama-server URL")

    args = parser.parse_args()
    profiler = OptimizationProfiler(args.url)

    if args.command == "profile":
        profiler.profile()
    elif args.command == "speculative":
        spec = profiler.get_speculative_config()
        print(json.dumps(spec, indent=2))
    elif args.command == "recommend":
        profiler.show_recommendations()


if __name__ == "__main__":
    main()
