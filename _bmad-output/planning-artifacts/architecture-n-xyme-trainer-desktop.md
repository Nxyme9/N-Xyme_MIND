---
stepsCompleted: [1, 2, 3]
inputDocuments:
  - "_bmad-output/planning-artifacts/product-brief-n-xyme-trainer-desktop.md"
  - "_bmad-output/planning-artifacts/prd-n-xyme-trainer-desktop.md"
  - "_bmad-output/planning-artifacts/ux-design-n-xyme-trainer-desktop.md"
workflowType: 'architecture'
project_name: 'N-Xyme Trainer Desktop'
user_name: 'N-Xyme'
date: '2026-04-23'
---

# Architecture Decision Document - N-Xyme Trainer Desktop App

**Author:** N-Xyme  
**Date:** 2026-04-23

---

## Input Documents

- Product Brief: ✅ loaded
- PRD: ✅ loaded  
- UX Design: ✅ loaded

---

## 1. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     N-XYME TRAINER DESKTOP APP                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                    FRONTEND (React)                        │    │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────┐   │    │
│  │  │Trainer  │ │   Hub   │ │Inference│ │   Team     │   │    │
│  │  │Wizard   │ │ Browser │ │  Chat   │ │ Workspace  │   │    │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └─────┬─────┘   │    │
│  │       │         │         │         │           │         │    │
│  │  ┌────┴─────────┴─────────┴─────────┴───────────┴────┐   │    │
│  │  │              ZUSTAND STATE STORE                   │   │    │
│  │  └──────────────────────┬──────────────────────────────┘   │    │
│  └───────────────────────┬─┴───────────────────────────────┘    │
│                          │                                     │
│  ┌──────────────────────┴──────────────────────────────────┐    │
│  │              TAURI IPC BRIDGE (invoke)                  │    │
│  └───────────────────────┬─────────────────────────────────┘    │
│                          │                                     │
│  ┌──────────────────────┴──────────────────────────────────┐    │
│  │                  BACKEND (Rust)                         │    │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐ │    │
│  │  │ trainer.rs  │ │  models.rs  │ │  cloud.rs       │ │    │
│  │  │ Job mgmt    │ │ HF/Model    │ │ RunPod/Lambda  │ │    │
│  │  └──────┬──────┘ └──────┬──────┘ └────────┬────────┘ │    │
│  │         │               │                  │             │    │
│  │  ┌──────┴───────────────┴──────────────────┴─────────┐ │    │
│  │  │               DATABASE (SQLite)                  │ │    │
│  │  │         jobs, models, users, teams             │ │    │
│  │  └─────────────────────────────────────────────────┘ │    │
│  └───────────────────────────────────────────────────────┘    │
│                          │                                     │
│  ┌──────────────────────┴──────────────────────────────────┐    │
│  │              EXTERNAL INTEGRATIONS                     │    │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐ │    │
│  │  │  Python    │ │ HuggingFace │ │  Cloud GPUs     │ │    │
│  │  │  Training  │ │    API     │ │ RunPod/Lambda  │ │    │
│  │  │  Pipeline  │ │             │ │                 │ │    │
│  │  └─────────────┘ └─────────────┘ └─────────────────┘ │    │
│  └───────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Technology Stack

| Layer | Technology | Version | Justification |
|-------|------------|---------|---------------|
| Desktop Shell | Tauri | 2.x | Fast, small, native |
| Frontend | React | 18.x | Component-based |
| Framework | Next.js | 14.x | SSR, routing |
| Styling | Tailwind CSS | 3.x | Rapid dev |
| State | Zustand | 4.x | Simple, performant |
| Charts | Chart.js | 4.x | Lightweight |
| Backend | Rust | 1.75+ | Native performance |
| Database | SQLite | - | Local, no setup |
| Training | Python + unsloth | - | QLoRA fine-tuning |
| HF Client | huggingface_hub | - | HF API integration |

