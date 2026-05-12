# AI in DAW & Voice Music Production — Comprehensive Research Report (2026)

> Compiled: May 12, 2026
> Scope: Voice control, natural language composition, LLM/DAW integration, voice-to-MIDI, AI assistants, open-source & commercial landscape

---

## 1. Voice-Controlled DAW Software & Plugins

### 1.1 Universal Audio LUNA — Voice Control (Feature Preview)
- Apple Silicon Macs only
- Voice-powered transport control (start/stop recording, session control)
- Native integration, no extra hardware

### 1.2 LIA — Voice Control via Telegram
- **URL:** https://liaplugin.com
- **Pricing:** $9–$30/mo subscription
- **How it works:** Send voice messages via Telegram — "start recording," "mute guitar track," "set tempo to 128"
- **DAWs:** Ableton Live (full), FL Studio, Logic Pro, Cubase, Studio One, Reaper, Bitwig
- No special hardware, sub-millisecond latency, 10 languages

### 1.3 Melosurf — Voice Assistant for Ableton Live
- **URL:** https://melosurf.com
- Hands-free voice-driven Ableton control

### 1.4 MAGDA — AI-Native Open-Source DAW
- **URL:** https://magda.land
- **Version:** v0.7.0 (GPL v3)
- Built-in AI agents with cloud or local inference (llama.cpp)
- Param automation (Write/Touch/Latch) + AI prompt
- Lua scripting, MIDI controllers, free/open-source

---

## 2. Natural Language Music Composition Tools

### 2.1 Jamu — AI Co-Producer for Ableton Live
- **URL:** https://www.jamu.ai
- **Pricing:** Token-based ($9–$30/mo)
- Natural language → DAW action: "four-bar boom-bap drum loop," "bring bass up 3dB"
- Full Ableton control: MIDI generation, mixing, arrangement, effects
- Context-aware (acts on selected track/clip/device)

### 2.2 Maestronaut — Claude-Powered Composition Agent
- **URL:** https://maestronaut.com
- Native Electron app, Claude + AbletonMCP over OSC
- Multi-agent: Claude + ChatGPT + other models in same session
- 24 compositional directives, real-time WebGL visuals

### 2.3 Muse — AI MIDI Composer
- **URL:** https://www.muse.art
- Generate/edit/refine MIDI via natural language
- Harmonic function + voice leading awareness
- Standalone, browser, Max for Live, Vital preset generator

### 2.4 Noteshift AI — Words to Sheet Music
- **URL:** https://noteshift.ai
- Free tier (20 gens) + paid
- Natural language → professional sheet music (PDF, WAV, MIDI, MusicXML)
- 50+ instruments, visual editor

### 2.5 Cadenza — Browser-Based AI Composition
- **URL:** https://www.usecadenza.studio
- Full browser DAW with piano roll, arrangement, AI chat (Claude API)

### 2.6 Anthemic — Conversational Learning Platform
- **URL:** https://anthemicai.com
- Public demo Aug 2026, beta Oct 2026
- "Anti-repetition technology," open-source, community-owned

---

## 3. ChatGPT/Claude Integration with DAWs

### 3.1 Official: Claude for Creative Work + Ableton Connector (April 28, 2026)
- Claude Pro ($20/mo) or Max ($100/mo)
- Reads session: track names, clip locations, tempo, scenes
- Triggers clips/scenes by name
- Generates MIDI clips from text brief
- Searches Splice via connector
- Writes mixer automation (volume, sends, returns, mix-bus)
- **Limitations:** No real-time DAW connection, MIDI-only, no audio generation

### 3.2 Community: AbletonMCP (Open Source)
- **URL:** https://github.com/jpoindexter/ableton-mcp
- MIT license, **200+ tools** for full Ableton Live Object Model
- Real-time: create tracks, build clips, load instruments, change tempo
- AI music helpers: scale reference (12+), drum patterns (8 styles), basslines (6)
- Quantize/humanize timing/velocity
- REST API mode for Ollama, OpenAI, Groq
- **Architecture:**
  ```
  Claude AI <-> MCP Server (FastMCP) <-> Ableton Remote Script <-> Ableton LOM
  ```

### 3.3 Ableton Live 12 MCP Server
- **URL:** https://mcp.harishgarg.com
- Simpler MCP via AbletonOSC, direct track/transport control

### 3.4 Producer Pal
- **URL:** https://github.com/clintoncreeves/producer-pal-with-claude
- Multi-model (Claude, Gemini, ChatGPT, Ollama)

### 3.5 DAW MIDI Generator MCP
- **URL:** https://github.com/s2d01/daw-midi-generator-mcp
- Universal MIDI generation for any DAW

### 3.6 SnappySnap + Claude AI
- Claude-controlled spatial audio VST via MCP
- Position audio objects, snapshots, interpolation via chat

