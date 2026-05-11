#!/usr/bin/env python3
"""N-Xyme Brain Bridge — single-entry dispatcher for oh-my-openagent hook."""
import sys
import json
import traceback
from typing import Any, Dict

PYTHONPATH_SET = False


def ensure_path():
    global PYTHONPATH_SET
    if not PYTHONPATH_SET:
        import os
        cwd = os.getcwd()
        if cwd not in sys.path:
            sys.path.insert(0, cwd)
        PYTHONPATH_SET = True


def search_memories(query: str, limit: int = 5) -> Dict[str, Any]:
    ensure_path()
    try:
        from packages.memory_store.mcp_server import search_memories as _sm
        result = _sm(query=query, top_k=limit)
        return {"results": result.get("results", []), "context": result}
    except Exception:
        return {"results": [], "context": None}


def route_task(task_description: str) -> Dict[str, Any]:
    ensure_path()
    try:
        from packages.nx_routing import route_task as _rt
        result = _rt(task_description)
        return {
            "status": "success",
            "agent": result.agent,
            "level": result.level,
            "confidence": result.confidence,
            "reason": result.reason,
            "strategy": result.strategy,
            "decisions_made": result.decisions_made,
        }
    except Exception:
        return {"status": "error", "agent": "build", "confidence": 0.5, "error": traceback.format_exc()}


def score_complexity(task_description: str) -> Dict[str, Any]:
    ensure_path()
    try:
        from packages.nx_routing import score_complexity as _sc
        result = _sc(task_description)
        return {
            "level": result.level,
            "tokens": result.tokens,
            "factors": result.factors,
        }
    except Exception:
        return {"level": 2, "tokens": 5000, "factors": {}, "error": traceback.format_exc()}


def inject_context(agent: str, task: str) -> Dict[str, Any]:
    ensure_path()
    try:
        from packages.context_store import inject_context as _ic
        result = _ic(context_type="all")
        return {"context": result.get("injected_context", "")}
    except Exception:
        return {"context": "", "error": traceback.format_exc()}


def log_outcome(task_id: str, agent: str, success: bool, latency_ms: float) -> Dict[str, Any]:
    ensure_path()
    try:
        from packages.learning_engine.outcome_logger import OutcomeLogger, DelegationOutcome
        outcome = DelegationOutcome(
            task_id=task_id,
            task_description="",
            task_type="delegation",
            agent=agent,
            level=3,
            success=success,
            latency_ms=latency_ms,
        )
        logger = OutcomeLogger()
        result = logger.log(outcome)
        return {"status": "success", "logged": result}
    except Exception:
        return {"status": "error", "error": traceback.format_exc()}


def record_pattern(pattern_type: str, outcome: Any) -> Dict[str, Any]:
    ensure_path()
    try:
        from packages.brain_mcp.namespaces.fingerprint import record_pattern as _rp
        return _rp(action_type=pattern_type, outcome=str(outcome))
    except Exception:
        return {"status": "error", "error": traceback.format_exc()}


DISPATCH: Dict[str, callable] = {
    "memory.search": lambda args: search_memories(args.get("task", "")),
    "learning.route_task": lambda args: route_task(args.get("task_description", "")),
    "intelligence.score_complexity": lambda args: score_complexity(args.get("task_description", "")),
    "fingerprint.inject_context": lambda args: inject_context(args.get("agent", ""), args.get("task", "")),
    "learning.log_outcome": lambda args: log_outcome(
        args.get("task_id", ""), args.get("agent", ""),
        args.get("success", True), args.get("latency_ms", 0.0)
    ),
    "fingerprint.record_pattern": lambda args: record_pattern(
        args.get("pattern_type", "tool_sequence"),
        args.get("outcome", "")
    ),
}


def dispatch(tool: str, args: Dict[str, Any]) -> Any:
    ensure_path()
    handler = DISPATCH.get(tool.lower())
    if handler:
        return handler(args)
    return {"error": f"unknown tool: {tool}"}


if __name__ == "__main__":
    try:
        data = json.load(sys.stdin)
        tool = data.get("tool", "")
        args = data.get("args", {})
        result = dispatch(tool, args)
        print(json.dumps(result))
    except Exception:
        print(json.dumps({"error": traceback.format_exc()}))
