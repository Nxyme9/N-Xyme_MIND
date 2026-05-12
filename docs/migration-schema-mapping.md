# Migration Schema Mapping

> Exact field-to-field mappings between legacy `.sisyphus/` databases and memory_store schema.

---

## 1. sessions Table → memory_store

### Source: `.sisyphus/state.db/sessions`

| Source Column | Type | Target Column | Type | Notes |
|---------------|------|---------------|------|-------|
| `session_id` | TEXT PRIMARY KEY | `id` | TEXT (PK) | Direct map |
| `last_agent` | TEXT NOT NULL DEFAULT '' | `content` (embedded) | TEXT | Embed as JSON in content |
| `last_action` | TEXT NOT NULL DEFAULT '' | `content` (embedded) | TEXT | Embed as JSON in content |
| `session_started` | TEXT NOT NULL DEFAULT '' | `created_at` | TEXT | ISO timestamp format |
| `last_updated` | TEXT NOT NULL DEFAULT '' | `updated_at` | TEXT | ISO timestamp format |
| `current_task` | TEXT NOT NULL DEFAULT '' | `content` (embedded) | TEXT | Store in content as task JSON |
| `pending_changes` | TEXT NOT NULL DEFAULT '[]' | `meta_json.tags` | TEXT | JSON array → tags |
| `completed_changes` | TEXT NOT NULL DEFAULT '[]' | `meta_json` | TEXT | JSON array in meta |
| `context` | TEXT NOT NULL DEFAULT '{}' | `meta_json` | TEXT | JSON object in meta |

**Migration Query:**
```sql
INSERT INTO memories (id, content, kind, scope, tier, meta_json, created_at, updated_at)
SELECT 
    session_id,
    json_object(
        'last_agent', last_agent,
        'last_action', last_action,
        'current_task', current_task,
        'pending_changes', pending_changes,
        'completed_changes', completed_changes
    ) as content,
    'episodic' as kind,
    'session' as scope,
    'short_term' as tier,
    context as meta_json,
    session_started as created_at,
    last_updated as updated_at
FROM sessions;
```

---

## 2. delegations Table → memory_store

### Source: `.sisyphus/state.db/delegations`

| Source Column | Type | Target Column | Type | Notes |
|---------------|------|---------------|------|-------|
| `id` | INTEGER PRIMARY KEY | `id` | TEXT | Generate UUID from integer |
| `task_id` | TEXT NOT NULL | `id` | TEXT | Use as memory ID prefix |
| `agent` | TEXT NOT NULL | `content` (embedded) | TEXT | Store in content |
| `level` | TEXT NOT NULL | `content` (embedded) | TEXT | Store in content |
| `status` | TEXT NOT NULL | `meta_json` | TEXT | Store in meta |
| `tokens` | INTEGER NOT NULL DEFAULT 0 | `meta_json` | TEXT | Store in meta |
| `timestamp` | TEXT NOT NULL | `created_at` | TEXT | ISO timestamp |

**Migration Query:**
```sql
INSERT INTO memories (id, content, kind, scope, tier, meta_json, created_at)
SELECT 
    'delegation_' || task_id || '_' || id as id,
    json_object(
        'agent', agent,
        'level', level,
        'status', status
    ) as content,
    'procedural' as kind,
    'session' as scope,
    'short_term' as tier,
    json_object('tokens', tokens) as meta_json,
    timestamp as created_at
FROM delegations;
```

---

## 3. session_context Table → memory_store

### Source: `.sisyphus/context.db/session_context`

| Source Column | Type | Target Column | Type | Notes |
|---------------|------|---------------|------|-------|
| `id` | INTEGER PRIMARY KEY | `id` | TEXT | Generate UUID |
| `session_id` | TEXT NOT NULL | `meta_json.session_id` | TEXT | Store in meta |
| `context_type` | TEXT NOT NULL | `kind` | TEXT | Map: active→episodic, semantic→semantic, etc |
| `context_key` | TEXT NOT NULL | `content` (key) | TEXT | Embed in content |
| `context_value` | TEXT | `content` (value) | TEXT | Main content |
| `priority` | INTEGER DEFAULT 0 | `meta_json.priority` | TEXT | Store in meta |
| `created_at` | REAL (epoch) | `created_at` | TEXT | Convert epoch to ISO |
| `expires_at` | REAL (epoch) | `meta_json.expires_at` | TEXT | Convert epoch, store in meta |
| `metadata` | TEXT | `meta_json` | TEXT | Merge with existing meta |

