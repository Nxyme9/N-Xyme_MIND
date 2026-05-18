# Global Rules — N-Xyme_MIND

## Rule 1: NO GUESSING — RESEARCH FIRST
If the LLM does not have authoritative, verifiable knowledge on a topic, it MUST launch parallel research agents (Librarian) before implementing. Never assume. Never guess. Never say "I think this works."

## Rule 2: NO CODE FROM SISYPHUS
Sisyphus (orchestrator) NEVER writes code, edits files, or implements features. ALL code changes go through Hephaestus via `delegate_task` or `task()`. Violations reset streak to 0.

## Rule 3: ONE SOURCE OF TRUTH
`agents/{name}/agent.js` is the ONLY source for agent definitions. `config/nx_agents.json` is the ONLY source for system config. No duplication, no scattering, no .opencode/agents/ hand-edits.

## Rule 4: VERIFY ALL DELEGATED WORK
Every delegated task must be verified after completion. Run quality gates, check output, confirm acceptance criteria met.

## Rule 5: NO PERMANENT DELETE
`safe_delete` is the ONLY delete mechanism. `rm -rf` is forbidden. All deletions go to `data/trash/` for 30 days.
