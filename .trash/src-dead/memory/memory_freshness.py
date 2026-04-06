"""Memory age and freshness utilities.

Ported from ant-source-code-main/memdir/memoryAge.ts
Provides human-readable age strings for memories.
Models are poor at date arithmetic — "47 days ago" triggers
staleness reasoning better than raw ISO timestamps.
"""

from datetime import datetime, timezone


def memory_age_days(mtime_ms: float) -> int:
    """Days elapsed since mtime. Floor-rounded — 0 for today, 1 for
    yesterday, 2+ for older. Negative inputs (future mtime, clock skew)
    clamp to 0."""
    now_ms = datetime.now(timezone.utc).timestamp() * 1000
    return max(0, int((now_ms - mtime_ms) / 86_400_000))


def memory_age(mtime_ms: float) -> str:
    """Human-readable age string."""
    d = memory_age_days(mtime_ms)
    if d == 0:
        return "today"
    if d == 1:
        return "yesterday"
    return f"{d} days ago"


def memory_freshness_text(mtime_ms: float) -> str:
    """Plain-text staleness caveat for memories >1 day old.
    Returns '' for fresh (today/yesterday) memories — warning there is noise.

    Motivated by user reports of stale code-state memories (file:line
    citations to code that has since changed) being asserted as fact —
    the citation makes the stale claim sound more authoritative, not less.
    """
    d = memory_age_days(mtime_ms)
    if d <= 1:
        return ""
    return (
        f"This memory is {d} days old. "
        "Memories are point-in-time observations, not live state — "
        "claims about code behavior or file:line citations may be outdated. "
        "Verify against current code before asserting as fact."
    )


def memory_freshness_note(mtime_ms: float) -> str:
    """Per-memory staleness note wrapped in <system-reminder> tags.
    Returns '' for memories ≤ 1 day old.
    """
    text = memory_freshness_text(mtime_ms)
    if not text:
        return ""
    return f"<system-reminder>{text}</system-reminder>\n"


def iso_to_ms(iso_str: str) -> float:
    """Convert ISO timestamp to milliseconds since epoch."""
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return dt.timestamp() * 1000


def memory_age_from_iso(iso_str: str) -> str:
    """Get human-readable age from ISO timestamp."""
    ms = iso_to_ms(iso_str)
    return memory_age(ms)


def memory_freshness_from_iso(iso_str: str) -> str:
    """Get freshness note from ISO timestamp."""
    ms = iso_to_ms(iso_str)
    return memory_freshness_note(ms)
