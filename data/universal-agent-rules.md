# Universal Agent Rules — N-Xyme MIND

## Required Sections (every agent.js)
Every agent prompt MUST have these sections in order:
1. IDENTITY — who they are, role, boundaries
2. CORE PROTOCOL — phased methodology
3. ANTI-HALLUCINATION — 5 universal rules
4. RULES — hard constraints + boundaries
5. TOOLS — decision tree per tool
6. DELEGATION — who to delegate to, when
7. QUALITY GATE — verification checklist

## Universal Anti-Hallucination Rules
1. READ BEFORE WRITE — never edit files unread this session
2. NO INVENTED TOOLS/IMPORTS — grep/glob before referencing
3. CITE SOURCES — reference file:line when possible
4. FLAG UNCERTAINTY — say it, don't guess
5. VERIFY EXISTENCE — check tools.json before calling tools

## Universal Delegation Rules
- delegate_task — BLOCKING, use when you NEED the result before continuing
- call_omo_agent — NON-BLOCKING, use for parallel/fire-and-forget
- NEVER use task() — it drops agent identity
- Include acceptance criteria in every delegation
- Verify delegated results before reporting done
- Use session_id for retry/continuation (saves 70% tokens)

## Universal Quality Gate
Before declaring done:
- [ ] Files read before written
- [ ] All tools verified to exist
- [ ] Uncertainty flagged
- [ ] Memory written (if applicable)

## Tool Naming Convention (NAP Standard)
- file_read, file_write, file_edit, file_glob, file_grep
- search_code, search_memory, read_memory, write_memory
- delegate_task, call_omo_agent
- review_code, verify_code, safe_delete
- project_map, session_status, context_prune

## Reference Files
- AGENTS.md — architecture, known broken things
- data/anti-hallucination-rules.md — anti-hallucination
- config/nx_agents.json — custom N-Xyme keys
- opencode.json — primary config
