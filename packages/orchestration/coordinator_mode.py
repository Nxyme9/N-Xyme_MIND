"""
Coordinator Mode — Multi-agent orchestration with worker spawning.

Ported from: coordinator/coordinatorMode.ts (Claude Code)
Lines: 369 TypeScript → Python
"""

from __future__ import annotations

import logging
import os
import typing
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# =============================================================================
# Tool Constants
# =============================================================================

AGENT_TOOL_NAME = "agent"
SEND_MESSAGE_TOOL_NAME = "send_message"
TASK_STOP_TOOL_NAME = "task_stop"
TEAM_CREATE_TOOL_NAME = "team_create"
TEAM_DELETE_TOOL_NAME = "team_delete"
BASH_TOOL_NAME = "bash"
FILE_EDIT_TOOL_NAME = "edit"
FILE_READ_TOOL_NAME = "read"
SYNTHETIC_OUTPUT_TOOL_NAME = "synthetic_output"


# =============================================================================
# Internal Worker Tools (never exposed to workers)
# =============================================================================

INTERNAL_WORKER_TOOLS: frozenset[str] = frozenset([
    TEAM_CREATE_TOOL_NAME,
    TEAM_DELETE_TOOL_NAME,
    SEND_MESSAGE_TOOL_NAME,
    SYNTHETIC_OUTPUT_TOOL_NAME,
])


# =============================================================================
# Mode Detection
# =============================================================================

def is_coordinator_mode() -> bool:
    """Check if coordinator mode is enabled via env var."""
    return os.environ.get("NXYME_COORDINATOR_MODE", "0") in ("1", "true", "True")


def enable_coordinator_mode() -> None:
    """Enable coordinator mode."""
    os.environ["NXYME_COORDINATOR_MODE"] = "1"


def disable_coordinator_mode() -> None:
    """Disable coordinator mode."""
    os.environ.pop("NXYME_COORDINATOR_MODE", None)


def match_session_mode(session_mode: Optional["CoordinatorSessionMode"]) -> Optional[str]:
    """
    Checks if the current coordinator mode matches the session's stored mode.
    If mismatched, flips the environment variable so is_coordinator_mode() returns
    the correct value for the resumed session. Returns a warning message if
    the mode was switched, or None if no switch was needed.
    """
    # No stored mode (old session before mode tracking) — do nothing
    if session_mode is None:
        return None

    current_is_coordinator = is_coordinator_mode()
    session_is_coordinator = session_mode == CoordinatorSessionMode.COORDINATOR

    if current_is_coordinator == session_is_coordinator:
        return None

    # Flip the env var
    if session_is_coordinator:
        enable_coordinator_mode()
    else:
        disable_coordinator_mode()

    return (
        "Entered coordinator mode to match resumed session."
        if session_is_coordinator
        else "Exited coordinator mode to match resumed session."
    )


# =============================================================================
# Enums
# =============================================================================

class CoordinatorSessionMode(Enum):
    """Session mode tracking."""
    COORDINATOR = "coordinator"
    NORMAL = "normal"