**Migration Query:**
```sql
INSERT INTO memories (id, content, kind, scope, tier, meta_json, created_at)
SELECT 
    'ctx_' || session_id || '_' || context_key || '_' || id as id,
    context_value as content,
    CASE 
        WHEN context_type = 'active' THEN 'episodic'
        WHEN context_type = 'semantic' THEN 'semantic'
        WHEN context_type = 'procedural' THEN 'procedural'
        ELSE 'declarative'
    END as kind,
    'session' as scope,
    'short_term' as tier,
    json_object(
        'session_id', session_id,
        'context_key', context_key,
        'priority', priority,
        'expires_at', expires_at,
        'metadata', metadata
    ) as meta_json,
    datetime(created_at, 'unixepoch') as created_at
FROM session_context;
```

---

## 4. session_summary Table → memory_store

### Source: `.sisyphus/context.db/session_summary`

| Source Column | Type | Target Column | Type | Notes |
|---------------|------|---------------|------|-------|
| `session_id` | TEXT PRIMARY KEY | `id` | TEXT | Direct map |
| `summary` | TEXT | `content` | TEXT | Direct map |
| `key_decisions` | TEXT | `meta_json.key_decisions` | TEXT | JSON array |
| `pending_items` | TEXT | `meta_json.pending_items` | TEXT | JSON array |
| `timestamp` | TEXT NOT NULL | `created_at` | TEXT | ISO timestamp |

**Migration Query:**
```sql
INSERT INTO memories (id, content, kind, scope, tier, meta_json, created_at)
SELECT 
    'summary_' || session_id as id,
    summary as content,
    'semantic' as kind,
    'session' as scope,
    'medium_term' as tier,
    json_object(
        'key_decisions', key_decisions,
        'pending_items', pending_items
    ) as meta_json,
    timestamp as created_at
FROM session_summary;
```

---

## 5. agent_weights Table → memory_store (for Q-Learning)

### Source: `.sisyphus/routing.db/agent_weights`

| Source Column | Type | Target Column | Type | Notes |
|---------------|------|---------------|------|-------|
| `agent` | TEXT PRIMARY KEY | `content` (key) | TEXT | Agent name as identifier |
| `success_rate` | REAL DEFAULT 0.5 | `meta_json.success_rate` | REAL | Q-value base |
| `avg_latency_ms` | REAL DEFAULT 0.0 | `meta_json.avg_latency_ms` | REAL | Performance metric |
| `total_tasks` | INTEGER DEFAULT 0 | `meta_json.total_tasks` | INTEGER | Sample count |
| `success_count` | INTEGER DEFAULT 0 | `meta_json.success_count` | INTEGER | Positive samples |
| `failure_count` | INTEGER DEFAULT 0 | `meta_json.failure_count` | INTEGER | Negative samples |
| `by_level` | TEXT DEFAULT '{}' | `meta_json.by_level` | TEXT | JSON per-level stats |
| `last_updated` | REAL (epoch) | `updated_at` | TEXT | Convert to ISO |

**Migration Query:**
```sql
INSERT INTO memories (id, content, kind, scope, tier, meta_json, created_at, updated_at)
SELECT 
    'weight_' || agent as id,
    agent as content,
    'declarative' as kind,
    'global' as scope,
    'long_term' as tier,
    json_object(
        'success_rate', success_rate,
        'avg_latency_ms', avg_latency_ms,
        'total_tasks', total_tasks,
        'success_count', success_count,
        'failure_count', failure_count,
        'by_level', by_level
    ) as meta_json,
    datetime('now') as created_at,
    datetime(last_updated, 'unixepoch') as updated_at
FROM agent_weights;
```

---

