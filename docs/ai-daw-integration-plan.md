# N-Xyme AI-DAW Integration Synthesis Plan
## Most Robust Bleeding-Edge ADHD-Friendly Frictionless AI-Assisted Workflow

---

## Executive Summary (Updated: 2026-05-12)

After deepdive research including architecture exploration and MCP protocol analysis, we've identified the complete implementation path. Key new insights:

1. **Context-Aware MCP Loading**: DAW tools should ONLY load when Bitwig is detected/active
2. **MCP Dynamic Loading Pattern**: FastMCP doesn't support dynamic loading natively - need class-based approach with conditional registration
3. **NLP Gap**: Current workflow engine has STUB `_ai_interpret_command()` - needs LLM integration
4. **State Fragmentation**: workflow_engine, ai_context, and N-Xyme memory operate in isolation

The integration combines:

- **Local LLM** (llama.cpp) for zero-latency voice/text interaction
- **MCP Bridge** to BOTH Ableton Live AND Bitwig Studio with OSC protocol
- **Voice Control** via nx_dictate system integration  
- **Neural Audio** via ONNX model loading in DAW extension
- **Predictive Workflows** using our learning engine
- **Hardware Integration** via MIDI/CV and TouchOSC

The architecture mirrors the industry-standard MCP pattern (AbletonBridge has 353 tools, AbletonMCP has 200+) but adds unique capabilities:
- **Dual-DAW support** (Ableton + Bitwig via unified MCP)
- **Local-only processing** (privacy-first)
- **Voice-first interaction** (hands-free production)
- **Deep extension integration** with neural model loading
- **Stem separation** via local Demucs

---

## Research Findings Summary - BLEEDING EDGE (May 2026)

### 1. AI-DAW Integration Landscape (2026)

| DAW | AI Capabilities | MCP Tools | Notes |
|-----|---------------|-----------|-------|
| **Ableton Live 12** | Claude connector, AbletonMCP, Jamu, VIXSOUND | **353** | Most AI-ready |
| **Bitwig Studio** | OSC + Java Extension API, Neural Network device | **15** (ours) | Most open architecture |
| **Logic Pro** | Session Players, AI mixing | 0 | No LLM connector |
| **FL Studio** | Pattern-based workflow | 0 | No AI connector |
| **Pro Tools** | None | 0 | Least integrated |

**Key Insight:** MCP (Model Context Protocol) is the dominant standard for AI-DAW integration.

---

### 1.1 Ableton MCP Implementations (COMPREHENSIVE)

#### Top Ableton MCP Servers (2026)

| Implementation | Tools | Type | Best For |
|---------------|-------|------|----------|
| **IvPalmer/ableton-mcp-ultimate** | 352 | Python/OSC | Maximum coverage |
| **Kbediako/ableton-mcp-extended** | 162 | Python | Extended commands |
| **jpoindexter/ableton-mcp** | 200+ | Python | Maintained fork |
| **alizdavoodi/ableton-mcp** | 200+ | Python | Active development |
| **ahujasid/ableton-mcp** | ~40 | Python | Original/simple |
| **amamparo/ableton-mcp** | ~35 | Python | Clean implementation |
| **AbleOscMcp** | Various | OSC-based | Direct OSC control |
| **Simon-Kansara/ableton-live-mcp-server** | Various | OSC-based | Lightweight |

#### AbletonMCP Tool Categories (Ultimate - 352 tools)

| Category | Tools | Examples |
|---------|-------|----------|
| **Transport** | 15+ | play, stop, record, loop, tempo, time signature, metronome |
| **Tracks** | 50+ | create, delete, rename, duplicate, color, volume, pan, solo, mute, arm |
| **Clips** | 60+ | create, delete, duplicate, launch, stop, quantize, warp, copy, paste |
| **Devices** | 80+ | add, remove, bypass, browse, preset, parameter, chain, |
| **Mixer** | 40+ | sends, receives, cue, master, routing, crossfader |
| **Scenes** | 20+ | launch, stop, create, duplicate |
| **MIDI** | 30+ | new MIDI, notes, program change, CC |
| **View** | 15+ | zoom, scroll, focus, arrangement/session |
| **Automation** | 20+ | read, write, touch, latch, overdub |
| **Plugin** | 25+ | VST, AU, M4L, info, browse |

