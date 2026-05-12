use std::collections::HashMap;
use std::io::{BufRead, BufReader};
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;

use crate::trainer::{cancel_job, complete_job, fail_job, update_job_progress, Job};

pub struct TrainingProcess {
    job_id: String,
    child: Option<std::process::Child>,
    cancelled: AtomicBool,
}

impl TrainingProcess {
    pub fn new(job_id: &str) -> Self {
        TrainingProcess {
            job_id: job_id.to_string(),
            child: None,
            cancelled: AtomicBool::new(false),
        }
    }
    
    pub fn spawn(&mut self, job: &Job) -> Result<(), String> {
        if self.cancelled.load(Ordering::SeqCst) {
            return Err("Training already cancelled".to_string());
        }
        
        let script_path = std::path::Path::new("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/nx_trainer/train_rosetta_unified.py");
        if !script_path.exists() {
            return Err("Training script not found".to_string());
        }
        
        let mut cmd = Command::new("python3");
        cmd.arg(script_path)
            .arg("--job_id")
            .arg(&job.id)
            .arg("--data")
            .arg(&job.data_path)
            .arg("--epochs")
            .arg(job.epochs.to_string())
            .arg("--batch")
            .arg(job.batch_size.to_string())
            .arg("--lr")
            .arg(job.learning_rate.to_string())
            .arg("--task_type")
            .arg(&job.task_type)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());
        
        let child = cmd.spawn().map_err(|e| format!("Failed to spawn training: {}", e))?;
        self.child = Some(child);
        
        log::info!("Training process spawned for job {}", self.job_id);
        Ok(())
    }
    
    pub fn cancel(&mut self) {
        self.cancelled.store(true, Ordering::SeqCst);
        if let Some(mut child) = self.child.take() {
            let _ = child.kill();
        }
    }
    
    pub fn is_cancelled(&self) -> bool {
        self.cancelled.load(Ordering::SeqCst)
    }
    
    pub fn poll_loss(&mut self) -> Option<f64> {
        let child = self.child.as_mut()?;
        let stdout = child.stdout.as_mut()?;
        let mut reader = BufReader::new(stdout);
        
        let mut line = String::new();
        while reader.read_line(&mut line).ok().is_some() {
            if line.contains("loss:") {
                if let Some(loss_str) = line.split("loss:").nth(1) {
                    let loss = loss_str.trim().split_whitespace().next()
                        .and_then(|s| s.parse::<f64>().ok());
                    if loss.is_some() {
                        return loss;
                    }
                }
            }
            line.clear();
        }
        
        None
    }
    
    pub fn is_running(&mut self) -> bool {
        if let Some(ref mut child) = self.child {
            child.try_wait().ok().flatten().is_none()
        } else {
            false
        }
    }
}

lazy_static::lazy_static! {
    static ref RUNNING_JOBS: Mutex<HashMap<String, TrainingProcess>> = Mutex::new(HashMap::new());
}

pub fn run_training(job_id: &str) -> Result<(), String> {
    let job = crate::trainer::get_job_status(job_id)?;
    
    if job.status != "pending" && job.status != "cancelled" {
        return Err(format!("Job {} is not in pending state (status: {})", job_id, job.status));
    }
    
    let mut jobs = RUNNING_JOBS.lock().map_err(|e| e.to_string())?;
    
    if jobs.contains_key(job_id) {
        return Err("Training already running for this job".to_string());
    }
    
    crate::trainer::start_training(job_id)?;
    
    let mut process = TrainingProcess::new(job_id);
    if let Err(e) = process.spawn(&job) {
        let _ = fail_job(job_id, &e);
        return Err(e);
    }
    
    jobs.insert(job_id.to_string(), process);
    
    let job_id_clone = job_id.to_string();
    std::thread::spawn(move || {
        training_loop(job_id_clone);
    });
    
    Ok(())
}

fn training_loop(job_id: String) {
    let mut last_loss: Option<f64> = None;
    let mut epoch: i32 = 0;
    
    loop {
        std::thread::sleep(std::time::Duration::from_secs(2));
        
        let mut jobs = match RUNNING_JOBS.lock() {
            Ok(j) => j,
            Err(_) => break,
        };
        
        let process = match jobs.get_mut(&job_id) {
            Some(p) => p,
            None => break,
        };
        
        if process.is_cancelled() {
            let _ = cancel_job(&job_id);
            break;
        }
        
        if let Some(loss) = process.poll_loss() {
            last_loss = Some(loss);
            epoch += 1;
            
            if let Err(e) = update_job_progress(&job_id, epoch, loss) {
                log::warn!("Failed to update progress: {}", e);
            }
        }
        
        if !process.is_running() {
            if let Some(loss) = last_loss {
                let gguf_path = format!("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/nx_trainer/outputs/{}/final", job_id);
                let _ = complete_job(&job_id, loss, &gguf_path);
            } else {
                let _ = fail_job(&job_id, "Training process ended without loss");
            }
            
            let _ = jobs.remove(&job_id);
            break;
        }
    }
}

pub fn cancel_training(job_id: &str) -> Result<(), String> {
    let mut jobs = RUNNING_JOBS.lock().map_err(|e| e.to_string())?;
    
    if let Some(process) = jobs.get_mut(job_id) {
        process.cancel();
    }
    
    cancel_job(job_id)?;
    
    log::info!("Training cancelled for job {}", job_id);
    Ok(())
}

pub fn is_training_running(job_id: &str) -> bool {
    if let Ok(jobs) = RUNNING_JOBS.lock() {
        jobs.contains_key(job_id)
    } else {
        false
    }
}

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelFile {
    pub id: String,
    pub name: String,
    pub path: String,
    pub size: String,
}

pub fn scan_models() -> Result<Vec<ModelFile>, String> {
    let model_dirs = vec![
        std::path::PathBuf::from("/home/nxyme/models"),
        dirs::home_dir()
            .map(|p| p.join(".cache/huggingface/hub"))
            .unwrap_or_default(),
        dirs::home_dir()
            .map(|p| p.join(".ollama/models"))
            .unwrap_or_default(),
    ];

    let mut models = Vec::new();
    let gguf_extensions = ["gguf", "ggml", "bin", "pth"];

    for dir in model_dirs {
        if !dir.exists() {
            continue;
        }

        if let Ok(entries) = std::fs::read_dir(&dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.is_file() {
                    if let Some(ext) = path.extension() {
                        let ext_str = ext.to_string_lossy().to_lowercase();
                        if gguf_extensions.contains(&ext_str.as_str()) {
                            let name = path.file_stem()
                                .map(|s| s.to_string_lossy().to_string())
                                .unwrap_or_default();
                            
                            let size = std::fs::metadata(&path)
                                .map(|m| {
                                    let bytes = m.len();
                                    if bytes > 1_000_000_000 {
                                        format!("{:.1}GB", bytes as f64 / 1_000_000_000.0)
                                    } else {
                                        format!("{:.1}MB", bytes as f64 / 1_000_000.0)
                                    }
                                })
                                .unwrap_or_else(|_| "Unknown".to_string());

                            models.push(ModelFile {
                                id: name.clone(),
                                name: name.replace("-instruct", "").replace("_Q4_K_M", ""),
                                path: path.to_string_lossy().to_string(),
                                size,
                            });
                        }
                    }
                }
            }
        }
    }

    Ok(models)
}