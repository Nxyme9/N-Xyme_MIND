-- Athena Local Index Schema
-- Sovereign Sidecar v1.0
CREATE TABLE IF NOT EXISTS files (
    path TEXT PRIMARY KEY,
    last_modified REAL,
    checksum TEXT,
    content_hash TEXT,
    type TEXT,
    -- 'protocol', 'memory', 'session'
    created_at REAL
);
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
);
CREATE TABLE IF NOT EXISTS file_tags (
    file_path TEXT,
    tag_id INTEGER,
    FOREIGN KEY(file_path) REFERENCES files(path) ON DELETE CASCADE,
    FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY(file_path, tag_id)
);
CREATE TABLE IF NOT EXISTS links (
    source_path TEXT,
    target_path TEXT,
    type TEXT,
    -- 'explicit', 'implicit'
    FOREIGN KEY(source_path) REFERENCES files(path) ON DELETE CASCADE,
    PRIMARY KEY(source_path, target_path)
);
CREATE INDEX IF NOT EXISTS idx_files_type ON files(type);
CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);