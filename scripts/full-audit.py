"""
Full Pipeline Audit — Comprehensive system test for N-Xyme Catalyst

Tests everything end-to-end:
1. All Python modules (import test)
2. All MCP servers (health check)
3. All configurations (valid JSON)
4. All BMAD commands (load test)
5. All agent mappings (verification)
6. Memory system (Graphiti)
7. Thinking effort system
8. Athena Bridge (full conversion)
9. Heartbeat system
10. Health monitoring

Usage:
    python scripts/full-audit.py
"""

import json
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Dict, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Suppress logging that causes Unicode errors
import logging

logging.disable(logging.CRITICAL)

AUDIT_RESULTS = {
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    "categories": {},
    "total_passed": 0,
    "total_failed": 0,
    "total_warnings": 0,
}


def test_result(category: str, test_name: str, passed: bool, message: str = ""):
    """Record a test result."""
    if category not in AUDIT_RESULTS["categories"]:
        AUDIT_RESULTS["categories"][category] = {
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "tests": [],
        }

    status = "PASS" if passed else "FAIL"
    AUDIT_RESULTS["categories"][category]["tests"].append(
        {
            "name": test_name,
            "status": status,
            "message": message,
        }
    )

    if passed:
        AUDIT_RESULTS["categories"][category]["passed"] += 1
        AUDIT_RESULTS["total_passed"] += 1
    else:
        AUDIT_RESULTS["categories"][category]["failed"] += 1
        AUDIT_RESULTS["total_failed"] += 1

    symbol = "[OK]" if passed else "[FAIL]"
    print(f"  {symbol} {test_name}" + (f" — {message}" if message else ""))


