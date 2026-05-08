"""
trigger-guardian-mcp
====================
MCP Tool Server for trigger phrase monitoring and routing.
Enables workflow initiation and agent handoff detection.

Transport: stdio (default), SSE (optional via --sse flag).
"""

from __future__ import annotations

import json
import logging
import os
import re
import signal
import time
from collections import defaultdict
from concurrent import futures
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Callable, Dict, List, Optional

from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Timeout Configuration
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUTS = {
    "brain:think": 30.0,
    "brain:embed": 10.0,
    "brain:rosetta": 15.0,
}

TIMEOUTS = {
    "brain:think": float(
        os.environ.get("BRAIN_THINK_TIMEOUT", DEFAULT_TIMEOUTS["brain:think"])
    ),
    "brain:embed": float(
        os.environ.get("BRAIN_EMBED_TIMEOUT", DEFAULT_TIMEOUTS["brain:embed"])
    ),
    "brain:rosetta": float(
        os.environ.get("BRAIN_ROSETTA_TIMEOUT", DEFAULT_TIMEOUTS["brain:rosetta"])
    ),
}

# ---------------------------------------------------------------------------
# Server Init
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="trigger-guardian",
    version="1.0.0",
    instructions=(
        "Trigger Guardian MCP Server — monitor and route trigger phrases.\n\n"
        "Tools:\n"
        "- register_trigger: Register a trigger phrase with callback action\n"
        "- list_triggers: List all registered triggers\n"
        "- check_trigger: Check if input matches any registered trigger\n"
        "- get_trigger_handlers: Return handlers for a matched trigger\n"
        "- log_trigger_event: Log trigger activation for analytics\n"
        "- clear_triggers: Clear all registered triggers\n"
    ),
)

logger = logging.getLogger("trigger-guardian-mcp")

# ---------------------------------------------------------------------------
# Rate Limiter System
# ---------------------------------------------------------------------------


class RateLimiter:
    """Token bucket rate limiter for trigger registration."""

    def __init__(self, max_calls: int = 10, window_seconds: float = 60.0):
        self._max_calls = max_calls
        self._window = window_seconds
        self._calls: dict = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, caller_id: str) -> tuple[bool, dict]:
        """Check if caller is within rate limit.

        Returns: (allowed: bool, info: dict)
        """
        with self._lock:
            now = time.time()
            self._calls[caller_id] = [
                t for t in self._calls[caller_id] if now - t < self._window
            ]

            if len(self._calls[caller_id]) >= self._max_calls:
                return False, {
                    "allowed": False,
                    "calls_in_window": len(self._calls[caller_id]),
                    "max_calls": self._max_calls,
                    "window_seconds": self._window,
                    "retry_after": self._window - (now - self._calls[caller_id][0])
                    if self._calls[caller_id]
                    else 0,
                }

            self._calls[caller_id].append(now)
            return True, {
                "allowed": True,
                "calls_in_window": len(self._calls[caller_id]),
                "max_calls": self._max_calls,
            }

    def get_caller_id(self, phrase: str = None) -> str:
        """Generate caller ID for rate limiting."""
        return "default"


# ---------------------------------------------------------------------------
# Callback Executor System
# ---------------------------------------------------------------------------


