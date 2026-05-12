# ADHD UX Patterns: Evidence-Based Design Guide

## Executive Summary

This research document compiles user experience design patterns specifically optimized for ADHD cognitive profiles. The patterns are grounded in HCI research, cognitive load theory, and empirical studies with ADHD populations. Four primary pattern domains are addressed: cognitive load management, attention anchoring, time blindness solutions, and working memory support.

---

## 1. Cognitive Load Management Patterns

### 1.1 Chunking & Progressive Disclosure

**Research Basis**: Cognitive Load Theory (Sweller, 1988) demonstrates that breaking complex information into smaller units reduces extraneous cognitive load. ADHD brains have reduced working memory capacity for task management, making chunking essential.

**Pattern Implementation**:

| Technique | Description | ADHD-Specific Rationale |
|----------|-------------|----------------------|
| **Multi-granularity chunking** | Content pre-segmented at multiple levels (micro-chunks → paragraphs → sections) | Allows adjustment to fluctuating attention capacity |
| **Dynamic chunk sizing** | Chunk size responds to detected attention state | Addresses variable focus levels unique to ADHD |
| **State-aware presentation** | Material presented based on cognitive availability | Prevents overwhelm during low-attention periods |

**Evidence**: AttentionGuard study (2024) showed significantly reduced cognitive load (NASA-TLX score reduction: p=.008, d=1.21) using attention-responsive chunking.

**Implementation Example**:
```
// Pseudocode: Dynamic Chunking Pattern
function getChunkSize(attentionState) {
  switch(attentionState) {
    case 'drifting': return 'micro-chunk';    // 1-2 sentences
    case 'focused': return 'paragraph';        // 3-5 sentences  
    case 'hyperfocus': return 'section';       // full content
    case 'fatigue': return 'review-mode';     // summary only
  }
}
```

### 1.2 Minimalist Interface Architecture

**Research Basis**: Nielsen's usability heuristics (1992) emphasize reducing visual clutter. For ADHD users, visual complexity directly impacts distraction susceptibility.

**Pattern**: 
- Collapsible sidebars with context-sensitive panels
- Hide non-essential menus and toolbars
- Emphasize primary task pane
- Collapsible panels that expand on demand

**Evidence**: "ADHD-Centered IDE Design" study (Kulsum & Fatima, 2025) reported 35% reduction in perceived distraction with minimalist layouts.

### 1.3 Automation with User Control

**Research Basis**: The ADHD Design Framework (Marshall, 2017) identifies three technological approaches: Manual Interaction, Automatic Execution, and Context Capture. The most effective pattern combines automation with user override.

**Pattern Implementation**:
- Offer automated assistance (task suggestions, reminders)
- Always allow manual override/control
- Provide transparency into AI decisions
- Make all adaptations reversible

---

## 2. Attention Anchoring Techniques

### 2.1 Visual Cues & Peripheral Attention

**Research Basis**: Vertegaal (2002, 2003) established frameworks for Attentive User Interfaces that direct attention without requiring active focus. Peripheral visual cues are particularly effective for ADHD because they operate below conscious attention threshold.

**Pattern Implementation**:

| Technique | Description | Evidence |
|-----------|-------------|----------|
| **Spatial landmark navigation** | Journey-based spatial visualization showing current position (not countdown) | AttentionGuard "Temporal Landmark" pattern; reduces anxiety-inducing timers |
| **Color-coded urgency** | Green → Yellow → Red progression for time awareness | Timbrica visual time tool; universally effective |
| **Floating progress indicators** | Persistent but collapsible progress bars | Timerjoy research; passive awareness without active monitoring |

**Implementation Example** (Timbrica approach):
```
// Color progression for deadline awareness
const URGENCY_COLORS = {
  safe: '#4CAF50',      // Green (>2 hours remaining)
  moderate: '#FFC107',  // Yellow (30min-2hours)  
  urgent: '#FF5722',    // Red (<30min)
  critical: '#F44336'    // Deep red (overdue)
};
```

