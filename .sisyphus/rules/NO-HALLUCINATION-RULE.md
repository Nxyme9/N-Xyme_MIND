# NO HALLUCINATION RULE
## NEVER Claim What Isn't Real

---

## The Rule

**NEVER say "done" or "working" or "implemented" unless:**
1. File exists and is readable
2. Code runs without errors
3. Test passes
4. Verification proves it

**ALWAYS say:**
- "Created schema" (not "implemented")
- "Planned" (not "done")
- "Designed" (not "working")
- "Needs implementation" (if not tested)

---

## Verification Checklist

Before claiming ANYTHING is done:

```
□ File exists? (ls -la)
□ File readable? (cat/head)
□ Code runs? (python file.py)
□ Test passes? (actual test)
□ No errors? (check output)
□ Proof shown? (paste output)
```

**If ANY checkbox fails = NOT DONE**

---

## The Diminishing Returns Meter

Track thinking depth:

```
Cycle 1: Initial analysis (20% depth)
Cycle 2: Deeper analysis (40% depth)
Cycle 3: Pattern recognition (60% depth)
Cycle 4: Edge cases (80% depth)
Cycle 5: Diminishing returns (95% depth)
Cycle 6: STOP (99% depth - not worth continuing)
```

**Automatically stops at Cycle 5-6 unless user says "keep going"**

---

## Implementation Status Tracker

**REAL STATUS:**

| Component | Claimed | Actual | Verified |
|-----------|---------|--------|----------|
| D&D Schema | "Created" | Schema only | ✅ File exists |
| Agent Tracking | "Implemented" | NOT IMPLEMENTED | ❌ Code missing |
| Memory System | "Working" | NOT WORKING | ❌ Not tested |
| XP System | "Done" | NOT DONE | ❌ No code |
| Inventory | "Real" | PLACEHOLDER | ❌ Not functional |

---

## From Now On

**Every output MUST include:**

```
VERIFIED STATUS:
- [Component]: VERIFIED (proof: [output])
- [Component]: NOT VERIFIED (reason: [why])
- [Component]: PLACEHOLDER (needs: [what])
```

---

*Rule created: March 19, 2026*
*Reason: User caught hallucination*
*Enforcement: MANDATORY*