class CallbackExecutor:
    """Executes callbacks for trigger handlers with timeout protection."""

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._timeouts = TIMEOUTS.copy()
        self._register_default_handlers()

    def set_timeout(self, handler_name: str, seconds: float):
        """Override timeout for a specific handler."""
        if handler_name in self._timeouts:
            self._timeouts[handler_name] = max(1.0, min(300.0, seconds))

    def _execute_with_timeout(
        self, handler_name: str, func: Callable, args: dict = None
    ) -> dict:
        """Execute handler with timeout protection."""
        timeout = self._timeouts.get(handler_name, 30.0)

        try:
            old_handler = signal.signal(
                signal.SIGALRM, self._timeout_handler(handler_name, timeout)
            )
            signal.alarm(int(timeout))
            try:
                result = func(args) if args else func()
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
        except (AttributeError, OSError):
            with futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, args) if args else executor.submit(func)
                try:
                    result = future.result(timeout=timeout)
                except futures.TimeoutError:
                    logger.warning(
                        f"HANDLER_TIMEOUT: {handler_name} exceeded {timeout}s"
                    )
                    return {
                        "success": False,
                        "error": f"Handler timed out after {timeout} seconds",
                        "handler": handler_name,
                        "timeout": timeout,
                    }
        except TimeoutError as e:
            logger.warning(f"HANDLER_TIMEOUT: {handler_name} - {e}")
            return {
                "success": False,
                "error": str(e),
                "handler": handler_name,
                "timeout": timeout,
            }

        return result

    def _timeout_handler(self, handler_name: str, timeout: float):
        """Create timeout handler for signal-based timeout."""

        def handler(signum, frame):
            raise TimeoutError(f"Handler {handler_name} timed out after {timeout}s")

        return handler

    def _register_default_handlers(self):
        """Register default callback handlers."""
        # Import Brain lazily to avoid circular imports
        try:
            from packages.local_llm.brain import Brain

            self._brain_instance = Brain()

            # Register brain handlers
            self._handlers["brain:think"] = self._handle_brain_think
            self._handlers["brain:embed"] = self._handle_brain_embed
            self._handlers["brain:rosetta"] = self._handle_brain_rosetta
            logger.info("Registered brain callback handlers")
        except ImportError as e:
            logger.warning(f"Could not import Brain: {e}")

    def _handle_brain_think(self, args: dict) -> dict:
        """Execute brain.think() callback with timeout."""
        prompt = args.get("prompt", "")
        mode = args.get("mode", "fast")

        if not prompt:
            return {"error": "prompt is required"}
        if len(prompt) > 10000:
            return {"error": "prompt exceeds maximum length (10000 chars)"}

        def _do_think():
            result = self._brain_instance.think(prompt, mode=mode)
            return {
                "success": True,
                "response": result.get("response"),
                "model_used": result.get("model_used"),
                "timing_ms": result.get("timing_ms"),
            }

        return self._execute_with_timeout("brain:think", _do_think)

    def _handle_brain_embed(self, args: dict) -> dict:
        """Execute brain.embed_text() callback with timeout."""
        text = args.get("text", "")

        if not text:
            return {"error": "text is required"}
        if len(text) > 50000:
            return {"error": "text exceeds maximum length (50000 chars)"}

        def _do_embed():
            result = self._brain_instance.embed_text(text)
            return {
                "success": True,
                "embedding": result.get("embedding"),
                "dimension": len(result.get("embedding", [])),
                "timing_ms": result.get("timing_ms"),
            }

        return self._execute_with_timeout("brain:embed", _do_embed)

    def _handle_brain_rosetta(self, args: dict) -> dict:
        """Execute brain.process_trigger() callback with timeout."""
        user_input = args.get("input", "")

        if not user_input:
            return {"error": "input is required"}
        if len(user_input) > 5000:
            return {"error": "input exceeds maximum length (5000 chars)"}

        def _do_rosetta():
            result = self._brain_instance.process_trigger(user_input)
            return {
                "success": True,
                "type": result.get("type"),
                "action": result.get("action"),
                "args": result.get("args"),
                "confidence": result.get("confidence"),
            }

        return self._execute_with_timeout("brain:rosetta", _do_rosetta)

    def execute(self, handler_target: str, args: dict = None) -> dict:
        """Execute a callback handler.

        Args:
            handler_target: The handler identifier (e.g., "brain:think")
            args: Arguments to pass to the handler

        Returns:
            Result from the handler
        """
        args = args or {}

        # Direct handler lookup
        if handler_target in self._handlers:
            return self._handlers[handler_target](args)

        # Skill handler (would invoke skill system)
        if handler_target.startswith("skill:"):
            skill_name = handler_target[6:]
            return {
                "success": False,
                "error": f"Skill handler '{skill_name}' not implemented",
                "handler": "skill",
            }

        # MCP handler (would invoke MCP tool)
        if ":" in handler_target:
            return {
                "success": False,
                "error": f"MCP handler '{handler_target}' not implemented",
                "handler": "mcp",
            }

        return {
            "success": False,
            "error": f"Unknown handler: {handler_target}",
        }

    def get_available_handlers(self) -> list:
        """Get list of available handlers."""
        return list(self._handlers.keys())

    def get_handler_status(self) -> dict:
        """Get status of all handlers including timeout configuration."""
        return {
            "available_handlers": list(self._handlers.keys()),
            "timeouts": self._timeouts.copy(),
            "timeout_unit": "seconds",
        }


