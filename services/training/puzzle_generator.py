#!/usr/bin/env python3
"""
puzzle_generator.py — Orchestration Puzzle Generator.

Reads real failure patterns from telemetry/training data, generates
synthetic orchestration challenges ("puzzles") for agents to practice.

Five puzzle types:
  1. SERVICE_DOWN    — "Service is down — find and restart it"
  2. CONFIG_DRIFT    — "Two configs disagree — find the drift and fix"
  3. NOTIFICATION_STORM — "Notification storm — identify and silence source"
  4. TOOL_FAILURE    — "Tool call failed — diagnose and retry with correct args"
  5. DELEGATION_BROKEN — "Delegation chain broken — complete the handoff"

Progressive difficulty:
  EASY   → known solution, single step, no time pressure
  MEDIUM → similar to past failures, 2-3 steps, moderate ambiguity
  HARD   → novel problem, multi-step, requires synthesis

Usage:
  python3 puzzle_generator.py                      # generate and print puzzles
  python3 puzzle_generator.py --count 10            # generate N puzzles
  python3 puzzle_generator.py --type TOOL_FAILURE   # specific type only
  python3 puzzle_generator.py --agent hephaestus    # for a specific agent
  python3 puzzle_generator.py --daemon              # continuous generation loop
  python3 puzzle_generator.py --solve               # attempt to solve puzzles

References:
  - Chain-of-Thought prompting (Wei et al. 2022) for task decomposition
  - Curriculum Learning (Bengio et al. 2009) for progressive difficulty
  - Sutton & Barto "Reinforcement Learning" Ch.8 — planning & learning
"""

import argparse
import hashlib
import json
import logging
import os
import random
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# ── Paths ──────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(os.environ.get(
    "NX_PROJECT_ROOT",
    Path(__file__).resolve().parent.parent.parent,
))

TRAINING_DIR = PROJECT_ROOT / "data" / "training"
EXAMPLES_FILE = TRAINING_DIR / "examples.jsonl"
CURRICULUM_FILE = TRAINING_DIR / "curriculum.json"
PUZZLES_FILE = TRAINING_DIR / "puzzles.jsonl"
PUZZLE_RESULTS_FILE = TRAINING_DIR / "puzzle_results.jsonl"
TELEMETRY_FILE = PROJECT_ROOT / "data" / "telemetry" / "tool-calls.jsonl"
OUTCOMES_FILE = PROJECT_ROOT / "data" / "learning" / "outcomes" / "log.jsonl"
LOG_DIR = TRAINING_DIR / "logs"

POLL_INTERVAL = 300  # 5 minutes between generation passes
MAX_PUZZLES_PER_PASS = 20
SEED = 42

# ── Puzzle templates ───────────────────────────────────────────────────────