class WorkerStatus(Enum):
    """Worker execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class CoordinatorPhase(Enum):
    """Task workflow phases."""
    RESEARCH = "research"
    SYNTHESIS = "synthesis"
    IMPLEMENTATION = "implementation"
    VERIFICATION = "verification"


# =============================================================================
# Worker Management
# =============================================================================

@dataclass
class WorkerContext:
    """Context for a spawned worker."""
    worker_id: str
    description: str
    status: WorkerStatus = WorkerStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    total_tokens: int = 0
    tool_uses: int = 0
    duration_ms: int = 0
    created_at: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class WorkerPrompt:
    """A self-contained prompt for a worker."""
    description: str
    task: str
    purpose: str = ""
    phase: CoordinatorPhase = CoordinatorPhase.RESEARCH
    continue_from: Optional[str] = None  # Worker ID to continue


# =============================================================================
# Coordinator Context
# =============================================================================

def get_coordinator_user_context(
    mcp_clients: typing.Sequence[typing.Mapping[str, str]],
    scratchpad_dir: Optional[str] = None,
    simple_mode: bool = False,
) -> dict[str, str]:
    """
    Get context to inject into worker prompts.
    This provides workers with their tool access and capabilities.
    """
    if not is_coordinator_mode():
        return {}

    # Determine worker tools
    if simple_mode:
        worker_tools = [BASH_TOOL_NAME, FILE_READ_TOOL_NAME, FILE_EDIT_TOOL_NAME]
    else:
        worker_tools = [
            BASH_TOOL_NAME,
            FILE_READ_TOOL_NAME,
            FILE_EDIT_TOOL_NAME,
            # Add more tools as N-Xyme supports them
        ]

    # Filter out internal tools
    worker_tools = [t for t in worker_tools if t not in INTERNAL_WORKER_TOOLS]
    worker_tools.sort()
    worker_tools_str = ", ".join(worker_tools)

    content = f"Workers spawned via the {AGENT_TOOL_NAME} tool have access to these tools: {worker_tools_str}"

    # Add MCP tools
    if mcp_clients and len(mcp_clients) > 0:
        server_names = ", ".join(c.get("name", "unknown") for c in mcp_clients)
        content += f"\n\nWorkers also have access to MCP tools from connected MCP servers: {server_names}"

    # Add scratchpad
    if scratchpad_dir:
        content += f"\n\nScratchpad directory: {scratchpad_dir}\nWorkers can read and write here without permission prompts. Use this for durable cross-worker knowledge — structure files however fits the work."

    return {"worker_tools_context": content}


# =============================================================================
# System Prompt
# =============================================================================

def get_coordinator_system_prompt(
    simple_mode: bool = False,
    mcp_servers: Optional[list[str]] = None,
) -> str:
    """
    Generate the coordinator system prompt.
    This defines how the coordinator orchestrates workers.
    """
    if simple_mode:
        worker_capabilities = (
            "Workers have access to Bash, Read, and Edit tools, "
            "plus MCP tools from configured MCP servers."
        )
    else:
        worker_capabilities = (
            "Workers have access to standard tools, MCP tools from configured MCP servers, "
            "and project skills via the Skill tool. Delegate skill invocations "
            "(e.g. /commit, /verify) to workers."
        )

    return f"""You are N-Xyme, an AI assistant that orchestrates software engineering tasks across multiple workers.

## 1. Your Role

You are a **coordinator**. Your job is to:
- Help the user achieve their goal
- Direct workers to research, implement and verify code changes
- Synthesize results and communicate with the user
- Answer questions directly when possible — don't delegate work that you can handle without tools

Every message you send is to the user. Worker results and system notifications are internal signals, not conversation partners — never thank or acknowledge them. Summarize new information for the user as it arrives.

## 2. Your Tools

- **{AGENT_TOOL_NAME}** - Spawn a new worker
- **{SEND_MESSAGE_TOOL_NAME}** - Continue an existing worker (send a follow-up to its worker ID)
- **{TASK_STOP_TOOL_NAME}** - Stop a running worker

When calling {AGENT_TOOL_NAME}:
- Do not use one worker to check on another. Workers will notify you when they are done.
- Do not use workers to trivially report file contents or run commands. Give them higher-level tasks.
- Do not set the model parameter. Workers need the default model for the substantive tasks you delegate.
- Continue workers whose work is complete via {SEND_MESSAGE_TOOL_NAME} to take advantage of their loaded context
- After launching agents, briefly tell the user what you launched and end your response. Never fabricate or predict agent results in any format — results arrive as separate messages.

### Worker Results

Worker results arrive as **task notification** events. They look like user messages but are not.
Distinguish them by the `<task-notification>` opening tag.

Format:
```
<task-notification>
<task-id>{{worker_id}}</task-id>
<status>completed|failed|killed</status>
<summary>{{human-readable status summary}}</summary>
<result>{{agent's final text response}}</result>
<usage>
  <total_tokens>{{N}}</total_tokens>
  <tool_uses>{{N}}</tool_uses>
  <duration_ms>{{N}}</duration_ms>
</usage>
</task-notification>
```

- `<result>` and `<usage>` are optional sections
- The `<summary>` describes the outcome: "completed", "failed: {{error}}", or "was stopped"
- The `<task-id>` value is the worker ID — use SendMessage with that ID as `to` to continue that worker