# Global callback executor
_callback_executor = CallbackExecutor()


# ---------------------------------------------------------------------------
# In-Memory Trigger Registry
# ---------------------------------------------------------------------------


class TriggerRegistry:
    """In-memory registry for trigger phrases and their handlers."""

    def __init__(self):
        self._triggers: Dict[str, dict] = {}
        self._event_log: List[dict] = {}
        self._rate_limiter = RateLimiter(max_calls=10, window_seconds=60.0)
        self._total_registrations = 0
        self._max_triggers_per_registry = 50
        self._load_defaults()

    def _load_defaults(self):
        """Load default triggers from built-in patterns."""
        defaults = [
            {
                "phrase": "/start-work",
                "description": "Start a new work session",
                "handler": "skill",
                "handler_target": "start-work",
                "pattern_type": "exact",
            },
            {
                "phrase": "/handoff",
                "description": "Hand off to another agent/session",
                "handler": "skill",
                "handler_target": "handoff",
                "pattern_type": "exact",
            },
            {
                "phrase": "/git-master",
                "description": "Git operations with master workflow",
                "handler": "skill",
                "handler_target": "git-master",
                "pattern_type": "exact",
            },
            {
                "phrase": "/refactor",
                "description": "Intelligent refactoring command",
                "handler": "skill",
                "handler_target": "refactor",
                "pattern_type": "exact",
            },
            {
                "phrase": "/playwright",
                "description": "Browser automation with Playwright",
                "handler": "skill",
                "handler_target": "playwright",
                "pattern_type": "exact",
            },
            {
                "phrase": "/dev-browser",
                "description": "Persistent browser automation",
                "handler": "skill",
                "handler_target": "dev-browser",
                "pattern_type": "exact",
            },
            # BMAD Workflow Triggers
            {
                "phrase": "/catalyst",
                "description": "Execute BMAD workflow via Catalyst orchestrator",
                "handler": "mcp",
                "handler_target": "catalyst:orchestrate",
                "pattern_type": "prefix",
            },
            {
                "phrase": "/document",
                "description": "Generate documentation via BMAD",
                "handler": "mcp",
                "handler_target": "catalyst:execute_workflow",
                "pattern_type": "prefix",
            },
            {
                "phrase": "/test",
                "description": "Generate tests via BMAD",
                "handler": "mcp",
                "handler_target": "catalyst:execute_workflow",
                "pattern_type": "prefix",
            },
            {
                "phrase": "/sprint",
                "description": "Run sprint planning via BMAD",
                "handler": "mcp",
                "handler_target": "catalyst:execute_workflow",
                "pattern_type": "prefix",
            },
            {
                "phrase": "/memory",
                "description": "Execute memory workflow via BMAD",
                "handler": "mcp",
                "handler_target": "catalyst:execute_workflow",
                "pattern_type": "prefix",
            },
            {
                "phrase": "/resilience",
                "description": "Execute resilience workflow via BMAD",
                "handler": "mcp",
                "handler_target": "catalyst:execute_workflow",
                "pattern_type": "prefix",
            },
            # Brain/LLM Triggers
            {
                "phrase": "/brain",
                "description": "Execute local brain (direct GGUF, zero overhead)",
                "handler": "callback",
                "handler_target": "brain:think",
                "pattern_type": "prefix",
            },
            # BMAD Main Trigger - List all workflows (CHANGED to prefix for flexibility)
            {
                "phrase": "/bmad",
                "description": "List and select BMAD workflows (Analysis, Planning, Solutioning, Implementation)",
                "handler": "mcp",
                "handler_target": "orchestration:list_workflows",
                "pattern_type": "prefix",  # Changed from "exact" - now matches /bmad anything
            },
            # BMAD Workflow Triggers - Full Integration
            {
                "phrase": "/audit",
                "description": "Run audit workflow via BMAD",
                "handler": "mcp",
                "handler_target": "catalyst:execute_workflow",
                "pattern_type": "prefix",
            },
            {
                "phrase": "/retro",
                "description": "Run sprint retrospective via BMAD",
                "handler": "mcp",
                "handler_target": "catalyst:execute_workflow",
                "pattern_type": "prefix",
            },
            {
                "phrase": "/sprint",
                "description": "Run sprint planning/status via BMAD",
                "handler": "mcp",
                "handler_target": "catalyst:execute_workflow",
                "pattern_type": "prefix",
            },
            {
                "phrase": "/brainstorm",
                "description": "Run brainstorming session via BMAD",
                "handler": "mcp",
                "handler_target": "catalyst:execute_workflow",
                "pattern_type": "prefix",
            },
            {
                "phrase": "/party",
                "description": "Run multi-agent group discussion via BMAD",
                "handler": "mcp",
                "handler_target": "catalyst:execute_workflow",
                "pattern_type": "prefix",
            },
            {
                "phrase": "/prd",
                "description": "Create or edit PRD via BMAD",
                "handler": "mcp",
                "handler_target": "catalyst:execute_workflow",
                "pattern_type": "prefix",
            },
            {
                "phrase": "/design",
                "description": "Run design thinking or UX design via BMAD",
                "handler": "mcp",
                "handler_target": "catalyst:execute_workflow",
                "pattern_type": "prefix",
            },
            {
                "phrase": "/epic",
                "description": "Create epics and stories via BMAD",
                "handler": "mcp",
                "handler_target": "catalyst:execute_workflow",
                "pattern_type": "prefix",
            },
            {
                "phrase": "/test",
                "description": "Run test architecture/design via BMAD",
                "handler": "mcp",
                "handler_target": "catalyst:execute_workflow",
                "pattern_type": "prefix",
            },
            {
                "phrase": "/research",
                "description": "Run market or technical research via BMAD",
                "handler": "mcp",
                "handler_target": "catalyst:execute_workflow",
                "pattern_type": "prefix",
            },
            {
                "phrase": "/memory",
                "description": "Recall memory or context via BMAD",
                "handler": "mcp",
                "handler_target": "catalyst:execute_workflow",
                "pattern_type": "prefix",
            },
            {
                "phrase": "/context",
                "description": "Get project context via BMAD",
                "handler": "mcp",
                "handler_target": "catalyst:execute_workflow",
                "pattern_type": "prefix",
            },
            {
                "phrase": "/arch",
                "description": "Run architecture design via BMAD",
                "handler": "mcp",
                "handler_target": "catalyst:execute_workflow",
                "pattern_type": "prefix",
            },
            {
                "phrase": "/quick-dev",
                "description": "Run quick development via BMAD",
                "handler": "mcp",
                "handler_target": "catalyst:execute_workflow",
                "pattern_type": "prefix",
            },
            {
                "phrase": "/story",
                "description": "Create or implement story via BMAD",
                "handler": "mcp",
                "handler_target": "catalyst:execute_workflow",
                "pattern_type": "prefix",
            },
            # Natural Language Triggers (no / prefix needed)
            {
                "phrase": "run audit",
                "description": "Run audit workflow",
                "handler": "mcp",
                "handler_target": "catalyst:execute_workflow",
                "pattern_type": "contains",
            },
            {
                "phrase": "sprint retrospective",
                "description": "Run sprint retrospective",
                "handler": "mcp",
                "handler_target": "catalyst:execute_workflow",
                "pattern_type": "contains",
            },
            {
                "phrase": "brainstorm",
                "description": "Run brainstorming session",
                "handler": "mcp",
                "handler_target": "catalyst:execute_workflow",
                "pattern_type": "contains",
            },
            {
                "phrase": "create prd",
                "description": "Create product requirements document",
                "handler": "mcp",
                "handler_target": "catalyst:execute_workflow",
                "pattern_type": "contains",
            },
            {
                "phrase": "run design thinking",
                "description": "Run design thinking session",
                "handler": "mcp",
                "handler_target": "catalyst:execute_workflow",
                "pattern_type": "contains",
            },
            {
                "phrase": "plan the sprint",
                "description": "Run sprint planning",
                "handler": "mcp",
                "handler_target": "catalyst:execute_workflow",
                "pattern_type": "contains",
            },
            {
                "phrase": "/embed",
                "description": "Generate embeddings using local brain (1.67x faster than Ollama)",
                "handler": "callback",
                "handler_target": "brain:embed",
                "pattern_type": "prefix",
            },
            {
                "phrase": "/rosetta",
                "description": "Translate natural language to tool calls (local 0.5B model)",
                "handler": "callback",
                "handler_target": "brain:rosetta",
                "pattern_type": "prefix",
            },
        ]

        for trigger in defaults:
            self.register(
                phrase=trigger["phrase"],
                description=trigger["description"],
                handler=trigger["handler"],
                handler_target=trigger["handler_target"],
                pattern_type=trigger["pattern_type"],
            )

    def register(
        self,
        phrase: str,
        description: str = "",
        handler: str = "callback",
        handler_target: str = "",
        pattern_type: str = "exact",
    ) -> dict:
        """Register a new trigger phrase."""
        allowed, info = self._rate_limiter.is_allowed(
            self._rate_limiter.get_caller_id(phrase)
        )
        if not allowed:
            logger.warning(f"REGISTRATION_RATE_LIMITED: {info}")
            return {
                "success": False,
                "error": "Rate limit exceeded. Try again later.",
                "retry_after": info.get("retry_after", 60),
                "rate_limit_info": info,
            }

        if len(self._triggers) >= self._max_triggers_per_registry:
            logger.warning(f"REGISTRY_FULL: {len(self._triggers)} triggers registered")
            return {
                "success": False,
                "error": f"Maximum triggers ({self._max_triggers_per_registry}) reached",
            }

        if phrase in self._triggers:
            return {
                "success": False,
                "error": f"Trigger '{phrase}' already registered",
                "phrase": phrase,
            }

        if not phrase or len(phrase) < 2:
            return {"success": False, "error": "Phrase too short (min 2 chars)"}
        if len(phrase) > 200:
            return {"success": False, "error": "Phrase too long (max 200 chars)"}

        if pattern_type == "regex":
            try:
                re.compile(phrase)
            except re.error as e:
                return {"success": False, "error": f"Invalid regex: {e}"}

        self._triggers[phrase] = {
            "phrase": phrase,
            "description": description[:500] if description else "",
            "handler": handler,
            "handler_target": handler_target[:200] if handler_target else "",
            "pattern_type": pattern_type,
            "registered_at": datetime.now().isoformat(),
            "trigger_count": 0,
            "last_triggered": None,
        }
        self._total_registrations += 1

        return {"success": True, "phrase": phrase, "registered": True}

    def list_all(self) -> dict:
        """List all registered triggers."""
        return {
            "triggers": list(self._triggers.values()),
            "count": len(self._triggers),
            "timestamp": datetime.now().isoformat(),
        }

    def get_rate_limit_status(self) -> dict:
        """Get current rate limit status."""
        allowed, info = self._rate_limiter.is_allowed(
            self._rate_limiter.get_caller_id()
        )
        return {
            "within_limit": allowed,
            "total_triggers": len(self._triggers),
            "total_registrations": self._total_registrations,
            **info,
        }

    def check(self, input_text: str) -> dict:
        """Check if input matches any registered trigger."""
        matched = None

        for phrase, trigger in self._triggers.items():
            pattern_type = trigger.get("pattern_type", "exact")

            if pattern_type == "exact":
                if input_text.strip() == phrase:
                    matched = trigger
                    break
            elif pattern_type == "prefix":
                if input_text.strip().startswith(phrase):
                    matched = trigger
                    break
            elif pattern_type == "regex":
                try:
                    if re.search(phrase, input_text):
                        matched = trigger
                        break
                except re.error:
                    pass
            elif pattern_type == "contains":
                if phrase.lower() in input_text.lower():
                    matched = trigger
                    break

        result = {
            "input": input_text,
            "matched": matched is not None,
            "trigger": None,
            "timestamp": datetime.now().isoformat(),
        }

        if matched:
            result["trigger"] = matched
            # Update trigger stats
            matched["trigger_count"] += 1
            matched["last_triggered"] = datetime.now().isoformat()

        return result

    def get_handlers(self, phrase: str) -> dict:
        """Get handlers for a specific trigger phrase."""
        trigger = self._triggers.get(phrase)

        if not trigger:
            return {
                "found": False,
                "phrase": phrase,
                "error": f"Trigger '{phrase}' not found",
            }

        return {
            "found": True,
            "phrase": phrase,
            "handler": trigger.get("handler"),
            "handler_target": trigger.get("handler_target"),
            "description": trigger.get("description"),
        }

    def log_event(self, phrase: str, input_text: str, metadata: dict = None) -> dict:
        """Log a trigger activation event."""
        event = {
            "phrase": phrase,
            "input": input_text,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }

        self._event_log.append(event)

        return {"success": True, "event_id": len(self._event_log) - 1, "logged": True}

    def clear(self) -> dict:
        """Clear all registered triggers (keeps event log)."""
        count = len(self._triggers)
        self._triggers.clear()

        return {
            "success": True,
            "cleared_count": count,
            "timestamp": datetime.now().isoformat(),
        }

    def get_events(self, limit: int = 50) -> dict:
        """Get recent trigger events."""
        return {
            "events": self._event_log[-limit:],
            "total_events": len(self._event_log),
            "timestamp": datetime.now().isoformat(),
        }


