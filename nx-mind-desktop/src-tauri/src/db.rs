use rusqlite::{Connection, Result};
use std::path::PathBuf;

pub fn init_db(app_dir: PathBuf) -> Result<Connection> {
    let db_path = app_dir.join("trainer.db");
    let conn = Connection::open(db_path)?;
    
    conn.execute(
        "CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            model_id TEXT NOT NULL,
            data_path TEXT NOT NULL,
            task_type TEXT NOT NULL,
            epochs INTEGER NOT NULL,
            learning_rate REAL NOT NULL,
            batch_size INTEGER NOT NULL,
            current_epoch INTEGER DEFAULT 0,
            loss_history TEXT,
            final_loss REAL,
            gguf_path TEXT,
            error_message TEXT
        )",
        [],
    )?;
    
    conn.execute(
        "CREATE TABLE IF NOT EXISTS models (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            size_gb REAL NOT NULL,
            vram_gb INTEGER NOT NULL,
            local_path TEXT,
            downloaded_at TEXT
        )",
        [],
    )?;
    
    Ok(conn)
}