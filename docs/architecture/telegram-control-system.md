# N-Xyme Telegram Control System Architecture

## Executive Summary

This architecture addresses the challenge of controlling a personal automation system through Telegram with zero friction—critical for ADHD users who need instant idea capture and minimal interaction overhead. The system leverages voice-first interaction, context-aware UI, and proactive automation to create a seamless bridge between thought and action.

**Core Design Principle**: Every action must be achievable in 2 taps maximum, with voice as the primary input for complex operations.

---

## 1. Unified Command Hierarchy

### The 2-Tap Maximum Rule

With 50+ actions, we cannot use flat menus. We need a **hierarchical radial layout** inspired by launcher apps like Alfred:

```
Level 0: Main Menu (8 buttons, 1 tap)
Level 1: Category Menu (8 buttons, 1 tap from main)  
Level 2: Action (direct execution or confirmation)
```

### Category Structure (8 Primary Buckets)

| Button | Category | Example Actions |
|--------|----------|-----------------|
| 🎵 **Music** | Record, mix, export, upload | 12 actions |
| 🎬 **Video** | Render, trim, upload | 10 actions |
| 💻 **Code** | Git ops, deploy, test | 15 actions |
| 🧠 **Capture** | Note, voice note, idea | 8 actions |
| 📅 **Schedule** | Meeting, reminder, block time | 6 actions |
| 🤖 **AI** | Chat, summarize, generate | 7 actions |
| 🔔 **Alerts** | System, health, notifications | 6 actions |
| ⚙️ **System** | Settings, context switch | 8 actions |

### Smart Default Actions

The main menu adapts based on **time of day** and **recent activity**:

- **Morning (6-9am)**: Music → Record, Video → Edit recent, Schedule → Today's plan
- **Work hours (9-6pm)**: Code → Git, AI → Review, System → Deploy
- **Evening (6-10pm)**: Music → Finish track, Video → Export, Capture → Voice note
- **Late night (10pm+)**: Capture → Dream idea, Schedule → Tomorrow's priorities

### Context Modes

Four persistent context modes that alter button layouts:

1. **Music Mode**: Production-focused buttons (record, mix, stems, export Spotify)
2. **Video Mode**: Editing-focused buttons (render, color grade, upload YouTube)  
3. **Coding Mode**: Git/terminal-focused (commit, push, test, deploy)
4. **General Mode**: Balanced default layout

**Mode Switching**: Single tap to switch modes, persists until changed.

---

## 2. Voice-First Workflow Engine

### Voice Processing Pipeline

```
User Voice → Whisper API → Intent Classification → Action Dispatcher → Execution
```

### Intent Patterns (Natural Language Understanding)

Define voice triggers as **regex patterns** with named groups:

```python
INTENT_PATTERNS = {
    "record_track": r"(?:record|capture) (?:track|song|beat) (?P<name>.+)",
    "schedule_meeting": r"schedule (?:meeting|call) (?P<title>.+) (?:at|for) (?P<time>.+)",
    "git_commit": r"commit (?P<message>.+)",
    "capture_idea": r"(?:note|idea|remember) (?P<content>.+)",
    "system_alert": r"alert me (?:when|if|about) (?P<trigger>.+)",
}
```

### Multi-Step Automation via Voice

Voice commands can trigger **chained workflows**:

```
"Finish the mix" → [1] Load project → [2] Apply limiter → [3] Export stems → [4] Upload to cloud
```

### Workflow Engine Architecture

```python
class WorkflowEngine:
    async def execute_voice_command(self, transcript: str) -> ExecutionResult:
        intent = await self.classify_intent(transcript)
        params = self.extract_parameters(intent, transcript)
        
        if intent.requires_approval:
            await self.request_confirmation(intent, params)
        
        workflow = self.get_workflow_chain(intent)
        results = []
        
        for step in workflow.steps:
            result = await self.execute_step(step, params, results)
            results.append(result)
            if step.requires_user_input:
                await self.pause_for_input(step)
        
        return self.summarize_results(results)
```

### Confirmation Styles