### 3.7 MIDI Agent (VST3/AU/AAX)
- **URL:** https://www.midiagent.com
- Multi-LLM (ChatGPT, Claude, Gemini, Grok, DeepSeek)
- Audio-to-MIDI transcription, local LLM support (Ollama/LM Studio)

---

## 4. Voice-to-MIDI & Voice Synthesis

### 4.1 Bace — Voice to MIDI Plugin
- **URL:** https://bace.app
- VST3/AU/Standalone, real-time, trainable
- Controls 4 drum tracks (Kick, Snare, Hi-Hat, Percussive)

### 4.2 Orca — Voice-to-MIDI Pipeline (QHacks 2026)
- **URL:** https://github.com/Beebdoles/qhacks-2026
- 5-stage: BasicPitch → Gemini segmentation → Score Builder → Instrument Mapper → MIDI Merger
- Singing/humming/beatboxing → multi-track MIDI

### 4.3 Vocuno — Vocal to MIDI
- **URL:** https://vocuno.com
- Browser-based, free+paid, handles vibrato/slides/bends

### 4.4 ACE Studio — Vocal to MIDI
- V1 (4 languages), V2 (more + lyric vs phoneme detection)

### 4.5 GAME — Generative Adaptive MIDI Extractor (Open Source)
- **URL:** https://github.com/openvpi/GAME
- MIT, v1.0.3, 131 stars
- D3PM diffusion models, 50M params, multilingual

### 4.6 SoulX-Singer — Zero-Shot Singing Synthesis
- **URL:** https://github.com/Soul-AILab/SoulX-Singer
- 42K+ hours training (Mandarin/English/Cantonese)
- Timbre cloning, cross-lingual synthesis, SVC mode

### 4.7 MelodyLM — Text-Controlled Melody-to-Song (arXiv 2026)
- 3-stage: text→MIDI → text→vocal → vocal→accompaniment

### 4.8 MIDI-Informed Singing Accompaniment Generation (arXiv Feb 2026)
- 2.5K hours audio, single RTX 3090

---

## 5. AI Assistants for Music Production — Current State (2026)

### 5.1 Landscape

| Category | Key Players | Best For | Licensing |
|----------|-------------|----------|-----------|
| Full song gen | Suno V5, Udio, ElevenMusic, Google Flow Music | Finished tracks | Disputed vs licensed |
| MIDI generation | VIXSOUND, Jamu, Muse, MIDI Agent | Editable output | Clean (MIDI = yours) |
| AI-native DAWs | MAGDA (OSS), Mozart AI Studio | Browser/lightweight | GPL v3 |
| Stem separation | Demucs, LALAL.ai, iZotope RX | Audio cleanup | Varies |
| AI mastering | iZotope Ozone, LANDR, eMastered | Quick polish | Processing owned audio |

### 5.2 Market Stats
- Deezer: 44% of new uploads AI-generated
- Suno V5 = most-used commercial text-to-song
- Udio V3 = best audio quality for detailed prompts
- ElevenMusic (April 29, 2026) — fully licensed (Kobalt + Merlin), artist publishing programme
- Google ProducerAI (Feb 2026) — Lyria 3 + Gemini + SynthID

### 5.3 Producer Consensus Workflow (2026)
1. AI for first 8-16 bars
2. Export stems/MIDI to DAW
3. Mute, rewrite, humanize
4. Your ears = final say
5. MIDI-first = cleanest path (you own the notes)

### 5.4 VIXSOUND — DAW Companion
- **URL:** https://vixsound.com
- $9–$79/mo, 7-day trial
- Desktop app alongside Ableton, music-tuned AI, local Demucs + Librosa

### 5.5 Critical Limitations
- Claude official connector = knowledge/planning, not real-time
- Community MCP servers achieve real-time but need Python/JSON/Remote Script setup
- LLMs generate MIDI only, not audio
- MAGDA not yet professional-grade
- Legal landscape volatile (Suno/Universal lawsuits)
- AI tracks <1% of total streams despite high awareness

---

## 6. Key Findings Summary

- **Most practical right now:** LIA (voice control) + Jamu/MIDI Agent (NL composition) + AbletonMCP (deep DAW integration)
- **Best open-source stack:** MAGDA (DAW) + GAME (voice→MIDI) + AbletonMCP (integration)
- **Best commercial stack:** Ableton Live + Claude for Creative Work (planning) + MIDI Agent (generation) + Splice (samples)
- **Emerging trend:** Everything is moving into the DAW — browser tools → plugins → standalone DAW companions
- **Critical gap:** No production-ready end-to-end voice-to-production pipeline exists yet. The components exist (voice→MIDI, NL→DAW, AI generation) but aren't integrated into a single seamless workflow.