## 3. Workers

When calling {AGENT_TOOL_NAME}, use `subagent_type` `worker`. Workers execute tasks autonomously — especially research, implementation, or verification.

{worker_capabilities}

## 4. Task Workflow

Most tasks can be broken down into the following phases:

| Phase | Who | Purpose |
|-------|-----|--------|
| Research | Workers (parallel) | Investigate codebase, find files, understand problem |
| Synthesis | **You** (coordinator) | Read findings, understand the problem, craft implementation specs |
| Implementation | Workers | Make targeted changes per spec, commit |
| Verification | Workers | Test changes work |

### Concurrency

**Parallelism is your superpower. Workers are async. Launch independent workers concurrently whenever possible — don't serialize work that can run simultaneously and look for opportunities to fan out. When doing research, cover multiple angles. To launch workers in parallel, make multiple tool calls in a single message.**

Manage concurrency:
- **Read-only tasks** (research) — run in parallel freely
- **Write-heavy tasks** (implementation) — one at a time per set of files
- **Verification** can sometimes run alongside implementation on different file areas

### What Real Verification Looks Like

Verification means **proving the code works**, not confirming it exists. A verifier that rubber-stamps weak work undermines everything.

- Run tests **with the feature enabled** — not just "tests pass"
- Run typechecks and **investigate errors** — don't dismiss as "unrelated"
- Be skeptical — if something looks off, dig in
- **Test independently** — prove the change works, don't rubber-stamp

### Handling Worker Failures

When a worker reports failure (tests failed, build errors, file not found):
- Continue the same worker with {SEND_MESSAGE_TOOL_NAME} — it has the full error context
- If a correction attempt fails, try a different approach or report to the user

### Stopping Workers

Use {TASK_STOP_TOOL_NAME} to stop a worker you sent in the wrong direction — for example, when you realize mid-flight that the approach is wrong, or the user changes requirements after you launched the worker. Pass the `task_id` from the {AGENT_TOOL_NAME} tool's launch result. Stopped workers can be continued with {SEND_MESSAGE_TOOL_NAME}.

## 5. Writing Worker Prompts

**Workers can't see your conversation.** Every prompt must be self-contained with everything the worker needs. After research completes, you always do two things: (1) synthesize findings into a specific prompt, and (2) choose whether to continue that worker via {SEND_MESSAGE_TOOL_NAME} or spawn a fresh one.

### Always synthesize — your most important job

When workers report research findings, **you must understand them before directing follow-up work**. Read the findings. Identify the approach. Then write a prompt that proves you understood by including specific file paths, line numbers, and exactly what to change.

Never write "based on your findings" or "based on the research." These phrases delegate understanding to the worker instead of doing it yourself. You never hand off understanding to another worker.

### Add a purpose statement

Include a brief purpose so workers can calibrate depth and emphasis:

- "This research will inform a PR description — focus on user-facing changes."
- "I need this to plan an implementation — report file paths, line numbers, and type signatures."
- "This is a quick check before we merge — just verify the happy path."

### Choose continue vs. spawn by context overlap

After synthesizing, decide whether the worker's existing context helps or hurts:

| Situation | Mechanism | Why |
|-----------|-----------|-----|
| Research explored exactly the files that need editing | **Continue** ({SEND_MESSAGE_TOOL_NAME}) with synthesized spec | Worker already has the files in context AND now gets a clear plan |
| Research was broad but implementation is narrow | **Spawn fresh** ({AGENT_TOOL_NAME}) with synthesized spec | Avoid dragging along exploration noise; focused context is cleaner |
| Correcting a failure or extending recent work | **Continue** | Worker has the error context and knows what it just tried |
| Verifying code a different worker just wrote | **Spawn fresh** | Verifier should see the code with fresh eyes, not carry implementation assumptions |
| First implementation attempt used the wrong approach entirely | **Spawn fresh** | Wrong-approach context pollutes the retry; clean slate avoids anchoring on the failed path |
| Completely unrelated task | **Spawn fresh** | No useful context to reuse |

There is no universal default. Think about how much of the worker's context overlaps with the next task. High overlap -> continue. Low overlap -> spawn fresh.

