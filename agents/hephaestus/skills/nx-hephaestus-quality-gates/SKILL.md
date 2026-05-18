---
name: nx-hephaestus-quality-gates
description: "Quality gates protocol — mandatory verification for all code. Runs fmt → clippy → test → audit."
---

## GATE PIPELINE (run in order)
1. **Format**: `code_verify(gate="fmt")` or `cargo fmt --all --check`
2. **Lint**: `code_verify(gate="lint")` or `cargo clippy --workspace -- -D warnings`
3. **Test**: `code_verify(gate="test")` or `cargo test --workspace`
4. **Audit**: `code_verify(gate="audit")` or `cargo audit`

## FAST PATH
`code_verify(session_id, gate="all")` runs all 4 gates in sequence.
Returns structured pass/fail per gate.

## EXPLORE FIRST
Before coding: `project_map(root, depth, max_files)` to see structure.
Then: `batch_read(paths)` to read multiple files in one call.

## GATE FAILURE RULES
- Format: auto-fix with `cargo fmt --all`
- Lint: fix warnings — they are bugs waiting to happen
- Test: fix code, NOT tests (zero test deletion)
- Audit: flag to parent, do not skip

## MANDATORY
All gates must pass before declaring done. No exceptions.
