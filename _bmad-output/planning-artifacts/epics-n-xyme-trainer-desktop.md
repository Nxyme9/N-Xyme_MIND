---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - "_bmad-output/planning-artifacts/product-brief-n-xyme-trainer-desktop.md"
  - "_bmad-output/planning-artifacts/prd-n-xyme-trainer-desktop.md"
  - "_bmad-output/planning-artifacts/ux-design-n-xyme-trainer-desktop.md"
  - "_bmad-output/planning-artifacts/architecture-n-xyme-trainer-desktop.md"
workflowType: 'epics'
project_name: 'N-Xyme Trainer Desktop'
user_name: 'N-Xyme'
date: '2026-04-23'
---

# Epics and Stories - N-Xyme Trainer Desktop App

**Author:** N-Xyme  
**Date:** 2026-04-23

---

## Epic 1: App Shell & Navigation

**User Value:** User can navigate between app sections and access settings

### Stories:

#### E1S1: Window Management
- Window minimize, maximize, close buttons work
- App remembers window size/position
- Custom title bar with app icon

#### E1S2: Sidebar Navigation
- Trainer, Hub, Inference, Team, Settings tabs
- Active tab highlighted
- Smooth transitions between pages

#### E1S3: GPU Status Bar
- Shows current GPU utilization
- Shows VRAM usage
- Quick cloud/local toggle

#### E1S4: Dark Theme
- All components use dark color palette
- Consistent styling across app

---

## Epic 2: Data Input & Validation

**User Value:** User can upload and validate training data from multiple sources

### Stories:

#### E2S1: Local File Upload
- Drag & drop zone for .jsonl and .csv
- Click to open file browser
- File type validation with error messages
- Max 100MB size limit

#### E2S2: JSONL Parsing & Validation
- Each line must be valid JSON
- Must have "messages" array with role/content
- Show line number for parse errors

#### E2S3: CSV Parsing
- Parse with header row
- Column mapping UI for input/output
- Minimum 2 columns required

#### E2S4: Data Preview
- Table showing first 5 rows
- Truncate long content with "..."
- Row count display

#### E2S5: URL Data Import
- Input field for URL
- Fetch and download progress
- Support for authentication headers

---

## Epic 3: Model Selection

**User Value:** User can browse and select base models from local cache or HuggingFace

### Stories:

#### E3S1: Local Model Display
- Grid of downloaded models
- Model card shows: name, size, VRAM, best for
- Selection state with checkmark

#### E3S2: HuggingFace Browser
- Search input for model queries
- Sort by: downloads, likes, recent
- Filter by: license, architecture
- Paginated results grid

#### E3S3: Model Details Modal
- Full model description
- Download count, stars
- Required VRAM
- "Download" and "Use" buttons

#### E3S4: GPU Compatibility Check
- Detect available VRAM
- Warn if model won't fit
- Suggest smaller alternatives

#### E3S5: Custom Model Upload
- Upload GGUF file as base
- Upload from local HF model directory
- Validate model format

---

## Epic 4: Training Configuration

**User Value:** User can configure and start training with sensible defaults

### Stories:

#### E4S1: Task Template Selection
- Dropdown: Chat, Tool-Calling, Classification, Summarization
- Description for each task
- Task affects default params

#### E4S2: Preset Selection
- Three cards: Fast, Balanced, Quality
- Shows: epochs, LR, batch size
- Click to select

#### E4S3: Advanced Parameters
- Collapsible "Show Advanced" section
- Epochs: 1-10
- Learning rate: 1e-5 to 1e-2
- Batch size: 1-32

#### E4S4: Config Validation
- Validate all params before starting
- Show errors inline
- Disable start button until valid

---

## Epic 5: Local Training Execution

**User Value:** User can run training locally with real-time progress

### Stories:

#### E5S1: Training Start
- Create job in SQLite
- Spawn Python subprocess
- Show "Starting..." state
- Redirect to dashboard

#### E5S2: Progress Polling
- Poll every 2 seconds
- Update progress bar
- Update epoch counter

#### E5S3: Loss Chart
- Real-time line chart
- X-axis: steps
- Y-axis: loss (auto-scale)
- Smooth updates

#### E5S4: GPU Monitoring
- Show VRAM usage bar
- Update every 2 seconds
- Color code: green (safe), yellow (high), red (critical)

