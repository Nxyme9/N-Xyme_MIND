---
title: AI-DAW Integration Epics and Stories
date: 2026-05-12
version: 1.0.0
inputDocuments:
  - docs/ai-daw-integration-plan.md
---

# AI-DAW Integration - Epics and Stories

## Project: N-Xyme AI-DAW Integration
**Goal**: Create bleeding-edge AI-assisted music production workflow with context-aware MCP loading

---

## Functional Requirements (FR)

### Core Architecture
FR1: MCP server must support context-aware tool loading (load only when DAW active)
FR2: DAWContextManager must detect Bitwig Studio via process check + OSC ping + user flag
FR3: Tool categories must be conditionally loaded (minimal/transport/tracks/clips/devices/mixer/arrangement/creative/voice)
FR4: MCP tools must expand from 15 to 200+ matching AbletonMCP capability

### Voice Control
FR5: Voice input must flow through nx_dictate (STT) → workflow_engine (NLP) → MCP → Bitwig
FR6: Wake word "Hey N-Xyme" must trigger voice command mode
FR7: TTS feedback must confirm every executed action
FR8: Voice commands must parse natural language to OSC commands

### Local LLM Integration
FR9: Local LLM must execute MCP tools directly with tool calling
FR10: Project context must be injected (project state, recent commands, templates)
FR11: Mode switching between fast (0.5b) and smart (7b) models based on complexity

### Predictive Workflows
FR12: Learning engine must predict next track creation from project history
FR13: Learning engine must suggest plugins from audio analysis
FR14: Learning engine must learn arrangement flow from scene/clip sequences

### Neural Audio
FR15: ONNX models must load via NXymeAudioExtension.java
FR16: VST3 AI plugins must integrate via Bitwig device chain
FR17: MIDI-triggered generation must work with clip launches

---

## Non-Functional Requirements (NFR)

NFR1: Voice command accuracy >95%
NFR2: Local LLM response time <500ms
NFR3: Predictive accuracy >70%
NFR4: Neural audio latency <100ms
NFR5: Time to complete voice workflow <5s
NFR6: Time to complete text workflow <10s
NFR7: MCP tools load in <1s when DAW detected
NFR8: System must work completely offline (local processing)

---

## Additional Requirements (Architecture)

- DAWContextManager class pattern from local_llm/integration.py
- Tool categories mapped to conditional loading triggers
- MCP not registered in global opencode.json (conditional module)
- Workflow engine and ai_context must synchronize (currently isolated)
- NLP parser _ai_interpret_command() is STUB - needs LLM integration

---

## Epics List

| Epic | Name | Priority | Target |
|------|------|----------|--------|
| EPIC-1 | Context-Aware MCP Architecture | P0 | Month 1 |
| EPIC-2 | MCP Tool Expansion (15→200+) | P0 | Month 1 |
| EPIC-3 | Voice Control Integration | P1 | Month 2 |
| EPIC-4 | Local LLM Integration | P1 | Month 2 |
| EPIC-5 | Predictive Workflows | P2 | Month 3 |
| EPIC-6 | Neural Audio Integration | P2 | Month 4 |

---

# EPIC-1: Context-Aware MCP Architecture

## Epic Goal
Implement DAWContextManager and conditional tool loading so MCP tools ONLY load when Bitwig Studio is detected/active

## Stories

### STORY-1.1: DAWContextManager Implementation
**Priority**: P0  
**Estimate**: 3 days

**Description**: Create DAWContextManager class that detects DAW state via three mechanisms

**Acceptance Criteria**:
- [ ] Process check: `pgrep -f "Bitwig Studio"` returns running status
- [ ] OSC ping: sends `/bitwig/ping` to 127.0.0.1:8000, receives response
- [ ] User flag: reads `daw-mode=on` from config
- [ ] State machine: idle → daw → voice modes
- [ ] Event emission: triggers tool registration on state change

**Implementation Files**:
- `nx-audio-bridge/daw_context.py` (new)

