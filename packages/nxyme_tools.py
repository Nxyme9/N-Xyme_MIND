#!/usr/bin/env python3
"""
N-Xyme Tools - Direct Python access to all N-Xyme capabilities.
Zero overhead - direct imports, no MCP, no JSON serialization.

Usage:
    from packages.nxyme_tools import think, remember, learn, route, context

    result = think("Hello, how are you?")
    results = remember("what did we do yesterday", limit=5)
    learn("task123", "success", 1500, 12000)
    routed = route("fix the auth bug")
    ctx = context("active")
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Setup paths for direct imports
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
packages_root = _project_root / "packages"
if str(packages_root) not in sys.path:
    sys.path.insert(0, str(packages_root))

# ============================================================================
# BRAIN - Local LLM with GGUF
# ============================================================================


def think(prompt: str, model: str = "auto", **kwargs) -> Dict[str, Any]:
    """Direct brain call - text completion.

    Args:
        prompt: The prompt/completion request
        model: Model to use (auto, qwen2.5-coder-7b, etc)
        **kwargs: Additional params (temperature, max_tokens, etc)

    Returns:
        Dict with {text, tokens, timing_ms}
    """
    try:
        from packages.local_llm.brain import get_brain

        brain = get_brain(default_model=model)
        return brain.complete(prompt, **kwargs)
    except Exception as e:
        return {"error": str(e), "text": "", "tokens": 0, "timing_ms": 0}


def chat(
    messages: List[Dict[str, str]], model: str = "auto", **kwargs
) -> Dict[str, Any]:
    """Direct brain call - chat completion.

    Args:
        messages: [{"role": "user", "content": "..."}, ...]
        model: Model to use
        **kwargs: Additional params

    Returns:
        Dict with {text, tokens, timing_ms, tool_calls}
    """
    try:
        from packages.local_llm.brain import get_brain

        brain = get_brain(default_model=model)
        return brain.chat(messages, **kwargs)
    except Exception as e:
        return {"error": str(e), "text": "", "tokens": 0, "timing_ms": 0}


def embed(text: str, model: str = "embed", **kwargs) -> Dict[str, Any]:
    """Direct brain call - embeddings.

    Args:
        text: Text to embed
        model: Embedding model (default: nomic-embed)
        **kwargs: Additional params

    Returns:
        Dict with {embedding: [...], dimensions: int}
    """
    try:
        from packages.local_llm.brain import get_brain

        brain = get_brain(default_model=model)
        return brain.embed(text, **kwargs)
    except Exception as e:
        return {"error": str(e), "embedding": [], "dimensions": 0}


def brain_status() -> Dict[str, Any]:
    """Get brain status - loaded models, GPU, etc."""
    try:
        from packages.local_llm.brain import get_brain

        brain = get_brain()
        return brain.get_status()
    except Exception as e:
        return {"error": str(e), "status": "unavailable"}


# ============================================================================
# MEMORY - Semantic search, episodic recall, context
# ============================================================================


def remember(
    query: str, limit: int = 10, strict: bool = False, rerank: bool = False
) -> Dict[str, Any]:
    """Search memory - semantic + episodic + session.

    Args:
        query: Search query
        limit: Max results
        strict: Strict matching
        rerank: Rerank results

    Returns:
        Dict with {results: [...], total: int}
    """
    try:
        from packages.memory_store import mcp_server as mem_mcp

        return mem_mcp.search_memories(query, limit, strict, rerank)
    except Exception as e:
        return {"error": str(e), "results": [], "total": 0}


def recall(limit: int = 50, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Recall session context.

    Args:
        limit: Max memories to recall
        session_id: Specific session (None = all)

    Returns:
        Dict with {sessions: [...], count: int}
    """
    try:
        from packages.memory_store import mcp_server as mem_mcp

        return mem_mcp.recall_session(session_id, limit)
    except Exception as e:
        return {"error": str(e), "sessions": [], "count": 0}


def memory_stats() -> Dict[str, Any]:
    """Get memory system statistics."""
    try:
        from packages.memory_store import mcp_server as mem_mcp

        return mem_mcp.get_memory_stats()
    except Exception as e:
        return {"error": str(e)}


def find_context(task: str, context_type: str = "all") -> Dict[str, Any]:
    """Find relevant context for a task.

    Args:
        task: Task description
        context_type: all, semantic, episodic, session

    Returns:
        Dict with {context: [...], sources: [...]}
    """
    try:
        from packages.memory_store import mcp_server as mem_mcp

        return mem_mcp.find_context(task, context_type)
    except Exception as e:
        return {"error": str(e), "context": [], "sources": []}