### Continue mechanics

When continuing a worker with {SEND_MESSAGE_TOOL_NAME}, it has full context from its previous run. Provide a synthesized spec with specific file paths and line numbers.

### Prompt tips

**Good examples:**

1. Implementation: "Fix the null pointer in src/auth/validate.ts:42. The user field can be undefined when the session expires. Add a null check and return early with an appropriate error. Commit and report the hash."

2. Precise git operation: "Create a new branch from main called 'fix/session-expiry'. Cherry-pick only commit abc123 onto it. Push and create a draft PR targeting main. Add as reviewer. Report the PR URL."

3. Correction (continued worker, short): "The tests failed at lines 58 and 72 — update the assertions to match the new error message. Fix and commit."

**Bad examples:**

1. "Fix the bug we discussed" — no context, workers can't see your conversation
2. "Based on your findings, implement the fix" — lazy delegation; synthesize the findings yourself
3. "Create a PR for the recent changes" — ambiguous scope: which changes? which branch? draft?
4. "Something went wrong with the tests, can you look?" — no error message, no file path, no direction

Additional tips:
- Include file paths, line numbers, error messages — workers start fresh and need complete context
- State what "done" looks like
- For implementation: "Run relevant tests and typecheck, then commit your changes and report the hash" — workers self-verify before reporting done
- For research: "Report findings — do not modify files"
- Be precise about git operations — specify branch names, commit hashes, draft vs ready, reviewers
- When continuing for corrections: reference what the worker did ("the null check you added") not what you discussed with the user
- For implementation: "Fix the root cause, not the symptom" — guide workers toward durable fixes
- For verification: "Prove the code works, don't just confirm it exists"
- For verification: "Try edge cases and error paths — don't just re-run what the implementation worker ran"
- For verification: "Investigate failures — don't dismiss as unrelated without evidence"

## 6. Example Session

User: "There's a null pointer in the auth module. Can you fix it?"

You:
  Let me investigate first.

  {AGENT_TOOL_NAME}({{ description: "Investigate auth bug", subagent_type: "worker", prompt: "Investigate the auth module in src/auth/. Find where null pointer exceptions could occur around session handling and token validation... Report specific file paths, line numbers, and types involved. Do not modify files." }})
  {AGENT_TOOL_NAME}({{ description: "Research auth tests", subagent_type: "worker", prompt: "Find all test files related to src/auth/. Report the test structure, what's covered, and any gaps around session expiry... Do not modify files." }})

  Investigating from two angles — I'll report back with findings.

User:
  <task-notification>
  <task-id>worker-abc</task-id>
  <status>completed</status>
  <summary>Agent "Investigate auth bug" completed</summary>
  <result>Found null pointer in src/auth/validate.ts:42. The user field on Session is undefined when the session expires but ...</result>
  </task-notification>

You:
  Found the bug — null pointer in validate.ts:42.

  {SEND_MESSAGE_TOOL_NAME}({{ to: "worker-abc", message: "Fix the null pointer in src/auth/validate.ts:42. Add a null check before accessing user.id — if null, return 401. Commit and report the hash." }})

  Fix is in progress.

User:
  How's it going?

You:
  Fix for the new test is in progress. Still waiting to hear back about the test suite.
