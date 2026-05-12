---
stepsCompleted: [1, 2]
inputDocuments:
  - "_bmad-output/planning-artifacts/product-brief-n-xyme-trainer-desktop.md"
  - "_bmad-output/planning-artifacts/prd-n-xyme-trainer-desktop.md"
workflowType: 'ux-design'
---

# UX Design Specification - N-Xyme Trainer Desktop App

**Author:** N-Xyme  
**Date:** 2026-04-23

---

## 1. Design Principles (ADHD-Friendly)

### Core Philosophy
- **One primary action per screen** - Never overwhelm
- **Progress always visible** - Never wonder "is it working?"
- **Big touch targets** - Minimum 44px buttons
- **Forgiving UI** - Confirm before destructive actions
- **Dark theme default** - Easy on eyes
- **Clear visual hierarchy** - What matters most is biggest

### Color Palette (Dark Theme)

| Role | Color | Hex |
|------|-------|-----|
| Background Primary | Deep Space | `#0d1117` |
| Background Secondary | Carbon | `#161b22` |
| Background Tertiary | Graphite | `#21262d` |
| Border | Slate | `#30363d` |
| Text Primary | Snow | `#c9d1d9` |
| Text Secondary | Silver | `#8b949e` |
| Accent Primary | Electric Blue | `#58a6ff` |
| Accent Hover | Bright Blue | `#79c0ff` |
| Success | Emerald | `#238636` |
| Error | Crimson | `#da3633` |
| Warning | Amber | `#d29922` |

### Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| App Title | Inter | 20px | 600 |
| Section Header | Inter | 18px | 600 |
| Body Text | Inter | 14px | 400 |
| Labels | Inter | 13px | 500 |
| Button Text | Inter | 14px | 600 |
| Code/Technical | JetBrains Mono | 13px | 400 |

### Spacing System

- Base unit: 4px
- Spacing scale: 4, 8, 12, 16, 24, 32, 48, 64px
- Card padding: 24px
- Section gap: 32px
- Element gap: 16px

---

## 2. App Shell Layout

### Window Structure

```
┌─────────────────────────────────────────────────────────────┐
│  [Icon] N-Xyme Trainer          [─] [□] [×]                │  ← Title Bar (32px)
├────────────┬────────────────────────────────────────────────┤
│            │                                                 │
│  SIDEBAR   │              MAIN CONTENT                      │
│   (200px)  │                                                 │
│            │   ┌─────────────────────────────────────────┐  │
│  🧠 Trainer │   │                                         │  │
│            │   │         STEP CONTENT AREA               │  │
│  📦 Models │   │                                         │  │
│            │   │                                         │  │
│  ⚙️ Settings│   │                                         │  │
│            │   │                                         │  │
│            │   └─────────────────────────────────────────┘  │
│            │                                                 │
│ ───────────│   ┌─────────────────────────────────────────┐  │
│ GPU: ████░ │   │  [← Back]              [Next →]        │  │  ← Action Bar
│ VRAM: 9.6GB│   └─────────────────────────────────────────┘  │
│            │                                                 │
└────────────┴────────────────────────────────────────────────┘
```

### Responsive Behavior
- Minimum width: 1024px
- Sidebar collapsible on smaller screens
- Content centers with max-width 900px

---

## 3. Step-by-Step UI Designs

### Step 1: Data Upload

