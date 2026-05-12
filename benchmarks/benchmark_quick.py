#!/usr/bin/env python3
"""
Quick System Benchmark - Measures current system state
=====================================================
Fast measurement of OpenCode capabilities without long-running agent calls.
"""

import subprocess
import time
import json
import os
from pathlib import Path
from datetime import datetime


def check_system_state() -> dict:
    """Check current system state."""
    results = {}

    # 1. OpenCode version
    try:
        result = subprocess.run(
            ["opencode", "--version"], capture_output=True, text=True, timeout=5
        )
        results["opencode_version"] = (
            result.stdout.strip() if result.returncode == 0 else "unknown"
        )
    except Exception as e:
        results["opencode_version"] = f"error: {e}"

    # 2. Plugin loaded?
    try:
        result = subprocess.run(
            ["opencode", "debug", "config"], capture_output=True, text=True, timeout=10
        )
        results["plugin_loaded"] = "oh-my-openagent" in result.stdout
    except:
        results["plugin_loaded"] = False

    # 3. Agent count
    try:
        result = subprocess.run(
            ["opencode", "agent", "list"], capture_output=True, text=True, timeout=10
        )
        agents = [
            line.split(" (")[0] for line in result.stdout.split("\n") if " (" in line
        ]
        results["agent_count"] = len(agents)
        results["agents"] = agents
    except Exception as e:
        results["agent_count"] = 0
        results["error"] = str(e)

    # 4. OMO agents present?
    omo_agents = [
        "sisyphus",
        "catalyst",
        "hephaestus",
        "oracle",
        "prometheus",
        "metis",
        "momus",
    ]
    results["omo_agents_present"] = [
        a for a in omo_agents if a in (results.get("agents") or [])
    ]

    # 5. MCP servers running
    results["mcp_servers"] = check_mcp_servers()

    # 6. Git status
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND",
        )
        changes = [l for l in result.stdout.strip().split("\n") if l]
        results["git_changes"] = len(changes)
    except:
        results["git_changes"] = 0

    # 7. Model availability (quick check)
    results["models_available"] = check_models()

    return results


def check_mcp_servers() -> dict:
    """Check which MCP servers are configured."""
    mcp_servers = {}

    # Check config for MCP servers
    config_file = Path("/home/nxyme/.config/opencode/oh-my-openagent.json")
    if config_file.exists():
        try:
            with open(config_file) as f:
                config = json.load(f)
                mcp_servers = list(config.get("mcp", {}).keys())
        except:
            pass

    return {"count": len(mcp_servers), "servers": mcp_servers[:10]}  # First 10


def check_models() -> list:
    """Check available models."""
    try:
        result = subprocess.run(
            ["opencode", "models"], capture_output=True, text=True, timeout=15
        )
        lines = result.stdout.split("\n")
        # Count available models
        available = [
            l
            for l in lines
            if "opencode/" in l and ("✅" in l or "active" in l.lower())
        ]
        return available[:5]  # First 5
    except:
        return []


def run_mini_task(task: str, timeout: int = 30) -> dict:
    """Run minimal task and measure."""
    start = time.time()
    try:
        result = subprocess.run(
            ["opencode", "--pure", "run", task],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND",
        )
        elapsed = (time.time() - start) * 1000
        output = result.stdout + result.stderr

        success = (
            result.returncode == 0 and len(output) > 30 and "Error" not in output[:100]
        )

        return {
            "task": task[:30],
            "success": success,
            "latency_ms": int(elapsed),
            "output_len": len(output),
        }
    except subprocess.TimeoutExpired:
        return {
            "task": task[:30],
            "success": False,
            "latency_ms": timeout * 1000,
            "error": "timeout",
        }
    except Exception as e:
        return {
            "task": task[:30],
            "success": False,
            "latency_ms": 0,
            "error": str(e)[:50],
        }


def main():
    print("=" * 60)
    print("QUICK SYSTEM BENCHMARK")
    print("=" * 60)

    # System state
    print("\n📊 SYSTEM STATE")
    state = check_system_state()

    print(f"  OpenCode Version: {state.get('opencode_version', 'unknown')}")
    print(
        f"  Plugin Loaded: {'✅' if state.get('plugin_loaded') else '❌'} oh-my-openagent"
    )
    print(f"  Agent Count: {state.get('agent_count', 0)}")
    print(f"  OMO Agents: {', '.join(state.get('omo_agents_present', []))}")
    print(f"  MCP Servers: {state.get('mcp_servers', {}).get('count', 0)}")
    print(f"  Git Changes: {state.get('git_changes', 0)}")

    # Mini tasks
    print("\n📋 MINI TASKS")
    tasks = [
        "What is 1+1?",
        "List 3 files in this directory",
    ]

    task_results = []
    for task in tasks:
        r = run_mini_task(task, timeout=20)
        status = "✅" if r["success"] else "❌"
        print(f"  {status} {r['task']}: {r['latency_ms']}ms")
        task_results.append(r)

    # Summary
    success_rate = (
        sum(1 for r in task_results if r["success"]) / len(task_results)
        if task_results
        else 0
    )
    avg_latency = (
        sum(r["latency_ms"] for r in task_results) / len(task_results)
        if task_results
        else 0
    )

    summary = {
        "timestamp": datetime.now().isoformat(),
        "system_state": state,
        "task_results": task_results,
        "summary": {
            "success_rate": success_rate,
            "avg_latency_ms": int(avg_latency),
        },
    }

    # Save
    output_path = Path(".sisyphus/benchmarks/quick-benchmark.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print("\n" + "=" * 60)
    print(f"SUCCESS RATE: {success_rate:.0%}")
    print(f"AVG LATENCY: {avg_latency:.0f}ms")
    print(f"Results: {output_path}")
    print("=" * 60)

    return summary


if __name__ == "__main__":
    main()
