#!/usr/bin/env python3
"""
Cost Tracker — Track token usage and costs across all AI models.

Tracks:
- Tokens used per model (input + output)
- Estimated costs (cloud models only — local is free!)
- Daily/monthly budgets
- Per-agent usage breakdown
- Savings from local routing

Usage:
    python scripts/cost-tracker.py              # Show dashboard
    python scripts/cost-tracker.py --daily      # Daily summary
    python scripts/cost-tracker.py --monthly    # Monthly summary
    python scripts/cost-tracker.py --reset      # Reset counters
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# ============================================
# CONFIG
# ============================================

DATA_DIR = Path(__file__).parent.parent / "data" / "cost-tracker"
USAGE_FILE = DATA_DIR / "usage.json"
BUDGET_FILE = DATA_DIR / "budgets.json"

# Token costs per 1M tokens (USD) — as of March 2026
MODEL_COSTS = {
    # OpenCode free models
    "opencode/mimo-v2-pro-free": {"input": 0.0, "output": 0.0, "provider": "opencode"},
    "opencode/minimax-m2.5-free": {"input": 0.0, "output": 0.0, "provider": "opencode"},
    "opencode/gpt-5-nano": {"input": 0.0, "output": 0.0, "provider": "opencode"},
    # Groq models
    "groq/llama-3.1-8b-instant": {"input": 0.05, "output": 0.08, "provider": "groq"},
    "groq/llama-3.1-70b-versatile": {"input": 0.59, "output": 0.79, "provider": "groq"},
    "groq/qwen-2.5-coder-32b": {"input": 0.59, "output": 0.79, "provider": "groq"},
    # OpenRouter models
    "openrouter/deepseek/deepseek-r1:free": {"input": 0.0, "output": 0.0, "provider": "openrouter"},
    "openrouter/qwen/qwen3-coder:free": {"input": 0.0, "output": 0.0, "provider": "openrouter"},
    "openrouter/hunter-alpha": {"input": 0.0, "output": 0.0, "provider": "openrouter"},
    # Local Ollama models (FREE!)
    "ollama/llama3.2:latest": {"input": 0.0, "output": 0.0, "provider": "ollama"},
    "ollama/llama3.2:3b": {"input": 0.0, "output": 0.0, "provider": "ollama"},
    "ollama/qwen2.5-coder:7b": {"input": 0.0, "output": 0.0, "provider": "ollama"},
    "ollama/qwen2.5-coder-14b-offload": {"input": 0.0, "output": 0.0, "provider": "ollama"},
    "ollama/qwen3:8b": {"input": 0.0, "output": 0.0, "provider": "ollama"},
    "ollama/qwen3-8b-full": {"input": 0.0, "output": 0.0, "provider": "ollama"},
    "ollama/deepseek-r1-14b-offload": {"input": 0.0, "output": 0.0, "provider": "ollama"},
    "ollama/llava:7b": {"input": 0.0, "output": 0.0, "provider": "ollama"},
    "ollama/nomic-embed-text": {"input": 0.0, "output": 0.0, "provider": "ollama"},
}

DEFAULT_BUDGETS = {
    "daily_limit_usd": 5.00,
    "monthly_limit_usd": 50.00,
    "opencode_daily": 200,  # requests per day
    "opencode_monthly": 6000,  # requests per month
}


# ============================================
# USAGE TRACKING
# ============================================


def load_usage() -> dict:
    """Load usage data from disk."""
    if USAGE_FILE.exists():
        return json.loads(USAGE_FILE.read_text(encoding="utf-8"))
    return {
        "daily": {},
        "total_tokens": {"input": 0, "output": 0},
        "total_cost_usd": 0.0,
        "local_tokens": 0,
        "cloud_tokens": 0,
        "providers": {},
        "agents": {},
        "last_reset": datetime.now().isoformat(),
    }


def save_usage(usage: dict):
    """Save usage data to disk."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    USAGE_FILE.write_text(json.dumps(usage, indent=2, default=str), encoding="utf-8")


def record_usage(
    model: str,
    input_tokens: int,
    output_tokens: int,
    agent: str = "unknown",
    latency_ms: float = 0.0,
):
    """Record token usage for a model call."""
    usage = load_usage()
    today = datetime.now().strftime("%Y-%m-%d")

    # Get cost info
    cost_info = MODEL_COSTS.get(model, {"input": 0.0, "output": 0.0, "provider": "unknown"})
    provider = cost_info["provider"]
    is_local = provider == "ollama"

    # Calculate cost
    input_cost = (input_tokens / 1_000_000) * cost_info["input"]
    output_cost = (output_tokens / 1_000_000) * cost_info["output"]
    total_cost = input_cost + output_cost

    # Update daily
    if today not in usage["daily"]:
        usage["daily"][today] = {
            "tokens": 0,
            "cost_usd": 0.0,
            "calls": 0,
            "local_calls": 0,
            "cloud_calls": 0,
        }
    usage["daily"][today]["tokens"] += input_tokens + output_tokens
    usage["daily"][today]["cost_usd"] += total_cost
    usage["daily"][today]["calls"] += 1
    if is_local:
        usage["daily"][today]["local_calls"] += 1
    else:
        usage["daily"][today]["cloud_calls"] += 1

    # Update totals
    usage["total_tokens"]["input"] += input_tokens
    usage["total_tokens"]["output"] += output_tokens
    usage["total_cost_usd"] += total_cost

    if is_local:
        usage["local_tokens"] += input_tokens + output_tokens
    else:
        usage["cloud_tokens"] += input_tokens + output_tokens

    # Update provider stats
    if provider not in usage["providers"]:
        usage["providers"][provider] = {"tokens": 0, "cost_usd": 0.0, "calls": 0}
    usage["providers"][provider]["tokens"] += input_tokens + output_tokens
    usage["providers"][provider]["cost_usd"] += total_cost
    usage["providers"][provider]["calls"] += 1

    # Update agent stats
    if agent not in usage["agents"]:
        usage["agents"][agent] = {"tokens": 0, "cost_usd": 0.0, "calls": 0, "local": 0, "cloud": 0}
    usage["agents"][agent]["tokens"] += input_tokens + output_tokens
    usage["agents"][agent]["cost_usd"] += total_cost
    usage["agents"][agent]["calls"] += 1
    if is_local:
        usage["agents"][agent]["local"] += 1
    else:
        usage["agents"][agent]["cloud"] += 1

    save_usage(usage)
    return {
        "model": model,
        "provider": provider,
        "is_local": is_local,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": total_cost,
        "latency_ms": latency_ms,
    }