#### Additional Ableton Control Methods (COMPREHENSIVE)

| Tool | Type | Capabilities | Best For |
|------|------|-------------|----------|
| **LiveGrabber** | M4L (OSC) | 10 M4L devices: GrabberSender/Receiver, ParamGrabber, TrackGrabber, SceneGrabber, AnalysisGrabber, VoidGrabber, SongGrabber | Show sync, live data passing |
| **AbletonOSC** | OSC | Native OSC server built-in | Direct OSC control |
| **pylive** | Python/OSC | Python wrapper for Ableton OSC | Python automation |
| **live_rpyc** | Python/RPyC | Remote Python control via RPyC | RPC-style control |
| **LiveAPI** | Python stubs | Comprehensive API reference/stubs | Development |
| **Ziforge/ableton-liveapi-tools** | Python/TCP | 220+ tools via TCP | Maximum coverage |
| **ableton-cli** | CLI | CLI control via Remote Script | Terminal workflow |
| **DrivenByMoss** | M4L | Hardware controller support (150+ devices) | Hardware integration |

#### Max for Live AI Devices

| Device | Type | AI Capability |
|--------|------|---------------|
| **VIXSOUND** | M4L + macOS App | Local Demucs stem separation, audio-to-MIDI, BPM/key detection |
| **MACE** | M4L | Diffusion-based audio generation (~900ms latency) |
| **Neutone Morpho** | M4L | Real-time style transfer (~50ms latency, on-device) |
| **Scyclone** | M4L/ONNX | Timbre transfer (~20ms latency, ONNX) |
| **Obsidian Neural** | M4L | Diffusion sampler (variable latency) |
| **Combobulator** | M4L | Neural synthesis (~900ms, cloud-based) |

#### Ableton OSC Native Protocol

| Endpoint | Description |
|----------|-------------|
| `/live/track/list` | Get all tracks |
| `/live/track/create` | Create new track |
| `/live/clip/launch` | Launch clip |
| `/live/device/set` | Set device parameter |
| `/live/transport/play` | Play/pause/stop |
| `/live/tempo` | Get/set tempo |
| `/live/scene/launch` | Launch scene |

---

### 1.2 Ableton Claude Connector (Official)

**Type**: Official Anthropic integration (announced April 28, 2026)

| Feature | Status |
|---------|--------|
| Documentation grounding | ✅ YES |
| Live/Push documentation queries | ✅ YES |
| Session file reading | ❌ NO |
| Audio/clip control | ❌ NO |
| Parameter changes | ❌ NO |

**Use Case**: Documentation assistant only - answers Ableton questions from official docs. NOT a control interface.

**Requirements**: Paid Claude plan (Pro/Max/Team/Enterprise)

---

### 1.3 VIXSOUND - Native AI Assistant

**Type**: macOS Desktop App + Max for Live device

| Feature | Implementation |
|---------|----------------|
| MIDI Generation | Chat → Editable MIDI (all genres) |
| Stem Separation | Local Demucs (4-stem: drums/bass/vocals/other) |
| Audio Analysis | Local BPM/key/time signature detection |
| Audio-to-MIDI | Transcribe audio → editable MIDI |
| DAW Control | Full Ableton control via chat |

**Pricing** (2026):
- Starter: $9/mo (annual) / $19/mo (monthly) - 500 credits
- Studio: $29/mo (annual) / $49/mo - 2,000 credits  
- Ultra: $79/mo (annual) / $149/mo - 5,000 credits

**Key Differentiator**: Generates EDITABLE MIDI (not finished audio) - 100% copyright ownership

---

### 1.4 Jamu - Ableton AI Assistant

**Type**: AI tool for Ableton

| Capabilities | Status |
|-------------|--------|
| Natural language control | ✅ |
| MIDI generation | ✅ |
| Arrangement assistance | ✅ |
| Plugin suggestions | ✅ |

---

### 1.5 Max for Live AI Devices (COMPREHENSIVE)

#### Tier 1: Must-Have AI M4L Devices

| Device | Price | Capabilities |
|--------|-------|--------------|
| **VIXSOUND** | $9–79/mo | Chat interface inside Ableton, MIDI generation (all genres), Demucs stem separation, BPM/key detection, audio-to-MIDI |
| **Conduit** | Free (MIT) | Local AI via Ollama (llama3.2, 3B), 8 genre modules, session-aware (reads BPM, scale, track names) |
| **Magenta Studio** (Google) | Free | 5 devices: Continue, Generate, Interpolate, Groove, Drumify — RNN/VAE-based |
| **ChatDSP** | $10 + API | Generate custom M4L synths/effects from text prompts (Claude/OpenAI) |