```
┌─────────────────────────────────────────────────────────────┐
│  STEP 1 OF 5: Upload Training Data                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────────────────────────────────────────────┐  │
│   │                                                      │  │
│   │              📁  DROP FILES HERE                    │  │
│   │                                                      │  │
│   │        or click to browse                           │  │
│   │                                                      │  │
│   │    Supported: .jsonl, .csv (max 100MB)             │  │
│   │                                                      │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
│   ✓ training-data.jsonl (2.3 MB)                          │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐  │
│   │ PREVIEW (first 5 rows)                              │  │
│   │ ─────────────────────────────────────────────────── │  │
│   │ [user] Hello                │ [assistant] Hi!      │  │
│   │ [user] How are you?         │ [assistant] Good...  │  │
│   │ ...                                                 │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐  │
│   │ [← Back]                           [Next →]        │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Components:**
- **Drop Zone**: 300px height, dashed border (#30363d), solid on hover, accent on drag-over
- **File Info**: Shows name + size in success green after upload
- **Preview Table**: Max 5 rows, horizontal scroll if needed

### Step 2: Model Selection

```
┌─────────────────────────────────────────────────────────────┐
│  STEP 2 OF 5: Select Base Model                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Choose a model to fine-tune:                             │
│                                                             │
│   ┌─────────────────┐  ┌─────────────────┐                │
│   │  ○ Qwen2.5-0.5B │  │  ○ Qwen2.5-1.8B │                │
│   │                 │  │                 │                │
│   │  Size: 0.5GB    │  │  Size: 1.8GB    │                │
│   │  VRAM: ~3GB     │  │  VRAM: ~4GB     │                │
│   │  Best: Fast     │  │  Best: Balanced │                │
│   └─────────────────┘  └─────────────────┘                │
│                                                             │
│   ┌─────────────────┐  ┌─────────────────┐                │
│   │  ● Qwen2.5-3B   │  │  ○ Llama3-8B    │ ← SELECTED    │
│   │                 │  │                 │                │
│   │  Size: 3GB      │  │  Size: 8GB      │                │
│   │  VRAM: ~6GB     │  │  VRAM: ~8GB     │                │
│   │  Best: Quality  │  │  Best: Advanced │                │
│   └─────────────────┘  └─────────────────┘                │
│                                                             │
│   ⚠️ Your GPU has 9.6GB VRAM - Qwen2.5-3B is recommended  │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐  │
│   │ [← Back]                           [Next →]        │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Components:**
- **Model Cards**: 200px width, 2 per row, selection ring in accent color
- **Selection Badge**: Checkmark + "SELECTED" text
- **GPU Warning**: Yellow warning if model might not fit

### Step 3: Configuration

```
┌─────────────────────────────────────────────────────────────┐
│  STEP 3 OF 5: Configure Training                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Task Type:                                                │
│   ┌─────────────────────────────────────────────────────┐  │
│   │ Chat (standard conversation)                    ▼   │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
│   Preset:                                                   │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐                │
│   │    ⚡    │  │    ⚖️    │  │    🎯    │                │
│   │   Fast  │  │ Balanced │  │ Quality  │                │
│   │ 1 epoch │  │ 2 epochs │  │ 3 epochs │                │
│   │ LR: 2e-3│  │ LR: 1e-3 │  │ LR: 5e-4 │                │
│   └──────────┘  └──────────┘  └──────────┘                │
│                                                             │
│   [Show Advanced Options ▼]                                │
│                                                             │
│   Epochs: [  2  ]  Learning Rate: [ 0.001 ]               │
│   Batch Size: [  4  ]                                      │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐  │
│   │ [← Back]                           [Start Training]│  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Components:**
- **Task Dropdown**: Native select with custom styling
- **Preset Cards**: 3-column grid, icon + name + specs
- **Advanced Toggle**: Collapsible section
- **Number Inputs**: With +/- buttons, validation inline

### Step 4: Training Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│  TRAINING IN PROGRESS                                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ╔═══════════════════════════════════════════════════════╗ │
│   ║ ████████████████████░░░░░░░░░░░░░  67%              ║ │
│   ╚═══════════════════════════════════════════════════════╝ │
│                                                             │
│   ┌────────────────┐  ┌────────────────┐  ┌──────────────┐ │
│   │   EPOCH       │  │    LOSS       │  │     ETA      │ │
│   │    2 / 3      │  │    0.4523     │  │  ~4 minutes  │ │
│   └────────────────┘  └────────────────┘  └──────────────┘ │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐  │
│   │ LOSS CHART                                          │  │
│   │ 2.0 ┤                        ╭──╮                   │  │
│   │ 1.5 ┤              ╭────────╯  ╰────               │  │
│   │ 1.0 ┤        ╭────╯                              │  │
│   │ 0.5 ┤───────╯                                    │  │
│   │ 0.0 ┼────────────────────────────────            │  │
│   │       0    100   200   300   400   500  steps    │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
│   GPU: ████████████░░░░░  9.6GB / 12GB used               │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐  │
│   │              [ Cancel Training ]                    │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Components:**
- **Progress Bar**: Large, gradient fill, percentage overlay
- **Stat Cards**: 3-column grid with large numbers
- **Loss Chart**: Real-time updating line chart
- **GPU Bar**: Horizontal bar with usage percentage
- **Cancel Button**: Red, requires confirmation

### Step 5: Export

```
┌─────────────────────────────────────────────────────────────┐
│  ✅ TRAINING COMPLETE!                                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────────────────────────────────────────────┐  │
│   │              TRAINING SUMMARY                       │  │
│   │  ───────────────────────────────────────────────    │  │
│   │  Model:         Qwen2.5-3B                         │  │
│   │  Task:          Chat                               │  │
│   │  Epochs:        3 / 3                              │  │
│   │  Final Loss:    0.0234                             │  │
│   │  Duration:      12 minutes                         │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐  │
│   │                                                     │  │
│   │           ⬇️  DOWNLOAD GGUF (994MB)                │  │
│   │                                                     │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐  │
│   │           Push to HuggingFace (Optional)           │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐  │
│   │              [ Start New Training ]                 │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### NEW Step 6: Cloud Training (Optional)