PUZZLE_TEMPLATES: dict[str, list[dict]] = {
    "SERVICE_DOWN": [
        {
            "title": "Dead Service Detective",
            "description": "The {service} service is not responding. Find it, check its health, and restart it.",
            "difficulty": "EASY",
            "tags": ["service", "health-check", "restart"],
            "solution_steps": [
                "Check if {service} service is running",
                "Read health endpoint or status",
                "Restart {service}",
                "Verify it recovered",
            ],
            "tools_needed": ["bash", "file_read", "grep"],
            "timeout_s": 120,
        },
        {
            "title": "Cascading Service Failure",
            "description": "{service} is down, and dependent service {dependency} is showing errors. Trace the root cause and bring the system back.",
            "difficulty": "MEDIUM",
            "tags": ["service", "dependency", "root-cause"],
            "solution_steps": [
                "Check both {service} and {dependency} status",
                "Read logs to find which failed first",
                "Restart the root-cause service",
                "Verify dependent service recovers",
            ],
            "tools_needed": ["bash", "file_read", "grep", "glob"],
            "timeout_s": 300,
        },
        {
            "title": "Silent Crash Recovery",
            "description": "{service} crashed silently — no error in health check, but requests timeout. Find the zombie process, diagnose why, and bring it back with monitoring.",
            "difficulty": "HARD",
            "tags": ["service", "zombie", "timeout", "monitoring"],
            "solution_steps": [
                "Detect the zombie process with timeout probes",
                "Read recent logs for crash clues",
                "Kill the stale process",
                "Restart with monitoring flags",
                "Verify requests succeed",
            ],
            "tools_needed": ["bash", "file_read", "grep", "file_write"],
            "timeout_s": 600,
        },
    ],
    "CONFIG_DRIFT": [
        {
            "title": "Single Config Mismatch",
            "description": "{config_a} and {config_b} have a disagreement about {key}. Find the drift and make them consistent.",
            "difficulty": "EASY",
            "tags": ["config", "drift", "sync"],
            "solution_steps": [
                "Read {config_a} and extract {key}",
                "Read {config_b} and extract {key}",
                "Identify the mismatch",
                "Update the outdated config to match",
                "Run validation",
            ],
            "tools_needed": ["file_read", "file_write", "grep"],
            "timeout_s": 120,
        },
        {
            "title": "Multi-Config Race Condition",
            "description": "{config_a}, {config_b}, and {config_c} are supposed to agree on {keys}. Instead they have 3 different values. Find the source of truth and sync all three.",
            "difficulty": "MEDIUM",
            "tags": ["config", "drift", "race-condition", "sync"],
            "solution_steps": [
                "Read all three configs",
                "Extract all relevant keys from each",
                "Identify source of truth (most recent / most complete)",
                "Update all three to match",
                "Run config_validate",
            ],
            "tools_needed": ["file_read", "file_write", "grep", "config_validate"],
            "timeout_s": 300,
        },
        {
            "title": "Nested Config Drift",
            "description": "A deep nesting of {config_a} imports {config_b} which overrides {config_c}. The chain produced an unexpected final value for {key}. Trace the import chain and fix the root.",
            "difficulty": "HARD",
            "tags": ["config", "drift", "import-chain", "deep-nesting"],
            "solution_steps": [
                "Map the import/override chain",
                "Read each layer in order",
                "Trace how {key} gets its final value",
                "Identify which layer introduces the error",
                "Fix the root layer",
                "Verify the final resolved value is correct",
            ],
            "tools_needed": ["file_read", "file_glob", "file_grep", "file_write"],
            "timeout_s": 600,
        },
    ],
    "NOTIFICATION_STORM": [
        {
            "title": "Single Source Spam",
            "description": "Agent {agent} is spamming the same notification every {interval}s. Find the source and silence it with a rate limit.",
            "difficulty": "EASY",
            "tags": ["notification", "spam", "rate-limit"],
            "solution_steps": [
                "Search recent notifications from {agent}",
                "Identify the duplicate pattern",
                "Add rate limiting for that notification type",
                "Verify spam stops",
            ],
            "tools_needed": ["grep", "file_read", "file_write", "search_memory"],
            "timeout_s": 180,
        },
        {
            "title": "Cross-Agent Notification Feedback Loop",
            "description": "{agent_a} notifies {agent_b}, which triggers {agent_c}, which notifies {agent_a} — infinite loop. Break the cycle by identifying and removing the circular trigger.",
            "difficulty": "MEDIUM",
            "tags": ["notification", "feedback-loop", "cycle"],
            "solution_steps": [
                "Trace the notification chain",
                "Identify the circular dependency",
                "Determine which notification is the redundant trigger",
                "Modify the agent or remove the trigger",
                "Verify the loop stops",
            ],
            "tools_needed": ["grep", "file_read", "file_write", "search_memory", "file_glob"],
            "timeout_s": 300,
        },
        {
            "title": "Distributed Notification Cascade",
            "description": "Multiple agents ({agents}) are caught in a cascade — each notification spawns 2 more. Find the root notification type and implement a circuit breaker.",
            "difficulty": "HARD",
            "tags": ["notification", "cascade", "circuit-breaker"],
            "solution_steps": [
                "Map the entire notification cascade graph",
                "Identify the root notification type",
                "Implement a circuit breaker at the root",
                "Add cooldown periods",
                "Verify cascade stops within 2 hops",
            ],
            "tools_needed": ["grep", "file_read", "file_write", "search_memory",
                            "file_glob", "glob"],
            "timeout_s": 600,
        },
    ],
    "TOOL_FAILURE": [
        {
            "title": "Wrong Argument Fix",
            "description": "Calling {tool} with argument {wrong_arg} fails with '{error}'. The correct argument is {correct_arg}. Diagnose and retry.",
            "difficulty": "EASY",
            "tags": ["tool", "argument", "fix"],
            "solution_steps": [
                "Read the tool documentation or schema",
                "Identify the correct parameter name",
                "Retry with {correct_arg}",
                "Verify success",
            ],
            "tools_needed": ["file_read", "grep", "bash"],
            "timeout_s": 120,
        },
        {
            "title": "Missing Dependency Chain",
            "description": "Calling {tool} fails with '{error}'. The error mentions a missing dependency ({dependency}). Install it and retry with the right flags.",
            "difficulty": "MEDIUM",
            "tags": ["tool", "dependency", "install"],
            "solution_steps": [
                "Parse the error to identify the missing dependency",
                "Check if the dependency is available system-wide",
                "Install or activate the dependency",
                "Retry the tool call",
                "Verify it works",
            ],
            "tools_needed": ["bash", "file_read", "grep"],
            "timeout_s": 300,
        },
        {
            "title": "Multi-Tool Orchestration Recovery",
            "description": "A {workflow} workflow that calls {tools} failed at step {failed_step} with '{error}'. The first {succeeded_steps} steps were done but the state is inconsistent. Roll back the completed steps and retry with corrected approach.",
            "difficulty": "HARD",
            "tags": ["tool", "orchestration", "rollback", "retry"],
            "solution_steps": [
                "Identify which steps completed before failure",
                "Determine rollback actions for each completed step",
                "Execute rollback in reverse order",
                "Analyse why step {failed_step} failed",
                "Retry with corrected approach",
                "Verify entire workflow completes",
            ],
            "tools_needed": ["bash", "file_read", "file_write", "file_edit",
                            "grep", "glob", "delegate_task"],
            "timeout_s": 600,
        },
    ],
    "DELEGATION_BROKEN": [
        {
            "title": "Simple Handoff Repair",
            "description": "Agent {from_agent} was supposed to delegate to {to_agent} but the handoff failed with '{error}'. Fix the delegation call and retry.",
            "difficulty": "EASY",
            "tags": ["delegation", "handoff", "repair"],
            "solution_steps": [
                "Read the delegation attempt from {from_agent}",
                "Identify the error in the handoff",
                "Fix the delegation parameters",
                "Retry the delegation",
            ],
            "tools_needed": ["file_read", "grep", "delegate_task"],
            "timeout_s": 180,
        },
        {
            "title": "Lost Context in Delegation Chain",
            "description": "{from_agent} delegated to {mid_agent}, which was supposed to delegate to {to_agent} with context about {context_key}. The context was lost. Restore the missing context and complete the chain.",
            "difficulty": "MEDIUM",
            "tags": ["delegation", "context-loss", "chain"],
            "solution_steps": [
                "Trace the delegation chain",
                "Find where {context_key} was dropped",
                "Determine the correct context value",
                "Re-send the delegation with full context",
                "Verify {to_agent} receives the context",
            ],
            "tools_needed": ["search_memory", "file_read", "grep",
                            "delegate_task", "call_omo_agent"],
            "timeout_s": 300,
        },
        {
            "title": "Complex Delegation Graph Repair",
            "description": "A {workflow} workflow requires {agents} to collaborate in a specific DAG. Agent {failed_agent} failed and the dependency chain is blocked. Redesign the delegation graph to work around {failed_agent}, then execute.",
            "difficulty": "HARD",
            "tags": ["delegation", "graph", "dag", "workaround"],
            "solution_steps": [
                "Map the intended delegation DAG",
                "Identify which agents depend on {failed_agent}",
                "Determine if {failed_agent} can be bypassed or replaced",
                "Redesign the DAG",
                "Execute the new delegation plan",
                "Verify workflow completes",
            ],
            "tools_needed": ["search_memory", "file_read", "grep", "glob",
                            "delegate_task", "call_omo_agent", "file_write"],
            "timeout_s": 900,
        },
    ],
}