---

### STORY-1.2: Dynamic Tool Loader Pattern
**Priority**: P0  
**Estimate**: 2 days

**Description**: Implement class-based MCP client with conditional tool registration

**Acceptance Criteria**:
- [ ] DAWMCPClient extends FastMCP
- [ ] Tool registration deferred to context check
- [ ] minimal tools: `get_audio_state`, `check_daw_running` always available
- [ ] Category-specific tool sets load on context match
- [ ] Graceful fallback when DAW not detected

**Implementation Files**:
- `nx-audio-bridge/mcp_server.py` (modify)

---

### STORY-1.3: Integration with OpenCode
**Priority**: P1  
**Estimate**: 1 day

**Description**: Configure MCP to load conditionally instead of globally

**Acceptance Criteria**:
- [ ] MCP server accepts `--daw-mode` flag
- [ ] MCP not in global opencode.json
- [ ] Startup logs "DAW mode: inactive" until detection
- [ ] Manual override: `daw-mode=on` CLI flag

**Implementation Files**:
- `nx-audio-bridge/mcp_server.py` (modify startup)
- `opencode.json` (optional override)

---

# EPIC-2: MCP Tool Expansion (15→200+)

## Epic Goal
Expand MCP server from 15 tools to 200+ matching AbletonMCP capability

## Stories

### STORY-2.1: Transport Tools (P0)
**Priority**: P0  
**Estimate**: 2 days

**Description**: Add transport control tools

**Acceptance Criteria**:
- [ ] play, stop, record, pause
- [ ] loop toggle, loop region set
- [ ] tempo (get/set), tempo bend
- [ ] time signature change
- [ ] metronome toggle

**Tools to Add**: 10

---

### STORY-2.2: Track Management Tools (P0)
**Priority**: P0  
**Estimate**: 3 days

**Description**: Add track CRUD operations

**Acceptance Criteria**:
- [ ] create_track (audio/MIDI/hybrid)
- [ ] delete_track, rename_track
- [ ] volume (get/set), volume ramp
- [ ] pan (get/set), pan law
- [ ] solo, mute, record arm
- [ ] color assignment
- [ ] track duplicates

**Tools to Add**: 15

---

### STORY-2.3: Clip Tools (P0)
**Priority**: P0  
**Estimate**: 3 days

**Description**: Add clip/arrangement manipulation

**Acceptance Criteria**:
- [ ] create_clip, delete_clip, duplicate_clip
- [ ] launch_clip, stop_clip
- [ ] quantize_clip, warp_clip
- [ ] clip color, clip name
- [ ] copy/paste between tracks
- [ ] arrangement sequence

**Tools to Add**: 15

---

### STORY-2.4: Device/Plugin Tools (P1)
**Priority**: P1  
**Estimate**: 4 days

**Description**: Add device and plugin control

**Acceptance Criteria**:
- [ ] add_device, remove_device
- [ ] browse_device (search presets)
- [ ] preset_load, preset_save
- [ ] parameter_get, parameter_set, parameter_bank
- [ ] device bypass, device enable
- [ ] chain ordering

**Tools to Add**: 20

---

### STORY-2.5: Mixer Tools (P1)
**Priority**: P1  
**Estimate**: 2 days

**Description**: Add mixer section control

**Acceptance Criteria**:
- [ ] send_level (get/set), send_pan
- [ ] receive_level
- [ ] cue volume, cue toggle
- [ ] master volume, master meter
- [ ] track routing

**Tools to Add**: 12

---

### STORY-2.6: Arrangement Tools (P2)
**Priority**: P2  
**Estimate**: 3 days

**Description**: Add arrangement-level operations

**Acceptance Criteria**:
- [ ] copy_region, paste_region
- [ ] glide_time, crossfade
- [ ] duplicate_arrangement
- [ ] section markers
- [ ] automation read/write

**Tools to Add**: 12

---

### STORY-2.7: Creative Tools (P2)
**Priority**: P2  
**Estimate**: 2 days

