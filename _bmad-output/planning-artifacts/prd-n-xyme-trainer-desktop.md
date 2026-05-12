---
stepsCompleted: [1]
inputDocuments:
  - "_bmad-output/planning-artifacts/product-brief-n-xyme-trainer-desktop.md"
workflowType: 'prd'
---

# Product Requirements Document - N-Xyme Trainer Desktop App

**Author:** N-Xyme  
**Date:** 2026-04-23  
**Version:** 1.0

---

## Step 2: Project Discovery

### Project Classification

- **Product Type:** Desktop Application (Tauri + React)
- **Domain:** Developer Tools / LLM Fine-tuning
- **Project Context:** Brownfield - extending existing nx-mind-desktop Tauri app
- **Domain Complexity:** Medium (leveraging existing infrastructure + training pipeline)

### Input Documents

Product Brief loaded from: `_bmad-output/planning-artifacts/product-brief-n-xyme-trainer-desktop.md`

### Key Inputs from Brief

**Problem:** Fine-tuning LLMs is fragmented, CLI-only, not general-purpose, no standalone UX

**Solution:** Desktop app from data → training → export in one flow

**Target Users:**
- ML Engineers (faster iteration)
- Full-Stack Devs (specialized LLMs)
- Startups (budget constraints)
- Research Hobbyists

**MVP Scope:**
- Base models: Qwen2.5 family, Llama3
- Task templates: tool-calling, chat, classification, summarization
- LoRA fine-tuning (QLoRA for consumer GPUs)
- Local training with GGUF export
- Hyperparameter presets (fast/balanced/quality)
- Training dashboard

**Tech Stack:**
- Tauri 2.x (Rust backend)
- React 18 + Next.js 14
- Tailwind CSS
- SQLite (job tracking)
- Python subprocess (training)

---

## Step 3: Functional Requirements

### FR1: Data Upload System
**Priority:** P0 (Must Have)

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR1.1 | Drag & drop file upload | User can drag .jsonl or .csv onto drop zone |
| FR1.2 | Click to browse | Click opens native file picker |
| FR1.3 | File type validation | Accept .jsonl, .csv; reject others with message |
| FR1.4 | File size limit | Max 100MB; show error if exceeded |
| FR1.5 | JSONL parsing | Each line must be valid JSON |
| FR1.6 | JSONL schema check | Must have "messages" array with role/content |
| FR1.7 | CSV parsing | Parse with header row |
| FR1.8 | Data preview | Show first 5 rows in table format |
| FR1.9 | Error line highlighting | Show exact line number for parse errors |
| FR1.10 | Column mapping | For CSV, map input/output columns |

### FR2: Model Selection
**Priority:** P0 (Must Have)

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR2.1 | Model catalog display | Show grid of available models |
| FR2.2 | Model card info | Each card shows name, size, VRAM, best for |
| FR2.3 | Model selection | Click to select; visual selected state |
| FR2.4 | VRAM requirement display | Show GB needed for each model |
| FR2.5 | GPU compatibility check | Detect available VRAM; warn if insufficient |
| FR2.6 | Single selection | Only one model selectable at a time |
| FR2.7 | Model list | Qwen2.5-0.5B, 1.8B, 3B, Llama3-8B |

### FR3: Training Configuration
**Priority:** P0 (Must Have)

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR3.1 | Task template dropdown | Options: Chat, Tool-Calling, Classification, Summarization |
| FR3.2 | Task description | Each task shows brief description |
| FR3.3 | Preset selector | Three cards: Fast, Balanced, Quality |
| FR3.4 | Preset details | Each preset shows epochs, LR, batch size |
| FR3.5 | Preset selection | Click to select; visual selected state |
| FR3.6 | Advanced toggle | "Show Advanced" button reveals extra params |
| FR3.7 | Epochs input | Number field, 1-10 range |
| FR3.8 | Learning rate input | Float field, 1e-5 to 1e-2 |
| FR3.9 | Batch size input | Number field, 1-32, power of 2 recommended |
| FR3.10 | Config validation | Validate all params before starting |

### FR4: Training Execution
**Priority:** P0 (Must Have)

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR4.1 | Start training button | Begins training with selected config |
| FR4.2 | Progress bar | Shows percentage complete |
| FR4.3 | Epoch counter | "Epoch 2/3" display |
| FR4.4 | Loss chart | Real-time line chart of loss values |
| FR4.5 | GPU memory display | Shows used/total VRAM |
| FR4.6 | ETA display | Shows estimated time remaining |
| FR4.7 | Cancel button | Stops training mid-process |
| FR4.8 | Job persistence | Job survives app restart |
| FR4.9 | Status polling | Updates every 2 seconds |

### FR5: Model Export
**Priority:** P0 (Must Have)

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR5.1 | Auto-export on complete | GGUF generated when training finishes |
| FR5.2 | Download button | "Download GGUF" button |
| FR5.3 | File size display | Show size of export file |
| FR5.4 | Direct download | File downloads directly, not via browser |
| FR5.5 | Training summary | Show final loss, epochs, time taken |
| FR5.6 | Export status | Show export progress if slow |
| FR5.7 | Retry on failure | "Retry Export" if export fails |

### FR6: App Shell
**Priority:** P0 (Must Have)

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR6.1 | Window controls | Minimize, maximize, close work |
| FR6.2 | App icon | Custom N-Xyme Trainer icon |
| FR6.3 | App title | "N-Xyme Trainer" in title bar |
| FR6.4 | Dark theme | Default dark theme applied |
| FR6.5 | Responsive layout | Works 1024px+ screens |
| FR6.6 | Sidebar navigation | Switch between Trainer/Models/Settings |

