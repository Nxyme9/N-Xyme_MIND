#!/usr/bin/env python3
"""
Anti-Pattern Detector
=====================
Scans session logs for recurring anti-patterns that waste tokens and time:

1. Repeated Questions — same question asked across 3+ sessions
2. Unresolved Deferrals — items deferred but never resolved
3. Session Thrashing — multiple short sessions on the same day

Inspired by vexp's dead-end exploration and file thrashing detection.

Usage:
    python -m athena.auditors.audit_antipatterns
"""

import re
from collections import Counter, defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

# ── ANSI Colors ──
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

# ── Configuration ──
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SESSION_LOG_DIR = PROJECT_ROOT / ".context" / "memories" / "session_logs"

# Similarity threshold for "repeated question" detection (0.0 - 1.0)
SIMILARITY_THRESHOLD = 0.65
# Minimum sessions a question must appear in to be flagged
MIN_REPEAT_COUNT = 3


def extract_session_date(filename: str) -> datetime | None:
    """Extract date from session log filename."""
    match = re.match(r"(\d{4}-\d{2}-\d{2})", filename)
    if match:
        return datetime.strptime(match.group(1), "%Y-%m-%d")
    return None


def extract_questions(content: str) -> list[str]:
    """Extract lines that look like questions from session content."""
    questions = []
    for line in content.split("\n"):
        line = line.strip()
        # Lines ending with ? that are substantial (>20 chars)
        if line.endswith("?") and len(line) > 20:
            # Strip markdown formatting
            clean = re.sub(r"[#*>`\-]", "", line).strip()
            if clean:
                questions.append(clean)
    return questions


def extract_deferrals(content: str) -> list[str]:
    """Extract deferred items from session logs."""
    deferrals = []
    in_deferred_section = False

    for line in content.split("\n"):
        stripped = line.strip()
        # Detect deferral sections
        if re.search(
            r"[Dd]eferred|[Nn]ext [Ss]ession|[Tt]odo|[Cc]arry [Ff]orward", stripped
        ):
            in_deferred_section = True
            continue
        if in_deferred_section:
            # New heading = end of section
            if stripped.startswith("#"):
                in_deferred_section = False
                continue
            # Bullet point items
            if re.match(r"^[-*]\s+.{10,}", stripped):
                item = re.sub(r"^[-*]\s+", "", stripped)
                if item and item != "-":
                    deferrals.append(item)

    return deferrals


def find_similar_questions(all_questions: dict[str, list[str]]) -> list[dict]:
    """Find questions that appear across multiple sessions (fuzzy match)."""
    # Flatten to (question, session) pairs
    pairs = []
    for session, questions in all_questions.items():
        for q in questions:
            pairs.append((q, session))

    # Group similar questions
    clusters = []
    used = set()

    for i, (q1, s1) in enumerate(pairs):
        if i in used:
            continue
        cluster = [(q1, s1)]
        used.add(i)

        for j, (q2, s2) in enumerate(pairs):
            if j in used or s1 == s2:
                continue
            similarity = SequenceMatcher(None, q1.lower(), q2.lower()).ratio()
            if similarity >= SIMILARITY_THRESHOLD:
                cluster.append((q2, s2))
                used.add(j)

        # Only flag if question appears across MIN_REPEAT_COUNT+ sessions
        unique_sessions = set(s for _, s in cluster)
        if len(unique_sessions) >= MIN_REPEAT_COUNT:
            clusters.append(
                {
                    "question": q1[:80],
                    "sessions": sorted(unique_sessions),
                    "count": len(unique_sessions),
                }
            )

    return clusters


def detect_session_thrashing(session_files: list[Path]) -> list[dict]:
    """Detect days with multiple short sessions (possible thrashing)."""
    sessions_by_date = defaultdict(list)

    for f in session_files:
        date = extract_session_date(f.name)
        if date:
            date_str = date.strftime("%Y-%m-%d")
            sessions_by_date[date_str].append(f)

    thrashing = []
    for date_str, files in sessions_by_date.items():
        if len(files) >= 4:
            thrashing.append(
                {
                    "date": date_str,
                    "count": len(files),
                    "files": [f.name for f in files],
                }
            )

    return sorted(thrashing, key=lambda x: x["count"], reverse=True)