DIFFICULTY_WEIGHTS = {"EASY": 0.4, "MEDIUM": 0.35, "HARD": 0.25}

SERVICES = [
    "bash-mcp", "megatool-mcp", "bmad-mcp", "mojo-router",
    "memory-pipeline", "embedding-service", "token-guard",
    "code-indexer", "nx-agents-mcp", "opencode-admin-mcp",
]

CONFIG_FILES = [
    "opencode.json", "config/nx_agents.json",
    "agents/sisyphus/agent.js", "agents/hephaestus/agent.js",
    "agents/atlas/agent.js", "agents/hermes/agent.js",
]

AGENTS = [
    "Catalyst", "Hephaestus", "Atlas", "Hermes",
    "Sisyphus Junior", "Momus", "Oracle", "Prometheus",
    "Explore", "Librarian", "Kairos", "Scalpel",
]

TOOLS = [
    "file_read", "file_write", "file_edit", "file_glob", "file_grep",
    "bash", "delegate_task", "call_omo_agent", "search_memory",
    "write_memory", "config_validate", "config_sync",
    "web_search", "web_fetch", "glob", "grep",
]

ERRORS = [
    "timeout: connection refused",
    "permission denied: tool not in allowlist",
    "not found: file does not exist",
    "ModuleNotFoundError: no module named 'xyz'",
    "config drift detected: values differ",
    "KeyError: 'session_id' not in context",
    "JSONDecodeError: unexpected token",
    "FileNotFoundError: path does not exist",
    "agent 'target' not found in agent registry",
    "tool call failed: invalid parameter 'args'",
]


