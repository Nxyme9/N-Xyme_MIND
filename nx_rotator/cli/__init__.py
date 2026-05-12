"""
NxRotator CLI
=============

Command-line interface for NxRotator.

Usage:
    python -m nx_rotator.cli test
    python -m nx_rotator.cli chat "Hello"
    python -m nx_rotator.cli dashboard
    python -m nx_rotator.cli metrics
    python -m nx_rotator.cli keys
    python -m nx_rotator.cli rotate
    python -m nx_rotator.cli reset
"""

import sys
import json
import argparse
from typing import Optional

from ..core.aggregator import NxRotator


def cmd_test(rotator: NxRotator, args):
    """Test the rotator with a simple request."""
    print("[TEST] Testing NxRotator...")

    model = "nvidia/nemotron-3-super-120b-a12b:free"
    if args.model:
        model = args.model

    result = rotator.chat(
        model,
        [{"role": "user", "content": "Say 'hello' in one word"}],
        max_tokens=10,
    )

    if result.success:
        content = (
            result.response.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        print(f"✅ Success with {result.key_used}")
        print(f"   Latency: {result.latency_ms:.0f}ms")
        print(f"   Tokens: {result.tokens}")
        print(f"   Response: {content[:100]}")
    else:
        print(f"❌ Error: {result.error}")
        print(f"   Key used: {result.key_used}")


def cmd_chat(rotator: NxRotator, args):
    """Interactive chat mode."""
    print("[CHAT] Interactive chat mode (Ctrl+C to exit)")
    print(f"Model: {args.model or 'nvidia/nemotron-3-super-120b-a12b:free'}")
    print()

    model = args.model or "nvidia/nemotron-3-super-120b-a12b:free"
    messages = []

    if args.system:
        messages.append({"role": "system", "content": args.system})

    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue

            messages.append({"role": "user", "content": user_input})

            result = rotator.chat(model, messages, max_tokens=8192)

            if result.success:
                content = (
                    result.response.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                print(f"\n🤖: {content}\n")
                messages.append({"role": "assistant", "content": content})
            else:
                print(f"\n❌ Error: {result.error}\n")

        except KeyboardInterrupt:
            print("\n[CHAT] Exiting...")
            break


def cmd_dashboard(rotator: NxRotator, args):
    """Show dashboard with all stats."""
    stats = rotator.get_all_stats()
    metrics = stats["metrics"]

    print("\n" + "=" * 70)
    print("🔄 NxRotator - Maximum Throughput Aggregator v1.0")
    print("=" * 70)

    print(f"\n📊 AGGREGATED LIMITS:")
    print(f"   RPM: {stats['aggregated_rpm']} (20 × {stats['total_keys']} keys)")
    print(f"   TPM: {stats['aggregated_tpm']:,}")

    print(f"\n🔑 KEYS: {stats['active_keys']}/{stats['total_keys']} active")
    print("-" * 70)
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
        print(f"   {status} {health_icon} {ks['key_id']}")
        print(
            f"       {ks['requests']} req | {ks['errors']} err | {ks['tokens']:,} tokens{cooldown}"
        )

    print(f"\n📈 METRICS:")
    print(f"   Total Requests: {metrics['total_requests']:,}")
    print(f"   Total Tokens: {metrics['total_tokens']:,}")
    print(f"   Total Errors: {metrics['total_errors']}")
    print(f"   Error Rate: {metrics['error_rate']:.2f}%")
    print(f"   Avg Latency: {metrics['avg_latency_ms']:.0f}ms")
    print(f"   Rotations: {metrics['total_rotations']}")
    print(f"   Uptime: {metrics['uptime_seconds'] / 3600:.1f}h")

    # Top models
    if metrics["by_model"]:
        print(f"\n🤖 MODELS:")
        for model, stats_dict in sorted(
            metrics["by_model"].items(), key=lambda x: -x[1]["requests"]
        )[:5]:
            print(
                f"   {model}: {stats_dict['requests']} req, {stats_dict['tokens']:,} tokens"
            )

    print("\n" + "=" * 70)


def cmd_metrics(rotator: NxRotator, args):
    """Show metrics as JSON."""
    print(json.dumps(rotator.get_all_stats(), indent=2))


def cmd_keys(rotator: NxRotator, args):
    """Show key status."""
    stats = rotator.get_all_stats()

    print(f"\n🔑 {stats['active_keys']}/{stats['total_keys']} Keys Active\n")

    for ks in stats["key_stats"]:
        status = "✅ ACTIVE" if ks["available"] else "❌ EXHAUSTED"
        print(f"{ks['key_id']}: {status}")
        print(
            f"   Health: {ks['health']:.1%} | Requests: {ks['requests']} | Errors: {ks['errors']}"
        )
        if ks["cooldown_remaining"] > 0:
            print(f"   Cooldown: {ks['cooldown_remaining']:.0f}s remaining")
        print()


def cmd_rotate(rotator: NxRotator, args):
    """Force rotate to next key."""
    key = rotator.get_next_key()
    rotator._current_key_idx = (rotator._current_key_idx + 1) % len(rotator.keys)
    print(f"Rotated to: {key.key_id} (health: {key.health_score:.1%})")


def cmd_reset(rotator: NxRotator, args):
    """Reset all exhausted keys."""
    rotator.reset_exhausted()
    print("All keys reset - ready for new requests")


def cmd_learn(rotator: NxRotator, args):
    """Show learning stats from SQLite."""
    import sqlite3
    from pathlib import Path

    # Use same path resolution as core
    _PROJECT_ROOT = Path(__file__).parent.parent.parent
    CONFIG_DIR = _PROJECT_ROOT / "configs" / "api-keys"
    DB_FILE = CONFIG_DIR / "nx_rotator_learning.db"

    conn = sqlite3.connect(str(DB_FILE))

    print("\n📊 KEY PERFORMANCE (from SQLite):")
    print("-" * 60)

    cursor = conn.execute("""
        SELECT key_id, total_requests, successful_requests, 
               avg_latency_ms, total_tokens, last_updated
        FROM key_performance
        ORDER BY total_requests DESC
    """)

    for row in cursor.fetchall():
        key_id, total_req, success_req, avg_lat, tokens, last_upd = row
        success_rate = success_req / max(total_req, 1) * 100
        print(f"{key_id}:")
        print(f"   Requests: {total_req} | Success: {success_rate:.1f}%")
        print(f"   Avg Latency: {avg_lat:.0f}ms | Tokens: {tokens:,}")
        print(
            f"   Last Used: {datetime.fromtimestamp(last_upd).isoformat() if last_upd else 'N/A'}"
        )
        print()

    conn.close()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="NxRotator - Maximum Throughput API Key Aggregator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # test
    test_parser = subparsers.add_parser("test", help="Test with simple request")
    test_parser.add_argument("--model", "-m", help="Model to use")
    test_parser.set_defaults(func=cmd_test)

    # chat
    chat_parser = subparsers.add_parser("chat", help="Interactive chat")
    chat_parser.add_argument("--model", "-m", help="Model to use")
    chat_parser.add_argument("--system", "-s", help="System prompt")
    chat_parser.set_defaults(func=cmd_chat)

    # dashboard
    dash_parser = subparsers.add_parser("dashboard", help="Show dashboard")
    dash_parser.set_defaults(func=cmd_dashboard)

    # metrics
    metrics_parser = subparsers.add_parser("metrics", help="Show metrics as JSON")
    metrics_parser.set_defaults(func=cmd_metrics)

    # keys
    keys_parser = subparsers.add_parser("keys", help="Show key status")
    keys_parser.set_defaults(func=cmd_keys)

    # rotate
    rotate_parser = subparsers.add_parser("rotate", help="Force rotate to next key")
    rotate_parser.set_defaults(func=cmd_rotate)

    # reset
    reset_parser = subparsers.add_parser("reset", help="Reset all exhausted keys")
    reset_parser.set_defaults(func=cmd_reset)

    # learn
    learn_parser = subparsers.add_parser("learn", help="Show learning stats")
    learn_parser.set_defaults(func=cmd_learn)

    args = parser.parse_args()

    # Initialize rotator
    try:
        rotator = NxRotator()
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        sys.exit(1)

    # Run command
    if args.command is None:
        # Default: show dashboard
        cmd_dashboard(rotator, args)
    else:
        args.func(rotator, args)


if __name__ == "__main__":
    main()


# Need datetime for learn command
from datetime import datetime
