"""
NxRotator Dashboard
===================

Real-time dashboard for monitoring NxRotator.

Usage:
    python -m nx_rotator.dashboard
    python -m nx_rotator.dashboard --live  # Live updating
"""

import sys
import time
import argparse
from datetime import datetime

from ..core.aggregator import NxRotator


def format_stats(rotator: NxRotator) -> str:
    """Format stats as a dashboard string."""
    stats = rotator.get_all_stats()
    metrics = stats["metrics"]

    lines = [
        "",
        "=" * 70,
        "🔄 NxRotator - Maximum Throughput Aggregator v1.0",
        "=" * 70,
        "",
        f"📊 AGGREGATED LIMITS:",
        f"   RPM: {stats['aggregated_rpm']} (20 × {stats['total_keys']} keys)",
        f"   TPM: {stats['aggregated_tpm']:,}",
        "",
        f"🔑 KEYS: {stats['active_keys']}/{stats['total_keys']} active",
        "-" * 70,
    ]

    for ks in stats["key_stats"]:
        status = "✅" if ks["available"] else "❌"
        health_icon = (
            "❤️" if ks["health"] > 0.7 else "💔" if ks["health"] < 0.3 else "😐"
        )
        cooldown = (
            f" (cooldown {ks['cooldown_remaining']:.0f}s)"
            if ks["cooldown_remaining"] > 0
            else ""
        )
        lines.append(f"   {status} {health_icon} {ks['key_id']}")
        lines.append(
            f"       {ks['requests']} req | {ks['errors']} err | {ks['tokens']:,} tokens{cooldown}"
        )

    lines.extend(
        [
            "",
            f"📈 METRICS:",
            f"   Total Requests: {metrics['total_requests']:,}",
            f"   Total Tokens: {metrics['total_tokens']:,}",
            f"   Total Errors: {metrics['total_errors']}",
            f"   Error Rate: {metrics['error_rate']:.2f}%",
            f"   Avg Latency: {metrics['avg_latency_ms']:.0f}ms",
            f"   P50 Latency: {metrics['p50_latency_ms']:.0f}ms",
            f"   P95 Latency: {metrics['p95_latency_ms']:.0f}ms",
            f"   P99 Latency: {metrics['p99_latency_ms']:.0f}ms",
            f"   Rotations: {metrics['total_rotations']}",
            f"   Retries: {metrics['total_retries']}",
            f"   Circuit Breaker Trips: {metrics['circuit_breaker_trips']}",
            f"   Uptime: {metrics['uptime_seconds'] / 3600:.1f}h",
        ]
    )

    # Top models
    if metrics["by_model"]:
        lines.extend(
            [
                "",
                "🤖 MODELS:",
            ]
        )
        for model, stats_dict in sorted(
            metrics["by_model"].items(), key=lambda x: -x[1]["requests"]
        )[:5]:
            lines.append(
                f"   {model}: {stats_dict['requests']} req, {stats_dict['tokens']:,} tokens"
            )

    lines.append("")
    lines.append("=" * 70)

    return "\n".join(lines)


def run_dashboard(rotator: NxRotator, interval: int = 5, live: bool = False):
    """Run the dashboard."""
    if live:
        print("[DASHBOARD] Live mode - press Ctrl+C to exit")
        print(f"[DASHBOARD] Updating every {interval}s\n")

        try:
            while True:
                # Clear screen (works in most terminals)
                print("\033[2J\033[H", end="")
                print(format_stats(rotator))
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[DASHBOARD] Stopped")
    else:
        print(format_stats(rotator))


def main():
    """Main dashboard entry point."""
    parser = argparse.ArgumentParser(description="NxRotator Dashboard")
    parser.add_argument(
        "--interval", "-i", type=int, default=5, help="Update interval in seconds"
    )
    parser.add_argument("--live", "-l", action="store_true", help="Live updating mode")
    parser.add_argument("--model", "-m", help="Test model to use")
    args = parser.parse_args()

    try:
        rotator = NxRotator()
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        sys.exit(1)

    # Optional test run
    if args.model:
        print(f"[TEST] Testing with {args.model}...")
        result = rotator.chat(
            args.model,
            [{"role": "user", "content": "Say 'ok' in one word"}],
            max_tokens=5,
        )
        if result.success:
            print(f"✅ Success: {result.key_used} ({result.latency_ms:.0f}ms)")
        else:
            print(f"❌ Failed: {result.error}")

    # Run dashboard
    run_dashboard(rotator, args.interval, args.live)


if __name__ == "__main__":
    main()