**Description**: Add generative/creative features

**Acceptance Criteria**:
- [ ] randomize_clip, randomize_parameters
- [ ] euclidean_generator
- [ ] chord_generator
- [ ] scale_quantize
- [ ] strum_pattern

**Tools to Add**: 10

---

# EPIC-3: Voice Control Integration

## Epic Goal
Implement voice-first workflow with wake word detection and TTS feedback

## Stories

### STORY-3.1: Wake Word Detection
**Priority**: P1  
**Estimate**: 2 days

**Description**: Implement "Hey N-Xyme" wake word trigger

**Acceptance Criteria**:
- [ ] Hotword detection via pocketsphinx or whisper
- [ ] Background listening mode
- [ ] Low CPU usage in idle
- [ ] Configurable wake phrase

**Implementation Files**:
- `nx_dictate/wake_word.py` (new or modify)

---

### STORY-3.2: Voice Command Pipeline
**Priority**: P1  
**Estimate**: 3 days

**Description**: Connect STT → NLP → MCP execution

**Acceptance Criteria**:
- [ ] nx_dictate STT processes voice input
- [ ] workflow_engine receives parsed command
- [ ] _ai_interpret_command() integrates LLM (not stub)
- [ ] MCP tools execute parsed command
- [ ] Error handling for unrecognized commands

**Implementation Files**:
- `nx-audio-workflow/voice_controller.py` (new)
- `nx-audio-workflow/workflow_engine.py` (modify _ai_interpret_command)

---

### STORY-3.3: TTS Feedback
**Priority**: P1  
**Estimate**: 1 day

**Description**: Add voice confirmation for all actions

**Acceptance Criteria**:
- [ ] TTS speaks action confirmation
- [ ] "Added reverb to track 3" style feedback
- [ ] Error messages spoken
- [ ] Configurable voice, speed, volume

**Implementation Files**:
- `nx_dictate/tts_feedback.py` (new)

---

### STORY-3.4: Hands-Free Workflows
**Priority**: P2  
**Estimate**: 3 days

**Description**: Enable fully hands-free production

**Acceptance Criteria**:
- [ ] Continuous voice session mode
- [ ] Context-aware follow-up commands
- [ ] "Do that again" repeat last action
- [ ] "Undo" voice command

**Implementation Files**:
- `nx-audio-workflow/voice_controller.py` (extend)

---

# EPIC-4: Local LLM Integration

## Epic Goal
Connect local LLM for zero-latency AI interaction with tool calling

## Stories

### STORY-4.1: Tool Calling Setup
**Priority**: P1  
**Estimate**: 2 days

**Description**: Configure local LLM to call MCP tools

**Acceptance Criteria**:
- [ ] llama.cpp server integrates with MCP
- [ ] Tool definitions passed to LLM
- [ ] JSON tool call parsing
- [ ] Tool result passed back to LLM

**Implementation Files**:
- `local_llm/integration.py` (extend for audio context)

---

### STORY-4.2: Context Injection
**Priority**: P1  
**Estimate**: 2 days

**Description**: Inject project state into LLM prompts

**Acceptance Criteria**:
- [ ] Current project structure in context
- [ ] Recent command history
- [ ] Active templates loaded
- [ ] DAW state (tempo, selected track)

**Implementation Files**:
- `nx-audio-workflow/ai_context.py` (extend)
- `local_llm/context_builder.py` (new)

---

### STORY-4.3: Model Selection
**Priority**: P2  
**Estimate**: 1 day

**Description**: Fast/smart model switching

**Acceptance Criteria**:
- [ ] qwen2.5-0.5b for simple commands
- [ ] qwen2.5-coder-7b for complex tasks
- [ ] Auto-selection based on complexity
- [ ] Cloud fallback if local fails

**Implementation Files**:
- `local_llm/model_selector.py` (new)

---

# EPIC-5: Predictive Workflows

## Epic Goal
Use learning engine to predict next actions