# Global registry instance
_registry = TriggerRegistry()

# ---------------------------------------------------------------------------
# TOOL: register_trigger
# ---------------------------------------------------------------------------


@mcp.tool(tags={"trigger", "register"})
def register_trigger(
    phrase: str,
    description: str = "",
    handler: str = "callback",
    handler_target: str = "",
    pattern_type: str = "exact",
) -> dict:
    """
    Registers a trigger phrase with callback action.

    Args:
        phrase: The trigger phrase to register (e.g., "/my-command")
        description: Human-readable description of the trigger
        handler: Handler type ("callback", "skill", "function", "workflow")
        handler_target: Target identifier for the handler
        pattern_type: Matching pattern ("exact", "prefix", "regex")

    Returns:
        dict with registration status
    """
    if not phrase:
        return {"success": False, "error": "Phrase cannot be empty"}

    valid_patterns = ["exact", "prefix", "regex"]
    if pattern_type not in valid_patterns:
        return {
            "success": False,
            "error": f"Invalid pattern_type. Must be one of: {valid_patterns}",
        }

    return _registry.register(
        phrase=phrase,
        description=description,
        handler=handler,
        handler_target=handler_target,
        pattern_type=pattern_type,
    )


# ---------------------------------------------------------------------------
# TOOL: list_triggers
# ---------------------------------------------------------------------------