```
┌─────────────────────────────────────────────────────────────┐
│  STEP 6 OF 6: Cloud Training (Optional)                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Training Location:                                        │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│   │   🖥️ LOCAL  │  │   ☁️ RUNPOD │  │   ⚡ LAMBDA │    │
│   │  (Your GPU) │  │             │  │             │    │
│   │   SELECTED  │  │             │  │             │    │
│   └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                             │
│   Cloud Settings (when RunPod selected):                   │
│   ┌─────────────────────────────────────────────────────┐  │
│   │ API Key: [••••••••••••••••••••]                   │  │
│   │ Instance Type: [ RTX 4090 x1                    ▼ ]│  │
│   │ Duration Limit: [ 2 hours ]                        │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
│   💰 Cost Estimate: ~$2.50/hour                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### NEW Step 7: Inference Testing

```
┌─────────────────────────────────────────────────────────────┐
│  INFERENCE TESTING                                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Model: qwen2.5-3b-chat-v1 [Change Model]                 │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐  │
│   │ 💬 Test your trained model                          │  │
│   │ ─────────────────────────────────────────────────── │  │
│   │                                                     │  │
│   │ You: What is fine-tuning?                          │  │
│   │                                                     │  │
│   │ 🤖: Fine-tuning is the process of taking a       │  │
│   │ pre-trained language model and training it       │  │
│   │ further on a specific dataset to specialize...   │  │
│   │                                                     │  │
│   │                                                     │  │
│   │ ┌───────────────────────────────────────────────┐  │  │
│   │ │ Type your message...                      [→] │  │
│   │ └───────────────────────────────────────────────┘  │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
│   Settings:                                                │
│   Temperature: [═══════●══] 0.7                            │
│   Max Tokens: [══════●════] 2048                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### NEW Page: HuggingFace Hub

```
┌─────────────────────────────────────────────────────────────┐
│  🤗 HuggingFace Hub                                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   🔍 Search models: [qwen2.5           Search]            │
│                                                             │
│   Sort by: [Downloads    ▼]  Filter: [License: Apache]    │
│                                                             │
│   ┌─────────────────┐  ┌─────────────────┐                │
│   │ Qwen/Qwen2.5-   │  │ meta-llama/     │                │
│   │   3B-Instruct   │  │ Llama-3-8B      │                │
│   │                 │  │                 │                │
│   │ 📥 2.3M        │  │ 📥 8.1M        │                │
│   │ ⭐ 4.2k        │  │ ⭐ 12k        │                │
│   │ 🧠 3B          │  │ 🧠 8B          │                │
│   └─────────────────┘  └─────────────────┘                │
│                                                             │
│   My Uploaded Models:                                       │
│   ├── qwen2.5-3b-tool-caller (you) - 📥 150               │
│   └── qwen2.5-0.5b-chat-v2 (you) - 📥 89                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### NEW Page: Team Workspace

```
┌─────────────────────────────────────────────────────────────┐
│  👥 Team Workspace                                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Team: N-Xyme AI                                          │
│   Members: 4 (you are Admin)                               │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐  │
│   │ SHARED MODELS                                       │  │
│   │ ─────────────────────────────────────────────────  │  │
│   │ • qwen2.5-3b-sales-bot    👤 john    2 days ago   │  │
│   │ • llama3-customer-support 👤 sarah   5 days ago   │  │
│   │ • qwen2.5-tech-docs       👤 you     1 week ago   │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐  │
│   │ TEAM TRAINING HISTORY                               │  │
│   │ ─────────────────────────────────────────────────  │  │
│   │ • john - Qwen2.5-0.5B - completed - 10 min ago    │  │
│   │ • sarah - Llama3-8B - completed - 2 hours ago     │  │
│   │ • you - Qwen2.5-3B - failed - 3 hours ago         │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
│   [Invite Member]  [Manage Roles]                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Sidebar Navigation (Updated)