- **Quick actions** (< 5 seconds): Execute immediately
- **Medium actions** (5-30 seconds): Inline confirmation "Confirm: Export mix?"  
- **Long/risky actions**: Full confirmation with preview

---

## 3. Context-Aware Button Layouts

### Layout System Architecture

```python
@dataclass
class ButtonLayout:
    name: str
    buttons: list[KeyboardButton]  # Max 8
    mode: ContextMode
    time_aware: bool
    
class ContextManager:
    def get_layout(self, user_id: int, context: Context) -> ButtonLayout:
        mode = self.get_current_mode(user_id)
        time_context = self.get_time_context()
        recent_activity = self.get_recent_activity(user_id)
        
        return self.assemble_layout(mode, time_context, recent_activity)
```

### Mode-Specific Layouts

**Music Mode Layout**:
```
[🎹 Record] [🎚️ Mix] [🎚️ Stems] [💾 Save] [📤 Export] [🎧 Preview] [🔄 Undo] [⚙️ More]
```

**Video Mode Layout**:
```
[🎬 Render] [✂️ Trim] [🎨 Color] [📤 Upload] [⏱️ Timeline] [🔄 Undo] [💾 Save] [⚙️ More]
```

**Coding Mode Layout**:
```
[📝 Commit] [⬆️ Push] [⬇️ Pull] [🧪 Test] [🚀 Deploy] [📋 Copy] [🔄 Revert] [⚙️ More]
```

### Dynamic Button Injection

Buttons can be injected based on **state**:

```python
# If project open in DAW → show project-specific actions
# If video project open → show render queue
# If git repo dirty → show uncommitted changes count
```

---

## 4. Proactive Automation

### Alert Engine

```
Event Sources → Condition Evaluator → Alert Generator → Notification Dispatcher
```

### Alert Categories

| Category | Examples | Priority |
|----------|----------|----------|
| **System** | CPU high, disk low, backup failed | Critical |
| **Schedule** | Meeting in 10min, deadline approaching | High |
| **Context** | You usually code at this time, "Want to start?" | Medium |
| **AI Proactive** | "You haven't captured an idea today, want to?" | Low |

### Scheduled Task Engine

```python
class ProactiveScheduler:
    def __init__(self):
        self.jobs: dict[str, ScheduledJob] = {}
        self.triggers: list[TriggerCondition] = []
    
    async def handle_time_trigger(self, job_id: str):
        job = self.jobs[job_id]
        if job.is_due() and job.should_run():
            await self.execute_job(job)
    
    async def handle_context_trigger(self, trigger: TriggerCondition):
        if trigger.evaluate():
            await self.send_contextual_prompt(trigger)
```

### Proactive Behaviors (User-configurable)

- **Idle detection**: "You've been idle for 2 hours. Start a focus session?"
- **Pattern recognition**: "You usually work on music on Saturday mornings"
- **Energy-based suggestions**: Based on time of day and historical productivity
- **Break reminders**: Pomodoro-style but adapted to ADHD flow states

---

## 5. Content Creation Pipeline

### Voice-to-Post Pipeline

```
[Voice Input] → [Whisper Transcription] → [AI Enhancement] → [Platform Formatting] → [Auto-Post]
```

### Pipeline Architecture

```python
class ContentPipeline:
    async def voice_to_post(self, voice_file: VoiceFile, platforms: list[str]) -> PostResult:
        # Step 1: Transcription
        transcript = await self.transcribe(voice_file)
        
        # Step 2: AI Enhancement (if enabled)
        if self.user_preferences.enhance_content:
            enhanced = await self.ai_enhance(transcript, self.user_preferences.style)
        else:
            enhanced = transcript
        
        # Step 3: Platform Formatting
        formatted = {}
        for platform in platforms:
            formatted[platform] = self.format_for_platform(enhanced, platform)
        
        # Step 4: Scheduling or Posting
        if self.user_preferences.auto_post:
            return await self.auto_post(formatted)
        else:
            return await self.request_approval(formatted)
```

### Platform Adapters

Each social platform gets an adapter:

```python
class PlatformAdapter(ABC):
    @abstractmethod
    async def format_post(self, content: Content, platform: str) -> FormattedPost:
        pass
    
    @abstractmethod
    async def post(self, formatted: FormattedPost) -> PostResult:
        pass

# Implementations
class TwitterAdapter(PlatformAdapter)
class InstagramAdapter(PlatformAdapter)
class YouTubeAdapter(PlatformAdapter)
class TikTokAdapter(PlatformAdapter)
```

### Content Templates

Pre-built templates for common post types:

- **Music release**: "🎵 Just dropped [track_name] - [link] #newmusic"
- **Video premiere**: "🎬 New video: [title] - [link] #newvideo"
- **Behind-the-scenes**: "[snippet] - Behind the scenes of [project] 🎬"
- **Work in progress**: "🎧 Working on [project] - feedback welcome!"

---

## 6. Memory/Knowledge Capture

### Capture Types

| Type | Trigger | Storage |
|------|---------|---------|
| **Quick idea** | Voice note | SQLite + vector index |
| **Task** | "Remember to..." | Task database + reminder |
| **Reference** | Any message with #ref tag | Knowledge graph |
| **Project context** | Project-specific notes | Project folder + index |

### Memory Architecture

```python
class MemorySystem:
    async def capture(self, user_id: int, content: CaptureContent) -> Memory:
        # Parse content type
        memory_type = self.classify_memory(content)
        
        # Store in appropriate system
        if memory_type == MemoryType.IDEAL:
            return await self.store_idea(user_id, content)
        elif memory_type == MemoryType.TASK:
            return await self.store_task(user_id, content)
        elif memory_type == MemoryType.REFERENCE:
            return await self.store_reference(user_id, content)
        
        # Index for retrieval
        await self.index_memory(memory)
        
        # Confirm capture to user
        await self.send_capture_confirmation(memory)
    
    async def recall(self, user_id: int, query: str) -> list[Memory]:
        # Semantic search across all memory types
        memories = await self.vector_search(query, user_id)
        return memories
```

### Context Tags

Users can tag captures for organization:

- `#project:name` - Project-specific
- `#music`, `#video`, `#code` - Domain
- `#asap`, `#later`, `#someday` - Priority
- `#ref` - Reference material

---

## 7. Security Model

### Threat Model

The bot runs shell commands—critical to secure:

| Threat | Mitigation |
|--------|------------|
| **Command injection** | Whitelist-only commands, parameterized execution |
| **Privilege escalation** | Dedicated automation user with minimal permissions |
| **Data exfiltration** | No outbound network except defined integrations |
| **Social engineering** | Confirmation for sensitive operations |
| **Accidental destruction** | Soft deletes, trash with TTL, snapshots before destructive ops |

### Command Whitelist System

```python
class SecureCommandExecutor:
    def __init__(self):
        self.command_whitelist = self.load_whitelist()
        self.dangerous_patterns = [
            r"rm -rf",
            r">\s*/dev/sd",
            r"dd if=",
            r"mkfs",
        ]
    
    async def execute(self, user_id: int, command: str) -> CommandResult:
        # Verify whitelist
        if not self.is_whitelisted(command):
            raise SecurityError("Command not in whitelist")
        
        # Check for dangerous patterns
        if self.contains_dangerous_pattern(command):
            await self.request_elevation(command)
        
        # Run as automation user (not root)
        return await self.run_as_user(command, self.automation_user)
```

### Permission Levels

```python
class PermissionLevel(Enum):
    NONE = 0           # Blocked
    READ = 1           # Query status only
    LIMITED = 2        # Safe automation commands
    STANDARD = 3        # Most commands (default)
    ELEVATED = 4       # Requires confirmation
    ADMIN = 5          # Full access (rarely used)
```

### User Verification

- **Primary**: Telegram user ID + bot username verification
- **Optional 2FA**: PIN for elevated commands
- **Session tokens**: Time-limited elevated access

---

## 8. State Management Strategy

