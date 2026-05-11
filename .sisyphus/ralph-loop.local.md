---
active: true
iteration: 1
max_iterations: 100
completion_promise: "DONE"
initial_completion_promise: "DONE"
started_at: "2026-05-11T22:19:53.961Z"
session_id: "ses_1e87f50cdffe0zQnn0TBRemSFC"
strategy: "continue"
message_count_at_start: 936
---
we found sevral more issues here
🔍 Root Cause Analysis: 100k+ Token Context Bloat on Fresh Sessions
The Initialization Chain (in order)
1. Session Pool Pre-warms 36 Sessions → session-pool-mcp/mcp_server.py
- get_pool() (line 588) creates 3 sessions × 12 agent types = 36 pre-warmed sessions
- Each session is lightweight (just a UUID), but this is step one of the cascade
2. brain_mcp Eager Import Cascade → brain_mcp/__init__.py:555
_register_namespace_tools()  # Called at MODULE LOAD TIME
This eagerly imports ALL 10 namespace modules including learning_engine, which at learning_engine/__init__.py:19 does:
from .rl import QLearningEngine, MultiArmedBandit, PolicyManager, CompositeReward
This loads q_learning.py which has the broken if block at line 222 → causes an IndentationError that cascades and crashes 5 MCP servers (learning, memory stats, catalyst orchestrate, etc.)
3. SessionInjector Aggregates ALL Context → session_hooks.py:94-125
When get_session_context() is called, _build_context() concatenates:
Source
Session state
Active context
Memory stats
Learning stats
4. inject_context("all") Loads EVERYTHING → context_store/__init__.py:568-697
When called with context_type="all", it reads ALL memory bank files with NO truncation:
File
activeContext.md
productContext.md
userContext.md
constraints.md
user_profile.md
Style (learner)
Archive sessions
Plus the inject_context tool in fingerprint.py (get_full_injected_context) stacks 4 layers:
[GLOBAL] → [CROSS-SESSION] → [SESSION] → [PREFERENCES]
The cross-session layer calls search_memories(rerank=True) which hits the memory router scanning multiple SQLite DBs.
5. Archive Scanner Scans Entire History → archive_scanner.py:109-211
- Reads entire session-log.jsonl (197 entries)
- Queries all 1,196 rows from outcomes.db (245KB)
- The .sisyphus/ directory alone is 7.8MB of accumulated state
6. The .sisyphus/ directory is a ticking time bomb:
File
routing.db
outcomes.jsonl
strategy_selector.db
state.db
context.db
memory.db
embedding_cache/
graphs.db
trajectories.db
memory_tiers.db
graph_fallback.db
rl_integration.db
Total