@mcp.tool(tags={"trigger", "list"})
def list_triggers() -> dict:
    """
    Lists all registered triggers.

    Returns:
        dict with list of all triggers and count
    """
    return _registry.list_all()


# ---------------------------------------------------------------------------
# TOOL: check_trigger
# ---------------------------------------------------------------------------


@mcp.tool(tags={"trigger", "check"})
def check_trigger(input_text: str) -> dict:
    """
    Checks if input matches any registered trigger.

    Args:
        input_text: The input string to check

    Returns:
        dict with match result and trigger info if matched
    """
    if not input_text:
        return {"input": input_text, "matched": False, "error": "Input cannot be empty"}

    return _registry.check(input_text)


# ---------------------------------------------------------------------------
# TOOL: get_trigger_handlers
# ---------------------------------------------------------------------------


@mcp.tool(tags={"trigger", "handlers"})
def get_trigger_handlers(phrase: str) -> dict:
    """
    Returns handlers for a matched trigger.

    Args:
        phrase: The trigger phrase to get handlers for

    Returns:
        dict with handler information
    """
    if not phrase:
        return {"found": False, "error": "Phrase cannot be empty"}

    return _registry.get_handlers(phrase)


# ---------------------------------------------------------------------------
# TOOL: log_trigger_event
# ---------------------------------------------------------------------------


