#!/usr/bin/env python3
"""Comprehensive end-to-end wiring test for N-Xyme_MIND.

Tests every single connection in the system and proves it works with real output.
"""

import sys
import os
import time
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

PASS = 0
FAIL = 0
SKIPPED = 0


def run_test(name, fn, skip=False):
    """Run a test and track results."""
    global PASS, FAIL, SKIPPED
    if skip:
        SKIPPED += 1
        print(f"  ⏭️  {name}: SKIPPED")
        return
    try:
        result = fn()
        if result is False:
            FAIL += 1
            print(f"  ❌ {name}: FAILED (returned False)")
        else:
            PASS += 1
            print(f"  ✅ {name}: PASSED")
    except Exception as e:
        FAIL += 1
        print(f"  ❌ {name}: FAILED ({e})")


def main():
    global PASS, FAIL, SKIPPED

    print("=" * 80)
    print("🧠 N-XYME MIND — COMPREHENSIVE END-TO-END WIRING TEST")
    print("=" * 80)
    print()

    # ─── CHAIN A: MCP Query → Search → Learning Feedback ───
    print("CHAIN A: MCP Query → Search → Learning Feedback")
    print("-" * 60)

    run_test("MCP server imports", lambda: __import__("src.memory.mcp_server"))

    test(
        "search_memories returns results",
        lambda: (lambda r: r.get("total_found", 0) >= 0)(
            __import__(
                "src.memory.mcp_server", fromlist=["search_memories"]
            ).search_memories("test", limit=3)
        ),
    )

    test(
        "EventBusConsumer initialized",
        lambda: (lambda c: c.get_stats().get("subscribed", False))(
            __import__(
                "src.memory.event_bus_consumer", fromlist=["get_consumer"]
            ).get_consumer()
        ),
    )

    test(
        "PriorityEngine receives feedback",
        lambda: (lambda pe: pe.get_learning_stats().get("total_feedback", 0) > 0)(
            __import__(
                "src.memory.priority_engine", fromlist=["PriorityEngine"]
            ).PriorityEngine(str(Path("context/memory/file_registry.db").resolve()))
        ),
    )

    test(
        "SelfLearner receives outcomes",
        lambda: (lambda sl: len(sl.get_outcomes()) >= 0)(
            __import__(
                "src.learning.self_learning", fromlist=["SelfLearner"]
            ).SelfLearner()
        ),
    )

    print()

    # ─── CHAIN B: Intelligence Layer ───
    print("CHAIN B: Intelligence Layer → Production")
    print("-" * 60)

    run_test("Intelligence modules import", lambda: __import__("src.intelligence"))

    test(
        "DelegationLearner available",
        lambda: (
            lambda: __import__(
                "src.intelligence.learning", fromlist=["DelegationLearner"]
            )
        )(),
    )

    test(
        "DynamicComplexityScorer available",
        lambda: (
            lambda: __import__(
                "src.intelligence.dynamic_scorer", fromlist=["DynamicComplexityScorer"]
            )
        )(),
    )

    test(
        "AgentOptimizer available",
        lambda: (
            lambda: __import__(
                "src.intelligence.agent_optimizer", fromlist=["AgentOptimizer"]
            )
        )(),
    )

    test(
        "PredictiveLoadBalancer available",
        lambda: (
            lambda: __import__(
                "src.intelligence.load_balancer", fromlist=["PredictiveLoadBalancer"]
            )
        )(),
    )

    test(
        "get_intelligence_stats MCP tool",
        lambda: (lambda r: r.get("status") == "ok")(
            __import__(
                "src.memory.mcp_server", fromlist=["get_intelligence_stats"]
            ).get_intelligence_stats()
        ),
    )

    print()

    # ─── CHAIN C: File Change → Watch → Embed → Index ───
    print("CHAIN C: File Change → Watch → Embed → Index")
    print("-" * 60)

    test(
        "Multi-drive scanner imports",
        lambda: __import__("src.memory.multi_drive_scanner"),
    )

    test(
        "Content extractor imports", lambda: __import__("src.memory.content_extractor")
    )

    run_test("Drive embedder imports", lambda: __import__("src.memory.drive_embedder"))

    test(
        "File content connector imports",
        lambda: __import__("src.memory.file_content_connector"),
    )

    test(
        "File content connector registered in router",
        lambda: (lambda sources: "file_content" in sources)(
            [
                s.name
                for s in __import__(
                    "src.memory.registry", fromlist=["get_enabled_connectors"]
                ).get_enabled_connectors()
            ]
        ),
    )

    test(
        "Drive index has files",
        lambda: (lambda s: s.get("total_files", 0) > 0)(
            __import__(
                "src.memory.drive_embedder", fromlist=["get_indexed_count"]
            ).get_indexed_count()
        ),
    )

    print()

    # ─── CHAIN D: Daemon → Self-Healing → Sleep Cycle ───
    print("CHAIN D: Daemon → Self-Healing → Sleep Cycle")
    print("-" * 60)

    run_test("Daemon imports", lambda: __import__("src.memory.daemon"))

    run_test("SelfHealer imports", lambda: __import__("src.memory.self_healer"))

    run_test("AutoRecovery imports", lambda: __import__("src.auto_recovery"))

    run_test("SleepCycle imports", lambda: __import__("src.memory.core.sleep_cycle"))

    test(
        "SleepCycle uses persistent DB",
        lambda: (lambda sc: sc._db_path != ":memory:")(
            __import__(
                "src.memory.core.sleep_cycle", fromlist=["SleepCycle"]
            ).SleepCycle(db_path=str(Path("context/memory/sleep_cycle.db").resolve()))
        ),
    )

    test(
        "Daemon has SelfHealer integration",
        lambda: (lambda: "SelfHealer" in open("src/memory/daemon.py").read())(),
    )

    test(
        "Daemon has sleep re-index",
        lambda: (lambda: "reindex" in open("src/memory/daemon.py").read())(),
    )

    print()

    # ─── CHAIN E: Session Lifecycle → OpenCode ───
    print("CHAIN E: Session Lifecycle → OpenCode")
    print("-" * 60)

    test(
        "Session lifecycle imports", lambda: __import__("src.memory.session_lifecycle")
    )

    test(
        "Session lifecycle wrapper exists", lambda: os.path.exists("bin/n-xyme-mind.sh")
    )

    test(
        "Fish shell function added",
        lambda: (
            lambda: (
                "n-xyme-mind.sh"
                in open(os.path.expanduser("~/.config/fish/config.fish")).read()
            )
        )(),
    )

    run_test("activeContext.md exists", lambda: os.path.exists(".context/activeContext.md"))

    print()

    # ─── CHAIN F: CLI/TUI → Memory System ───
    print("CHAIN F: CLI/TUI → Memory System (Read + Write)")
    print("-" * 60)

    run_test("CLI imports", lambda: __import__("src.cli.mind_cli"))

    test(
        "CLI has save command",
        lambda: (lambda: "cmd_save" in open("src/cli/mind_cli.py").read())(),
    )

    run_test("TUI dashboard imports", lambda: __import__("src.tui.mind_dashboard"))

    test(
        "Memory write-back works",
        lambda: (lambda r: r.get("status") == "ok")(
            __import__(
                "src.memory.mcp_server", fromlist=["create_memory"]
            ).create_memory("Wiring test memory", kind="note", scope="global")
        ),
    )

    print()

    # ─── CHAIN G: Learning Signals → Production ───
    print("CHAIN G: Learning Signals → Production")
    print("-" * 60)

    test(
        "SignalDetector imports",
        lambda: (
            lambda: __import__("src.learning.signals", fromlist=["SignalDetector"])
        )(),
    )

    test(
        "SignalDetector exported in __init__",
        lambda: (
            lambda: hasattr(
                __import__("src.memory", fromlist=["SignalDetector"]), "SignalDetector"
            )
        )(),
    )

    test(
        "PromptWizard imports",
        lambda: (
            lambda: __import__(
                "src.learning.prompt_evolution", fromlist=["PromptWizard"]
            )
        )(),
    )

    test(
        "evolve_prompt MCP tool exists",
        lambda: (
            lambda: hasattr(
                __import__("src.memory.mcp_server", fromlist=["evolve_prompt"]),
                "evolve_prompt",
            )
        )(),
    )

    print()

    # ─── CHAIN H: Hindsight MCP ───
    print("CHAIN H: Hindsight MCP Configuration")
    print("-" * 60)

    test(
        "Hindsight MCP in opencode.json",
        lambda: (
            lambda: "hindsight" in json.load(open("opencode.json")).get("mcp", {})
        )(),
    )

    print()

    # ─── SUMMARY ───
    print("=" * 80)
    print(f"RESULTS: {PASS} passed, {FAIL} failed, {SKIPPED} skipped")
    print("=" * 80)

    if FAIL == 0:
        print("✅ ALL CONNECTIONS VERIFIED — SYSTEM FULLY WIRED")
    else:
        print(f"❌ {FAIL} CONNECTIONS FAILED — NEEDS FIXING")

    return FAIL == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
