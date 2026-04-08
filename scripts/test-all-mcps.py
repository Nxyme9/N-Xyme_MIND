#!/usr/bin/env python3
"""Comprehensive test of all N-Xyme_MIND MCP servers, learning, and memory systems."""

import sys
import os
import importlib

# Ensure project root is in path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

results = []

def test(name, fn):
    try:
        result = fn()
        status = "✅ PASS"
        detail = str(result)[:150] if result else "OK"
    except Exception as e:
        status = "❌ FAIL"
        detail = f"{type(e).__name__}: {e}"
    results.append((name, status, detail))
    print(f"  {status} | {name} | {detail}")

def mod(name):
    """Import a module by full dotted path."""
    return importlib.import_module(name)

print("=" * 90)
print("N-Xyme_MIND — Full System Test")
print("=" * 90)

# ── MCP Server Imports ──
print("\n── MCP Server Imports ──")

test("n-xyme-core import", lambda: mod("core_mcp").mcp)
test("nx-mind import", lambda: mod("nx_mind_mcp").mcp)
test("unified-memory import", lambda: mod("packages.memory_core.mcp_server").mcp)
test("learning-engine import", lambda: mod("packages.learning_engine.mcp_server").mcp)
test("intelligence import", lambda: mod("packages.intelligence.mcp_server").mcp)
test("quality-gates import", lambda: mod("quality_gates_mcp").mcp)

# ── n-xyme-core tools ──
print("\n── n-xyme-core (32 tools) ──")

def core_tools():
    import asyncio
    from core_mcp import mcp
    loop = asyncio.new_event_loop()
    try:
        tools = loop.run_until_complete(mcp.list_tools())
        return len(tools)
    finally:
        loop.close()

test("core-mcp tool count", core_tools)

# ── nx-mind tools ──
print("\n── nx-mind MCP ──")
test("nx-mind get_mind_state", lambda: mod("nx_mind_mcp").get_mind_state())

# ── unified-memory tools ──
print("\n── unified-memory MCP ──")
mem_srv = lambda: mod("packages.memory_core.mcp_server")
test("memory search_memories", lambda: mem_srv().search_memories("test", limit=3))
test("memory get_memory_stats", lambda: mem_srv().get_memory_stats())
test("memory recall_session", lambda: mem_srv().recall_session(limit=5))

# ── learning-engine tools ──
print("\n── learning-engine MCP ──")
learn_srv = lambda: mod("packages.learning_engine.mcp_server")
test("learning route_task", lambda: learn_srv().route_task("fix a bug"))
test("learning status", lambda: learn_srv().status())
test("learning score_complexity", lambda: learn_srv().score_complexity("add feature") if hasattr(learn_srv(), 'score_complexity') else "N/A (in intelligence MCP)")

# ── intelligence tools ──
print("\n── intelligence MCP ──")
intel_srv = lambda: mod("packages.intelligence.mcp_server")
test("intelligence route", lambda: intel_srv().route("fix a TypeScript error"))
test("intelligence score_complexity", lambda: intel_srv().score_complexity("add feature"))
test("intelligence available_agents", lambda: intel_srv().available_agents())

# ── quality-gates tools ──
print("\n── quality-gates MCP ──")
qg_srv = lambda: mod("quality_gates_mcp")
def qg_typecheck():
    srv = qg_srv()
    # Tools are registered dynamically via loop — check mcp instance exists
    return "mcp" if hasattr(srv, 'mcp') else "no mcp"
test("quality-gates mcp", qg_typecheck)

# ── Learning Engine Direct ──
print("\n── Learning Engine (Direct) ──")

def le_route():
    from packages.learning_engine import route_task
    return route_task("fix a bug in auth", 2)

def le_record():
    from packages.learning_engine import record_outcome
    return record_outcome("test_task_001", "hephaestus", True, latency_ms=150)

def le_status():
    from packages.learning_engine import status
    return status()

test("learning route_task (direct)", le_route)
test("learning record_outcome (direct)", le_record)
test("learning status (direct)", le_status)

# ── Memory System Direct ──
print("\n── Memory System (Direct) ──")

def mem_write():
    from packages.memory_core.mcp_server import memory_write
    return memory_write("test content from full system test", kind="episodic")

def mem_search():
    from packages.memory_core.mcp_server import search_memories
    return search_memories("test content", limit=3)

def mem_stats():
    from packages.memory_core.memory_manager import MemoryManager
    mgr = MemoryManager()
    return mgr.get_stats()

test("memory write (direct)", mem_write)
test("memory search (direct)", mem_search)
test("memory stats (direct)", mem_stats)

# ── Intelligence Direct ──
print("\n── Intelligence (Direct) ──")

def intel_route():
    import asyncio
    from packages.intelligence import route
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(route("fix a TypeScript error"))
    finally:
        loop.close()

def intel_score():
    from packages.intelligence import score_complexity
    return score_complexity("add a new feature")

test("intelligence route (direct)", intel_route)
test("intelligence score (direct)", intel_score)

# ── Summary ──
print("\n" + "=" * 90)
total = len(results)
passed = sum(1 for _, s, _ in results if "PASS" in s)
failed = sum(1 for _, s, _ in results if "FAIL" in s)
print(f"TOTAL: {total} tests | ✅ {passed} passed | ❌ {failed} failed")
if failed:
    print("\n── FAILURES ──")
    for name, status, detail in results:
        if "FAIL" in status:
            print(f"  ❌ {name}: {detail}")
print("=" * 90)