# ============================================
# DASHBOARD
# ============================================


def show_dashboard():
    """Show cost tracking dashboard."""
    usage = load_usage()
    today = datetime.now().strftime("%Y-%m-%d")
    today_data = usage.get("daily", {}).get(
        today, {"tokens": 0, "cost_usd": 0.0, "calls": 0, "local_calls": 0, "cloud_calls": 0}
    )

    total_tokens = usage["total_tokens"]["input"] + usage["total_tokens"]["output"]
    local_pct = (usage["local_tokens"] / total_tokens * 100) if total_tokens > 0 else 0

    print("=" * 60)
    print("COST TRACKER - N-Xyme Catalyst")
    print("=" * 60)

    print(f"\nTODAY ({today})")
    print(f"  Tokens: {today_data['tokens']:,}")
    print(f"  Cost: ${today_data['cost_usd']:.4f}")
    print(
        f"  Calls: {today_data['calls']} (LOCAL {today_data['local_calls']}, CLOUD {today_data['cloud_calls']})"
    )

    print(f"\nALL TIME")
    print(f"  Total tokens: {total_tokens:,}")
    print(f"  Local tokens: {usage['local_tokens']:,} ({local_pct:.0f}%)")
    print(f"  Cloud tokens: {usage['cloud_tokens']:,} ({100 - local_pct:.0f}%)")
    print(f"  Total cost: ${usage['total_cost_usd']:.4f}")

    print(f"\nPROVIDERS")
    for provider, data in sorted(
        usage.get("providers", {}).items(), key=lambda x: -x[1]["cost_usd"]
    ):
        print(
            f"  {provider:20} {data['tokens']:>10,} tokens  ${data['cost_usd']:>8.4f}  ({data['calls']} calls)"
        )

    print(f"\nAGENTS")
    for agent, data in sorted(usage.get("agents", {}).items(), key=lambda x: -x[1]["tokens"]):
        total = data["local"] + data["cloud"]
        local_pct = (data["local"] / total * 100) if total > 0 else 0
        print(
            f"  {agent:20} {data['tokens']:>10,} tokens  ${data['cost_usd']:>8.4f}  ({local_pct:.0f}% local)"
        )

    print(f"\nSAVINGS FROM LOCAL ROUTING")
    # Calculate what it WOULD cost if everything was cloud
    cloud_rate = 0.59  # Average cloud cost per 1M tokens
    if usage["local_tokens"] > 0:
        saved = (usage["local_tokens"] / 1_000_000) * cloud_rate
        print(f"  Local tokens saved: ${saved:.2f}")
        print(f"  (Would cost ${saved:.2f} if routed to cloud)")
    else:
        print(f"  No local usage yet")

    print("=" * 60)


def show_daily():
    """Show daily breakdown."""
    usage = load_usage()
    print("\nDAILY BREAKDOWN")
    print("-" * 60)
    for date in sorted(usage.get("daily", {}).keys(), reverse=True)[:30]:
        data = usage["daily"][date]
        print(
            f"  {date}  {data['tokens']:>10,} tokens  ${data['cost_usd']:>8.4f}  ({data['calls']} calls)"
        )


def show_monthly():
    """Show monthly breakdown."""
    usage = load_usage()
    months = {}
    for date, data in usage.get("daily", {}).items():
        month = date[:7]
        if month not in months:
            months[month] = {"tokens": 0, "cost_usd": 0.0, "calls": 0}
        months[month]["tokens"] += data["tokens"]
        months[month]["cost_usd"] += data["cost_usd"]
        months[month]["calls"] += data["calls"]

    print("\nMONTHLY BREAKDOWN")
    print("-" * 60)
    for month in sorted(months.keys(), reverse=True)[:12]:
        data = months[month]
        print(
            f"  {month}  {data['tokens']:>10,} tokens  ${data['cost_usd']:>8.4f}  ({data['calls']} calls)"
        )


def reset_counters():
    """Reset all counters."""
    save_usage(
        {
            "daily": {},
            "total_tokens": {"input": 0, "output": 0},
            "total_cost_usd": 0.0,
            "local_tokens": 0,
            "cloud_tokens": 0,
            "providers": {},
            "agents": {},
            "last_reset": datetime.now().isoformat(),
        }
    )
    print("✅ Counters reset.")


# ============================================
# MAIN
# ============================================


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--daily":
            show_daily()
        elif arg == "--monthly":
            show_monthly()
        elif arg == "--reset":
            reset_counters()
        elif arg == "--json":
            print(json.dumps(load_usage(), indent=2, default=str))
        else:
            print(f"Unknown option: {arg}")
            print("Usage: cost-tracker.py [--daily|--monthly|--reset|--json]")
    else:
        show_dashboard()


if __name__ == "__main__":
    main()