# ── Logging ────────────────────────────────────────────────────────────────


def setup_logging(daemon: bool = False) -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / "puzzle_generator.log"
    handlers = [logging.FileHandler(str(log_file))]
    if not daemon:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )
    return logging.getLogger("puzzle_generator")


# ── Training data reader ───────────────────────────────────────────────────


def read_training_data(logger: logging.Logger) -> list[dict]:
    """Read existing training examples to inform puzzle generation."""
    if not EXAMPLES_FILE.exists():
        logger.debug("No training examples found")
        return []
    records = []
    try:
        with open(EXAMPLES_FILE) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except OSError as e:
        logger.warning(f"Cannot read training data: {e}")
    logger.debug(f"Read {len(records)} training records")
    return records


def read_failure_patterns(logger: logging.Logger) -> list[dict]:
    """Extract failure patterns from training data and telemetry."""
    patterns = []

    # From training examples
    records = read_training_data(logger)
    failures = [r for r in records if r.get("outcome") == "failure"]
    seen: set = set()
    for rec in failures:
        agent = rec.get("agent", "unknown")
        tool = rec.get("tool", "unknown")
        error = rec.get("error", "")[:80]
        key = f"{agent}|{tool}|{error}"
        if key not in seen:
            seen.add(key)
            patterns.append({
                "agent": agent,
                "tool": tool,
                "error": error,
                "source": "training",
            })

    # From outcomes
    if OUTCOMES_FILE.exists():
        try:
            with open(OUTCOMES_FILE) as f:
                for line in f:
                    if line.strip():
                        try:
                            entry = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if not entry.get("success", True):
                            agent = entry.get("agent", "unknown")
                            task = entry.get("task", "")[:80]
                            key = f"{agent}||{task}"
                            if key not in seen:
                                seen.add(key)
                                patterns.append({
                                    "agent": agent,
                                    "tool": task,
                                    "error": entry.get("task", "")[:80],
                                    "source": "outcome",
                                })
        except OSError:
            pass

    logger.debug(f"Extracted {len(patterns)} failure patterns")
    return patterns


# ── Puzzle generation ──────────────────────────────────────────────────────