def detect_unresolved_deferrals(session_files: list[Path]) -> list[dict]:
    """Find items deferred in early sessions that never appear as resolved."""
    all_deferrals = {}
    all_content = []

    # Collect deferrals and all content
    for f in sorted(session_files):
        try:
            content = f.read_text(encoding="utf-8")
        except Exception:
            continue
        all_content.append(content)
        deferrals = extract_deferrals(content)
        if deferrals:
            all_deferrals[f.name] = deferrals

    # Check if deferred items appear as "completed" or "done" in later sessions
    combined_content = "\n".join(all_content).lower()
    unresolved = []

    for session, items in all_deferrals.items():
        for item in items:
            # Simple heuristic: check if keywords from the deferral appear near "done"/"completed"
            keywords = [w for w in item.lower().split() if len(w) > 4][:3]
            appears_resolved = False
            for kw in keywords:
                # Check if keyword appears in a "completed" context
                if re.search(
                    rf"(completed|done|resolved|finished|fixed).*{re.escape(kw)}",
                    combined_content,
                ):
                    appears_resolved = True
                    break
                if re.search(
                    rf"{re.escape(kw)}.*(completed|done|resolved|finished|fixed)",
                    combined_content,
                ):
                    appears_resolved = True
                    break

            if not appears_resolved:
                unresolved.append(
                    {
                        "session": session,
                        "item": item[:80],
                    }
                )

    return unresolved


def audit_antipatterns():
    """Run the anti-pattern audit."""
    print(f"\n{BOLD}{CYAN}🔄 ANTI-PATTERN DETECTOR{RESET}")
    print(f"{CYAN}{'━' * 70}{RESET}")
    print(
        f"{DIM}Scanning session logs for repeated questions, unresolved deferrals, and thrashing...{RESET}\n"
    )

    if not SESSION_LOG_DIR.exists():
        print(f"{YELLOW}⚠️  No session logs found at {SESSION_LOG_DIR}{RESET}")
        return

    session_files = sorted(SESSION_LOG_DIR.glob("*.md"))
    if not session_files:
        print(f"{YELLOW}⚠️  No session logs found.{RESET}")
        return

    patterns_found = 0

    # ── 1. Repeated Questions ──
    print(f"{BOLD}1. Repeated Questions{RESET}")
    print(f"{DIM}   (Same question asked across {MIN_REPEAT_COUNT}+ sessions){RESET}\n")

    all_questions = {}
    for f in session_files:
        try:
            content = f.read_text(encoding="utf-8")
            questions = extract_questions(content)
            if questions:
                all_questions[f.name] = questions
        except Exception:
            continue

    repeated = find_similar_questions(all_questions)
    if repeated:
        for cluster in sorted(repeated, key=lambda x: x["count"], reverse=True):
            patterns_found += 1
            print(f'   {RED}🔁 "{cluster["question"]}..."{RESET}')
            print(
                f"      Appears in {cluster['count']} sessions: {', '.join(cluster['sessions'][:5])}"
            )
        print()
    else:
        print(f"   {GREEN}✅ No repeated questions detected.{RESET}\n")

    # ── 2. Unresolved Deferrals ──
    print(f"{BOLD}2. Unresolved Deferrals{RESET}")
    print(f"{DIM}   (Items marked 'deferred' that never appear resolved){RESET}\n")

    unresolved = detect_unresolved_deferrals(session_files)
    if unresolved:
        # Show top 10
        for item in unresolved[:10]:
            patterns_found += 1
            print(f"   {YELLOW}⏳ [{item['session']}] {item['item']}{RESET}")
        if len(unresolved) > 10:
            print(f"   {DIM}   ... and {len(unresolved) - 10} more{RESET}")
        print()
    else:
        print(f"   {GREEN}✅ No unresolved deferrals detected.{RESET}\n")

    # ── 3. Session Thrashing ──
    print(f"{BOLD}3. Session Thrashing{RESET}")
    print(f"{DIM}   (4+ sessions in a single day may indicate context loss){RESET}\n")

    thrashing = detect_session_thrashing(session_files)
    if thrashing:
        for day in thrashing:
            patterns_found += 1
            color = RED if day["count"] >= 6 else YELLOW
            print(f"   {color}⚡ {day['date']}: {day['count']} sessions{RESET}")
        print()
    else:
        print(f"   {GREEN}✅ No session thrashing detected.{RESET}\n")

    # ── Summary ──
    print(f"{'─' * 70}")
    if patterns_found > 0:
        print(f"{BOLD}📊 {patterns_found} anti-pattern(s) detected.{RESET}")
        print(
            f"{YELLOW}💡 Review flagged items to reduce wasted tokens and improve session quality.{RESET}"
        )
    else:
        print(
            f"{GREEN}{BOLD}✅ No anti-patterns detected. Clean session history!{RESET}"
        )


if __name__ == "__main__":
    audit_antipatterns()