#### E5S5: ETA Calculation
- Based on current loss rate
- Show "X minutes remaining"
- Update every epoch

#### E5S6: Cancel Training
- Cancel button with confirmation
- Kill subprocess
- Mark job as "cancelled"

#### E5S7: Job Persistence
- Jobs survive app restart
- Resume polling on restart
- Show current state immediately

---

## Epic 6: Cloud Training (Optional)

**User Value:** User can train on remote GPU when local isn't enough

### Stories:

#### E6S1: Cloud Provider Selection
- Cards: RunPod, Lambda Labs
- Show pricing info
- Select default provider

#### E6S2: Cloud Credentials
- Secure API key input
- Save to OS keychain
- Test connection button

#### E6S3: Instance Configuration
- Select GPU type (4090, A100, etc.)
- Set duration limit
- Show cost estimate

#### E6S4: Remote Training
- Create cloud instance via API
- Upload training data
- Start training remotely
- Sync progress every 5 seconds

#### E6S5: Cloud Cleanup
- Auto-terminate on complete
- Manual terminate button
- Cost summary after

---

## Epic 7: Multi-GPU Training

**User Value:** User can distribute training across multiple GPUs

### Stories:

#### E7S1: GPU Detection
- Detect all available GPUs
- Show GPU list with names/memory

#### E7S2: GPU Selection
- Checkboxes for each GPU
- Select all / Clear all

#### E7S3: Distributed Training
- Split batch across GPUs
- Aggregate gradients
- Report combined loss

---

## Epic 8: Model Export

**User Value:** User can download trained model in standard format

### Stories:

#### E8S1: Auto GGUF Export
- Export on training complete
- Show export progress
- Default quantization: Q4_K_M

#### E8S2: Download Button
- "Download GGUF" prominent button
- Shows file size
- Direct browser download

#### E8S3: HuggingFace Push
- "Push to HF" button
- Model card creation
- Set model name, visibility

#### E8S4: Export Settings
- Choose quantization level
- Custom filename
- Include metadata

---

## Epic 9: In-App Inference

**User Value:** User can test trained model immediately

### Stories:

#### E9S1: Chat Interface
- Message input
- Stream response tokens
- Conversation history

#### E9S2: System Prompt
- Custom system prompt field
- Save/load presets

#### E9S3: Generation Settings
- Temperature slider
- Max tokens
- Top-p, top-k

#### E9S4: Model Selector
- Switch between trained models
- Quick comparison

---

## Epic 10: Team Features

**User Value:** Teams can share models and collaborate

### Stories:

#### E10S1: Team Creation
- Create team with name
- Invite members by email

#### E10S2: Role Management
- Roles: Admin, Editor, Viewer
- Admin can change roles
- Viewer can only read

#### E10S3: Shared Models
- Share trained model with team
- View team members' models
- Download team models

#### E10S4: Team Training History
- View all team training jobs
- Filter by member, status
- Stats summary

---

## Implementation Priority

### Phase 1: Core MVP
- E1: App Shell
- E2: Data Input
- E3: Model Selection
- E4: Training Config
- E5: Local Training
- E8: Export (basic)

### Phase 2: Cloud & Multi-GPU
- E6: Cloud Training
- E7: Multi-GPU

### Phase 3: Advanced
- E9: Inference
- E10: Team Features

---

## Coverage Matrix

| Requirement | Epic | Story |
|------------|------|--------|
| FR1: Data Upload | E2 | E2S1-E2S5 |
| FR2: Model Selection | E3 | E3S1-E3S5 |
| FR3: Training Config | E4 | E4S1-E4S4 |
| FR4: Training Execution | E5 | E5S1-E5S7 |
| FR5: Model Export | E8 | E8S1-E8S4 |
| FR7: Cloud Training | E6 | E6S1-E6S5 |
| FR8: Multi-GPU | E7 | E7S1-E7S3 |
| FR9: HF Integration | E3 | E3S2-E3S4 |
| FR10: Custom Upload | E3 | E3S5 |
| FR11: URL Import | E2 | E2S5 |
| FR12: Inference | E9 | E9S1-E9S4 |
| FR13: Team | E10 | E10S1-E10S4 |

---

**Epics and Stories Complete** - Ready for Implementation

**Output:** `_bmad-output/planning-artifacts/epics-n-xyme-trainer-desktop.md`