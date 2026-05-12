use chrono::Utc;
use rusqlite::Connection;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::sync::Mutex;
use uuid::Uuid;

pub static DB: std::sync::OnceLock<Mutex<Connection>> = std::sync::OnceLock::new();

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrainingConfig {
    pub model_id: String,
    pub data_path: String,
    pub task_type: String,
    pub epochs: i32,
    pub learning_rate: f64,
    pub batch_size: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Job {
    pub id: String,
    pub created_at: String,
    pub updated_at: String,
    pub status: String,
    pub model_id: String,
    pub data_path: String,
    pub task_type: String,
    pub epochs: i32,
    pub learning_rate: f64,
    pub batch_size: i32,
    pub current_epoch: i32,
    pub loss_history: Option<String>,
    pub final_loss: Option<f64>,
    pub gguf_path: Option<String>,
    pub error_message: Option<String>,
}

pub fn init_database(app_dir: PathBuf) -> Result<(), String> {
    let db_path = app_dir.join("trainer.db");
    let conn = Connection::open(&db_path).map_err(|e| e.to_string())?;
    
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
    ).map_err(|e| e.to_string())?;
    
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
    ).map_err(|e| e.to_string())?;
    
    DB.set(Mutex::new(conn)).map_err(|_| "DB already initialized")?;
    
    log::info!("Database initialized at {:?}", db_path);
    Ok(())
}

pub fn create_job(config: TrainingConfig) -> Result<Job, String> {
    let db = DB.get().ok_or("Database not initialized")?;
    let conn = db.lock().map_err(|e| e.to_string())?;
    
    let job_id = Uuid::new_v4().to_string();
    let now = Utc::now().to_rfc3339();
    
    conn.execute(
        "INSERT INTO jobs (id, created_at, updated_at, status, model_id, data_path, task_type, epochs, learning_rate, batch_size, current_epoch)
         VALUES (?1, ?2, ?3, 'pending', ?4, ?5, ?6, ?7, ?8, ?9, 0)",
        [&job_id, &now, &now, &config.model_id, &config.data_path, &config.task_type, &config.epochs.to_string(), &config.learning_rate.to_string(), &config.batch_size.to_string()],
    ).map_err(|e| e.to_string())?;
    
    Ok(Job {
        id: job_id,
        created_at: now.clone(),
        updated_at: now,
        status: "pending".to_string(),
        model_id: config.model_id,
        data_path: config.data_path,
        task_type: config.task_type,
        epochs: config.epochs,
        learning_rate: config.learning_rate,
        batch_size: config.batch_size,
        current_epoch: 0,
        loss_history: None,
        final_loss: None,
        gguf_path: None,
        error_message: None,
    })
}

pub fn get_job_status(job_id: &str) -> Result<Job, String> {
    let db = DB.get().ok_or("Database not initialized")?;
    let conn = db.lock().map_err(|e| e.to_string())?;
    
    let mut stmt = conn.prepare(
        "SELECT id, created_at, updated_at, status, model_id, data_path, task_type, epochs, learning_rate, batch_size, current_epoch, loss_history, final_loss, gguf_path, error_message FROM jobs WHERE id = ?1"
    ).map_err(|e| e.to_string())?;
    
    let job = stmt.query_row([job_id], |row| {
        Ok(Job {
            id: row.get(0)?,
            created_at: row.get(1)?,
            updated_at: row.get(2)?,
            status: row.get(3)?,
            model_id: row.get(4)?,
            data_path: row.get(5)?,
            task_type: row.get(6)?,
            epochs: row.get(7)?,
            learning_rate: row.get(8)?,
            batch_size: row.get(9)?,
            current_epoch: row.get(10)?,
            loss_history: row.get(11)?,
            final_loss: row.get(12)?,
            gguf_path: row.get(13)?,
            error_message: row.get(14)?,
        })
    }).map_err(|e| e.to_string())?;
    
    Ok(job)
}

