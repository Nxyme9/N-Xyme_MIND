"""Memory Extractor — Durable memory extraction from session transcripts.

Ported from ant-source-code-main/services/extractMemories/
Extracts durable memories from session transcripts and writes them to
the auto-memory directory (~/.n-xyme/projects/<path>/memory/).

Pattern: Runs at end of each complete query loop. Uses LLM to identify
key facts, decisions, corrections, and learnings from the conversation
and saves them as structured markdown files with YAML frontmatter.

Memory types (from ant-source memoryTypes.ts):
- user: Information about the user's role, goals, preferences
- feedback: Guidance on how to approach work (corrections + confirmations)
- project: Ongoing work, goals, initiatives, bugs, incidents
- reference: Pointers to external systems (Linear, Slack, Grafana, etc.)
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MEMORY_TYPES = ["user", "feedback", "project", "reference"]
MEMORY_DIR_NAME = "memory"
FRONTMATTER_DELIMITER = "---"

# What NOT to save as memory (derivable from code/git)
WHAT_NOT_TO_SAVE = [
    "Code patterns derivable from reading the code",
    "Architecture derivable from file structure",
    "Git history derivable from git log",
    "File structure derivable from ls/glob",
    "Dependencies derivable from package.json/pyproject.toml",
    "API endpoints derivable from route definitions",
    "Test results derivable from running tests",
]


@dataclass
class MemoryEntry:
    """A single durable memory entry."""

    type: str  # user, feedback, project, reference
    content: str
    why: str = ""  # Why this memory is important
    how_to_apply: str = ""  # How to use this memory
    scope: str = "private"  # private or team
    source_session: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    tags: list[str] = field(default_factory=list)

    def to_frontmatter(self) -> str:
        """Convert to markdown with YAML frontmatter."""
        fm_lines = [
            FRONTMATTER_DELIMITER,
            f"type: {self.type}",
            f"scope: {self.scope}",
            f"created: {self.timestamp}",
        ]
        if self.source_session:
            fm_lines.append(f"source_session: {self.source_session}")
        if self.tags:
            fm_lines.append(f"tags: {json.dumps(self.tags)}")
        fm_lines.append(FRONTMATTER_DELIMITER)
        fm_lines.append("")

        # Body structure: lead with rule, then Why and How to apply
        body_lines = [self.content]
        if self.why:
            body_lines.append(f"\n**Why:** {self.why}")
        if self.how_to_apply:
            body_lines.append(f"\n**How to apply:** {self.how_to_apply}")

        return "\n".join(fm_lines + body_lines) + "\n"

    def to_filename(self) -> str:
        """Generate a filename from the memory content."""
        # First 50 chars, slugified
        slug = re.sub(r"[^a-z0-9]+", "-", self.content[:50].lower()).strip("-")
        return f"{slug}.md"


@dataclass
class ExtractionResult:
    """Result of memory extraction from a session."""

    session_id: str
    memories_extracted: int
    memories_saved: int
    memories_skipped: int
    errors: list[str] = field(default_factory=list)
    extraction_time_ms: float = 0.0


class MemoryExtractor:
    """Extracts durable memories from session transcripts."""

    def __init__(self, memory_dir: Path | None = None):
        """Initialize extractor.

        Args:
            memory_dir: Directory to save memories. Defaults to
                ~/.n-xyme/memory/
        """
        if memory_dir is None:
            memory_dir = Path.home() / ".n-xyme" / MEMORY_DIR_NAME
        self.memory_dir = memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def extract_from_transcript(
        self,
        session_id: str,
        transcript: str,
        existing_memories: list[MemoryEntry] | None = None,
    ) -> ExtractionResult:
        """Extract memories from a session transcript.

        This is the core extraction method. In production, this would use
        an LLM to analyze the transcript and identify key memories. For now,
        it uses pattern matching to identify common memory-worthy patterns.

        Args:
            session_id: Session identifier.
            transcript: Full session transcript.
            existing_memories: Existing memories to avoid duplicates.

        Returns:
            ExtractionResult with counts and any errors.
        """
        start_time = datetime.now(timezone.utc).timestamp() * 1000
        memories = []
        errors = []

        # Pattern 1: User corrections ("don't", "stop", "no not that")
        corrections = self._extract_corrections(transcript)
        memories.extend(corrections)

        # Pattern 2: User confirmations ("yes exactly", "perfect", "keep doing")
        confirmations = self._extract_confirmations(transcript)
        memories.extend(confirmations)

        # Pattern 3: User preferences ("I prefer", "I like", "I want")
        preferences = self._extract_preferences(transcript)
        memories.extend(preferences)

        # Pattern 4: Project decisions ("we decided", "we're going to")
        decisions = self._extract_decisions(transcript)
        memories.extend(decisions)

        # Pattern 5: External references ("tracked in", "check the", "look at")
        references = self._extract_references(transcript)
        memories.extend(references)

        # Deduplicate against existing memories
        if existing_memories:
            memories = self._deduplicate(memories, existing_memories)

        # Save memories
        saved = 0
        skipped = 0
        for memory in memories:
            memory.source_session = session_id
            try:
                self._save_memory(memory)
                saved += 1
            except Exception as e:
                errors.append(f"Failed to save memory: {e}")
                skipped += 1

        elapsed = datetime.now(timezone.utc).timestamp() * 1000 - start_time

        return ExtractionResult(
            session_id=session_id,
            memories_extracted=len(memories),
            memories_saved=saved,
            memories_skipped=skipped,
            errors=errors,
            extraction_time_ms=elapsed,
        )

    def _extract_corrections(self, transcript: str) -> list[MemoryEntry]:
        """Extract user corrections from transcript."""
        memories = []
        # Look for correction patterns
        patterns = [
            r"(?:don't|do not|stop|no|not that|wrong|incorrect)[,:.\s]+(.{20,200})",
            r"(?:never|always|must|should)[,:.\s]+(.{20,200})",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, transcript, re.IGNORECASE):
                content = match.group(1).strip()
                if len(content) > 10:
                    memories.append(
                        MemoryEntry(
                            type="feedback",
                            content=f"Avoid: {content}",
                            why="User explicitly corrected this approach",
                            how_to_apply="Do not use this approach in future",
                            scope="private",
                            tags=["correction"],
                        )
                    )
        return memories

    def _extract_confirmations(self, transcript: str) -> list[MemoryEntry]:
        """Extract user confirmations from transcript."""
        memories = []
        patterns = [
            r"(?:yes|exactly|perfect|good|great|keep doing|right)[,:.\s]+(.{20,200})",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, transcript, re.IGNORECASE):
                content = match.group(1).strip()
                if len(content) > 10:
                    memories.append(
                        MemoryEntry(
                            type="feedback",
                            content=f"Keep doing: {content}",
                            why="User confirmed this approach works",
                            how_to_apply="Continue using this approach",
                            scope="private",
                            tags=["confirmation"],
                        )
                    )
        return memories

    def _extract_preferences(self, transcript: str) -> list[MemoryEntry]:
        """Extract user preferences from transcript."""
        memories = []
        patterns = [
            r"(?:I prefer|I like|I want|I need|I'd like)[,:.\s]+(.{20,200})",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, transcript, re.IGNORECASE):
                content = match.group(1).strip()
                if len(content) > 10:
                    memories.append(
                        MemoryEntry(
                            type="user",
                            content=f"Preference: {content}",
                            why="User explicitly stated this preference",
                            how_to_apply="Tailor behavior to this preference",
                            scope="private",
                            tags=["preference"],
                        )
                    )
        return memories

    def _extract_decisions(self, transcript: str) -> list[MemoryEntry]:
        """Extract project decisions from transcript."""
        memories = []
        patterns = [
            r"(?:we decided|we're going to|we will|we should|let's)[,:.\s]+(.{20,200})",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, transcript, re.IGNORECASE):
                content = match.group(1).strip()
                if len(content) > 10:
                    memories.append(
                        MemoryEntry(
                            type="project",
                            content=f"Decision: {content}",
                            why="Team decision affecting project direction",
                            how_to_apply="Follow this decision in future work",
                            scope="team",
                            tags=["decision"],
                        )
                    )
        return memories

    def _extract_references(self, transcript: str) -> list[MemoryEntry]:
        """Extract external references from transcript."""
        memories = []
        patterns = [
            r"(?:tracked in|check the|look at|see the|refer to)[,:.\s]+(.{20,200})",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, transcript, re.IGNORECASE):
                content = match.group(1).strip()
                if len(content) > 10:
                    memories.append(
                        MemoryEntry(
                            type="reference",
                            content=f"Reference: {content}",
                            why="External system or resource mentioned",
                            how_to_apply="Use this reference when relevant",
                            scope="team",
                            tags=["reference"],
                        )
                    )
        return memories

    def _deduplicate(
        self,
        new_memories: list[MemoryEntry],
        existing: list[MemoryEntry],
    ) -> list[MemoryEntry]:
        """Remove memories that already exist."""
        existing_contents = {e.content.lower() for e in existing}
        return [m for m in new_memories if m.content.lower() not in existing_contents]

    def _save_memory(self, memory: MemoryEntry) -> None:
        """Save a memory entry to disk."""
        filename = memory.to_filename()
        filepath = self.memory_dir / filename

        # Avoid overwriting existing files
        counter = 1
        while filepath.exists():
            filename = memory.to_filename().replace(".md", f"_{counter}.md")
            filepath = self.memory_dir / filename
            counter += 1

        filepath.write_text(memory.to_frontmatter())
        logger.info(f"Saved memory: {filepath}")

    def load_existing_memories(self) -> list[MemoryEntry]:
        """Load all existing memories from disk."""
        memories = []
        for filepath in self.memory_dir.glob("*.md"):
            try:
                content = filepath.read_text()
                memory = self._parse_memory_file(content, str(filepath))
                if memory:
                    memories.append(memory)
            except Exception as e:
                logger.warning(f"Failed to parse memory file {filepath}: {e}")
        return memories

    def _parse_memory_file(self, content: str, filepath: str) -> MemoryEntry | None:
        """Parse a memory markdown file into a MemoryEntry."""
        # Extract frontmatter
        if not content.startswith(FRONTMATTER_DELIMITER):
            return None

        parts = content.split(FRONTMATTER_DELIMITER, 2)
        if len(parts) < 3:
            return None

        fm_text = parts[1].strip()
        body = parts[2].strip()

        # Parse frontmatter
        fm: dict[str, Any] = {}
        for line in fm_text.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                fm[key.strip()] = value.strip().strip('"')

        # Parse body
        why = ""
        how_to_apply = ""
        content_text = body

        if "**Why:**" in body:
            parts = body.split("**Why:**", 1)
            content_text = parts[0].strip()
            rest = parts[1]
            if "**How to apply:**" in rest:
                why_part, how_part = rest.split("**How to apply:**", 1)
                why = why_part.strip()
                how_to_apply = how_part.strip()
            else:
                why = rest.strip()

        return MemoryEntry(
            type=fm.get("type", "project"),
            content=content_text,
            why=why,
            how_to_apply=how_to_apply,
            scope=fm.get("scope", "private"),
            source_session=fm.get("source_session", ""),
            timestamp=fm.get("created", datetime.now(timezone.utc).isoformat()),
            tags=json.loads(fm.get("tags", "[]")),
        )

    def get_summary(self) -> dict[str, Any]:
        """Get summary of all memories."""
        memories = self.load_existing_memories()
        by_type: dict[str, int] = {}
        by_scope: dict[str, int] = {}
        for m in memories:
            by_type[m.type] = by_type.get(m.type, 0) + 1
            by_scope[m.scope] = by_scope.get(m.scope, 0) + 1

        return {
            "total_memories": len(memories),
            "by_type": by_type,
            "by_scope": by_scope,
            "memory_dir": str(self.memory_dir),
        }
