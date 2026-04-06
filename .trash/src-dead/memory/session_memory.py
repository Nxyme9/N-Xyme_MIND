"""Session Memory — Auto-maintained session notes.

Ported from ant-source-code-main/services/SessionMemory/
Automatically maintains a markdown file with notes about the current session.
Tracks: current state, decisions, errors, corrections, learnings, key results.

Pattern: Session notes are updated periodically during conversation to maintain
continuity across compaction, context window limits, and session resumption.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SESSION_NOTES_TEMPLATE = """# Session Title
_A short and distinctive 5-10 word descriptive title for the session_

# Current State
_What is actively being worked on right now? Pending tasks. Immediate next steps._

# Task Specification
_What did the user ask to build? Design decisions or explanatory context._

# Files and Functions
_Important files, what they contain, why they're relevant._

# Workflow
_Bash commands usually run and in what order. How to interpret output._

# Errors & Corrections
_Errors encountered and how they were fixed. What did the user correct?
What approaches failed and should not be tried again?_

# Codebase and System Documentation
_Important system components. How do they work/fit together?_

# Learnings
_What has worked well? What has not? What to avoid?_

# Key Results
_If the user asked for specific output (answer, table, document), repeat it here._

# Worklog
_Terse step-by-step summary of what was attempted and done._
"""

SECTIONS = [
    "Session Title",
    "Current State",
    "Task Specification",
    "Files and Functions",
    "Workflow",
    "Errors & Corrections",
    "Codebase and System Documentation",
    "Learnings",
    "Key Results",
    "Worklog",
]

MAX_SECTION_LENGTH = 2000
MAX_TOTAL_TOKENS = 12000


@dataclass
class SessionNote:
    """A single note entry within a section."""

    section: str
    content: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    tags: list[str] = field(default_factory=list)


@dataclass
class SessionMemory:
    """Auto-maintained session notes."""

    session_id: str
    notes_path: Path
    sections: dict[str, list[SessionNote]] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self):
        """Initialize empty sections from template."""
        for section in SECTIONS:
            if section not in self.sections:
                self.sections[section] = []

    def add_note(
        self, section: str, content: str, tags: list[str] | None = None
    ) -> None:
        """Add a note to a section.

        Args:
            section: Section name (must be one of SECTIONS).
            content: Note content.
            tags: Optional tags for filtering.
        """
        if section not in self.sections:
            logger.warning(f"Unknown section: {section}. Creating it.")
            self.sections[section] = []

        note = SessionNote(
            section=section,
            content=content,
            tags=tags or [],
        )
        self.sections[section].append(note)
        self.updated_at = datetime.now(timezone.utc).isoformat()

        # Enforce section length limit
        self._trim_section(section)

    def _trim_section(self, section: str) -> None:
        """Trim section content to stay within token limits."""
        notes = self.sections.get(section, [])
        total_len = sum(len(n.content) for n in notes)

        while total_len > MAX_SECTION_LENGTH and notes:
            removed = notes.pop(0)  # Remove oldest
            total_len -= len(removed.content)

    def get_section(self, section: str) -> list[SessionNote]:
        """Get all notes in a section."""
        return self.sections.get(section, [])

    def get_notes_by_tag(self, tag: str) -> list[SessionNote]:
        """Get all notes with a specific tag across all sections."""
        results = []
        for notes in self.sections.values():
            results.extend(n for n in notes if tag in n.tags)
        return results

    def render(self) -> str:
        """Render session notes as markdown."""
        lines = []
        for section in SECTIONS:
            notes = self.sections.get(section, [])
            lines.append(f"# {section}")
            if notes:
                for note in notes:
                    lines.append(note.content)
            else:
                lines.append("_No entries yet._")
            lines.append("")

        lines.append(f"_Last updated: {self.updated_at}_")
        return "\n".join(lines)

    def save(self) -> None:
        """Save session notes to disk."""
        self.notes_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "sections": {
                section: [
                    {
                        "section": n.section,
                        "content": n.content,
                        "timestamp": n.timestamp,
                        "tags": n.tags,
                    }
                    for n in notes
                ]
                for section, notes in self.sections.items()
            },
        }
        self.notes_path.write_text(json.dumps(data, indent=2))
        logger.info(f"Session notes saved: {self.notes_path}")

    @classmethod
    def load(cls, session_id: str, notes_path: Path) -> "SessionMemory":
        """Load session notes from disk."""
        if notes_path.exists():
            data = json.loads(notes_path.read_text())
            memory = cls(
                session_id=session_id,
                notes_path=notes_path,
                created_at=data.get(
                    "created_at", datetime.now(timezone.utc).isoformat()
                ),
                updated_at=data.get(
                    "updated_at", datetime.now(timezone.utc).isoformat()
                ),
            )
            for section, notes in data.get("sections", {}).items():
                memory.sections[section] = [
                    SessionNote(
                        section=n["section"],
                        content=n["content"],
                        timestamp=n.get(
                            "timestamp", datetime.now(timezone.utc).isoformat()
                        ),
                        tags=n.get("tags", []),
                    )
                    for n in notes
                ]
            return memory

        return cls(session_id=session_id, notes_path=notes_path)

    def update_current_state(self, state: str) -> None:
        """Convenience: update current state (replaces all existing state notes)."""
        self.sections["Current State"] = []
        self.add_note("Current State", state)

    def log_error(self, error: str, fix: str | None = None) -> None:
        """Convenience: log an error and its fix."""
        content = f"**Error:** {error}"
        if fix:
            content += f"\n**Fix:** {fix}"
        self.add_note("Errors & Corrections", content, tags=["error"])

    def log_decision(self, decision: str, rationale: str | None = None) -> None:
        """Convenience: log a design decision."""
        content = f"**Decision:** {decision}"
        if rationale:
            content += f"\n**Rationale:** {rationale}"
        self.add_note("Task Specification", content, tags=["decision"])

    def log_learning(self, learning: str) -> None:
        """Convenience: log a learning."""
        self.add_note("Learnings", learning, tags=["learning"])

    def log_worklog(self, step: str) -> None:
        """Convenience: log a worklog entry."""
        self.add_note("Worklog", step, tags=["worklog"])

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of session memory for quick inspection."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "total_notes": sum(len(notes) for notes in self.sections.values()),
            "sections": {
                section: len(notes) for section, notes in self.sections.items() if notes
            },
        }