---

## Step 4: Non-Functional Requirements

### NFR1: Performance
| Requirement | Target |
|-------------|--------|
| Cold start time | < 3 seconds |
| Training start latency | < 2 seconds after click |
| Progress update latency | < 2 seconds |
| Memory usage (idle) | < 200MB |

### NFR2: Reliability
| Requirement | Target |
|-------------|--------|
| Crash rate | < 1% |
| Training persistence | Jobs survive restart |
| Auto-save | Config saved on each step |

### NFR3: Usability (ADHD-Friendly)
| Requirement | Target |
|-------------|--------|
| Button minimum size | 44px x 44px |
| Contrast ratio | WCAG AA (4.5:1) |
| Focus indicators | Visible focus states |
| Error messages | Friendly, actionable |
| Progress always visible | Never ambiguous state |

### NFR4: Security
| Requirement | Target |
|-------------|--------|
| No external data sending | All processing local |
| File path sanitization | Prevent path traversal |
| Config validation | Sanitize all inputs |

---

## Step 5: Technical Requirements

### TR1: Integration
| Requirement | Implementation |
|-------------|----------------|
| Training pipeline | Call `python train_rosetta_unified.py` |
| Model cache | Use HuggingFace cache |
| Job storage | SQLite database in app data dir |
| GGUF export | Via training pipeline |

### TR2: Data Flow
```
User UI (React)
    → Tauri Command (Rust)
    → Spawn Python Subprocess
    → Training runs
    → Progress written to SQLite
    → UI polls status
    → Export GGUF on complete
```

### TR3: Database Schema
```sql
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    created_at TEXT,
    status TEXT,  -- pending, running, completed, failed, exported
    model TEXT,
    data_file TEXT,
    task TEXT,
    epochs INTEGER,
    lr REAL,
    batch_size INTEGER,
    current_epoch INTEGER,
    total_epochs INTEGER,
    loss_history TEXT,  -- JSON array
    error_message TEXT,
    gguf_path TEXT,
    created_at TEXT
);

CREATE TABLE models (
    id TEXT PRIMARY KEY,
    name TEXT,
    size_gb REAL,
    vram_gb REAL,
    best_for TEXT
);
```

---

## Step 7: Edge Cases

| Scenario | Handling |
|----------|----------|
| Invalid file uploaded | Show error with line number |
| Model too big for GPU | Warn before starting, suggest smaller |
| Training crashes | Save state, allow retry |
| App closes during training | Job continues, resume on restart |
| Export fails | Retry button + error details |
| Disk full | Warn before training starts |
| No internet (for model download) | Show offline message |

---

## Step 8: In Scope for v1.0

The following were initially marked out of scope but are NOW INCLUDED:

| Feature | Description |
|---------|-------------|
| **Cloud Training** | Option to train on remote GPU (RunPod, Lambda Labs) |
| **Multi-GPU Training** | Distribute training across multiple GPUs |
| **HuggingFace Hub** | Browse/search models from HuggingFace |
| **Custom Base Model** | Upload your own base model to fine-tune |
| **Training from URL** | Import training data from URL |
| **Real-time Inference** | Test your trained model in-app |
| **Team Features** | Share models with team, view team training history |

---

## Step 9: Additional Functional Requirements

### FR7: Cloud Training
| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR7.1 | Cloud provider selection | Choose RunPod, Lambda, etc. |
| FR7.2 | Cloud credentials | Secure storage of API keys |
| FR7.3 | Remote training | Training runs on cloud GPU |
| FR7.4 | Sync progress | Real-time status from cloud |
| FR7.5 | Download results | Pull trained model back locally |

### FR8: Multi-GPU Training
| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR8.1 | GPU detection | Detect all available GPUs |
| FR8.2 | GPU selection | Choose which GPUs to use |
| FR8.3 | Distributed training | Split batch across GPUs |
| FR8.4 | Load balancing | Distribute work evenly |

### FR9: HuggingFace Integration
| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR9.1 | Browse models | Search HF hub for base models |
| FR9.2 | Model details | Show model info, downloads, stars |
| FR9.3 | Download model | Download to local cache |
| FR9.4 | Push model | Upload trained model to HF |
| FR9.5 | List my models | Show previously uploaded models |

### FR10: Custom Model Upload
| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR10.1 | Upload GGUF | Upload custom GGUF as base |
| FR10.2 | Upload HF model | Upload from local HF model dir |
| FR10.3 | Model validation | Verify model format before use |

### FR11: URL Data Import
| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR11.1 | Import from URL | Fetch JSONL/CSV from URL |
| FR11.2 | Auth support | Support auth headers if needed |
| FR11.3 | Progress indication | Show download progress |

### FR12: In-App Inference
| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR12.1 | Chat interface | Test trained model with chat UI |
| FR12.2 | System prompt | Set custom system prompt |
| FR12.3 | Temperature control | Adjust generation parameters |
| FR12.4 | Stream responses | Show tokens as generated |

### FR13: Team Features
| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR13.1 | Team workspace | Shared space for team models |
| FR13.2 | Share model | Share trained model with team |
| FR13.3 | Team training history | View all team training jobs |
| FR13.4 | Role-based access | Admin, Editor, Viewer roles |

---

**PRD Complete** - Ready for UX Design Phase

**Output:** `_bmad-output/planning-artifacts/prd-n-xyme-trainer-desktop.md`