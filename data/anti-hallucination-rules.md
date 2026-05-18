# Universal Anti-Hallucination Rules

**This file is referenced by ALL agents in the N-Xyme ecosystem.**
Every agent must enforce these rules. No exceptions.

---

## THE 5 NON-NEGOTIABLE RULES

### 1. READ BEFORE WRITE
If you haven't read a file this session, you don't know what's in it.
- Never edit a file you haven't read
- Never reference a file's contents without reading it first
- Guessing file contents produces hallucinations

### 2. NO INVENTED IMPORTS
Every module, function, and API you reference must be verified to exist.
- grep/glob/read to confirm before importing
- Never assume a library is available
- Never invent function signatures

### 3. CITE SOURCES
Every claim about external systems, libraries, or documentation must have a source.
- Include URLs for external references
- Distinguish between official docs, blogs, and forum posts
- If you can't cite it, don't claim it

### 4. FLAG UNCERTAINTY
When you're not sure, say so explicitly.
- Use "I'm not certain but..." instead of stating guesses as facts
- Use confidence levels: "high confidence", "medium confidence", "speculative"
- Never say "I think this works" — verify or admit uncertainty

### 5. VERIFY TOOL EXISTENCE
Every tool, MCP endpoint, and CLI command you reference must actually exist.
- Check tools.json before claiming an agent has a capability
- Check MCP server definitions before calling a tool
- Never invent tool names or parameters

---

## ADDITIONAL RULES FOR CODE-PRODUCING AGENTS

### 6. MINIMAL DIFFS
Only change the exact lines required.
- No reformatting unrelated code
- No import reordering
- No fixing unrelated style issues

### 7. FIVE STRIKE RULE
If you try 3 fixes and none works, stop guessing.
- Re-read the error message
- Your mental model is wrong
- Trace execution from scratch

### 8. COMPILE BEFORE DECLARING DONE
- Run the build. Show the output.
- "This should work" is NOT evidence.
- Run tests. Show the results.

---

## HOW TO USE THIS FILE

Agents should reference these rules in their prompt. Example:

```
## Anti-Hallucination Rules
See data/anti-hallucination-rules.md for the full protocol.
In summary: READ BEFORE WRITE, NO INVENTED IMPORTS, CITE SOURCES,
FLAG UNCERTAINTY, VERIFY TOOL EXISTENCE.
```

---

## WHY THESE RULES EXIST

Research on multi-agent systems (MAST study, NeurIPS 2025) shows:
- 15.7% of failures are from step repetition (caused by hallucinated state)
- 13.2% are reasoning-action mismatches (caused by hallucinated capabilities)
- 12.4% are unaware of termination (caused by hallucinated progress)

These rules directly address the top 3 failure modes.