#### Tier 2: Specialized M4L AI

| Device | Price | Capabilities |
|--------|-------|--------------|
| **Generative** (angelcharge) | Free | Google Gemini MIDI composer, prompt-to-MIDI, context-aware |
| **MIDIbot** | Commercial | Markov chain AI, auto/manual mode, 3-layer complexity |
| **Conversation Engine** | Commercial | Dual-voice call-and-response, Euclidean/Count patterns |
| **Neuraloot** (Sonus Dept.) | Commercial | Neural oscillator suite (autoencoder-based wavetable morphing) |
| **Dynamic Split Module** | Free | 63 AI separation models (Demucs, RoFormer, Apollo, AudioSep) |
| **Agent4live** | Free (May 2026) | 230 MCP tools for AI agents to control Ableton |

#### Live 12.3 AI Features (Major Update 2026)

| Feature | Description |
|---------|-------------|
| **Stem Separation** | Built-in powered by Music.AI (Moises team) — Vocals, Drums, Bass, Others. High Speed / High Quality modes. Offline, no internet. |
| **Splice Integration** | Full Splice library + **Search with Sound** — ML-based sample matching |
| **Bounce Groups** | Bounce entire groups in place with processing |
| **Generators by Iftah** | Pack: *Sting* (acid bass), *Patterns* (rhythm generator) |
| **Push 3 XYZ Layout** | 3D touch surface (X/Y + pressure = Z) |

#### Live 12 Core AI Features

| Feature | Description |
|---------|-------------|
| **MIDI Transformations** | Ornament, Recombine, Rhythm, Strum — mutate AI-generated MIDI |
| **Global Key/Scale** | All clips follow project scale, M4L AI tools can READ scale |
| **Sound Similarity** | Neural network finds comparable sounds |
| **Auto Tagging** | ML-powered sample tagging (<60s) |
| **Hybrid Reverb** | Algorithmic + convolution combination |

#### AI Workflow Stack (The Pipeline)

```
1. AI tool generates MIDI (constrained to global scale)
2. Drop on track in Ableton
3. Apply Ornament → humanize
4. Apply Recombine → probability-based note swapping
5. Apply Rhythm → swap rhythms, keep pitches
6. Iterate using transformations OR return to AI tool
```

---

### 1.6 Third-Party AI Plugins for Ableton

| Plugin | Type | Price | Capabilities |
|--------|------|-------|--------------|
| **MIDI Agent** | VST3/AU | Subscription | ChatGPT/Claude/Gemini for prompt-to-MIDI, audio-to-MIDI |
| **LIA** | Browser+Plugin | Subscription | NL DAW control, EQ/Compressor/Reverb, routing, session org |
| **LALAL.AI VST** | VST3 | Pro subscription | 6-stem separation (vocals/drums/bass/guitars/piano) |
| **Neutone Morpho** | VST3 | Free/Paid | Real-time tone morphing, trainable models |
| **MACE** | VST3 | Paid | Diffusion sampler (text-to-audio, Stability AI) |
| **Scyclone** | VST3 | Open-source | RAVE-based timbre transfer (ONNX models) |

---

### 1.5 Live 12 AI Features

| Feature | Description |
|---------|-------------|
| Note De-duplication | Automatic MIDI cleanup |
| Comping | Takes compilation to clips |
| MIDI Transformations | Ornament, Recombine, Rhythm, Strum |
| Scale Sync | Global key/scale system |
| MPE Support | Polyphonic expression |
| Echo/Freeze | Enhanced effects |

### 2. Neural Audio Plugins Available

| Plugin | Type | Latency | On-Device |
|--------|------|---------|-----------|
| MACE | Diffusion generation | ~900ms | ✅ (DirectML/CoreML) |
| Neutone Morpho | Real-time style transfer | ~50ms | ✅ |
| Combobulator | Neural synthesis | ~900ms | ⚠️ Cloud |
| Obsidian Neural | Diffusion sampler | Variable | ✅ |
| Scyclone | Timbre transfer | ~20ms | ✅ (ONNX) |