@mcp.tool(tags={"trigger", "log", "analytics"})
def log_trigger_event(phrase: str, input_text: str, metadata: dict = None) -> dict:
    """
    Logs trigger activation for analytics.

    Args:
        phrase: The matched trigger phrase
        input_text: The original input that triggered it
        metadata: Additional metadata to log

    Returns:
        dict with logging status
    """
    if not phrase:
        return {"success": False, "error": "Phrase cannot be empty"}

    if not input_text:
        return {"success": False, "error": "Input text cannot be empty"}

    return _registry.log_event(phrase, input_text, metadata)


# ---------------------------------------------------------------------------
# TOOL: clear_triggers
# ---------------------------------------------------------------------------


@mcp.tool(tags={"trigger", "clear"})
def clear_triggers() -> dict:
    """
    Clears all registered triggers.

    Note: This does not clear the event log, only the trigger registry.

    Returns:
        dict with clear operation status
    """
    return _registry.clear()


# ---------------------------------------------------------------------------
# TOOL: execute_trigger
# ---------------------------------------------------------------------------


@mcp.tool(tags={"trigger", "execute", "callback"})
def execute_trigger(phrase: str, args: dict = None) -> dict:
    """
    Execute a trigger's callback handler.

    This is the key function that actually EXECUTES the callback
    instead of just detecting the trigger.

    Args:
        phrase: The trigger phrase to execute
        args: Optional arguments to pass to the handler

    Returns:
        dict with execution result
    """
    if not phrase:
        return {"success": False, "error": "Phrase cannot be empty"}

    # Get trigger info
    trigger_info = _registry.get_handlers(phrase)
    if not trigger_info.get("found"):
        return {"success": False, "error": f"Trigger '{phrase}' not found"}

    handler = trigger_info.get("handler")
    handler_target = trigger_info.get("handler_target")

    # Execute callback
    if handler == "callback":
        result = _callback_executor.execute(handler_target, args or {})
        return result

    # Skill handler - delegate to skill registry or spawn agent
    if handler == "skill":
        try:
            # Try to use skill registry for intelligent routing
            from packages.learning_engine.skill_registry import SkillRegistry

            registry = SkillRegistry()
            routes = registry.route_query(handler_target)

            if routes:
                # Found matching skill - return routing info
                return {
                    "success": True,
                    "handler": "skill",
                    "handler_target": handler_target,
                    "routed_to": routes[0]["skill_id"],
                    "score": routes[0]["score"],
                    "routes": routes[:3],  # Top 3 matches
                }

            # No route found - try spawning agent directly
            return {
                "success": True,
                "handler": "skill",
                "handler_target": handler_target,
                "action": "spawn_agent",
                "message": f"No skill route found. Spawn agent for: {handler_target}",
            }
        except Exception:
            return {
                "success": True,
                "handler": "skill",
                "handler_target": handler_target,
                "action": "delegate",
                "message": f"Skill handler delegated: {handler_target}",
            }

    # MCP handler - execute BMAD workflow via orchestration
    if handler == "mcp":
        try:
            # Special case: list_workflows just returns the list
            if handler_target == "orchestration:list_workflows":
                from packages.orchestration.bmad import list_workflows

                workflow_list = list_workflows()  # Returns List[str]
                # Format as structured response
                formatted_workflows = []
                for name in workflow_list:
                    # Extract module from name (e.g., "bmad-quick-flow/bmad-quick-dev" -> "Quick Dev")
                    parts = name.split("/")
                    module = parts[0] if len(parts) > 1 else "core"
                    readable_name = (
                        parts[-1].replace("bmad-", "").replace("-", " ").title()
                    )
                    formatted_workflows.append(
                        {
                            "id": name,
                            "name": readable_name,
                            "module": module,
                            "trigger": f"/bmad {name}",
                        }
                    )
                return {
                    "success": True,
                    "handler": "mcp",
                    "handler_target": handler_target,
                    "action": "list_workflows",
                    "workflows": formatted_workflows,
                    "count": len(formatted_workflows),
                    "message": f"Found {len(formatted_workflows)} BMAD workflows. Use /bmad <workflow-id> to execute.",
                }

            # Import orchestration MCP functions
            from packages.orchestration import spawn

            # Determine workflow to execute based on handler_target
            workflow_name = handler_target

            # Spawn catalyst agent to execute the workflow
            task_id = spawn(
                agent="catalyst",
                task=f"Execute BMAD workflow: {workflow_name}",
                context={"workflow": workflow_name, "trigger": phrase},
                inject_memory=True,
                warm_pool=False,
                log_sequence=True,
            )

            return {
                "success": True,
                "handler": "mcp",
                "handler_target": handler_target,
                "action": "workflow_spawned",
                "task_id": task_id,
                "workflow": workflow_name,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to execute MCP handler: {str(e)}",
                "handler": "mcp",
                "handler_target": handler_target,
            }

    return {
        "success": False,
        "error": f"Unknown handler type: {handler}",
    }


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Trigger Guardian MCP Server")
    parser.add_argument("--sse", action="store_true", help="Use SSE transport")
    parser.add_argument("--port", type=int, default=8767, help="SSE port")
    args = parser.parse_args()

    if args.sse:
        mcp.run(transport="sse", port=args.port)
    else:
        mcp.run(transport="stdio")
