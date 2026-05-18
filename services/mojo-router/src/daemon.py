#!/usr/bin/env python3
"""
Mojo Router Daemon - Python Implementation
Stories 1.1-1.4: Startup, TF-IDF Routing, Error Handling, Metrics
"""

import json
import sys
import time

# =========================================================================
# TOOL LEXICON - 25 tools loaded at startup
# =========================================================================
TOOL_NAMES = [
    "session_start", "session_status", "continue_session", "welcome_back",
    "next_step", "memory_write", "memory_read", "memory_list", "context_prune",
    "audit_log_recent", "ralph_start", "ralph_status", "ralph_iterate", "ralph_cancel",
    "delegate_to_hephaestus", "project_map", "batch_read",
    "code_verify", "safe_delete", "trash_restore", "hephaestus_new_task",
    "ask", "decision_log", "delegate_task"
]

TOOL_DESCS = [
    "Start/resume session. Returns streak, XP, achievements.",
    "Session state: calls, memory, loops, context %.",
    "Resume last active loop. No IDs needed.",
    "Warm session restore: streak, XP, last task.",
    "ONE next action suggestion. Never a list.",
    "Store key-value in session. >500 chars needs confirm.",
    "Read a value by key.",
    "List all memory keys in session.",
    "Smart compaction by agent type. Dry-run available.",
    "Recent tool calls for session.",
    "Start iterative loop. Persists across restarts.",
    "Check loop iteration, max, active.",
    "Advance loop. Returns cont, pct, est. remaining.",
    "Cancel active loop.",
    "Inject dictated text. REQUIRES confirm:true.",
    "Delegate code task to Hephaestus.",
    "Project structure: dirs, files, depth-limited.",
    "Read multiple files in one call.",
    "Run quality gates: fmt, lint, test, audit.",
    "Move to data/trash/ instead of permanent rm.",
    "List/restore trashed files.",
    "Parallel-worker-safe fresh task. Prunes old context.",
    "NL entry: say what you need, tool routes automatically.",
    "Save design decision with rationale.",
    "Delegate task to another agent via shared memory."
]

# =========================================================================
# METRICS STORAGE
# =========================================================================
routing_history = []
last_100_confidences = []

def do_route(query: str) -> tuple[str, float]:
    """TF-IDF-based routing to best matching tool"""
    best_score = 0.0
    second_best_score = 0.0
    best_tool = ""
    
    q = query.lower()
    terms = q.split()
    
    # FIX: Remove unused enumerate index
    for name, desc in zip(TOOL_NAMES, TOOL_DESCS):
        score = 0.0
        desc_lower = desc.lower()
        
        for term in terms:
            if len(term) < 2:
                continue
            # Count occurrences in description
            count = desc_lower.count(term)
            if count > 0:
                score += 1.0 + count * 0.5 / (count + 1.0)
        
        # Bonus for exact name match
        if name in q:
            score += 5.0
        
        # Bonus for partial name match
        for term in terms:
            if term in name and len(term) >= 2:
                score += 4.0
        
        if score > best_score:
            second_best_score = best_score
            best_score = score
            best_tool = name
        elif score > second_best_score:
            second_best_score = score
    
    # Calculate confidence
    confidence = 0.0
    if best_score > 0.0:
        confidence = best_score / 20.0
        if second_best_score > 0.0:
            margin = (best_score - second_best_score) / best_score
            confidence += margin * 0.3
        else:
            confidence += 0.3
        confidence = min(confidence, 1.0)
    
    return best_tool, confidence

def get_percentile(data: list, percentile: float) -> float:
    """Calculate percentile from sorted data"""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = int((percentile / 100.0) * (len(sorted_data) - 1))
    return sorted_data[min(idx, len(sorted_data) - 1)]

def check_warn():
    """Log warning if low confidence >= 10%"""
    if len(last_100_confidences) < 10:
        return
    low_conf = sum(1 for c in last_100_confidences if c < 0.5)
    ratio = low_conf / len(last_100_confidences)
    if ratio >= 0.1:
        print(f"[WARNING] Low confidence rate: {int(ratio*100)}% ({low_conf}/{len(last_100_confidences)}) in recent queries", 
              file=sys.stderr)

def main():
    """Main daemon loop"""
    # FIX: Dynamic tool count instead of hardcoded
    tools_loaded = len(TOOL_NAMES)
    
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        
        # Parse JSON
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            # FIX: Add flush=True
            print(json.dumps({"type": "error", "message": "parse error", "id": "0"}), flush=True)
            continue
        
        msg_type = data.get("type", "")
        query = data.get("query", "")
        id_val = data.get("id", "0")
        
        # Story 1.1: Status
        if msg_type == "status":
            print(json.dumps({
                "type": "status_result",
                "running": True,
                "tools_loaded": tools_loaded,
                "id": id_val
            }), flush=True)
        
        # Story 1.2: Route
        elif msg_type == "route":
            if not query:
                print(json.dumps({
                    "type": "error",
                    "code": "EMPTY_QUERY",
                    "id": id_val
                }), flush=True)
                continue
            
            start = time.perf_counter()
            tool, confidence = do_route(query)
            latency_us = (time.perf_counter() - start) * 1_000_000
            
            # Log routing
            timestamp = int(time.perf_counter() * 1_000_000)
            print(f"[ROUTE] {timestamp}|{tool}|{confidence}|{int(latency_us)} us", file=sys.stderr)
            
            # Store metrics
            routing_history.append(latency_us)
            if len(routing_history) > 1000:
                routing_history.pop(0)
            
            last_100_confidences.append(confidence)
            if len(last_100_confidences) > 100:
                last_100_confidences.pop(0)
            
            check_warn()
            
            print(json.dumps({
                "type": "route_result",
                "tool": tool,
                "confidence": round(confidence, 2),
                "latency_us": int(latency_us),
                "id": id_val
            }), flush=True)
        
        # Story 1.4: Metrics
        elif msg_type == "metrics":
            count = len(routing_history)
            p50 = get_percentile(routing_history, 50)
            p95 = get_percentile(routing_history, 95)
            p99 = get_percentile(routing_history, 99)
            
            print(json.dumps({
                "type": "metrics_result",
                "p50": int(p50),
                "p95": int(p95),
                "p99": int(p99),
                "count": count,
                "id": id_val
            }), flush=True)
        
        # Unknown type
        else:
            print(json.dumps({
                "type": "error",
                "code": "UNKNOWN_TYPE",
                "id": id_val
            }), flush=True)

if __name__ == "__main__":
    main()