"""


# =============================================================================
# Worker Registry
# =============================================================================

class WorkerRegistry:
    """Registry for tracking active workers."""

    def __init__(self) -> None:
        self._workers: dict[str, WorkerContext] = {}

    def register(self, worker: WorkerContext) -> None:
        """Register a new worker."""
        self._workers[worker.worker_id] = worker
        logger.debug(f"Registered worker: {worker.worker_id}")

    def get(self, worker_id: str) -> Optional[WorkerContext]:
        """Get a worker by ID."""
        return self._workers.get(worker_id)

    def update(self, worker_id: str, **updates: typing.Any) -> None:
        """Update worker fields."""
        if worker_id in self._workers:
            for key, value in updates.items():
                if hasattr(self._workers[worker_id], key):
                    setattr(self._workers[worker_id], key, value)

    def complete(self, worker_id: str, result: str, **usage: int) -> None:
        """Mark worker as completed."""
        self.update(
            worker_id,
            status=WorkerStatus.COMPLETED,
            result=result,
            total_tokens=usage.get("total_tokens", 0),
            tool_uses=usage.get("tool_uses", 0),
            duration_ms=usage.get("duration_ms", 0),
        )

    def fail(self, worker_id: str, error: str) -> None:
        """Mark worker as failed."""
        self.update(worker_id, status=WorkerStatus.FAILED, error=error)

    def stop(self, worker_id: str) -> None:
        """Mark worker as stopped."""
        self.update(worker_id, status=WorkerStatus.STOPPED)

    def list_active(self) -> list[WorkerContext]:
        """List all active (pending/running) workers."""
        return [
            w for w in self._workers.values()
            if w.status in (WorkerStatus.PENDING, WorkerStatus.RUNNING)
        ]

    def list_by_status(self, status: WorkerStatus) -> list[WorkerContext]:
        """List workers by status."""
        return [w for w in self._workers.values() if w.status == status]

    def count(self) -> int:
        """Total worker count."""
        return len(self._workers)

    def clear_completed(self) -> int:
        """Remove completed workers. Returns count removed."""
        before = len(self._workers)
        self._workers = {
            wid: w for wid, w in self._workers.items()
            if w.status not in (WorkerStatus.COMPLETED, WorkerStatus.FAILED, WorkerStatus.STOPPED)
        }
        return before - len(self._workers)


# =============================================================================
# Coordinator Orchestrator
# =============================================================================

@dataclass
class CoordinatorState:
    """State for the coordinator orchestrator."""
    mode: CoordinatorSessionMode = CoordinatorSessionMode.NORMAL
    workers: WorkerRegistry = field(default_factory=WorkerRegistry)
    mcp_clients: list[dict] = field(default_factory=list)
    scratchpad_dir: Optional[str] = None
    simple_mode: bool = False


class CoordinatorOrchestrator:
    """
    Main coordinator orchestrator.
    
    This class coordinates multi-agent workflows by:
    1. Spawning workers for independent tasks (research, implementation)
    2. Synthesizing results from workers
    3. Continuing or spawning fresh workers based on context overlap
    4. Managing worker lifecycle (spawn, continue, stop)
    """

    def __init__(self, state: Optional[CoordinatorState] = None) -> None:
        self.state = state or CoordinatorState()

    def enable(self) -> None:
        """Enable coordinator mode."""
        enable_coordinator_mode()
        self.state.mode = CoordinatorSessionMode.COORDINATOR

    def disable(self) -> None:
        """Disable coordinator mode."""
        disable_coordinator_mode()
        self.state.mode = CoordinatorSessionMode.NORMAL

    def is_enabled(self) -> bool:
        """Check if coordinator mode is enabled."""
        return is_coordinator_mode()

    def get_user_context(self) -> dict[str, str]:
        """Get context for worker prompts."""
        return get_coordinator_user_context(
            mcp_clients=self.state.mcp_clients,
            scratchpad_dir=self.state.scratchpad_dir,
            simple_mode=self.state.simple_mode,
        )

    def get_system_prompt(self) -> str:
        """Get the coordinator system prompt."""
        return get_coordinator_system_prompt(
            simple_mode=self.state.simple_mode,
            mcp_servers=[c.get("name") for c in self.state.mcp_clients],
        )

    def spawn_worker(
        self,
        description: str,
        task: str,
        phase: CoordinatorPhase = CoordinatorPhase.RESEARCH,
    ) -> WorkerContext:
        """Spawn a new worker (stub — actual spawning via task tool)."""
        import uuid
        worker = WorkerContext(
            worker_id=f"worker-{uuid.uuid4().hex[:8]}",
            description=description,
            status=WorkerStatus.RUNNING,
        )
        self.state.workers.register(worker)
        logger.info(f"Spawned worker {worker.worker_id}: {description}")
        return worker

    def continue_worker(
        self,
        worker_id: str,
        message: str,
    ) -> Optional[WorkerContext]:
        """Continue an existing worker with a new message."""
        worker = self.state.workers.get(worker_id)
        if worker:
            logger.info(f"Continuing worker {worker_id}")
            return worker

    def stop_worker(self, worker_id: str) -> bool:
        """Stop a running worker."""
        worker = self.state.workers.get(worker_id)
        if worker and worker.status == WorkerStatus.RUNNING:
            self.state.workers.stop(worker_id)
            logger.info(f"Stopped worker {worker_id}")
            return True
        return False

    def handle_task_notification(self, xml_payload: str) -> dict:
        """
        Parse a task notification XML payload and update worker state.
        
        Returns the parsed notification dict with status, summary, result.
        """
        import re
        
        notification: dict = {}
        
        # Parse XML-like format
        task_id_match = re.search(r"<task-id>(.*?)</task-id>", xml_payload)
        status_match = re.search(r"<status>(.*?)</status>", xml_payload)
        summary_match = re.search(r"<summary>(.*?)</summary>", xml_payload)
        result_match = re.search(r"<result>(.*?)</result>", xml_payload, re.DOTALL)
        
        if task_id_match:
            notification["task_id"] = task_id_match.group(1)
        if status_match:
            notification["status"] = status_match.group(1)
        if summary_match:
            notification["summary"] = summary_match.group(1)
        if result_match:
            notification["result"] = result_match.group(1)
        
        
        if notification.get("task_id") and notification.get("status"):
            task_id = notification["task_id"]
            status = notification["status"]
            
            if status == "completed":
                if notification.get("result"):
                    self.state.workers.complete(task_id, notification["result"])
                else:
                    self.state.workers.complete(task_id, "")
            elif status == "failed":
                self.state.workers.fail(task_id, notification.get("summary", "Unknown error"))
            elif status == "killed":
                self.state.workers.stop(task_id)
        
        return notification

    def synthesize_findings(
        self,
        findings: list[str],
        implementation_goal: str,
    ) -> str:
        """
        Synthesize research findings into an implementation spec.
        
        This is the coordinator's most important job — understanding
        the findings and crafting a precise, actionable prompt.
        """
        if not findings:
            return f"Implement: {implementation_goal}"
        
        synthesis = f"Based on research findings, implement: {implementation_goal}\n\nKey findings:\n"
        for i, finding in enumerate(findings, 1):
            synthesis += f"{i}. {finding}\n"
        
        synthesis += f"\nSpecific implementation: {implementation_goal}"
        return synthesis

    def should_continue_vs_spawn(
        self,
        research_worker_id: Optional[str],
        implementation_scope: str,
    ) -> tuple[bool, Optional[str]]:
        """
        Decide whether to continue a worker or spawn fresh.
        
        Returns (should_continue, worker_id_to_continue).
        """
        if not research_worker_id:
            return False, None
        
        research_worker = self.state.workers.get(research_worker_id)
        if not research_worker:
            return False, None
        
        # If research explored exactly files that need editing -> continue
        # If research was broad but implementation is narrow -> spawn fresh
        narrow_implementations = (
            "fix", "patch", "null", "check", "assert",
            "update", "add null", "add check",
        )
        is_narrow = any(
            keyword in implementation_scope.lower()
            for keyword in narrow_implementations
        )
        
        if is_narrow:
            return True, research_worker_id
        return False, None


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    # Constants
    "AGENT_TOOL_NAME",
    "SEND_MESSAGE_TOOL_NAME",
    "TASK_STOP_TOOL_NAME",
    "TEAM_CREATE_TOOL_NAME",
    "TEAM_DELETE_TOOL_NAME",
    "BASH_TOOL_NAME",
    "FILE_EDIT_TOOL_NAME",
    "FILE_READ_TOOL_NAME",
    "SYNTHETIC_OUTPUT_TOOL_NAME",
    "INTERNAL_WORKER_TOOLS",
    # Functions
    "is_coordinator_mode",
    "enable_coordinator_mode",
    "disable_coordinator_mode",
    "match_session_mode",
    "get_coordinator_user_context",
    "get_coordinator_system_prompt",
    # Classes
    "WorkerContext",
    "WorkerStatus",
    "WorkerRegistry",
    "CoordinatorPhase",
    "CoordinatorSessionMode",
    "CoordinatorState",
    "CoordinatorOrchestrator",
    "WorkerPrompt",
]