### State Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User State Store                         │
├─────────────┬─────────────┬─────────────┬───────────────────┤
│ Preferences │   Context   │   History   │ Active Flows      │
│ - Mode      │ - Project   │ - Commands  │ - Running         │
│ - Notif prefs│ - DAW in use│ - Captures  │ - Paused          │
│ - Templates │ - Git state │ - Sessions  │ - Queued          │
└─────────────┴─────────────┴─────────────┴───────────────────┘
```

### State Persistence

```python
class StateManager:
    def __init__(self):
        self.redis: Redis  # Fast state cache
        self.sqlite: SQLite  # Persistent storage
        
    async def get_user_state(self, user_id: int) -> UserState:
        # Try cache first
        state = await self.redis.get(f"state:{user_id}")
        if state:
            return UserState.parse_raw(state)
        
        # Load from SQLite
        state = await self.sqlite.load_user_state(user_id)
        await self.redis.set(f"state:{user_id}", state, ex=3600)
        
        return state
    
    async def update_state(self, user_id: int, updates: dict):
        state = await self.get_user_state(user_id)
        state.apply_updates(updates)
        
        await self.sqlite.save_user_state(state)
        await self.redis.set(f"state:{user_id}", state, ex=3600)
```

### Context Tracking

Track current context to enable smart defaults:

```python
@dataclass
class UserContext:
    current_mode: ContextMode
    active_project: str | None
    daw_running: str | None
    git_repo_dirty: bool
    last_capture_time: datetime
    daily_activity_summary: dict
    energy_level: int  # 1-10 inferred from patterns
```

---

## 9. Integration Points

### Required Integrations

| Integration | Purpose | Priority |
|-------------|---------|----------|
| **Google Calendar** | Schedule meetings, reminders | P0 |
| **Spotify/Apple Music** | Track metadata, release to distributors | P0 |
| **YouTube API** | Video upload, metadata | P0 |
| **GitHub API** | Repository operations | P0 |
| **OpenAI/Anthropic** | AI assistance | P0 |
| **Notion/Obsidian** | Knowledge base sync | P1 |
| **Discord Webhook** | Cross-platform notifications | P1 |
| **Home Assistant** | Smart home control | P2 |
| **Plex/Jellyfin** | Media server management | P2 |
| **FFmpeg** | Audio/video processing | P0 (local) |

### Integration Architecture

```python
class IntegrationRegistry:
    def __init__(self):
        self.integrations: dict[str, Integration] = {}
    
    def register(self, name: str, integration: Integration):
        self.integrations[name] = integration
    
    async def invoke(self, integration_name: str, action: str, params: dict) -> Any:
        integration = self.integrations.get(integration_name)
        if not integration:
            raise IntegrationError(f"Unknown integration: {integration_name}")
        
        return await integration.execute(action, params)