## 6. outcomes Table → memory_store

### Source: `.sisyphus/outcomes.db/outcomes`

| Source Column | Type | Target Column | Type | Notes |
|---------------|------|---------------|------|-------|
| `id` | INTEGER PRIMARY KEY | `id` | TEXT | Generate UUID |
| `task_id` | TEXT NOT NULL | `id` (prefix) | TEXT | Prefix memory ID |
| `task_description` | TEXT | `content` | TEXT | Main content |
| `task_type` | TEXT NOT NULL | `kind` | TEXT | Map to memory kind |
| `agent` | TEXT NOT NULL | `meta_json.agent` | TEXT | Store in meta |
| `level` | INTEGER NOT NULL | `meta_json.level` | INTEGER | Store in meta |
| `success` | INTEGER NOT NULL | `meta_json.success` | INTEGER | 0 or 1 |
| `latency_ms` | REAL NOT NULL | `meta_json.latency_ms` | REAL | Store in meta |
| `tokens_used` | INTEGER DEFAULT 0 | `meta_json.tokens_used` | INTEGER | Store in meta |
| `quality_score` | REAL | `meta_json.quality_score` | REAL | Store in meta |
| `context_json` | TEXT DEFAULT '{}' | `meta_json` | TEXT | Merge with meta |
| `timestamp` | TEXT NOT NULL | `created_at` | TEXT | ISO timestamp |

**Migration Query:**
```sql
INSERT INTO memories (id, content, kind, scope, tier, meta_json, created_at)
SELECT 
    'outcome_' || task_id || '_' || id as id,
    task_description as content,
    CASE 
        WHEN task_type = 'implementation' THEN 'procedural'
        WHEN task_type = 'research' THEN 'semantic'
        WHEN task_type = 'review' THEN 'episodic'
        WHEN task_type = 'fix' THEN 'procedural'
        ELSE 'declarative'
    END as kind,
    'session' as scope,
    'short_term' as tier,
    json_object(
        'agent', agent,
        'level', level,
        'success', success,
        'latency_ms', latency_ms,
        'tokens_used', tokens_used,
        'quality_score', quality_score,
        'extra', context_json
    ) as meta_json,
    timestamp as created_at
FROM outcomes;
```

---

## 7. triggers Table → memory_store

### Source: `.sisyphus/routing.db/triggers`

| Source Column | Type | Target Column | Type | Notes |
|---------------|------|---------------|------|-------|
| `phrase` | TEXT PRIMARY KEY | `id` | TEXT | Use phrase as ID |
| `agent` | TEXT NOT NULL | `content` (embedded) | TEXT | Target agent |
| `priority` | INTEGER DEFAULT 0 | `meta_json.priority` | INTEGER | Store in meta |
| `description` | TEXT | `content` | TEXT | Main content |
| `last_triggered` | REAL (epoch) | `updated_at` | TEXT | Convert to ISO |
| `trigger_count` | INTEGER DEFAULT 0 | `meta_json.trigger_count` | INTEGER | Usage count |

---

## Summary: Kind Mapping

| Original Source | Target memory_store `kind` |
|-----------------|---------------------------|
| sessions | episodic |
| delegations | procedural |
| session_context (type=active) | episodic |
| session_context (type=semantic) | semantic |
| session_summary | semantic |
| agent_weights | declarative |
| outcomes | procedural |
| triggers | declarative |

---

## Verification SQL

After migration, verify with:

```sql
-- Count by kind
SELECT kind, COUNT(*) FROM memories GROUP BY kind;

-- Count by scope
SELECT scope, COUNT(*) FROM memories GROUP BY scope;

-- Sample migrated sessions
SELECT id, SUBSTR(content, 1, 50) as content_preview FROM memories 
WHERE kind = 'episodic' LIMIT 5;

-- Verify Q-values preserved (compare sums)
SELECT 'source' as src, SUM(success_rate) as total_q FROM agent_weights
UNION ALL
SELECT 'target' as src, SUM(json_extract(meta_json, '$.success_rate')) as total_q 
FROM memories WHERE id LIKE 'weight_%';
```