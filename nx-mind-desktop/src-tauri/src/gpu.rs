use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GPUInfo {
    pub name: String,
    pub total_memory_mb: u64,
    pub used_memory_mb: u64,
    pub free_memory_mb: u64,
    pub available: bool,
}

impl Default for GPUInfo {
    fn default() -> Self {
        GPUInfo {
            name: "No GPU detected".to_string(),
            total_memory_mb: 0,
            used_memory_mb: 0,
            free_memory_mb: 0,
            available: false,
        }
    }
}

pub fn get_gpu_info() -> Result<GPUInfo, String> {
    let output = std::process::Command::new("nvidia-smi")
        .args(["--query-gpu=name,memory.total,memory.used,memory.free", "--format=csv,noheader"])
        .output()
        .map_err(|e| format!("nvidia-smi not available: {}", e))?;
    
    if !output.status.success() {
        return Err("nvidia-smi failed".to_string());
    }
    
    let stdout = String::from_utf8_lossy(&output.stdout);
    let line = stdout.trim().lines().next().ok_or("No GPU output")?;
    
    let parts: Vec<&str> = line.split(',').map(|s| s.trim()).collect();
    if parts.len() < 4 {
        return Err("Invalid nvidia-smi output".to_string());
    }
    
    let name = parts[0].to_string();
    let total = parts[1].trim_end_matches("MiB").trim().parse::<u64>().unwrap_or(0);
    let used = parts[2].trim_end_matches("MiB").trim().parse::<u64>().unwrap_or(0);
    let free = parts[3].trim_end_matches("MiB").trim().parse::<u64>().unwrap_or(0);
    
    Ok(GPUInfo {
        name,
        total_memory_mb: total,
        used_memory_mb: used,
        free_memory_mb: free,
        available: true,
    })
}

pub fn has_nvidia_gpu() -> bool {
    std::process::Command::new("nvidia-smi")
        .arg("--version")
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}