### 2.2 Motion & Animation

**Research Basis**: The "Attention-Responsive Chunking" pattern from AttentionGuard uses motion to re-engage drifting attention without inducing startle response.

**Pattern Implementation**:
- Gentle motion (not sudden) to redirect attention
- Animated progress bars visible in peripheral vision
- Avoid aggressive animations that trigger rejection sensitive dysphoria (RSD)
- Use "safe" rounded shapes (scientifically shown to reduce amygdala activation - see Aestu design)

**Evidence**: Aestu timer design (2026) applies "Softness Psychology": "SF Pro Rounded font. Sharp angles activate the amygdala (fear response), while rounded shapes are perceived as safe and friendly."

### 2.3 Bi-Directional Scaffolding

**Research Basis**: ADHD involves both overstimulation AND understimulation states. Most interfaces only reduce stimulation, failing understimulation.

**Pattern**: Respond to BOTH states:
- **Overstimulation response**: Reduce visual complexity, increase whitespace, pre-reveal hints
- **Understimulation response**: Inject novelty, surface curiosity hooks, enable gamified elements

**Evidence**: AttentionGuard study showed bi-directional adaptation necessary because "Current adaptive interfaces treat attention as binary and constant, failing users whose attention fluctuates dynamically."

---

## 3. Time Blindness Solutions

### 3.1 Visual Timer Patterns

**Research Basis**: Dr. Russell Barkley identifies time blindness as a core executive function deficit. The prefrontal cortex, which regulates time perception, functions differently in ADHD. Visual timers externalize time—make it visible.

**Pattern Implementation**:

| Timer Type | How It Works | ADHD Benefit |
|------------|-------------|--------------|
| **Shrinking disk/bar** | Colored area disappears as time passes | Immediate intuitive sense of remaining time |
| **Progress bar** | Bar empties as time passes | Peripheral vision awareness |
| **Color progression** | Colors shift (blue→orange→red) | Emotional cue without numbers |
| **Fluid visualization** | Liquid "draining" metaphor (Aestu) | Concrete, emotional time representation |

**Evidence**: Timerjoy research states: "A visual countdown timer acts as a prosthetic for time perception, providing the external structure that the ADHD brain struggles to generate internally."

### 3.2 Journey-Based Spatial Visualization

**Research Basis**: Traditional countdown timers create anxiety. Spatial/temporal landmarks provide orientation without urgency.

**Pattern** (AttentionGuard Temporal Landmark Navigation):
- Show current position in a journey, not time remaining
- Display "Finishing at [time]" (concrete endpoint) vs "00:15:00 remaining" (abstract deficit)
- No countdown displays during focus sessions
- Review-mode visualization showing completed journey

**Evidence**: AttentionGuard found "journey-based spatial visualization" preferred over anxiety-inducing timers.

### 3.3 Time Estimation Training

**Research Basis**: ADHD brains consistently underestimate task duration. External estimation tools build metacognitive awareness.

**Patterns**:
- Elapsed time tracking (see actual vs estimated time)
- Task duration history logging
- "How long will this take?" prompts with comparison to actual
- Color-coded bar showing elapsed time for task awareness

**Evidence**: Timbrica includes "Elapsed time tracker for task awareness" enabling users to "notice how long tasks actually take."

### 3.4 Interval Reminder Systems

**Research Basis**: Time Ninja research establishes that interval reminders provide the external time awareness ADHD brains need.

**Pattern**:
- High-risk (hyperfocus-prone): Every 15-20 minutes
- General work: Every 30-45 minutes  
- Routine tasks: Hourly check-ins

**Multi-modal reminders** are most effective:
- Audio: Chimes, bells
- Visual: Screen flashes, popups
- Physical: Smartwatch vibrations
- Environmental: Visible timers in workspace

---

## 4. Working Memory Support

### 4.1 Cognitive Offloading (External Memory)

**Research Basis**: ADHD working memory deficits require external memory aids. The "Thinking Space" pattern from AttentionGuard acts as a Cognitive Offloading Workspace (COW).