---

## 3. Data Flow Architecture

### 3.1 Training Flow (Local)

```
User selects config
       │
       ▼
Frontend (React)
       │ invoke("start_training", config)
       ▼
Tauri Command (Rust)
       │ validate_config()
       ▼
Create Job (SQLite)
       │ status: "pending"
       ▼
Spawn Python Process
       │ subprocess::spawn("python train.py ...")
       ▼
Training Loop (Python)
       │ for epoch in epochs:
       │   │ train_step()
       │   │ write_loss_to_db()
       ▼
Polling (Frontend)
       │ every 2s: invoke("get_status")
       ▼
Update UI (Progress Bar + Chart)
       │
       ▼
Training Complete
       │ export_gguf()
       ▼
Update Job Status → "completed"
       │
       ▼
Download GGUF
```

### 3.2 Cloud Training Flow

```
User selects cloud provider
       │
       ▼
Get Cloud Credentials
       │ from config store (encrypted)
       ▼
Create Cloud Instance (Rust)
       │ call RunPod/Lambda API
       │
       ▼
Upload Training Data
       │ sftp to cloud instance
       │
       ▼
Start Remote Training
       │ ssh "python train.py ..."
       │
       ▼
Polling (sync status)
       │ poll cloud API every 5s
       │
       ▼
On Complete: Download Model
       │ sftp from cloud
       │
       ▼
Cleanup Cloud Instance
       │ terminate API
```

### 3.3 HuggingFace Integration

```
User searches HF
       │ invoke("search_models", query)
       │
       ▼
Call HF API
       │ huggingface_hub::ModelInfo
       │
       ▼
Display Results
       │ paginated grid
       │
       ▼
User selects model
       │ invoke("download_model", model_id)
       │
       ▼
Cache locally
       │ ~/.cache/huggingface/
       │
       ▼
Use for training
```

---

## 4. Database Schema

### SQLite Tables

```sql
-- Core job tracking
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    
    -- Config
    model_id TEXT NOT NULL,
    data_source TEXT NOT NULL,  -- 'local', 'url', 'hub'
    data_path TEXT,
    task_type TEXT NOT NULL,
    
    -- Training params
    epochs INTEGER NOT NULL,
    learning_rate REAL NOT NULL,
    batch_size INTEGER NOT NULL,
    
    -- Progress
    current_epoch INTEGER DEFAULT 0,
    loss_history TEXT,  -- JSON array
    
    -- Results
    final_loss REAL,
    gguf_path TEXT,
    export_size INTEGER,
    
    -- Cloud (optional)
    cloud_provider TEXT,  -- 'runpod', 'lambda', NULL for local
    cloud_job_id TEXT,
    
    -- Metadata
    error_message TEXT,
    started_at TEXT,
    completed_at TEXT,
    user_id TEXT
);

-- Local models cache
CREATE TABLE models (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    hub_id TEXT,  -- HuggingFace ID
    size_gb REAL NOT NULL,
    vram_gb INTEGER NOT NULL,
    best_for TEXT,
    quantization TEXT,  -- 'q4_k_m', 'q8_0', etc.
    downloaded_at TEXT,
    local_path TEXT,
    is_custom INTEGER DEFAULT 0
);

-- HuggingFace credentials
CREATE TABLE hf_credentials (
    id TEXT PRIMARY KEY,
    token_encrypted TEXT NOT NULL,
    created_at TEXT NOT NULL,
    is_default INTEGER DEFAULT 1
);

-- Cloud credentials
CREATE TABLE cloud_credentials (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,  -- 'runpod', 'lambda'
    api_key_encrypted TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Team workspace
CREATE TABLE teams (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    owner_id TEXT NOT NULL
);

CREATE TABLE team_members (
    team_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,  -- 'admin', 'editor', 'viewer'
    joined_at TEXT NOT NULL,
    PRIMARY KEY (team_id, user_id)
);

-- Shared models
CREATE TABLE shared_models (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL,
    job_id TEXT NOT NULL,
    name TEXT NOT NULL,
    shared_by TEXT NOT NULL,
    shared_at TEXT NOT NULL,
    access_link TEXT
);

-- User settings
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

---

## 5. Rust Backend Commands

### Trainer Module (`src-tauri/src/trainer.rs`)

```rust
// Job management
#[tauri::command]
fn start_training(config: TrainingConfig) -> Result<Job, String>