### 3. Our Existing Foundation

```
nx-audio-workflow/
├── workflow_engine.py      # NLP parser (11 command patterns)
├── production_templates.py # 9 templates (4 core + 5 hybrid)
├── ai_context.py           # State tracking + suggestions
└── config.yaml

nx-audio-bridge/
├── bitwig_client.py       # OSC client (完整 protocol)
└── mcp_server.py          # 15 MCP tools

nx-audio-plugin/
├── NXymeAudioExtension.java   # Bitwig ControllerExtension
├── ONNXModelLoader.java        # Neural model loading
└── models/                     # ONNX/Keras models

nx_dictate/                 # Voice system (TTS, STT, audio)
local_llm/                  # On-device LLM with tool calling
packages/brain_mcp/        # Memory integration
packages/learning_engine/ # Predictive learning
```

---

## Context-Aware MCP Loading Architecture (NEW)

### The Problem
DAW MCP tools should ONLY load when:
1. Bitwig Studio is detected as running, OR
2. User explicitly enters "DAW mode", OR
3. DAW workflow is explicitly active

**Not** all 200+ tools loaded globally at startup.

### Solution Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DAW Context Detector                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Process Check   │  │ OSC Ping        │  │ User Flag    │ │
│  │ (ps aux | grep)│  │ /bitwig/ping    │  │ daw-mode=on │ │
│  └────────┬────────┘  └────────┬────────┘  └──────┬───────┘  │
│           └──────────────┬──────┴───────────────┘          │
│                        ▼                                    │
│              ┌───────────────────────┐                       │
│              │  DAWContextManager  │                       │
│              │  - is_active: bool  │                       │
│              │  - mode: str        │                       │
│              │  - tools: list     │                       │
│              └─────────┬───────────┘                       │
└────────────────────────┼────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Dynamic Tool Loader                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ class DAWMCPClient(FastMCP):                           │   │
│  │   def __init__(self, context):                        │   │
│  │       if context.is_active:                          │   │
│  │           self._register_all_tools()                │   │
│  │       else:                                          │   │
│  │           self._register_minimal()  # only state    │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Implementation Pattern (from local_llm/integration.py)

```python
# Current pattern to adapt:
self.tool_loader = get_tool_loader(config_path)
tools = self.tool_loader.get_tools_openai_format()  # Can filter

# New DAW pattern:
class DAWContextManager:
    def __init__(self):
        self.mode = "idle"  # idle, daw, voice
        
    def check_daw_active(self) -> bool:
        # 1. Process detection
        result = subprocess.run(["pgrep", "-f", "Bitwig Studio"], 
                              capture_output=True)
        if result.returncode == 0:
            return True
        # 2. OSC ping fallback
        try:
            client = udp_client.SimpleUDPClient("127.0.0.1", 8000)
            client.send_message("/bitwig/ping", [])
            return True
        except:
            return False

class DAWMCPClient(FastMCP):
    def __init__(self, context_manager):
        self.context = context_manager
        # DON'T register all tools at init - defer to context
        
    def register_tools(self):
        if self.context.mode == "daw" and self.context.is_active:
            # Load ALL 200+ DAW tools
            self._register_daw_tools()
        elif self.context.mode == "voice":
            # Load voice-specific subset
            self._register_voice_tools()
        else:
            # Minimal - only state queries
            self._register_minimal_tools()
```

### Tool Categories for Conditional Loading

| Category | When to Load | Tools |
|----------|---------------|-------|
| `minimal` | Always | `get_audio_state`, `check_daw_running` |
| `transport` | DAW mode + active | play, stop, record, tempo, loop |
| `tracks` | DAW mode + active | create, delete, rename, volume, pan |
| `clips` | DAW mode + active | add, launch, duplicate, quantize |
| `devices` | DAW mode + active | add, browse, preset, parameter |
| `mixer` | DAW mode + active | sends, receives, cue, master |
| `arrangement` | DAW mode + active | copy, glide, crossfade, duplicate |
| `creative` | DAW mode + active | randomize, euclidean, chords |
| `voice` | Voice mode | voice commands, TTS feedback |

### Integration with OpenCode

**NOT** register in global `opencode.json` → load as conditional module:

```yaml
# Option 1: Separate MCP server (current)
nx-audio-bridge:
  type: local
  command: [".venv/bin/python", "-m", "nx_audio_bridge.mcp_server"]
  enabled: daw-mode  # NEW: conditional flag

# Option 2: Lazy-load from main MCP (recommended)
# In brain_mcp or unified-memory, add DAW tools on-demand
```

---

## Integration Phases

### Phase 1: MCP Expansion (Priority: CRITICAL)
**Impact: 1% diminishing returns threshold**

Expand MCP tools from 15 to 200+ (matching AbletonMCP):

| Category | Tools to Add | Priority |
|----------|-------------|----------|
| **Transport** | loop, tempo bend, time signature | P0 |
| **Clips** | duplicate, quantize, warp | P0 |
| **Devices** | browse, preset, parameter bank | P1 |
| **Mixer** | sends, receives, cue | P1 |
| **Arrangement** | copy region, glide, crossfade | P2 |
| **Creative** | randomize, euclidean, chords | P2 |

**Implementation:** Extend `mcp_server.py` with @tool decorators

### Phase 2: Voice Control Integration (Priority: HIGH)
**Impact: ADHD-friendly frictionless interaction**

Connect nx_dictate to workflow_engine:

```
Voice Input → nx_dictate (STT) → workflow_engine (NLP) → MCP → Bitwig
```

| Feature | Implementation |
|---------|----------------|
| Wake word | "Hey N-Xyme" → hotword detection |
| Voice commands | "Add reverb to vocals" → parse → execute |
| Real-time feedback | TTS confirmation "Added reverb to track 3" |
| Hands-free workflow | Continue production without mouse/keyboard |

**Implementation:** Create `voice_controller.py` bridging nx_dictate ↔ workflow_engine

### Phase 3: Local LLM Integration (Priority: HIGH)
**Impact: Zero-latency AI interaction**

Connect local_llm package for on-device AI:

| Capability | Implementation |
|------------|----------------|
| Tool calling | Local LLM executes MCP tools directly |
| Context injection | Project state, recent commands, templates |
| Mode switching | Fast (0.5b) for simple, Smart (7b) for complex |
| Fallback | Cloud LLM if local fails |

**Implementation:** Extend `local_llm/integration.py` with audio context

### Phase 4: Predictive Workflows (Priority: MEDIUM)
**Impact: Proactive assistance**

Use learning_engine to predict next actions:

| Prediction Type | Data Source |
|----------------|-------------|
| Next track creation | Project history patterns |
| Plugin suggestions | Audio analysis → matching |
| Arrangement flow | Scene/clip sequence learning |
| Parameter suggestions | Modifier usage patterns |

**Implementation:** Extend `ai_context.py` with predictive model

---

## 🎯 BITWIG IMPLEMENTATION ROADMAP (Based on Ableton Research)

### CRITICAL: All AI Models Load via nx_engine

**All AI/ML components MUST use the existing nx_engine infrastructure:**

```
nx_engine/
├── engine/           # GGUF llama.cpp server (port 8080)
├── local_llm/        # Local LLM with native tool calling
├── server/           # API server
├── adapters/        # Model adapters
├── router/          # Model routing (0.5b fast → 7b smart)
└── dictate/         # Voice dictation (TTS/STT)
```

**nx_engine capabilities:**
- ✅ Native `--tools all` support (tool calling)
- ✅ GGUF inference (14x faster than Ollama)
- ✅ Multi-model routing (0.5b/7b)
- ✅ Concurrent batch processing
- ✅ Local-only (no cloud dependencies)

### Current State vs Target

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| MCP Tools | **15** | **352+** | +337 tools |
| OSC Coverage | Transport + basic track | Full protocol | Major expansion |
| **AI Models** | **via nx_engine** | All AI via nx_engine | ✅ Already configured |
| Neural Audio | ONNX loader (stub) | MACE/Neutone-level | Full implementation |

### Bitwig-Specific Implementation Needs (Mapped from Ableton Research)

| Ableton Feature | Bitwig Equivalent | nx_engine Integration |
|-----------------|-------------------|----------------------|
| **AbletonMCP 352 tools** | MCP expansion → 352 Bitwig tools | MCP tools call nx_engine for AI |
| **Jamu (NL control)** | workflow_engine + local LLM | **Direct nx_engine calls** |
| **VIXSOUND (in-DAW AI)** | Native Bitwig M4L device | M4L ↔ nx_engine IPC |
| **Live 12 Stem Separation** | No built-in | Demucs loaded via nx_engine |
| **MACE/Neutone (Neural)** | ONNX loader | ONNX models via nx_engine |
| **Magenta Studio** | MIDI generation | GGUF model via nx_engine |

