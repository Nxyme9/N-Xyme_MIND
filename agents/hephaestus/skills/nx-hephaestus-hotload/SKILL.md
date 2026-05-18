---
name: nx-hephaestus-hotload
description: "Hot-load activation + Structured CoT code generation protocol. Uses 6-band specification and manual QA mandate."
---

## WORKER MODEL

Each Hephaestus worker = independent session_id. Context does NOT bleed.
- Single: "hephaestus"
- Parallel: "hephaestus_auth", "hephaestus_api", "hephaestus_X"
- Sisyphus assigns session_id. Use it. Do not hardcode.

## ACTIVATION

1. session_start(session_id="{your_session_id}")
2. session_status → check context_util_pct
3. memory_list → find delegation_* (set by Sisyphus)
4. memory_read → get task, files, acceptance_criteria

## STRUCTURED CoT (Before ANY Code)

### SEQUENTIAL
List every file, every step, in order. No skipping.

### BRANCH
What decisions exist? What conditions determine the path? If X → A, if Y → B.

### LOOP
What repeats? Test cases? Retry logic? Batch processing?

## CONSTRAINTS (42.7% of quality)

FORBIDDEN:
- Scope reduction, mock data, partial completion
- Skipping existing patterns, hallucinated APIs
- Test deletion, debug prints, dead code

MANDATORY:
- Production code, error handling, clean imports
- Match codebase style exactly
- Edge case coverage (empty, malformed, failure, concurrent)

## MANUAL QA (Final Gate)

| Change | Must |
|--------|------|
| CLI | Run it. Show output. |
| Build | Run. Verify. |
| API | Call. Show response. |
| Feature | Test e2e. Show result. |

NOT optional. "This should work" is not evidence.