#[tauri::command]
fn get_job_status(job_id: String) -> Result<JobStatus, String>

#[tauri::command]
fn cancel_job(job_id: String) -> Result<(), String>

#[tauri::command]
fn list_jobs(filter: JobFilter) -> Result<Vec<JobSummary>, String>

#[tauri::command]
fn get_job_details(job_id: String) -> Result<Job, String>

// Training execution
#[tauri::command]
async fn run_local_training(config: TrainingConfig) -> Result<Job, String>

#[tauri::command]
fn spawn_python_process(config: TrainingConfig, job_id: String) -> Result<(), String>
```

### Models Module (`src-tauri/src/models.rs`)

```rust
#[tauri::command]
fn list_local_models() -> Result<Vec<Model>, String>

#[tauri::command]
fn search_hf_models(query: String) -> Result<Vec<HFModel>, String>

#[tauri::command]
fn download_hf_model(model_id: String) -> Result<Model, String>

#[tauri::command]
fn upload_to_hf(job_id: String, model_id: String) -> Result<String, String>

#[tauri::command]
fn get_model_info(model_id: String) -> Result<Model, String>
```

### Cloud Module (`src-tauri/src/cloud.rs`)

```rust
#[tauri::command]
fn create_cloud_instance(config: CloudConfig) -> Result<CloudInstance, String>

#[tauri::command]
fn get_instance_status(instance_id: String) -> Result<InstanceStatus, String>

#[tauri::command]
fn terminate_instance(instance_id: String) -> Result<(), String>

#[tauri::command]
fn estimate_cost(provider: String, instance: String, hours: f32) -> Result<f32, String>

#[tauri::command]
fn sync_cloud_training(job_id: String) -> Result<JobStatus, String>
```

### Team Module (`src-tauri/src/team.rs`)

```rust
#[tauri::command]
fn create_team(name: String) -> Result<Team, String>

#[tauri::command]
fn invite_member(team_id: String, email: String, role: String) -> Result<(), String>

#[tauri::command]
fn list_team_models(team_id: String) -> Result<Vec<SharedModel>, String>

#[tauri::command]
fn share_model(job_id: String, team_id: String) -> Result<SharedModel, String>
```

---

## 6. Frontend Architecture

### 6.1 Directory Structure

```
src/
├── app/
│   ├── layout.tsx           # Root layout with sidebar
│   ├── page.tsx             # Redirect to /trainer
│   ├── trainer/
│   │   └── page.tsx         # 5-step wizard
│   ├── hub/
│   │   └── page.tsx        # HF browser
│   ├── inference/
│   │   └── page.tsx        # Chat testing
│   ├── team/
│   │   └── page.tsx       # Team workspace
│   └── settings/
│       └── page.tsx       # App settings
├── components/
│   ├── ui/                 # Reusable UI components
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   ├── Input.tsx
│   │   ├── Modal.tsx
│   │   └── ...
│   ├── trainer/            # Trainer-specific
│   │   ├── DataUpload.tsx
│   │   ├── ModelSelect.tsx
│   │   ├── Configure.tsx
│   │   ├── TrainingDashboard.tsx
│   │   └── Export.tsx
│   ├── hub/
│   │   ├── ModelCard.tsx
│   │   ├── SearchBar.tsx
│   │   └── ModelDetail.tsx
│   ├── inference/
│   │   ├── ChatMessage.tsx
│   │   ├── ChatInput.tsx
│   │   └── SettingsPanel.tsx
│   └── shared/
│       ├── Sidebar.tsx
│       ├── Header.tsx
│       └── StepIndicator.tsx
├── hooks/
│   ├── useTraining.ts       # Training job logic
│   ├── useModels.ts        # Model management
│   ├── useCloud.ts         # Cloud operations
│   └── useTeam.ts          # Team features
├── stores/
│   ├── trainingStore.ts   # Zustand: wizard state
│   ├── modelStore.ts      # Model cache
│   └── settingsStore.ts   # User preferences
├── lib/
│   ├── tauri.ts           # Tauri invoke wrappers
│   ├── api.ts             # API helpers
│   └── utils.ts           # Utility functions
└── styles/
    └── globals.css        # Tailwind + custom styles