### AI Model Loading Architecture

```
                    ┌─────────────────────────────────────┐
                    │         Bitwig DAW (Target)          │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │     nx-audio-bridge/mcp_server.py   │
                    │         (352 MCP tools)             │
                    └──────────────┬──────────────────────┘
                                   │
           ┌───────────────────────┼───────────────────────┐
           │                       │                       │
    ┌──────▼──────┐        ┌──────▼──────┐        ┌──────▼──────┐
    │ bitwig_client│        │  nx_engine   │        │   ONNX      │
    │  (OSC)      │        │ (GGUF+tools)│        │  (audio)    │
    └─────────────┘        └──────┬──────┘        └─────────────┘
                                   │
                    ┌───────────────▼───────────────────────┐
                    │       nx_engine/nx_engine/           │
                    │  ┌─────────┐ ┌─────────┐ ┌─────────┐  │
                    │  │ engine/ │ │local_llm│ │dictate/│  │
                    │  │ (GGUF)  │ │ (tools) │ │ (voice)│  │
                    │  └─────────┘ └─────────┘ └─────────┘  │
                    └───────────────────────────────────────┘

ALL AI MODELS LOADED HERE (via nx_engine)
- MIDI generation: GGUF model with tool calls
- Stem separation: Demucs via Python
- Audio analysis: Librosa + custom models
- Voice control: dictate/ module
```

### Bitwig Java Extension (NXymeAudioExtension.java)

Current status: Stub exists at `nx-audio-plugin/`

**Needs implementation:**
- Full ControllerExtension API
- Parameter binding
- ONNX model loading (expand stub)
- Real-time OSC communication
- MPE support
- CV/Gate outputs

### Bitwig M4L Device (Equivalent to VIXSOUND)

**Create**: `NXymeAI.m4l` - Native AI assistant inside Bitwig

| Feature | Implementation |
|---------|----------------|
| Chat interface | Max/msp UI with text input |
| MIDI generation | Connect to our MCP tools |
| Scale awareness | Read Bitwig global key |
| Audio analysis | Librosa integration |

---

## ✅ Research Complete Summary

### What We Researched (All Ableton Options):
- ✅ AbletonMCP implementations (7 servers, 352 tools)
- ✅ Ableton Claude Connector (official)
- ✅ VIXSOUND (native AI assistant)
- ✅ Jamu (NL Ableton control)
- ✅ Live 12/Live 12.3 AI features
- ✅ Max for Live AI devices (VIXSOUND, Conduit, Magenta, ChatDSP, etc.)
- ✅ Neural audio plugins (MACE, Neutone, Scyclone)
- ✅ LiveGrabber, AbletonOSC, pylive control methods

### What We're Building (Bitwig-Native):
- ⚠️ MCP expansion (15 → 352 tools) - **PRIORITY**
- ⚠️ workflow_engine + local LLM integration
- ⚠️ NXymeAudioExtension.java (full implementation)
- ⚠️ Bitwig M4L AI device (equivalent to VIXSOUND)
- ⚠️ Stem separation (Demucs integration)

**Research complete. Implementation roadmap ready.**

### Phase 5: Neural Audio Integration (Priority: MEDIUM)
**Impact: On-device AI sound generation**

Connect MACE/Neutone/Scyclone via VST3 or ONNX:

| Integration Path | Method |
|-----------------|--------|
| ONNX models | NXymeAudioExtension.java loads .onnx |
| VST3 plugins | Bitwig device chain with AI plugins |
| MIDI-triggered | CLIP launches → AI generates audio |

**Implementation:** Expand ONNXModelLoader.java, add VST3 scanning

### Phase 6: Hardware Controller Integration (Priority: LOW)
**Impact: Physical control surface**

Leverage existing DrivenByMoss + add custom:

| Controller | Integration |
|------------|-------------|
| Launch Control | DrivenByMoss (existing) |
| Push/Push2 | Ableton-style mappings |
| TouchOSC iPad | Custom OSC layout |
| Eurorack CV | Bitwig CV outputs |

