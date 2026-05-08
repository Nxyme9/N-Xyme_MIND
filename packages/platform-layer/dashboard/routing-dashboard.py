#!/usr/bin/env python3
"""Routing Dashboard CLI

Shows current routing statistics, agent performance, and system status.
"""

import json
import time
from pathlib import Path
from typing import Any


def load_json_file(path: Path) -> Any:
    """Load JSON file safely."""
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def load_jsonl_file(path: Path) -> list:
    """Load JSONL file safely."""
    if path.exists():
        with open(path) as f:
            return [json.loads(line) for line in f if line.strip()]
    return []


def print_header(title: str):
    """Print section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_stat(label: str, value: str):
    """Print statistic."""
    print(f"  {label:25s} {value}")


def show_routing_stats():
    """Show routing statistics."""
    print_header("ROUTING STATISTICS")
    
    outcomes = load_jsonl_file(Path('.sisyphus/outcomes.jsonl'))
    total = len(outcomes)
    
    if total == 0:
        print_stat("Total delegations", "0")
        return
    
    print_stat("Total delegations", str(total))
    
    # Calculate success rate
    success = sum(1 for o in outcomes if o.get('success'))
    rate = (success / total * 100) if total > 0 else 0
    print_stat("Success rate", f"{rate:.0f}%")
    
    # Average latency
    latencies = [o.get('latency_ms', 0) for o in outcomes if o.get('latency_ms')]
    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        print_stat("Avg latency", f"{avg_latency:.0f}ms")
    
    # Recent activity
    if outcomes:
        latest = outcomes[-1]
        print_stat("Last delegation", latest.get('task_description', 'N/A')[:40])


def show_agent_performance():
    """Show agent performance."""
    print_header("AGENT PERFORMANCE")
    
    weights = load_json_file(Path('.sisyphus/routing-weights.json'))
    if not weights:
        print("  No agent data available")
        return
    
    # Sort by success rate
    agents = []
    for name, data in weights.items():
        if data.get('total_tasks', 0) > 0:
            agents.append((
                name,
                data.get('success_rate', 0),
                data.get('total_tasks', 0),
                data.get('avg_latency_ms', 0)
            ))
    
    agents.sort(key=lambda x: (x[1], x[2]), reverse=True)
    
    print(f"  {'Agent':20s} {'Success':>8s} {'Tasks':>6s} {'Avg Latency':>12s}")
    print(f"  {'-' * 20} {'-' * 8} {'-' * 6} {'-' * 12}")
    
    for name, rate, tasks, latency in agents:
        print(f"  {name:20s} {rate:7.0%} {tasks:6d} {latency:10.0f}ms")


def show_trigger_patterns():
    """Show trigger patterns."""
    print_header("TRIGGER PATTERNS")
    
    config = load_json_file(Path('.sisyphus/routing-triggers.json'))
    if not config:
        print("  No triggers configured")
        return
    
    triggers = config.get('routing_triggers', [])
    print(f"  Total triggers: {len(triggers)}")
    print(f"\n  {'Name':20s} {'Level':>6s} {'Agent':20s} {'Priority':>9s}")
    print(f"  {'-' * 20} {'-' * 6} {'-' * 20} {'-' * 9}")
    
    for trigger in sorted(triggers, key=lambda x: x.get('priority', 0), reverse=True):
        print(f"  {trigger['name']:20s} {trigger['level']:6d} {trigger['agent']:20s} {trigger.get('priority', 0):9d}")


def show_recent_outcomes(count: int = 10):
    """Show recent outcomes."""
    print_header(f"RECENT OUTCOMES (last {count})")
    
    outcomes = load_jsonl_file(Path('.sisyphus/outcomes.jsonl'))
    if not outcomes:
        print("  No outcomes recorded")
        return
    
    recent = outcomes[-count:]
    print(f"  {'Task ID':>15s} {'Description':35s} {'Agent':15s} {'Level':>5s} {'Status':>7s}")
    print(f"  {'-' * 15} {'-' * 35} {'-' * 15} {'-' * 5} {'-' * 7}")
    
    for outcome in recent:
        task_id = outcome.get('task_id', '?')[-12:]
        desc = outcome.get('task_description', '?')[:35]
        agent = outcome.get('agent', '?')[:15]
        level = outcome.get('level', '?')
        status = '✅' if outcome.get('success') else '❌'
        print(f"  {task_id:>15s} {desc:35s} {agent:15s} {str(level):>5s} {status:>7s}")


def main():
    """Main dashboard function."""
    print("=" * 60)
    print("  N-Xyme_MIND ROUTING DASHBOARD")
    print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    show_routing_stats()
    show_agent_performance()
    show_trigger_patterns()
    show_recent_outcomes(10)
    
    print(f"\n{'=' * 60}")
    print("  Dashboard complete")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
