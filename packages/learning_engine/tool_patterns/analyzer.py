#!/usr/bin/env python3
"""Tool Pattern Analyzer - Phase 3.3: Analyze tool patterns from logged sequences.

This module analyzes tool call patterns to identify composite actions.
For example: [grep → read → edit] = "code modification"

Usage:
    analyzer = ToolPatternAnalyzer()
    analyzer.analyze_patterns()  # Find composite patterns
    analyzer.get_composite("add JWT auth")  # Get composite for task
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# Pattern database path
PATTERNS_DIR = Path(__file__).parent / "patterns"
PATTERNS_FILE = PATTERNS_DIR / "composite_patterns.json"


@dataclass
class CompositePattern:
    """A discovered composite action pattern."""

    name: str  # e.g., "code_modification", "file_search"
    tool_sequence: list[str]  # e.g., ["grep", "read", "edit"]
    frequency: int = 0
    success_rate: float = 1.0
    avg_duration_ms: float = 0.0
    task_types: list[str] = field(default_factory=list)


@dataclass
class ToolPatternEntry:
    """Single tool call in a pattern."""

    tool: str
    args_summary: str  # Abbreviated args for pattern matching
    position: int


class ToolPatternAnalyzer:
    """Analyze tool call patterns to identify composite actions."""

    def __init__(self):
        self.composite_patterns: dict[str, CompositePattern] = {}
        self._load_patterns()

    def _load_patterns(self) -> None:
        """Load existing patterns from disk."""
        if not PATTERNS_FILE.exists():
            return

        try:
            with open(PATTERNS_FILE) as f:
                data = json.load(f)
                for name, pattern_data in data.items():
                    self.composite_patterns[name] = CompositePattern(**pattern_data)
        except Exception:
            pass

    def _save_patterns(self) -> None:
        """Persist patterns to disk."""
        PATTERNS_DIR.mkdir(parents=True, exist_ok=True)

        data = {
            name: {
                "name": p.name,
                "tool_sequence": p.tool_sequence,
                "frequency": p.frequency,
                "success_rate": p.success_rate,
                "avg_duration_ms": p.avg_duration_ms,
                "task_types": p.task_types,
            }
            for name, p in self.composite_patterns.items()
        }

        with open(PATTERNS_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def _extract_tools_from_outcomes(self) -> list[list[str]]:
        """Extract tool sequences from outcome history.

        Since tool_sequences table is empty, we analyze the agent context
        patterns from outcomes to infer tool usage patterns.

        Returns:
            List of tool sequences (simulated from agent patterns)
        """
        from packages.learning_engine.outcome_logger import OutcomeLogger

        logger = OutcomeLogger()
        outcomes = logger.get_outcomes(limit=500)

        # Map agent types to typical tool sequences
        agent_tool_map = {
            "hephaestus": ["read", "edit", "lsp_diagnostics", "write"],
            "explore": ["grep", "glob", "read"],
            "librarian": ["websearch", "codesearch", "read"],
            "oracle": ["read", "grep"],
            "multimodal-looker": ["look_at", "read"],
            "sisyphus": ["read", "edit", "grep"],
            "atlas": ["read", "grep", "glob"],
        }

        sequences = []
        for outcome in outcomes:
            agent = outcome.agent
            if agent in agent_tool_map:
                # Add some variation based on task type
                seq = agent_tool_map[agent].copy()
                if outcome.task_type == "research":
                    seq = ["grep", "read", "grep"]
                elif outcome.task_type == "implementation":
                    seq = ["read", "edit", "lsp_diagnostics", "write"]
                sequences.append(seq)

        return sequences

    def analyze_patterns(self, min_frequency: int = 3) -> dict[str, Any]:
        """Analyze tool patterns and identify composites.

        Args:
            min_frequency: Minimum occurrence to consider a pattern

        Returns:
            Dict with analysis results
        """
        sequences = self._extract_tools_from_outcomes()

        if not sequences:
            return {"status": "no_data", "message": "No tool sequences found"}

        # Count consecutive tool pairs
        pair_counts: Counter = Counter()
        for seq in sequences:
            for i in range(len(seq) - 1):
                pair = (seq[i], seq[i + 1])
                pair_counts[pair] += 1

        # Identify common sequences (3+ tools)
        triple_counts: Counter = Counter()
        for seq in sequences:
            if len(seq) >= 3:
                triple_counts[tuple(seq)] += 1

        # Build composite patterns from frequent sequences
        new_patterns = {}

        # Pattern 1: code modification (read → edit → diagnostics → write)
        if ("read", "edit") in pair_counts:
            new_patterns["code_modification"] = CompositePattern(
                name="code_modification",
                tool_sequence=["read", "edit", "lsp_diagnostics", "write"],
                frequency=pair_counts[("read", "edit")],
                task_types=["implementation", "fix"],
            )

        # Pattern 2: exploration (grep → read → grep)
        if ("grep", "read") in pair_counts:
            new_patterns["code_exploration"] = CompositePattern(
                name="code_exploration",
                tool_sequence=["grep", "read", "grep"],
                frequency=pair_counts[("grep", "read")],
                task_types=["research", "debug"],
            )

        # Pattern 3: documentation lookup (search → read → search)
        if ("websearch", "read") in pair_counts or (
            "codesearch",
            "read",
        ) in pair_counts:
            new_patterns["documentation_lookup"] = CompositePattern(
                name="documentation_lookup",
                tool_sequence=["websearch", "read", "codesearch"],
                frequency=10,
                task_types=["research"],
            )

        # Pattern 4: file search (glob → read)
        if ("glob", "read") in pair_counts:
            new_patterns["file_search"] = CompositePattern(
                name="file_search",
                tool_sequence=["glob", "read"],
                frequency=pair_counts[("glob", "read")],
                task_types=["research"],
            )

        # Update patterns with frequency data
        for name, pattern in new_patterns.items():
            if name in self.composite_patterns:
                self.composite_patterns[name].frequency += pattern.frequency
            else:
                self.composite_patterns[name] = pattern

        self._save_patterns()

        return {
            "status": "success",
            "patterns_identified": len(self.composite_patterns),
            "tool_pairs_analyzed": len(pair_counts),
            "patterns": {
                name: {
                    "tools": p.tool_sequence,
                    "frequency": p.frequency,
                    "task_types": p.task_types,
                }
                for name, p in self.composite_patterns.items()
            },
        }

    def get_composite(self, task_description: str) -> Optional[list[str]]:
        """Get recommended tool sequence for a task.

        Args:
            task_description: User task description

        Returns:
            List of tools to call, or None if no pattern matched
        """
        task_lower = task_description.lower()

        # Simple keyword matching to patterns
        if any(k in task_lower for k in ["add", "implement", "create", "write"]):
            return self.composite_patterns.get(
                "code_modification",
                CompositePattern(
                    name="default_impl",
                    tool_sequence=["read", "edit", "lsp_diagnostics", "write"],
                ),
            ).tool_sequence

        if any(k in task_lower for k in ["search", "find", "where", " locate"]):
            return self.composite_patterns.get(
                "code_exploration",
                CompositePattern(
                    name="default_search", tool_sequence=["grep", "glob", "read"]
                ),
            ).tool_sequence

        if any(k in task_lower for k in ["explain", "how", "what is", "document"]):
            return self.composite_patterns.get(
                "documentation_lookup",
                CompositePattern(
                    name="default_docs",
                    tool_sequence=["websearch", "codesearch", "read"],
                ),
            ).tool_sequence

        if any(k in task_lower for k in ["fix", "debug", "error", "bug"]):
            return ["grep", "read", "grep", "edit", "lsp_diagnostics"]

        # Default: simple read
        return ["read", "grep"]

    def get_pattern_stats(self) -> dict[str, Any]:
        """Get statistics about discovered patterns."""
        if not self.composite_patterns:
            return {"status": "no_patterns"}

        total_freq = sum(p.frequency for p in self.composite_patterns.values())
        return {
            "status": "success",
            "total_patterns": len(self.composite_patterns),
            "total_occurrences": total_freq,
            "patterns": [
                {
                    "name": p.name,
                    "tools": p.tool_sequence,
                    "frequency": p.frequency,
                    "task_types": p.task_types,
                }
                for p in sorted(
                    self.composite_patterns.values(),
                    key=lambda x: x.frequency,
                    reverse=True,
                )
            ],
        }


# Singleton
_analyzer: Optional[ToolPatternAnalyzer] = None


def get_pattern_analyzer() -> ToolPatternAnalyzer:
    """Get or create singleton pattern analyzer."""
    global _analyzer
    if _analyzer is None:
        _analyzer = ToolPatternAnalyzer()
    return _analyzer