```

### 6.2 State Management (Zustand)

```typescript
// trainingStore.ts
interface TrainingStore {
  // Wizard state
  currentStep: number;
  selectedModel: Model | null;
  selectedPreset: Preset;
  customConfig: TrainingConfig;
  jobId: string | null;
  
  // Actions
  setStep: (step: number) => void;
  selectModel: (model: Model) => void;
  selectPreset: (preset: Preset) => void;
  updateConfig: (config: Partial<TrainingConfig>) => void;
  startTraining: () => Promise<void>;
  cancelTraining: () => Promise<void>;
}
```

---

## 7. Integration Points

### 7.1 Python Training Pipeline

```python
# Called from Rust via subprocess
# packages/training/train_rosetta_unified.py

import subprocess
import sys

def train(config: dict):
    cmd = [
        sys.executable,
        "packages/training/train_rosetta_unified.py",
        "--model", config["model_id"],
        "--data", config["data_path"],
        "--task", config["task_type"],
        "--epochs", str(config["epochs"]),
        "--lr", str(config["learning_rate"]),
        "--batch_size", str(config["batch_size"]),
        "--output_dir", config["output_dir"]
    ]
    subprocess.run(cmd)
```

### 7.2 HuggingFace API

```rust
// Using huggingface_hub crate
use huggingface_hub::InferenceClient;

fn search_models(query: &str) -> Vec<ModelInfo> {
    let client = InferenceClient::from_env()
        .map_err(|e| e.to_string())?;
    
    client
        .search_model(query)
        .await
        .map_err(|e| e.to_string())?
}
```

### 7.3 Cloud Providers

```rust
// RunPod API
async fn create_runpod_instance(config: RunPodConfig) -> Result<Instance, String> {
    let client = reqwest::Client::new();
    
    let response = client
        .post("https://api.runpod.io/graphql")
        .json(&graphql_query! {
            query: "mutation { ... }",
            variables: config
        })
        .send()
        .await
        .map_err(|e| e.to_string())?;
    
    Ok(response.json()?)
}
```

---

## 8. Security

### 8.1 Credential Storage

- All API keys encrypted with AES-256
- Keys stored in OS keychain (Windows Credential Manager / macOS Keychain / Linux Secret Service)
- Never stored in plaintext in config files

### 8.2 Input Validation

- All user inputs sanitized before SQL queries (parameterized)
- File paths validated to prevent traversal attacks
- URL inputs validated and sanitized

### 8.3 Network Security

- HTTPS only for all external API calls
- Certificate pinning for HuggingFace API
- No sensitive data in logs

---

## 9. Performance Targets

| Metric | Target |
|--------|--------|
| App cold start | < 3 seconds |
| Training start | < 2 seconds |
| Status poll latency | < 100ms |
| UI frame rate | 60fps |
| Memory (idle) | < 200MB |
| Memory (training) | < 500MB + GPU |
| Binary size | < 15MB |

---

## 10. Complete

**Architecture Complete** - Ready for Epics and Stories

**Output:** `_bmad-output/planning-artifacts/architecture-n-xyme-trainer-desktop.md`