-- Task embeddings for semantic routing
CREATE TABLE IF NOT EXISTS task_embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_hash TEXT UNIQUE NOT NULL,
    task_text TEXT NOT NULL,
    embedding_blob BLOB NOT NULL,
    model_version TEXT DEFAULT 'all-MiniLM-L6-v2',
    embedding_dim INTEGER DEFAULT 384,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_task_embeddings_hash ON task_embeddings(task_hash);
CREATE INDEX IF NOT EXISTS idx_task_embeddings_created ON task_embeddings(created_at DESC);

-- Strategy selection tracking (for meta-learning)
CREATE TABLE IF NOT EXISTS strategy_selections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_hash TEXT NOT NULL,
    strategy TEXT NOT NULL,
    confidence REAL NOT NULL,
    level INTEGER,
    outcome TEXT,
    latency_ms REAL,
    tokens_used INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_strategy_selections_task ON strategy_selections(task_hash);
CREATE INDEX IF NOT EXISTS idx_strategy_selections_strategy ON strategy_selections(strategy);
CREATE INDEX IF NOT EXISTS idx_strategy_selections_created ON strategy_selections(created_at DESC);

-- Cross-session model weights (for transfer learning)
CREATE TABLE IF NOT EXISTS cross_session_model (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_type TEXT NOT NULL,
    weight_blob BLOB NOT NULL,
    session_id TEXT NOT NULL,
    task_types TEXT,
    performance_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_cross_session_model_type ON cross_session_model(model_type);
CREATE INDEX IF NOT EXISTS idx_cross_session_model_session ON cross_session_model(session_id);

-- Prompt version tracking (for prompt evolution)
CREATE TABLE IF NOT EXISTS prompt_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_name TEXT NOT NULL,
    version INTEGER NOT NULL,
    prompt_text TEXT NOT NULL,
    score REAL DEFAULT 0.0,
    outcome_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(prompt_name, version)
);
CREATE INDEX IF NOT EXISTS idx_prompt_versions_name ON prompt_versions(prompt_name);
CREATE INDEX IF NOT EXISTS idx_prompt_versions_score ON prompt_versions(score);