**Pattern Implementation**:
- Persistent external storage for current tasks
- "Current Focus Box" showing immediate task
- Auto-populated next task suggestions
- Task state persistence (survives refresh/session end)

**Evidence**: Focus Buddy study (2024) co-designed with ADHD students found "low-cognitive-load interface" essential—minimalist design that's "distraction-free and easy to navigate."

### 4.2 Progress Visualization

**Research Basis**: External progress markers reduce mental load of tracking incomplete items.

**Pattern**:
- Visual progress bars for goals
- Completion counters (gamification)
- Streak tracking for routines
- "Win" visualization for completed tasks

**Implementation** (Focus Buddy):
- "Visual wins" for daily accomplishments
- Productivity points system
- Pomodoro goal tracker: 8 visual indicators fill upon completion

### 4.3 Task Persistence

**Research Basis**: ADHD brains lose track of in-progress items. State must persist beyond active attention.

**Pattern**:
- Local storage persistence (survives refresh)
- Auto-save with smart rescheduling
- Visible "where was I" indicators
- Floating UI elements that persist across views

### 4.4 External Routine Anchors

**Research Basis**: Routines that exist only as mental scripts collapse. External anchors maintain structure.

**Pattern**:
- Morning/evening routine progress bars
- Checklists anchored to physical/device locations
- Widget-based routine visibility
- Notification cues at routine transition points

---

## 5. Cross-Cutting Design Principles

### 5.1 RSD-Safe Feedback

**Research Basis**: Rejection Sensitive Dysphoria affects most ADHD individuals. Standard error/warning patterns can trigger distress.

**Pattern**:
- Avoid aggressive red/error styling
- Use gentle notifications (not startling)
- Present "too many errors" as system limitation, not user failure
- Non-punitive hyperfocus handling (suggestextend vs force-stop)

### 5.2 Flow State Protection

**Research Basis**: Hyperfocus is valuable but can cause neglect of essentials. Forced interruptions damage flow.

**Pattern**:
- Detect flow state (interaction consistency)
- Suggest extension vs force break
- Provide "extend by 15/30/60min" option
- Never auto-interrupt during hyperfocus

### 5.3 Agency & Transparency

**Research Basis**: AttentionGuard emphasizes "support user agency and interface-level transparency."

**Pattern**:
- All adaptations reversible
- User can pause/disable AI features
- Expose inferred attention state (optional "observer view")
- Never force categories or states

---

## 6. Implementation Resources

### Tools Referenced in Research:

| Tool | Purpose | URL |
|------|---------|-----|
| Timbrica | Visual time blindness helper | timbrica.com |
| Aestu | Liquid timer for ADHD | giuseppep.me/aestu-promo-eng.html |
| Timerjoy | Visual timer guide | timerjoy.com |
| Time Ninja | Interval reminders | timeninja.io |
| 25MinuteTimer | ADHD-friendly Pomodoro | 25mintimer.com/timers/adhd-friendly/ |
| Focus Buddy | Co-designed task app | samita.design/works/focusbuddy |

### Academic Sources:

1. Marshall, K. (2017). "A Design Framework for ADHD Assistive Technologies." UCL Discovery.
2. AttentionGuard (2024). "Attention-Adaptive Interfaces for ADHD." arxiv.org/pdf/2602.07865
3. Kulsum & Fatima (2025). "ADHD-Centered IDE Design." irejournals.com.
4. Ahufinger & Herrero-Martín (2021). "Alien Attack: Cognitive Training for ADHD." Entropy journal.
5. Springer Nature (2024). "Interaction Design Strategies for ADHD Learning Attention."

---

## Research Status

- [x] Cognitive load management patterns (chunking, progressive disclosure)
- [x] Attention anchoring techniques (visual cues, motion)
- [x] Time blindness solutions (timers, progress visualization)
- [x] Working memory support (external memory, persistence)
- [x] Implementation examples with rationale