```
┌────────────┬────────────────────────────────────────────────┐
│            │                                                 │
│  SIDEBAR   │              MAIN CONTENT                       │
│            │                                                 │
│  🧠 Trainer │   (5-step wizard)                              │
│  📊 Hub    │   (HuggingFace browser)                        │
│  💬 Inference│  (Chat testing)                               │
│  👥 Team    │   (Team workspace)                            │
│  ⚙️ Settings│  (App settings)                              │
│            │                                                 │
│ ───────────│                                                 │
│ GPU: ████░ │   [Cloud: ● LOCAL | ○ RUNPOD | ○ LAMBDA]       │
│ VRAM: 9.6GB│                                                 │
└────────────┴────────────────────────────────────────────────┘
```

**Components:**
- **Summary Card**: All training stats in one place
- **Download Button**: Large, prominent, shows file size
- **HF Button**: Secondary style, optional
- **New Training**: Resets wizard to Step 1

---

## 4. Component Library

### Buttons

| Variant | Background | Text | Use |
|---------|------------|------|-----|
| Primary | `#58a6ff` | White | Main actions |
| Secondary | `#21262d` | `#c9d1d9` | Secondary actions |
| Danger | `#da3633` | White | Destructive actions |
| Disabled | `#21262d` | `#484f58` | Inactive state |

### Form Inputs

- Background: `#0d1117`
- Border: `#30363d`
- Border Focus: `#58a6ff`
- Text: `#c9d1d9`
- Placeholder: `#484f58`
- Height: 44px
- Border Radius: 8px

### Cards

- Background: `#161b22`
- Border: `#30363d`
- Border Radius: 12px
- Padding: 24px
- Hover: Border `#58a6ff`

### Progress Bar

- Background: `#21262d`
- Fill: Gradient `#58a6ff` → `#238636`
- Height: 24px
- Border Radius: 12px

---

## 5. Animations & Micro-interactions

| Element | Animation | Duration |
|---------|-----------|----------|
| Step transitions | Fade + slide | 300ms ease |
| Button hover | Scale 1.02 | 150ms |
| Card hover | Border glow | 200ms |
| Progress bar | Width transition | 300ms ease |
| Chart update | Smooth append | 200ms |
| Drop zone drag | Pulse border | 500ms |
| Success state | Checkmark draw | 400ms |

---

## 6. Accessibility

| Requirement | Implementation |
|-------------|----------------|
| Keyboard nav | Tab order follows visual flow |
| Focus states | 2px outline in accent color |
| Screen reader | ARIA labels on all icons |
| Color contrast | WCAG AA compliant |
| Error states | Icon + text (not color alone) |
| Touch targets | Min 44px × 44px |

---

## 7. Error States

| Scenario | UI Response |
|----------|-------------|
| Invalid file | Red border on drop zone + error message below |
| Model OOM | Modal: "Insufficient VRAM. Try Qwen2.5-0.5B" |
| Training crash | Error banner with "View Logs" and "Retry" |
| Export fail | Toast notification + retry button |
| Network offline | Banner: "Some features require internet" |

---

## 8. Complete

**UX Design Complete** - Ready for Architecture Phase

**Output:** `_bmad-output/planning-artifacts/ux-design-n-xyme-trainer-desktop.md`