def fill_template(template: dict, substitutions: dict) -> dict:
    """Fill template placeholders with random substitutions."""
    puzzle = {}
    for key, value in template.items():
        if isinstance(value, str):
            puzzle[key] = value.format(**substitutions)
        elif isinstance(value, list):
            puzzle[key] = [
                item.format(**substitutions) if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            puzzle[key] = value
    return puzzle


def generate_substitutions(puzzle_type: str, template: dict,
                           failure_pattern: Optional[dict] = None) -> dict:
    """Generate context substitutions for a puzzle template."""
    subs = {}

    # Common substitutions
    subs["service"] = random.choice(SERVICES)
    subs["dependency"] = random.choice(SERVICES)
    subs["config_a"] = random.choice(CONFIG_FILES)
    subs["config_b"] = random.choice(CONFIG_FILES)
    subs["config_c"] = random.choice(CONFIG_FILES)
    subs["key"] = random.choice(["model", "temperature", "timeout",
                                  "max_tokens", "allowed_tools"])
    subs["keys"] = random.choice([["model", "temperature"],
                                   ["timeout", "max_retries"],
                                   ["allowed_tools", "blocked_tools"]])
    subs["agent"] = random.choice(AGENTS)
    subs["agent_a"] = random.choice(AGENTS)
    subs["agent_b"] = random.choice(AGENTS)
    subs["agent_c"] = random.choice(AGENTS)
    subs["agents"] = random.sample(AGENTS, min(3, len(AGENTS)))
    subs["tool"] = random.choice(TOOLS)
    subs["tools"] = random.sample(TOOLS, min(3, len(TOOLS)))
    subs["error"] = random.choice(ERRORS)
    subs["interval"] = str(random.choice([5, 10, 30, 60, 300]))
    subs["from_agent"] = random.choice(AGENTS)
    subs["to_agent"] = random.choice(AGENTS)
    subs["mid_agent"] = random.choice(AGENTS)
    subs["wrong_arg"] = random.choice(["path", "file", "query", "cmd"])
    subs["correct_arg"] = random.choice(["filePath", "pattern", "command",
                                          "task"])
    subs["failed_step"] = str(random.randint(2, 5))
    subs["succeeded_steps"] = str(random.randint(1, 3))
    subs["workflow"] = random.choice(["deploy", "build", "test", "migrate",
                                       "ingest"])
    subs["context_key"] = random.choice(["session_id", "parent_session",
                                          "agent_identity", "task_id"])
    subs["failed_agent"] = random.choice(AGENTS)

    # Override with real failure data if available
    if failure_pattern:
        subs["tool"] = failure_pattern.get("tool", subs["tool"])
        subs["error"] = failure_pattern.get("error", subs["error"])
        subs["agent"] = failure_pattern.get("agent", subs["agent"])

    return subs


def generate_puzzle(
    puzzle_type: str,
    difficulty: Optional[str] = None,
    target_agent: Optional[str] = None,
    failure_pattern: Optional[dict] = None,
    logger: Optional[logging.Logger] = None,
) -> Optional[dict]:
    """
    Generate a single puzzle of the given type.

    Args:
        puzzle_type: SERVICE_DOWN | CONFIG_DRIFT | NOTIFICATION_STORM
                    | TOOL_FAILURE | DELEGATION_BROKEN
        difficulty: EASY | MEDIUM | HARD (random if None)
        target_agent: If provided, tailor puzzle for this agent
        failure_pattern: If provided, base puzzle on this real failure

    Returns:
        Puzzle dict or None if template not found
    """
    templates = PUZZLE_TEMPLATES.get(puzzle_type)
    if not templates:
        if logger:
            logger.warning(f"Unknown puzzle type: {puzzle_type}")
        return None

    # Filter by difficulty if specified
    if difficulty:
        candidates = [t for t in templates if t["difficulty"] == difficulty]
        if not candidates:
            candidates = templates
    else:
        candidates = templates

    template = random.choice(candidates)

    # Generate substitutions
    subs = generate_substitutions(puzzle_type, template, failure_pattern)

    # Override agent if target specified
    if target_agent:
        subs["agent"] = target_agent
        subs["from_agent"] = target_agent

    # Fill template
    puzzle = fill_template(template, subs)

    # Add metadata
    puzzle_id = hashlib.md5(
        f"{puzzle_type}:{puzzle['title']}:{time.time()}:{random.random()}"
        .encode()
    ).hexdigest()[:12]

    return {
        "id": puzzle_id,
        "type": puzzle_type,
        "difficulty": puzzle["difficulty"],
        "title": puzzle["title"],
        "description": puzzle["description"],
        "tags": puzzle.get("tags", []),
        "solution_steps": puzzle.get("solution_steps", []),
        "tools_needed": puzzle.get("tools_needed", []),
        "timeout_s": puzzle.get("timeout_s", 300),
        "context": subs,
        "generated_at": datetime.now().isoformat(),
        "solved": False,
        "attempts": 0,
    }


def generate_puzzles(
    count: int = 5,
    puzzle_type: Optional[str] = None,
    difficulty: Optional[str] = None,
    target_agent: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
) -> list[dict]:
    """
    Generate a batch of puzzles.

    Strategy:
      1. Read real failure patterns from training data
      2. Use them to seed a portion of puzzles (biasing toward real problems)
      3. Fill remaining with random templates
      4. Balance difficulty distribution
    """
    patterns = read_failure_patterns(logger) if logger else []

    puzzles = []
    types = list(PUZZLE_TEMPLATES.keys()) if not puzzle_type else [puzzle_type]

    # Determine difficulty distribution
    if difficulty:
        diff_dist = {difficulty: 1.0}
    else:
        diff_dist = DIFFICULTY_WEIGHTS

    # Seed with real failure patterns (up to 60% of puzzles)
    pattern_count = min(int(count * 0.6), len(patterns))
    random.shuffle(patterns)

    for i in range(pattern_count):
        ptype = random.choice(types)
        # Choose difficulty based on distribution
        diff = random.choices(
            list(diff_dist.keys()),
            weights=list(diff_dist.values()),
        )[0]
        puzzle = generate_puzzle(
            puzzle_type=ptype,
            difficulty=diff,
            target_agent=target_agent,
            failure_pattern=patterns[i],
            logger=logger,
        )
        if puzzle:
            puzzle["from_real_failure"] = True
            puzzle["source_failure"] = {
                "agent": patterns[i].get("agent", "unknown"),
                "tool": patterns[i].get("tool", "unknown"),
                "error": patterns[i].get("error", "")[:100],
            }
            puzzles.append(puzzle)

    # Fill remaining with random templates
    remaining = count - len(puzzles)
    for _ in range(remaining):
        ptype = random.choice(types)
        diff = random.choices(
            list(diff_dist.keys()),
            weights=list(diff_dist.values()),
        )[0]
        puzzle = generate_puzzle(
            puzzle_type=ptype,
            difficulty=diff,
            target_agent=target_agent,
            logger=logger,
        )
        if puzzle:
            puzzle["from_real_failure"] = False
            puzzles.append(puzzle)

    random.shuffle(puzzles)

    if logger:
        type_counts = Counter(p["type"] for p in puzzles)
        diff_counts = Counter(p["difficulty"] for p in puzzles)
        real_count = sum(1 for p in puzzles if p.get("from_real_failure"))
        logger.info(
            f"Generated {len(puzzles)} puzzles: "
            f"types={dict(type_counts)}, "
            f"difficulty={dict(diff_counts)}, "
            f"from_real_failures={real_count}"
        )

    return puzzles[:count]


# ── Puzzle solving (simulation) ────────────────────────────────────────────


def solve_puzzle(puzzle: dict, logger: logging.Logger) -> dict:
    """
    Attempt to "solve" a puzzle by validating it against known solution
    patterns. This is a simulation — real solving is done by agents.

    Returns result dict with solution attempt metadata.
    """
    difficulty = puzzle.get("difficulty", "EASY")
    tools_needed = puzzle.get("tools_needed", [])
    solution_steps = puzzle.get("solution_steps", [])

    # EASY puzzles always "succeed" (known solution)
    # MEDIUM: 70% chance
    # HARD: 40% chance
    success_chances = {"EASY": 0.95, "MEDIUM": 0.70, "HARD": 0.40}
    success = random.random() < success_chances.get(difficulty, 0.5)

    attempts = random.randint(1, 3) if not success else 1

    solved_steps = []
    failed_at = None
    for i, step in enumerate(solution_steps):
        if success or i < len(solution_steps) - 1:
            solved_steps.append({"step": i + 1, "action": step, "status": "ok"})
        else:
            solved_steps.append({"step": i + 1, "action": step, "status": "failed"})
            failed_at = step
            break

    result = {
        "puzzle_id": puzzle["id"],
        "solved": success,
        "attempts": attempts,
        "steps_completed": len(solved_steps),
        "total_steps": len(solution_steps),
        "failed_at_step": failed_at,
        "tools_used": random.sample(tools_needed,
                                     min(len(tools_needed),
                                         random.randint(1, len(tools_needed)))),
        "solve_time_s": random.randint(10, puzzle.get("timeout_s", 300)),
        "timestamp": time.time(),
    }

    logger.debug(
        f"Puzzle {puzzle['id'][:8]} ({puzzle['type']}/{difficulty}): "
        f"{'SOLVED' if success else 'FAILED'} "
        f"in {result['solve_time_s']}s / {attempts} attempt(s)"
    )
    return result


def store_puzzle_result(result: dict, logger: logging.Logger):
    """Append puzzle solve result to results file."""
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    with open(PUZZLE_RESULTS_FILE, "a") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")
    logger.debug(f"Stored result for puzzle {result['puzzle_id'][:8]}")


# ── Main generation pass ───────────────────────────────────────────────────


def generate_pass(logger: logging.Logger,
                  count: int = MAX_PUZZLES_PER_PASS,
                  puzzle_type: Optional[str] = None,
                  difficulty: Optional[str] = None,
                  target_agent: Optional[str] = None,
                  solve: bool = False) -> list[dict]:
    """
    Generate a batch of puzzles and optionally solve them.
    Stores puzzles and results. Returns puzzle list.
    """
    logger.info(f"Generating up to {count} puzzles "
                f"(type={puzzle_type or 'all'}, "
                f"difficulty={difficulty or 'mixed'}, "
                f"agent={target_agent or 'any'})")

    puzzles = generate_puzzles(
        count=count,
        puzzle_type=puzzle_type,
        difficulty=difficulty,
        target_agent=target_agent,
        logger=logger,
    )

    if not puzzles:
        logger.warning("No puzzles generated")
        return []

    # Store puzzles
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    with open(PUZZLES_FILE, "a") as f:
        for p in puzzles:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    logger.info(f"Stored {len(puzzles)} puzzles to {PUZZLES_FILE}")

    # Optionally solve
    if solve:
        logger.info(f"Solving {len(puzzles)} puzzles...")
        for puzzle in puzzles:
            result = solve_puzzle(puzzle, logger)
            store_puzzle_result(result, logger)

        solved = sum(1 for p in puzzles
                     if any(
                         r.get("solved")
                         for r in [_read_results_for(p["id"], logger)]
                     ))
        logger.info(f"Solved: {solved}/{len(puzzles)}")

    return puzzles


def _read_results_for(puzzle_id: str,
                      logger: logging.Logger) -> list[dict]:
    """Read stored results for a specific puzzle."""
    if not PUZZLE_RESULTS_FILE.exists():
        return []
    results = []
    try:
        with open(PUZZLE_RESULTS_FILE) as f:
            for line in f:
                if line.strip():
                    try:
                        r = json.loads(line)
                        if r.get("puzzle_id") == puzzle_id:
                            results.append(r)
                    except json.JSONDecodeError:
                        pass
    except OSError:
        pass
    return results


# ── Daemon loop ────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="N-Xyme Orchestration Puzzle Generator"
    )
    parser.add_argument("--count", type=int, default=5,
                        help="Number of puzzles to generate")
    parser.add_argument("--type", choices=list(PUZZLE_TEMPLATES.keys()),
                        help="Puzzle type filter")
    parser.add_argument("--difficulty", choices=["EASY", "MEDIUM", "HARD"],
                        help="Difficulty filter")
    parser.add_argument("--agent", help="Target agent")
    parser.add_argument("--solve", action="store_true",
                        help="Attempt to solve generated puzzles")
    parser.add_argument("--daemon", action="store_true",
                        help="Continuous generation loop")
    parser.add_argument("--interval", type=int, default=POLL_INTERVAL,
                        help=f"Generation interval (default: {POLL_INTERVAL})")
    parser.add_argument("--once", action="store_true",
                        help="Single generation pass, then exit")
    args = parser.parse_args()

    logger = setup_logging(daemon=args.daemon)
    logger.info("=" * 50)
    logger.info("ORCHESTRATION PUZZLE GENERATOR")
    logger.info("=" * 50)
    logger.info(f"Puzzles file:   {PUZZLES_FILE}")
    logger.info(f"Results file:   {PUZZLE_RESULTS_FILE}")
    logger.info(f"Training data:  {EXAMPLES_FILE}")
    logger.info(f"Puzzle types:   {list(PUZZLE_TEMPLATES.keys())}")

    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    if args.once or not args.daemon:
        generate_pass(
            logger,
            count=args.count,
            puzzle_type=args.type,
            difficulty=args.difficulty,
            target_agent=args.agent,
            solve=args.solve,
        )
        return

    # Continuous loop
    logger.info(f"Generating puzzles every {args.interval}s...")
    while True:
        try:
            generate_pass(
                logger,
                count=args.count,
                puzzle_type=args.type,
                difficulty=args.difficulty,
                target_agent=args.agent,
                solve=args.solve,
            )
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            break
        except Exception as e:
            logger.error(f"Generation error: {e}", exc_info=True)
        time.sleep(args.interval)

    logger.info("Puzzle generator stopped.")


if __name__ == "__main__":
    main()
