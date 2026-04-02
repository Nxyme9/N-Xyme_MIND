"""
athena.boot.loaders.context_summaries
======================================
Tier 0 Pre-computation: Generates compressed summaries of Memory Bank files
for fast query routing without loading full documents.

Philosophy (Min-Latency × Max-Effectiveness):
    Full documents (e.g., System_Principles.md at 800 lines) are expensive
    to load for every query. Compressed summaries (~500 tokens each) let the
    classifier make better routing decisions at near-zero cost.

    Summaries are generated at boot and cached. They update only when the
    source file changes (hash-based delta detection).

Origin: Session 04, Feb 2026 (Workspace Optimization Analysis)
"""

import hashlib
import json
import logging
from pathlib import Path

from athena.boot.constants import DIM, GREEN, PROJECT_ROOT, RESET

logger = logging.getLogger("athena.boot.context_summaries")

# === Configuration ===

# Files to pre-summarize (path relative to PROJECT_ROOT)
SUMMARY_SOURCES = {
    "userContext": ".context/memory_bank/userContext.md",
    "productContext": ".context/memory_bank/productContext.md",
    "activeContext": ".context/memory_bank/activeContext.md",
    "systemPatterns": ".context/memory_bank/systemPatterns.md",
    "decisionLog": ".context/memory_bank/decisionLog.md",
    "semanticLog": ".context/memory_bank/semantic_log.md",
}

# Cache location
SUMMARY_CACHE_DIR = PROJECT_ROOT / ".agent" / "state" / "context_cache"
SUMMARY_CACHE_FILE = SUMMARY_CACHE_DIR / "summaries.json"
HASH_CACHE_FILE = SUMMARY_CACHE_DIR / "hashes.json"

# Target summary length (in characters, ~125 tokens)
MAX_SUMMARY_CHARS = 500


def _file_hash(path: Path) -> str:
    """SHA-256 hash of file contents for delta detection."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    except Exception:
        return ""


def _extract_summary(path: Path) -> str:
    """Extract a compressed summary from a Memory Bank file.

    Strategy: Take the first heading + first N characters of content.
    This is a heuristic extraction, not LLM-generated — zero API cost.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return ""

    lines = content.strip().splitlines()
    if not lines:
        return ""

    # Collect: first H1/H2, then first substantive lines
    summary_parts = []
    char_count = 0

    for line in lines:
        stripped = line.strip()
        # Skip YAML frontmatter
        if stripped == "---":
            continue
        # Skip empty lines
        if not stripped:
            continue
        # Skip YAML metadata keys (only in frontmatter region)
        if (
            char_count == 0
            and ":" in stripped
            and stripped.split(":")[0].strip().replace("_", "").isalpha()
            and not stripped.startswith("#")
        ):
            continue

        summary_parts.append(stripped)
        char_count += len(stripped)

        if char_count >= MAX_SUMMARY_CHARS:
            break

    result = " | ".join(summary_parts)
    return result[:MAX_SUMMARY_CHARS]


def generate_summaries(force: bool = False) -> dict:
    """Generate compressed summaries for all Memory Bank files.

    Uses hash-based delta detection: only regenerates if source changed.

    Args:
        force: If True, regenerate all summaries regardless of cache.

    Returns:
        dict: {name: summary_text, ...}
    """
    SUMMARY_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Load existing caches
    existing_hashes = {}
    existing_summaries = {}
    if not force:
        try:
            if HASH_CACHE_FILE.exists():
                existing_hashes = json.loads(HASH_CACHE_FILE.read_text())
            if SUMMARY_CACHE_FILE.exists():
                existing_summaries = json.loads(SUMMARY_CACHE_FILE.read_text())
        except Exception:
            pass

    summaries = {}
    updated = 0

    for name, rel_path in SUMMARY_SOURCES.items():
        full_path = PROJECT_ROOT / rel_path
        if not full_path.exists():
            summaries[name] = ""
            continue

        current_hash = _file_hash(full_path)

        # Delta detection: skip if unchanged
        if (
            not force
            and name in existing_hashes
            and existing_hashes[name] == current_hash
            and name in existing_summaries
        ):
            summaries[name] = existing_summaries[name]
            continue

        # Generate new summary
        summaries[name] = _extract_summary(full_path)
        existing_hashes[name] = current_hash
        updated += 1

    # Save caches
    try:
        SUMMARY_CACHE_FILE.write_text(json.dumps(summaries, indent=2))
        HASH_CACHE_FILE.write_text(json.dumps(existing_hashes, indent=2))
    except Exception as e:
        logger.warning("Failed to save summary cache: %s", e)

    return summaries


def get_cached_summaries() -> dict | None:
    """Load pre-computed summaries from cache (zero-cost retrieval)."""
    try:
        if SUMMARY_CACHE_FILE.exists():
            return json.loads(SUMMARY_CACHE_FILE.read_text())
    except Exception:
        pass
    return None


def display_summary_status(summaries: dict):
    """Display summary generation status during boot."""
    total = len(summaries)
    non_empty = sum(1 for v in summaries.values() if v)
    print(
        f"   {GREEN}📋 Context Summaries: {non_empty}/{total} files pre-computed.{RESET}"
    )
    for name, summary in summaries.items():
        preview = summary[:60] + "..." if len(summary) > 60 else summary
        if summary:
            print(f"   {DIM}   ✅ {name}: {preview}{RESET}")
        else:
            print(f"   {DIM}   ⚠️  {name}: (empty/missing){RESET}")
