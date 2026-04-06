"""Memory type taxonomy — adapted from Claude Code's memory system.

Four discrete types capturing context NOT derivable from the current
project state. Code patterns, architecture, git history, and file
structure are derivable (via grep/git) and should NOT be saved as memories.
"""

from enum import Enum
from typing import Optional


class MemoryType(str, Enum):
    """Four memory types from Claude Code's proven taxonomy."""

    USER = "user"
    FEEDBACK = "feedback"
    PROJECT = "project"
    REFERENCE = "reference"


# Human-readable descriptions
MEMORY_TYPE_DESCRIPTIONS = {
    MemoryType.USER: (
        "Information about the user's role, goals, preferences, responsibilities, "
        "and knowledge. Helps tailor future behavior to the user's perspective."
    ),
    MemoryType.FEEDBACK: (
        "Guidance the user has given about how to approach work — both what to avoid "
        "and what to keep doing. Record from failure AND success."
    ),
    MemoryType.PROJECT: (
        "Information about ongoing work, goals, initiatives, bugs, or incidents "
        "that is not derivable from code or git history."
    ),
    MemoryType.REFERENCE: (
        "Pointers to where information can be found in external systems "
        "(e.g., Linear projects, Slack channels, Grafana dashboards)."
    ),
}

# When to save each type
MEMORY_TYPE_WHEN_TO_SAVE = {
    MemoryType.USER: (
        "When you learn details about the user's role, preferences, "
        "responsibilities, or knowledge."
    ),
    MemoryType.FEEDBACK: (
        "Any time the user corrects your approach OR confirms a non-obvious "
        "approach worked. Record from failure AND success."
    ),
    MemoryType.PROJECT: (
        "When you learn who is doing what, why, or by when. Convert relative "
        "dates to absolute dates when saving."
    ),
    MemoryType.REFERENCE: (
        "When you learn about resources in external systems and their purpose."
    ),
}


def parse_memory_type(raw: Optional[str]) -> Optional[MemoryType]:
    """Parse a raw string into a MemoryType.

    Invalid or missing values return None — legacy memories without a
    `type:` field keep working, memories with unknown types degrade gracefully.
    """
    if not raw:
        return None
    try:
        return MemoryType(raw.lower().strip())
    except ValueError:
        return None


def get_memory_type_prompt(memory_type: MemoryType) -> str:
    """Get the system prompt section for a memory type."""
    desc = MEMORY_TYPE_DESCRIPTIONS.get(memory_type, "")
    when = MEMORY_TYPE_WHEN_TO_SAVE.get(memory_type, "")
    return f"""## Memory Type: {memory_type.value}

**Description**: {desc}

**When to save**: {when}
"""


def get_all_memory_types_prompt() -> str:
    """Get the full memory types section for system prompts."""
    sections = []
    for mt in MemoryType:
        sections.append(get_memory_type_prompt(mt))
    return "\n".join(sections)