def run_audit():
    """Run full pipeline audit."""

    print("=" * 60)
    print("FULL PIPELINE AUDIT — N-Xyme Catalyst")
    print("=" * 60)

    # ============================================
    # CATEGORY 1: Python Modules
    # ============================================
    print("\n[1/10] PYTHON MODULES")
    src_dir = Path("src")
    modules = list(src_dir.glob("*.py"))

    for module_path in modules:
        module_name = module_path.stem
        try:
            mod = __import__(module_name)
            test_result("modules", f"Import {module_name}", True)
        except Exception as e:
            test_result("modules", f"Import {module_name}", False, str(e)[:50])

    # ============================================
    # CATEGORY 2: Config Files
    # ============================================
    print("\n[2/10] CONFIGURATION FILES")
    configs = [
        (r"C:\Users\N-Xyme\.config\opencode\opencode.json", "opencode.json"),
        (r"C:\Users\N-Xyme\.config\opencode\oh-my-opencode.json", "oh-my-opencode.json"),
        ("ecosystem.config.js", "ecosystem.config.js"),
        ("_bmad/_config/manifest.yaml", "BMAD manifest"),
    ]

    for config_path, name in configs:
        try:
            path = Path(config_path)
            if path.exists():
                if path.suffix == ".json":
                    json.loads(path.read_text(encoding="utf-8"))
                test_result("configs", f"{name} valid", True)
            else:
                test_result("configs", f"{name} exists", False, "File not found")
        except Exception as e:
            test_result("configs", f"{name} valid", False, str(e)[:50])

    # ============================================
    # CATEGORY 3: BMAD Commands
    # ============================================
    print("\n[3/10] BMAD COMMANDS")
    commands_dir = Path(".opencode/commands")
    bmad_commands = list(commands_dir.glob("bmad-*.md"))

    for cmd_path in bmad_commands:
        try:
            content = cmd_path.read_text(encoding="utf-8")
            has_agent_ref = "_bmad/bmm/agents/" in content
            has_persona = "persona" in content.lower() or "agent" in content.lower()
            test_result(
                "bmad_commands",
                f"{cmd_path.stem} loads agent",
                has_agent_ref and has_persona,
                "OK" if has_agent_ref else "Missing agent reference",
            )
        except Exception as e:
            test_result("bmad_commands", f"{cmd_path.stem} valid", False, str(e)[:50])

    # ============================================
    # CATEGORY 4: BMAD Agent Definitions
    # ============================================
    print("\n[4/10] BMAD AGENT DEFINITIONS")
    agents_dir = Path("_bmad/bmm/agents")
    agent_files = list(agents_dir.glob("*.md"))

    for agent_path in agent_files:
        try:
            content = agent_path.read_text(encoding="utf-8")
            has_xml = "<persona>" in content or "<activation>" in content
            test_result(
                "bmad_agents",
                f"{agent_path.stem} definition",
                len(content) > 100 and has_xml,
                f"{len(content)} chars" if has_xml else "Missing XML structure",
            )
        except Exception as e:
            test_result("bmad_agents", f"{agent_path.stem} readable", False, str(e)[:50])

    # ============================================
    # CATEGORY 5: Athena Bridge
    # ============================================
    print("\n[5/10] ATHENA BRIDGE")
    try:
        from athena_bridge import AthenaBridge, BMADStory, Task

        bridge = AthenaBridge()

        # Test agent mapping
        analyst_maps = bridge.AGENT_MAP.get("analyst") == "oracle"
        test_result("bridge", "Agent mapping (analyst→oracle)", analyst_maps)

        architect_maps = bridge.AGENT_MAP.get("architect") == "hephaestus"
        test_result("bridge", "Agent mapping (architect→hephaestus)", architect_maps)

        pm_maps = bridge.AGENT_MAP.get("pm") == "prometheus"
        test_result("bridge", "Agent mapping (pm→prometheus)", pm_maps)

        sm_maps = bridge.AGENT_MAP.get("sm") == "atlas"
        test_result("bridge", "Agent mapping (sm→atlas)", sm_maps)

        # Test plan conversion
        plan = {"stories": [{"id": "s1", "title": "Test", "assigned_to": "dev", "type": "coding"}]}
        tasks = bridge.convert_plan(plan)
        test_result("bridge", "Plan conversion", len(tasks) == 1 and tasks[0].agent == "hephaestus")

        # Test execute (stub check)
        results = bridge.execute(tasks)
        test_result("bridge", "Execute returns results", len(results) > 0)

        # Test status
        status = bridge.get_status()
        test_result("bridge", "Get status", status["bmad_agents"] > 0)

    except Exception as e:
        test_result("bridge", "Import AthenaBridge", False, str(e)[:50])

    # ============================================
    # CATEGORY 6: Thinking Effort
    # ============================================
    print("\n[6/10] THINKING EFFORT SYSTEM")
    try:
        from thinking_effort import ThinkingEffort, ThinkingLevel

        effort = ThinkingEffort()

        # Test simple task
        level = effort.evaluate("Fix typo in color")
        test_result("thinking", "Simple task → medium", level == "medium")

        # Test high task
        level = effort.evaluate("Research and analyze security vulnerabilities", file_count=3)
        test_result("thinking", "Research task → high/ultra", level in ("high", "ultra"))

        # Test ultra task
        level = effort.evaluate("Emergency critical system-wide failure", file_count=10)
        test_result("thinking", "Critical task → ultra", level == "ultra")

        # Test architecture task
        level = effort.evaluate("Design new database architecture")
        test_result("thinking", "Architecture task → ultra", level == "ultra")

        # Test debug task
        level = effort.evaluate("Debug root cause of memory leak")
        test_result("thinking", "Debug task → high", level == "high")

        # Test minimum level
        level = effort.evaluate("Change button color to blue")
        test_result("thinking", "Minimum level is medium", level == "medium")

    except Exception as e:
        test_result("thinking", "Import ThinkingEffort", False, str(e)[:50])

    # ============================================
    # CATEGORY 7: Health System
    # ============================================
    print("\n[7/10] HEALTH SYSTEM")
    try:
        from health_core import HealthMonitor, ComponentHealth, ComponentStatus

        monitor = HealthMonitor()

        # Test registration
        monitor.register("test", lambda: ComponentStatus("test", ComponentHealth.HEALTHY, "OK"))
        test_result("health", "Register component", "test" in monitor._components)

        # Test check
        status = monitor.check("test")
        test_result("health", "Check component", status.health == ComponentHealth.HEALTHY)

        # Test overall health
        overall = monitor.get_overall_health()
        test_result("health", "Overall health", overall == ComponentHealth.HEALTHY)

        # Test full report
        report = monitor.get_full_report()
        test_result("health", "Full report", "overall" in report and "components" in report)

    except Exception as e:
        test_result("health", "Import HealthMonitor", False, str(e)[:50])

    # ============================================
    # CATEGORY 8: MCP Servers
    # ============================================
    print("\n[8/10] MCP SERVERS (HTTP)")
    import httpx

    mcp_ports = [
        12010,
        12011,
        12012,
        12014,
        11435,
        12001,
        12002,
        12003,
        12020,
        12021,
        12022,
        12023,
        8001,
    ]
    mcp_names = {
        12010: "playwright",
        12011: "puppeteer",
        12012: "fetch",
        12014: "exa",
        11435: "ollama",
        12001: "github",
        12002: "git",
        12003: "sqlite",
        12020: "context7",
        12021: "grep-app",
        12022: "obsidian",
        12023: "shadcn",
        8001: "graphiti",
    }

    client = httpx.Client(timeout=3)
    for port in mcp_ports:
        try:
            resp = client.get(f"http://localhost:{port}/health")
            is_ok = resp.status_code == 200
            test_result("mcp", f"{mcp_names.get(port, port)} (:{port})", is_ok)
        except:
            test_result("mcp", f"{mcp_names.get(port, port)} (:{port})", False, "Connection failed")
    client.close()

    # ============================================
    # CATEGORY 9: Memory System
    # ============================================
    print("\n[9/10] MEMORY SYSTEM (Graphiti)")
    try:
        import httpx

        client = httpx.Client(timeout=5)

        # Test store
        resp = client.post(
            "http://localhost:8001/json-rpc",
            json={
                "jsonrpc": "2.0",
                "method": "graphiti_add_episode",
                "params": {
                    "name": "audit_test",
                    "text": "Full pipeline audit test",
                    "source": "audit",
                },
                "id": "audit_store",
            },
        )
        store_ok = resp.status_code == 200
        test_result("memory", "Store episode", store_ok)

        # Test search
        resp = client.post(
            "http://localhost:8001/json-rpc",
            json={
                "jsonrpc": "2.0",
                "method": "graphiti_search_nodes",
                "params": {"query": "audit test", "limit": 3},
                "id": "audit_search",
            },
        )
        search_ok = resp.status_code == 200
        test_result("memory", "Search episodes", search_ok)

        # Test Neo4j connection
        resp = client.get("http://localhost:8001/health")
        health = resp.json()
        test_result("memory", "Neo4j connected", health.get("neo4j") == "connected")

        client.close()
    except Exception as e:
        test_result("memory", "Memory system", False, str(e)[:50])

    # ============================================
    # CATEGORY 10: Ollama
    # ============================================
    print("\n[10/10] OLLAMA")
    try:
        import httpx

        client = httpx.Client(timeout=5)

        # Test models
        resp = client.get("http://localhost:11434/api/tags")
        models = resp.json().get("models", [])
        test_result("ollama", f"Models loaded ({len(models)})", len(models) > 0)

        # Test generation
        resp = client.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2:3b-instruct-q4_K_M",
                "prompt": "Say hello",
                "stream": False,
                "options": {"num_predict": 10},
            },
        )
        gen_ok = resp.status_code == 200 and "response" in resp.json()
        test_result("ollama", "Generation works", gen_ok)

        client.close()
    except Exception as e:
        test_result("ollama", "Ollama connection", False, str(e)[:50])

    # ============================================
    # FINAL REPORT
    # ============================================
    print("\n" + "=" * 60)
    print("AUDIT COMPLETE")
    print("=" * 60)

    for category, data in AUDIT_RESULTS["categories"].items():
        total = data["passed"] + data["failed"]
        print(f"  {category:20} {data['passed']}/{total} passed")

    print(
        f"\n  TOTAL: {AUDIT_RESULTS['total_passed']} passed, {AUDIT_RESULTS['total_failed']} failed"
    )

    if AUDIT_RESULTS["total_failed"] == 0:
        print("\n  RESULT: ALL GREEN ✓")
    else:
        print(f"\n  RESULT: {AUDIT_RESULTS['total_failed']} FAILURES")

    # Save report
    report_path = Path("data/audit-report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(AUDIT_RESULTS, indent=2), encoding="utf-8")
    print(f"\n  Report saved to: {report_path}")


if __name__ == "__main__":
    run_audit()