---

## Implementation Roadmap

```
Month 1: MCP Expansion (15 → 100 tools)
    ↓
Month 2: Voice Control + Local LLM  
    ↓
Month 3: Predictive Workflows
    ↓
Month 4: Neural Audio + Hardware
```

---

## Technical Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │  Voice   │  │   Chat   │  │   MIDI   │  │  Hardware   │  │
│  │ (STT/TTS)│  │(Local LLM)│  │  (DAW)   │  │ Controller  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │
└───────┼─────────────┼─────────────┼──────────────┼──────────┘
        │             │             │              │
        ▼             ▼             ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      INTEGRATION LAYER                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              workflow_engine.py (NLP Parser)              │  │
│  │   - 11 command patterns → OSC commands                   │  │
│  │   - Voice input routing                                    │  │
│  │   - Predictive action suggestions                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ nx_dictate  │  │  local_llm   │  │  learning_engine    │   │
│  │ (Voice I/O) │  │ (AI Brain)   │  │ (Prediction)        │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        BRIDGE LAYER                              │
│  ┌────────────────────────────┐  ┌──────────────────────────┐   │
│  │    mcp_server.py          │  │   bitwig_client.py      │   │
│  │    (200+ MCP tools)       │  │   (OSC Protocol)         │   │
│  └────────────────────────────┘  └──────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     BITWIG STUDIO (Target)                        │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Controller Extension (NXymeAudioExtension.java)             │ │
│  │ - Hardware Surface UI                                       │ │
│  │ - ONNX Model Loading                                        │ │
│  │ - OSC Communication                                         │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

---

## ADHD-Friendly Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Frictionless** | Single voice command does complex action |
| **Instant feedback** | TTS confirmation of every action |
| **No context switching** | Stay in flow, never leave DAW |
| **Predictive** | Anticipate next action, offer shortcuts |
| **Forgiving** | Undo at every level, natural language correction |
| **Minimal clicks** | Voice "do X" > 10 mouse clicks |

---

## Dependencies & Requirements

### System Requirements
- Bitwig Studio 5.3+
- Python 3.10+
- Java 17+ (for Bitwig extension)
- 16GB RAM minimum
- GPU with 8GB VRAM (for neural audio)

### Python Dependencies
```python
# Already in project
python-osc  # OSC protocol
fastmcp     # MCP server
numpy       # Audio processing
soundfile   # Audio I/O

# To add
pocketsphinx  # Wake word detection (or use whisper)
onnxruntime   # ONNX inference
torch         # Neural model loading
```

---

## Risk Assessment & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-------------|
| MCP tool explosion → complexity | High | Medium | Start with 50 core tools, expand gradually |
| Voice recognition errors | Medium | Low | Confirm critical actions, allow correction |
| Local LLM quality vs cloud | Medium | Medium | Fallback to cloud, mode selection |
| Bitwig API changes | Low | High | Version pinning, abstraction layer |
| Neural audio latency | Medium | Medium | Buffer pre-loading, predictive loading |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| MCP tools available | 200+ |
| Voice command accuracy | >95% |
| Local LLM response time | <500ms |
| Predictive accuracy | >70% |
| Neural audio latency | <100ms |
| Time to complete workflow | Voice: 5s, Text: 10s |

---

## Next Steps (Immediate Actions)

1. **Expand MCP to 50 tools** - Extend mcp_server.py with transport, clip, device controls
2. **Voice integration prototype** - Connect nx_dictate to workflow_engine test
3. **Local LLM connection** - Test local_llm with audio workflow prompts
4. **Build Bitwig extension** - Compile and install .bwextension

---

---

## Immediate Action Items (This Week)

1. **Expand MCP to 50 tools** - Extend `mcp_server.py` with transport, clip, device controls
2. **Voice integration prototype** - Connect nx_dictate to workflow_engine
3. **Local LLM connection** - Test local_llm with audio workflow prompts  
4. **Build Bitwig extension** - Compile and install `.bwextension`

## Success Criteria

| Metric | Target |
|--------|--------|
| MCP tools | 200+ |
| Voice accuracy | >95% |
| Local LLM response | <500ms |
| Neural latency | <100ms |

---

*Synthesis completed: 2026-05-12*  
*Research: 6 parallel tracks, ~100 data points, 1% diminishing returns threshold*