```

### MCP Tool Integration

Expose bot capabilities via MCP for IDE integration:

```
MCP Server → Bot Command Handler → Execution → Result
```

---

## 10. Extension Architecture

### Plugin System

```python
class Extension(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        pass
    
    @abstractmethod
    def register(self, registry: ExtensionRegistry):
        pass
    
    @abstractmethod
    async def initialize(self, config: dict):
        pass

class ExtensionRegistry:
    def __init__(self):
        self.extensions: dict[str, Extension] = {}
        self.command_handlers: dict[str, CommandHandler] = {}
        self.button_providers: list[ButtonProvider] = []
        self.workflow_steps: list[WorkflowStep] = []
    
    def register_extension(self, ext: Extension):
        self.extensions[ext.name] = ext
        ext.register(self)
```

### Extension Types

1. **Command Extensions**: Add new voice/button commands
2. **Integration Extensions**: Connect to new services
3. **Automation Extensions**: Add new proactive behaviors
4. **UI Extensions**: Add custom button layouts
5. **Processing Extensions**: Add content transformations

### Extension Loading

```
Extension Directory (~/nxyme_extensions/)
├── music_production/
│   ├── __init__.py
│   ├── commands.py
│   └── integration.py
├── video_editing/
│   └── ...
└── custom_alerts/
    └── ...
```

---

## 2-Year Roadmap

### Phase 1: Foundation (Months 1-6)

| Month | Focus | Deliverables |
|-------|-------|--------------|
| 1-2 | Core Infrastructure | Bot setup, command hierarchy, basic state management |
| 3-4 | Voice Engine | Whisper transcription, intent classification, basic automation |
| 5-6 | Security Model | Command whitelist, permission levels, user verification |

**Dependencies**: None (foundation-first)
**Success Metrics**: 
- 50+ commands accessible in 2 taps
- Voice commands execute correctly
- No security incidents

### Phase 2: Intelligence (Months 7-12)

| Month | Focus | Deliverables |
|-------|-------|--------------|
| 7-8 | Context Awareness | Mode switching, time-aware layouts, project tracking |
| 9-10 | Proactive Automation | Alert system, scheduled tasks, context prompts |
| 11-12 | Memory System | Capture, recall, knowledge graph, Notion sync |

**Dependencies**: Phase 1 complete, security model validated
**Success Metrics**:
- Layout adapts to context correctly
- User receives <5 proactive prompts/day with >50% engagement
- 1000+ memories indexed with semantic search

### Phase 3: Content Engine (Months 13-18)

| Month | Focus | Deliverables |
|-------|-------|--------------|
| 13-14 | Content Pipeline | Voice→transcription→AI enhancement→formatting |
| 15-16 | Social Integration | YouTube, Twitter, Instagram auto-posting |
| 17-18 | Media Processing | FFmpeg integration for audio/video transformation |

**Dependencies**: Phase 2 (memory system needed for content context)
**Success Metrics**:
- Complete pipeline executes in <60 seconds
- All major social platforms connected
- 10+ content templates available

### Phase 4: Ecosystem (Months 19-24)

| Month | Focus | Deliverables |
|-------|-------|--------------|
| 19-20 | Extension System | Plugin architecture, marketplace, documentation |
| 21-22 | Advanced Integrations | Home Assistant, Plex, custom DAW integration |
| 23-24 | AI Enhancement | Predictive suggestions, flow state detection, personalized automation |

**Dependencies**: Phase 3 (content engine), Extension system complete
**Success Metrics**:
- 10+ community extensions
- 90%+ user satisfaction
- System runs autonomously with minimal friction

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Telegram User Interface                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Reply       │  │ Inline      │  │ Voice      │  │ Callback Queries    │ │
│  │ Keyboard    │  │ Buttons     │  │ Input      │  │ (confirmations)     │ │
│  └──────┬──────┘  └──────┬──────┘  └─────┬─────┘  └──────────┬──────────┘ │
└─────────┼─────────────────┼──────────────┼───────────────────┼────────────┘
          │                 │              │                   │
          ▼                 ▼              ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Command Dispatcher                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Intent      │  │ Permission │  │ Context     │  │ History             │ │
│  │ Router      │  │ Checker    │  │ Manager     │  │ Tracker             │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
└─────────┼─────────────────┼──────────────┼───────────────────┼────────────┘
          │                 │              │                   │
          ▼                 ▼              ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Execution Layer                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Shell       │  │ Git        │  │ API         │  │ MCP                 │ │
│  │ Executor   │  │ Handler    │  │ Client      │  │ Tool                │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
          │                 │              │                   │
          ▼                 ▼              ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Integration Layer                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │Calendar  │  │YouTube   │  │Spotify   │  │GitHub    │  │Home Assistant│  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Data Layer                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │SQLite    │  │Redis     │  │Vector DB │  │File      │  │Knowledge    │  │
│  │(state)   │  │(cache)   │  │(memory) │  │Storage   │  │Graph        │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Priority Summary

1. **P0 (Must Have)**: Command hierarchy, voice engine, security, calendar, GitHub, AI
2. **P1 (Should Have)**: Context modes, proactive alerts, memory capture, Notion sync
3. **P2 (Nice to Have)**: Home Assistant, Plex, extension marketplace
4. **P3 (Future)**: Advanced AI prediction, community extensions

---

*Architecture v1.0 — Ready for implementation planning*