pub fn update_job_progress(job_id: &str, epoch: i32, loss: f64) -> Result<(), String> {
    let db = DB.get().ok_or("Database not initialized")?;
    let conn = db.lock().map_err(|e| e.to_string())?;

    let now = Utc::now().to_rfc3339();

    let current_loss_history: String = {
        let mut stmt = conn.prepare("SELECT loss_history FROM jobs WHERE id = ?1")
            .map_err(|e| e.to_string())?;
        stmt.query_row([job_id], |row| row.get(0))
            .ok()
            .flatten()
            .unwrap_or_default()
    };

    let new_loss = format!("{}:{}", epoch, loss);
    let new_history = if current_loss_history.is_empty() {
        new_loss
    } else {
        format!("{},{}", current_loss_history, new_loss)
    };

    let job_id_owned = job_id.to_string();
    conn.execute(
        "UPDATE jobs SET current_epoch = ?1, loss_history = ?2, updated_at = ?3 WHERE id = ?4",
        rusqlite::params![epoch, new_history, now, job_id_owned],
    ).map_err(|e| e.to_string())?;

    Ok(())
}

pub fn cancel_job(job_id: &str) -> Result<(), String> {
    let db = DB.get().ok_or("Database not initialized")?;
    let conn = db.lock().map_err(|e| e.to_string())?;

    let now = Utc::now().to_rfc3339();
    let job_id_owned = job_id.to_string();

    conn.execute(
        "UPDATE jobs SET status = 'cancelled', updated_at = ?1 WHERE id = ?2",
        rusqlite::params![now, job_id_owned],
    ).map_err(|e| e.to_string())?;

    Ok(())
}

pub fn list_jobs() -> Result<Vec<Job>, String> {
    let db = DB.get().ok_or("Database not initialized")?;
    let conn = db.lock().map_err(|e| e.to_string())?;
    
    let mut stmt = conn.prepare(
        "SELECT id, created_at, updated_at, status, model_id, data_path, task_type, epochs, learning_rate, batch_size, current_epoch, loss_history, final_loss, gguf_path, error_message FROM jobs ORDER BY created_at DESC"
    ).map_err(|e| e.to_string())?;
    
    let jobs = stmt.query_map([], |row| {
        Ok(Job {
            id: row.get(0)?,
            created_at: row.get(1)?,
            updated_at: row.get(2)?,
            status: row.get(3)?,
            model_id: row.get(4)?,
            data_path: row.get(5)?,
            task_type: row.get(6)?,
            epochs: row.get(7)?,
            learning_rate: row.get(8)?,
            batch_size: row.get(9)?,
            current_epoch: row.get(10)?,
            loss_history: row.get(11)?,
            final_loss: row.get(12)?,
            gguf_path: row.get(13)?,
            error_message: row.get(14)?,
        })
    }).map_err(|e| e.to_string())?;
    
    let mut result = Vec::new();
    for job in jobs {
        result.push(job.map_err(|e| e.to_string())?);
    }
    
    Ok(result)
}

pub fn complete_job(job_id: &str, final_loss: f64, gguf_path: &str) -> Result<(), String> {
    let db = DB.get().ok_or("Database not initialized")?;
    let conn = db.lock().map_err(|e| e.to_string())?;
    
    let now = Utc::now().to_rfc3339();
    
    conn.execute(
        "UPDATE jobs SET status = 'completed', final_loss = ?1, gguf_path = ?2, updated_at = ?3 WHERE id = ?4",
        [&final_loss.to_string(), gguf_path, &now, &job_id],
    ).map_err(|e| e.to_string())?;
    
    Ok(())
}

pub fn fail_job(job_id: &str, error_message: &str) -> Result<(), String> {
    let db = DB.get().ok_or("Database not initialized")?;
    let conn = db.lock().map_err(|e| e.to_string())?;

    let now = Utc::now().to_rfc3339();
    let job_id_owned = job_id.to_string();

    conn.execute(
        "UPDATE jobs SET status = 'failed', error_message = ?1, updated_at = ?2 WHERE id = ?3",
        rusqlite::params![error_message, now, job_id_owned],
    ).map_err(|e| e.to_string())?;

    Ok(())
}

pub fn start_training(job_id: &str) -> Result<(), String> {
    let db = DB.get().ok_or("Database not initialized")?;
    let conn = db.lock().map_err(|e| e.to_string())?;

    let now = Utc::now().to_rfc3339();
    let job_id_owned = job_id.to_string();

    conn.execute(
        "UPDATE jobs SET status = 'running', updated_at = ?1 WHERE id = ?2",
        rusqlite::params![now, job_id_owned],
    ).map_err(|e| e.to_string())?;

    log::info!("Training started for job {}", job_id);
    Ok(())
}