# ============================================================================
# LEARNING - Record outcomes, get recommendations
# ============================================================================


def learn(
    task: str, outcome: str, success: bool, latency_ms: int = 0, tokens_used: int = 0
) -> Dict[str, Any]:
    """Record delegation outcome for learning.

    Args:
        task: Task description
        outcome: "success" or "failed"
        success: Boolean success status
        latency_ms: Execution time
        tokens_used: Tokens consumed

    Returns:
        Dict with {recorded: bool}
    """
    try:
        from packages.learning_engine import record_outcome

        return record_outcome(task, success, latency_ms, tokens_used)
    except Exception as e:
        return {"error": str(e), "recorded": False}


def recommend(task: str) -> Dict[str, Any]:
    """Get agent recommendations for a task.

    Args:
        task: Task description

    Returns:
        Dict with {agents: [...], recommended: str, confidence: float}
    """
    try:
        from packages.learning_engine import get_recommendations

        return get_recommendations(task)
    except Exception as e:
        return {"error": str(e), "agents": [], "recommended": None}


def learning_status() -> Dict[str, Any]:
    """Get learning system status."""
    try:
        from packages.learning_engine import status

        return status()
    except Exception as e:
        return {"error": str(e), "status": "unavailable"}


# ============================================================================
# ROUTING - Intelligence, complexity scoring
# ============================================================================


def route(task_description: str) -> Dict[str, Any]:
    """Route task to optimal agent.

    Args:
        task_description: What needs to be done

    Returns:
        Dict with {agent: str, level: int, strategy: str}
    """
    try:
        from packages.learning_engine import route_task

        return route_task(task_description)
    except Exception as e:
        return {"error": str(e), "agent": "hephaestus", "level": 3}


def score_complexity(task_description: str) -> Dict[str, Any]:
    """Score task complexity (L1-L5).

    Args:
        task_description: Task to score

    Returns:
        Dict with {level: int, complexity: str, confidence: float}
    """
    try:
        from packages.intelligence import score_complexity

        return score_complexity(task_description)
    except Exception as e:
        return {"error": str(e), "level": 3, "complexity": "moderate"}


# ============================================================================
# CONTEXT - Active, product, user, constraints, BMAD
# ============================================================================


def context(context_type: str = "active") -> Dict[str, Any]:
    """Get context by type.

    Args:
        context_type: active, product, user, constraints, style, archive, bmad_agents, bmad_workflows

    Returns:
        Dict with context data
    """
    try:
        from packages.context_store import (
            get_active_context,
            get_product_context,
            get_user_context,
            get_constraints,
            get_style_context,
            get_archive_context,
            get_bmad_agents,
            get_bmad_workflows,
        )

        type_map = {
            "active": get_active_context,
            "product": get_product_context,
            "user": get_user_context,
            "constraints": get_constraints,
            "style": get_style_context,
            "archive": get_archive_context,
            "bmad_agents": get_bmad_agents,
            "bmad_workflows": get_bmad_workflows,
        }

        func = type_map.get(context_type, get_active_context)
        return func()
    except Exception as e:
        return {"error": str(e), "context_type": context_type}


def inject_context(
    context_type: str = "all", output_path: Optional[str] = None
) -> Dict[str, Any]:
    """Inject context into session.

    Args:
        context_type: What to inject
        output_path: Optional output file

    Returns:
        Dict with {injected: bool, tokens: int}
    """
    try:
        from packages.context_store import inject_context

        return inject_context(context_type, output_path)
    except Exception as e:
        return {"error": str(e), "injected": False}


# ============================================================================
# MIND - State, history, workflows
# ============================================================================


def mind_state() -> Dict[str, Any]:
    """Get current mind state."""
    try:
        from packages.nx_mind_mcp.nx_mind_mcp import get_mind_state

        return get_mind_state()
    except Exception as e:
        return {"error": str(e), "phase": None, "project": None}