## Stories

### STORY-5.1: Action Prediction Engine
**Priority**: P2  
**Estimate**: 3 days

**Description**: Implement prediction based on patterns

**Acceptance Criteria**:
- [ ] Track usage patterns learned
- [ ] Plugin sequences predicted
- [ ] Arrangement flow suggestions
- [ ] Confidence scoring

**Implementation Files**:
- `packages/learning_engine/audio_predictor.py` (new)
- `nx-audio-workflow/ai_context.py` (modify)

---

### STORY-5.2: Proactive Suggestions
**Priority**: P2  
**Estimate**: 2 days

**Description**: Surface predictions to user

**Acceptance Criteria**:
- [ ] Toast/notification of predictions
- [ ] Quick-accept buttons
- [ ] "Predict next" manual trigger
- [ ] Learning from acceptance/rejection

**Implementation Files**:
- `nx-audio-workflow/suggestion_ui.py` (new)

---

# EPIC-6: Neural Audio Integration

## Epic Goal
Integrate ONNX models and AI plugins for on-device sound generation

## Stories

### STORY-6.1: ONNX Model Loader
**Priority**: P2  
**Estimate**: 3 days

**Description**: Load neural models in Bitwig extension

**Acceptance Criteria**:
- [ ] ONNX runtime integration
- [ ] Model pre-loading for low latency
- [ ] MACE/Neutone/Scyclone model support
- [ ] Real-time inference

**Implementation Files**:
- `nx-audio-plugin/ONNXModelLoader.java` (extend)

---

### STORY-6.2: VST3 AI Plugin Integration
**Priority**: P2  
**Estimate**: 2 days

**Description**: Discover and control AI VST3 plugins

**Acceptance Criteria**:
- [ ] VST3 scanning for AI plugins
- [ ] Device chain insertion
- [ ] Parameter control via MCP
- [ ] Preset browsing

**Implementation Files**:
- `nx-audio-bridge/vst3_discovery.py` (new)

---

### STORY-6.3: MIDI-Triggered Generation
**Priority**: P3  
**Estimate**: 3 days

**Description**: AI generation triggered by clip launch

**Acceptance Criteria**:
- [ ] Clip MIDI note triggers generation
- [ ] Audio generated in real-time
- [ ] Seamless integration with Bitwig
- [ ] Latency <100ms target

**Implementation Files**:
- `nx-audio-plugin/NXymeAudioExtension.java` (modify)

---

# Requirements Coverage Map

| FR | EPIC-1 | EPIC-2 | EPIC-3 | EPIC-4 | EPIC-5 | EPIC-6 |
|----|--------|--------|--------|--------|--------|--------|
| FR1 | ● | | | | | |
| FR2 | ● | | | | | |
| FR3 | ● | ● | | | | |
| FR4 | | ● | | | | |
| FR5 | | | ● | | | |
| FR6 | | | ● | | | |
| FR7 | | | ● | | | |
| FR8 | | | ● | | | |
| FR9 | | | | ● | | |
| FR10 | | | | ● | | |
| FR11 | | | | ● | | |
| FR12 | | | | | ● | |
| FR13 | | | | | ● | |
| FR14 | | | | | ● | |
| FR15 | | | | | | ● |
| FR16 | | | | | | ● |
| FR17 | | | | | | ● |

---

# Summary

| Epic | Stories | Total Days |
|------|---------|-------------|
| EPIC-1 | 3 | 6 |
| EPIC-2 | 7 | 18 |
| EPIC-3 | 4 | 9 |
| EPIC-4 | 3 | 5 |
| EPIC-5 | 2 | 5 |
| EPIC-6 | 3 | 8 |
| **TOTAL** | **22** | **51** |

**Timeline**: ~4 months (Month 1: EPIC-1+2, Month 2: EPIC-3+4, Month 3: EPIC-5, Month 4: EPIC-6)

---

*Generated: 2026-05-12*  
*Source: docs/ai-daw-integration-plan.md*