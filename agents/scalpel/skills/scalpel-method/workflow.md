---
agent: Scalpel - Code Surgeon
---

# Scalpel Method — Code Surgery Workflow

**Goal:** Decompile, understand, reconstruct, or Frankenstein-stitch code.

## Phase 1 — SCAN (Territory Map)

```bash
# Find every relevant file
fd -e rs -e ts -e py -e cpp -e c -e go .

# Search for key patterns
grep -rn "pattern" --include="*.rs"

# Structural search (if ast-grep is installed)
npx @ast-grep/cli --pattern 'async fn $_($$$)' --lang rust
```

## Phase 2 — DECOMPILE (Understand)

Read the entry point. Trace the call graph. Map dependencies.

For binaries:
```bash
objdump -d binary | head -200   # disassembly
strings binary | head -50       # interesting strings
nm binary                       # symbols
```

For Python bytecode:
```bash
pip install uncompyle6 --break-system-packages
uncompyle6 file.pyc
```

## Phase 3 — PLAN (Blueprint)

Document:
- Files to modify
- Lines to change
- Adapter layers needed (if Frankenstein stitching)
- Rollback strategy

## Phase 4 — SCALPEL (Execute)

One edit at a time. Verify after each:
1. Read the changed file
2. Compile / type-check
3. Run tests
4. Review diff

## Phase 5 — VERIFY (Quality Gate)

Checklist:
- Compiles clean
- Tests pass
- No hallucinations (verify imports, signatures, types)
- Diff is minimal
- Frankenstein seams are documented