def update_mind(
    phase: Optional[str] = None,
    project: Optional[str] = None,
    active_tasks: Optional[List[str]] = None,
    context: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Update mind state.

    Args:
        phase: Current phase
        project: Current project
        active_tasks: List of active task IDs
        context: Additional context

    Returns:
        Dict with {updated: bool}
    """
    try:
        from packages.nx_mind_mcp.nx_mind_mcp import update_mind_state

        return update_mind_state(
            phase=phase, project=project, active_tasks=active_tasks, context=context
        )
    except Exception as e:
        return {"error": str(e), "updated": False}


def session_history(limit: int = 10) -> Dict[str, Any]:
    """Get session history.

    Args:
        limit: Max sessions

    Returns:
        Dict with {sessions: [...], count: int}
    """
    try:
        from packages.nx_mind_mcp.nx_mind_mcp import get_session_history

        return get_session_history(limit)
    except Exception as e:
        return {"error": str(e), "sessions": [], "count": 0}


# ============================================================================
# CATALYST - Orchestration, workflow execution
# ============================================================================


def orchestrate(user_input: str, context: Optional[Dict] = None) -> Dict[str, Any]:
    """Orchestrate BMAD workflow.

    Args:
        user_input: What the user wants
        context: Optional context

    Returns:
        Dict with {workflow: str, state: str, result: dict}
    """
    try:
        from packages.catalyst_orchestrator import orchestrate as _orch

        return _orch(user_input, context)
    except Exception as e:
        return {"error": str(e), "workflow": None, "state": "error"}


def detect_state(user_input: str) -> Dict[str, Any]:
    """Detect user state (FLOW, FRICTION, ADAPT).

    Args:
        user_input: User's message

    Returns:
        Dict with {state: str, confidence: float}
    """
    try:
        from packages.catalyst_orchestrator import detect_state as _detect

        return _detect(user_input)
    except Exception as e:
        return {"error": str(e), "state": "unknown", "confidence": 0.0}


def list_workflows() -> Dict[str, Any]:
    """List available BMAD workflows."""
    try:
        from packages.catalyst_orchestrator import list_workflows

        return list_workflows()
    except Exception as e:
        return {"error": str(e), "workflows": []}


# ============================================================================
# TRIGGERS - Command triggers
# ============================================================================


def register_trigger(
    phrase: str, handler: str = "callback", description: str = ""
) -> Dict[str, Any]:
    """Register a command trigger.

    Args:
        phrase: Trigger phrase (e.g., "/deploy")
        handler: callback, skill, function
        description: What it does

    Returns:
        Dict with {registered: bool}
    """
    try:
        from packages.trigger_guardian_mcp.trigger_guardian_mcp import (
            register_trigger as _reg,
        )

        return _reg(phrase, description, handler, "")
    except Exception as e:
        return {"error": str(e), "registered": False}


def list_triggers() -> Dict[str, Any]:
    """List all registered triggers."""
    try:
        from packages.trigger_guardian_mcp.trigger_guardian_mcp import list_triggers

        return list_triggers()
    except Exception as e:
        return {"error": str(e), "triggers": []}


def check_trigger(input_text: str) -> Dict[str, Any]:
    """Check if input matches any trigger.

    Args:
        input_text: Text to check

    Returns:
        Dict with {matched: bool, trigger: str}
    """
    try:
        from packages.trigger_guardian_mcp.trigger_guardian_mcp import (
            check_trigger as _check,
        )

        return _check(input_text)
    except Exception as e:
        return {"error": str(e), "matched": False}


# ============================================================================
# HEALTH - System health check
# ============================================================================


def health() -> Dict[str, Any]:
    """Full system health check.

    Returns:
        Dict with {brain, memory, context, learning, mind, triggers, catalyst}
    """
    return {
        "brain": brain_status(),
        "memory": memory_stats(),
        "context": context("active"),
        "learning": learning_status(),
        "mind": mind_state(),
        "triggers": list_triggers(),
    }


# ============================================================================
# Convenience aliases
# ============================================================================

# Shorthand aliases
t = think
r = remember
c = context
l = learn
route_task = route  # Alias for clarity
get_rec = recommend  # Alias for clarity

__all__ = [
    # Brain
    "think",
    "chat",
    "embed",
    "brain_status",
    # Memory
    "remember",
    "recall",
    "memory_stats",
    "find_context",
    # Learning
    "learn",
    "recommend",
    "learning_status",
    # Routing
    "route",
    "score_complexity",
    # Context
    "context",
    "inject_context",
    # Mind
    "mind_state",
    "update_mind",
    "session_history",
    # Catalyst
    "orchestrate",
    "detect_state",
    "list_workflows",
    # Triggers
    "register_trigger",
    "list_triggers",
    "check_trigger",
    # Health
    "health",
    # Aliases
    "t",
    "r",
    "c",
    "l",
    "route_task",
    "get_rec",
]
