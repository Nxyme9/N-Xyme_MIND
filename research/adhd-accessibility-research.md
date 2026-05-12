# ADHD Accessibility Research: Comprehensive Technical Document

**Document Type:** Research Synthesis  
**Date:** May 2026  
**Status:** Complete  

---

## Executive Summary

This document synthesizes comprehensive research on ADHD accessibility across five key domains: WCAG COGA guidelines, ADHD UX patterns, academic learning interfaces, AR/VR interfaces, and commercial app design patterns. The research provides actionable design patterns for creating ADHD-friendly digital interfaces, drawing from W3C standards, peer-reviewed academic literature, and commercial app analysis.

---

## Table of Contents

1. [WCAG COGA Guidelines](#1-wcag-coga-guidelines)
2. [ADHD UX Patterns](#2-adhd-ux-patterns)
3. [Academic Learning Interfaces](#3-academic-learning-interfaces)
4. [AR/VR Interfaces for ADHD](#4-arvr-interfaces-for-adhd)
5. [Commercial App Design Patterns](#5-commercial-app-design-patterns)
6. [Design Principles Summary](#6-design-principles-summary)
7. [References](#7-references)

---

## 1. WCAG COGA Guidelines

### 1.1 Overview

The W3C WCAG COGA (Cognitive and Learning Disabilities Accessibility) guidelines provide a comprehensive framework for making digital content accessible to people with cognitive and learning disabilities, including ADHD. The guidelines are documented in "Making Content Usable for People with Cognitive and Learning Disabilities" (W3C Working Group Note, April 29, 2021).

**Source:** https://www.w3.org/TR/coga-usable/

### 1.2 The 8 COGA Objectives

#### Objective 1: Help Users Understand What Things Are and How to Use Them

**User Story:** "As a user with a memory impairment, attention impairment and/or executive function impairment, I need to know the purpose of the content so that I know if I am in the right place, and what I am doing even if I lose attention and focus for a time."

**Design Patterns (7 patterns):**
- Make the purpose of your page clear
- Use a familiar hierarchy and design
- Use a consistent visual design
- Make each step clear
- Clearly identify controls and their use
- Make the relationship clear between controls and what they affect
- Use symbols that help the user

**ADHD Applicability:** Users with ADHD often struggle with working memory and attention. Clear page purposes and familiar designs reduce cognitive load, helping them stay oriented.

---

#### Objective 2: Help Users Find What They Need

**User Story:** "As a user with a memory impairment, I need to be able to find the features and functions that I need in order to use the site without having to remember them from a previous visit."

**Design Patterns (6 patterns):**
- Make it easy to find the most important tasks and features
- Make the site hierarchy easy to understand and navigate
- Use a clear and understandable page structure
- Make it easy to find the most important things on the page
- Break media into chunks
- Provide search

**ADHD Applicability:** When users with ADHD lose focus, they may forget what they're looking for. Clear hierarchies and prominent search help them reorient quickly.

---

#### Objective 3: Use Clear and Understandable Content

**User Story:** "As a user with a language impairment, slow processing speed, or attention impairment, I need content that is unambiguous and easy to understand so that I can understand the information the first time it is read."

**Design Patterns (13 patterns):**
- Use clear words (common, everyday words)
- Use a simple tense and voice (present tense, active voice)
- Avoid double negatives or nested clauses
- Use literal language (avoid metaphors and idioms)
- Keep text succinct
- Use clear, unambiguous formatting and punctuation
- Include symbols necessary to decipher words
- Provide summary of long documents and media
- Separate each instruction
- Use white spacing
- Ensure foreground content is not obscured by background
- Explain implied content
- Provide alternatives for numerical concepts

**ADHD Applicability:** Users with ADHD may have difficulties with reading comprehension and processing speed. Clear, simple language, white space, and chunked instructions help maintain attention.

---

#### Objective 4: Help Users Avoid Mistakes and Know How to Correct Them

**User Story:** "As a user with a short term memory impairment, I need to be able to reverse my actions easily so that I do not have to remembering what I did previously."

**Design Patterns (12+ patterns):**
- Ensure controls and content do not move unexpectedly
- Let users go back
- Notify users of fees and charges at the start of a task
- Design forms to prevent mistakes
- Make it easy to undo form errors
- Use clear visible labels
- Use clear step-by-step instructions
- Accept different input formats
- Avoid data loss and "timeouts"
- Provide feedback
- Help the user stay safe
- Use familiar metrics and units

**ADHD Applicability:** Impulsivity is a core ADHD feature. Error prevention, clear undo functionality, and visible labels help prevent mistakes.

---

#### Objective 5: Help Users Focus

**User Story:** "As a user with an attention impairment, I need to be able to carry out and complete an activity without losing my attention and without having to start again if I get distracted."

**Design Patterns (4 patterns):**
- Limit interruptions
- Make short critical paths
- Avoid too much content
- Provide information so a user can complete and prepare for a task

**ADHD Applicability:** This directly addresses attention regulation challenges. Limiting interruptions and short critical paths help maintain focus.

---

#### Objective 6: Ensure Processes Do Not Rely on Memory

**User Story:** "As a user with a memory impairment, I need to be able to use content and complete a course of action without having to depend on remembering lots of different information."

**Design Patterns (5 patterns):**
- Provide a login that does not rely on memory or other cognitive skills
- Allow the user a simple, single step login
- Provide a login alternative with less words
- Let users avoid navigating voice menus
- Do not rely on users calculations or memorizing information

**ADHD Applicability:** Working memory deficits are a core ADHD feature. Password alternatives and avoiding voice menus directly address this.

---

#### Objective 7: Provide Help and Support

**User Story:** "As a user with a memory impairment, I need to get help easily from every place where I get stuck so that I can complete my intended task."

**Design Patterns (7 patterns):**
- Provide human help
- Provide alternative content for complex information and tasks
- Clearly state the results and disadvantages of actions, options, and selections
- Provide help for forms and non-standard controls
- Make it easy to find help and give feedback
- Provide help with directions
- Provide reminders

**ADHD Applicability:** Users with ADHD benefit from multiple forms of help. Human help access is especially important when attention lapses cause users to forget how to complete tasks.

---

#### Objective 8: Support Adaptation and Personalization

**User Story:** "As a user with a cognitive disability, I need to be able to use add-ons and extensions that I already use and customize the display and content to meet my needs."

**Design Patterns (4 patterns):**
- Let users control when the content moves or changes
- Enable APIs and extensions
- Support simplification
- Support a personalized and familiar interface

**ADHD Applicability:** Personalization allows users with ADHD to customize interfaces to reduce distractions and match their processing preferences.

---

### 1.3 WCAG COGA Pattern Summary

| Objective | # of Patterns | ADHD Priority |
|-----------|---------------|----------------|
| 1. Understand What Things Are | 7 | High |
| 2. Find What They Need | 6 | High |
| 3. Clear Content | 13 | Very High |
| 4. Avoid Mistakes | 12+ | High |
| 5. Help Users Focus | 4 | Very High |
| 6. No Memory Reliance | 5 | Very High |
| 7. Provide Help & Support | 7 | Medium |
| 8. Personalization | 4 | High |
| **TOTAL** | **50+ patterns** | |

---

## 2. ADHD UX Patterns

### 2.1 Cognitive Load Management

**Key Pattern: Dynamic Chunking**
- Break complex tasks into smaller, manageable units
- Progressive disclosure of information
- Allow users to control information density

**Research Citation:** AttentionGuard study (d=1.21), Marshall (2017)

**Implementation:**
- Use accordion-style content expansion
- Provide "show more" options for detailed information
- Implement step-by-step wizards for multi-step processes

---

### 2.2 Attention Anchoring Techniques

**Visual Cues:**
- Color-coded urgency indicators (distinct from red/green only)
- Bi-directional scaffolding (hints + progress indicators)
- Peripheral motion for important notifications

**Research Citation:** Vertegaal (2002-03), Aestu study

**Implementation:**
- Persistent visual indicators for current task
- Highlight active elements without overwhelming
- Use subtle animations to draw attention without startling

---

### 2.3 Time Blindness Solutions

**Visual Timers:**
- Shrinking disk or bar representations
- Journey-based spatial visualization
- Interval reminders with gentle nudges

**Research Citation:** Timerjoy, Timbrica, Barkley time blindness research

**Implementation:**
- Circular progress indicators (more intuitive than linear)
- "Time remaining" prominently displayed
- Multiple reminder types (visual, audio, haptic)

---

### 2.4 Working Memory Support

**Cognitive Offloading:**
- Workspace persistence (auto-save everything)
- Progress visualization at all times
- Routine anchors for task initiation

**Research Citation:** Focus Buddy, AttentionGuard research

**Implementation:**
- All input auto-saved with no explicit save action needed
- Visual progress bars for multi-step tasks
- Template systems for recurring tasks

---

### 2.5 ADHD UX Pattern Summary Table

| Domain | Key Patterns | Implementation Priority |
|--------|-------------|------------------------|
| Cognitive Load | Dynamic chunking, minimalist architecture, automation-with-control | Critical |
| Attention Anchoring | Visual cues, color-coded urgency, bi-directional scaffolding, peripheral motion | Critical |
| Time Blindness | Visual timers, journey-based spatial viz, interval reminders | Very High |
| Working Memory | Cognitive offloading, progress viz, persistence, routine anchors | Very High |

---

## 3. Academic Learning Interfaces

### 3.1 Springer Research

**AHA (ADHD-Augmented) Project:**
- Web-based AR learning environment for literacy
- Demonstrated feasibility and user acceptance
- Highlighted complexity of AR interventions for ADHD

**AR Picture Book Intervention (2026):**
- Published in Frontiers in Psychology
- Found significant improvements in attentional focus, learning motivation, emotion regulation
- Used SEM to validate pathway: AR engagement → learning motivation → attentional focus → emotional regulation → behavioral improvement

**Say-It & Learn (2020):**
- Tablet application with facial/voice recognition
- Features: real-life familiar objects, highlighted task elements, self-evaluation quizzes
- High engagement and satisfaction demonstrated

**BRAVO Project (2024):**
- XR serious games targeting self-control, rule compliance, attention, concentration
- Biofeedback sensors for real-time adaptation
- Six-month evaluation showed general cognitive/behavioral improvements

---

### 3.2 arXiv Research

**arXiv:2405.01218 (2024):** Attention and Sensory Processing in Augmented Reality
- Comprehensive review of attentional mechanisms in AR for ADHD
- Proposed framework for cognitively accessible AR applications
- Key insight: poorly designed AR may worsen cognitive overload

**arXiv:2511.01248 (2025):** FocusView
- Video customization interface for ADHD viewers
- Significantly reduced perceived distractions
- Key design insight: reduce customization options to avoid overwhelm

**arXiv:2602.20350 (2026):** Misty Forest VR
- Neurodiversity-affirming design approach
- Treats ADHD cognitive patterns as design assets, not deficits
- Higher task completion, increased self-acceptance among ADHD participants

**arXiv:1911.01003 (2019):** AR-Therapist
- Gamified CBT framework using AR
- Real-time progress measurement throughout treatment sessions

---

### 3.3 IEEE Research

- **Attentive Visual Interfaces (2025):** Extending attention span for children with ADHD using gaze-based AUI principles
- **Advanced Learning Tools (2025):** Specific tooling needs for ADHD learners in higher education
- **Distance Learning for Adults (2025):** LMS accommodations for adult ADHD learners
- **Synchronous Virtual Classrooms (2025):** Real-time learning environment accommodations

---

### 3.4 Academic Design Recommendations

| Category | Recommendation | Source |
|----------|---------------|--------|
| Engagement | Use AR to increase task salience and task initiation | Parmar et al. (2026) |
| Engagement | Implement adaptive difficulty adjustment | BRAVO Project (2024) |
| Engagement | Design for variable attention patterns | Misty Forest VR (2026) |
| Visual Design | Use real-life familiar objects | Say-It & Learn (2020) |
| Visual Design | Highlight active task elements | Say-It & Learn (2020) |
| Visual Design | Provide visual scaffolds (mind maps, annotated slides) | Strathclyde study |
| Executive Function | Provide progress tracking and status markers | LLM Mind Map Creator (2025) |
| Executive Function | Include task breakdown features | LLM Mind Map Creator |
| Executive Function | Offer just-in-time AI scaffolding | Parmar et al. (2026) |
| Multimodal | Combine cognitive training with physical exercise | BrainFit RCT (2024) |
| Inclusion | Involve care ecosystem (parents, teachers, clinicians) | Stefanidi et al. (ACM CHI, 2022) |

---

## 4. AR/VR Interfaces for ADHD

### 4.1 SEEV Model

The **Salience, Effort, Expectancy, Value (SEEV) model** is a computational model of visual attention allocation that provides a framework for designing ADHD-friendly AR/VR interfaces.

**Core Components:**
- **Salience (S):** Bottom-up perceptual attractiveness — high salience increases attention
- **Effort (EF):** Mental exertion required — higher effort reduces attention (inhibitor)
- **Expectancy (EX):** Expected information bandwidth — top-down expectation
- **Value (V):** Personal importance — top-down motivation factor

**SEEV Equation:** `P(A) = s·S − ef·EF + (ex·EX + v·V)`

**ADHD Application:**
| SEEV Factor | ADHD Challenge | Design Application |
|-------------|---------------|------------------|
| Salience | Difficulty filtering irrelevant stimuli | Maximize target salience; minimize distraction |
| Effort | Executive function demands reduce resources | Minimize navigation effort |
| Expectancy | Time blindness and unpredictable timelines | Clear temporal cues; predictable rewards |
| Value | Motivation and reward sensitivity | High-value reinforcement; immediate feedback |

---

### 4.2 FocusViz

**Technical Approach:**
- Uses eye-tracking (Apple Vision Pro)
- Real-time eye tracking data analysis (fixation, saccade patterns)
- Distinguishes top-down vs. bottom-up attention
- Implements SEEV model in AR spatial interfaces

**Design Principles:**
1. Distraction management — cognitive support to filter irrelevant AR elements
2. Social presence — maintain awareness of real-world social cues
3. Personalization — adapts to individual ADHD profiles
4. Accessibility — usable across ADHD spectrum

---

### 4.3 Other Notable AR/VR Systems

**Empowered Brain (2019):**
- Google Glass-based social-emotional communication aid
- Significant correlations between game performance and ADHD symptom severity
- Used gamification with points/stars as rewards

**FocusVR (2025):**
- VR video game for concentration in children with ADHD
- 77.24% average improvement in sustained attention
- 55.66% average correct filtering in selective attention
- Best combined with CBT and medication

**Focus Field (Reality Hack 2020):**
- Microsoft HoloLens 2 with eye-tracking
- Radiating visual rings for attention redirection
- Non-intrusive visual cues to avoid cognitive overload

---

### 4.4 Cogleap Systems

**Hope Focus System (HFS):**
- Strength-based coaching
- Auditory processing activities with bone-conduction headphones
- Skill-building exercises for coordination/motor skills
- Observed outcomes: improved attention, emotional self-control, social skills

**vCAT (Virtual Classroom Attention Tracker):**
- 13-minute CPT paradigm in VR classroom
- Normative database from 837 neurotypical children (ages 6-13)
- Multi-dimensional data: head/hand movement, gaze, reaction time, accuracy
- Machine learning integration for pattern identification

**FocusEDTx:**
- 12-week CBT-informed training program
- 35 animated video lessons, 25 interactive activities
- Parent/caregiver video tutorials
- Progress tracking

---

### 4.5 AR/VR Design Specifications

| Specification | Recommendation |
|---------------|----------------|
| Element sizing | Minimum 1.5° visual angle |
| Color coding | Maximum 4 categories; avoid red/green only |
| Feedback latency | <100ms for all interactions |
| Session duration | Max 20 min (AR), 30 min (VR) |
| Break intervals | Mandatory breaks every 20 minutes |

---

## 5. Commercial App Design Patterns

### 5.1 Feature Analysis: 22+ Apps

**Category 1: Focus/Timer Apps**
| App | Core Features | ADHD Suitability |
|-----|---------------|------------------|
| Forest | Gamified timer, phone locking, tree-planting | High |
| Focus Keeper | Clean Pomodoro timer, customizable | Medium |
| Be Focused | Task-linked Pomodoro, iCloud sync | High |
| Bento Focus | 3-task limit, AI insights, Japanese themes | Very High |
| Tide/Brain.fm | Focus music, AI-generated audio | Medium |

**Category 2: Todo/Task Management**
| App | Core Features | ADHD Suitability |
|-----|---------------|------------------|
| Todoist | Natural language input, Karma system | High |
| TickTick | Tasks + habits + Pomodoro + calendar | Very High |
| Things 3 | GTD methodology, beautiful UI | High |
| Remember The Milk | Smart scheduling, reminders | Medium |

**Category 3: ADHD-Specific Apps**
| App | Core Features | ADHD Suitability |
|-----|---------------|------------------|
| Inflow | CBT modules, coaching, AI (Quinn), coworking | Very High |
| Tiimo | Visual timeline, color-coded schedules, soft nudges | Very High |
| Wavio | Mastery-based learning, EF tracking | High |
| Focus Buddy | Task breakdown, accountability partner | Very High |

**Category 4: Habit Tracking**
| App | Core Features | ADHD Suitability |
|-----|---------------|------------------|
| Habitica | RPG gamification, parties, guilds | Very High |
| Streaks | Simple habit tracking, iOS widgets | Medium |
| Loop Habit Tracker | Open-source, flexible tracking | Medium |

---

### 5.2 Key Design Patterns

**Pattern 1: Constraint-Based Task Management**
- Impose artificial limits that reduce decision paralysis
- Examples: Bento's 3-task limit, Forest's session limits, Tiimo's timeline constraints

**Pattern 2: Visual Progress & Immediate Feedback**
- Visual feedback provides immediate dopamine reinforcement
- Examples: Forest's trees, Habitica's XP/leveling, Tiimo's color timeline
- Forest users showed 37% increase in tasks completed, 42% reduction in self-interruptions

**Pattern 3: External Accountability Integration**
- Social accountability outperforms self-motivation for ADHD
- Examples: Inflow's coworking, Habitica's parties, Focus Buddy's accountability partner

**Pattern 4: Gentle, Non-Punitive Design**
- Punitive language causes abandonment
- Examples: Tiimo's soft nudges, Bento's celebration-focused feedback, Inflow's supportive language

**Pattern 5: Multi-Modal Support Bundling**
- Single-feature apps have limited efficacy
- Examples: TickTick (tasks + habits + Pomodoro), Inflow (coaching + community + education + AI)

---

### 5.3 CBT Integration Patterns

| Component | Apps Implementing | Effectiveness |
|-----------|-------------------|----------------|
| Psychoeducation | Inflow, ParentCoach | High |
| Cognitive Restructuring | Inflow (AI Quinn), Focus Buddy | Medium |
| Behavioral Activation | Habitica, Todoist, TickTick | Very High |
| Self-Monitoring | Tiimo, Inflow, Habitica | High |
| Goal Setting | All task apps, Inflow modules | High |
| Mindfulness Integration | Brain.fm, Noisli, Inflow | Medium |
| Skill Building | Inflow (14-day challenges), Focus Buddy | High |

**Inflow as CBT Model:**
- Entry assessment identifies affected areas
- Module curriculum covers anxiety, procrastination, impulsivity, avoidance
- AI assistant (Quinn) provides real-time CBT-based guidance
- 88% of users reported benefits from daily use (PubMed study)

---

### 5.4 Notification Strategy Effectiveness

| Strategy | User Response |
|----------|---------------|
| Gentle nudges (soft vibration, non-alarming) | Positive — reduces anxiety |
| Punitive alerts (red badges, urgent tones) | Negative — causes avoidance |
| Context-aware timing (energy-aware scheduling) | Positive — respects cognitive state |
| Minimal interruption | Mixed — depends on user |

**Best Practice:** 2-3 strategic reminders per day; "We're glad you're back" style maintains engagement

---

### 5.5 Onboarding Best Practices

| Practice | Example | Evidence |
|----------|---------|----------|
| Low-friction quick start | Forest: immediate timer, Bento: 3-step setup | Reduces abandonment |
| Personalization quiz | Inflow (ADHD assessment), Bento (ADHD questions) | Increases relevance |
| Value before paywall | 7-day trials, free tier with core features | Builds trust |
| Progressive complexity | Tiimo: simple timeline → advanced | Matches energy |
| Neurodiverse-specific language | Bento, Inflow, Tiimo | Signals understanding |

---

## 6. Design Principles Summary

### 10 Principles for ADHD-Friendly Interface Design

1. **Constraint-Based Freedom** — Impose artificial limits that compensate for executive function deficits
2. **Visual First, Text Second** — Use color, icons, timelines over lists
3. **Immediate Dopamine Delivery** — Build rewards into every action
4. **Gentle Accountability Over Pressure** — Support, don't shame
5. **Stress-Aware UX** — Design for low-energy states: simple flows, forgiving interfaces
6. **Multi-Modal Bundling** — Combine tasks + focus + education + community
7. **Externalize Memory** — Everything goes in app; nothing relies on internal recall
8. **Time Blindness Solutions** — Visual timelines, timers, duration estimates
9. **Personalization Over Presets** — Allow deep customization
10. **Forgiveness Architecture** — Undo delete, pause without penalty, flexible schedules

---

### ADHD Challenge to Design Pattern Mapping

| ADHD Challenge | COGA Objectives | UX Patterns | AR/VR | App Patterns |
|---------------|-----------------|-------------|-------|--------------|
| Attention/Focus Issues | Objective 5 | Attention anchoring | SEEV optimization | Constraint-based |
| Working Memory Limits | Objective 6 | Cognitive offloading | Effort reduction | External memory |
| Impulsivity | Objective 4 | Error prevention | Value enhancement | Gentle accountability |
| Processing Speed | Objective 3 | Clear language | Salience optimization | Minimal UI |
| Task Completion | Objectives 1, 5 | Progress visualization | Session management | Gamification |

---

## 7. References

### W3C/WCAG COGA
- https://www.w3.org/TR/coga-usable/
- https://www.w3.org/WAI/cognitive/
- https://www.w3.org/WAI/GL/task-forces/coga/wiki/index.php?title=Gap_Analysis/ADHD

### Academic Sources
- Chiazzese, G., et al. (2020). AR literacy for ADHD children. Virtual Reality, Springer.
- Parmar, R., et al. (2026). AR + Generative AI for ADHD students. Discover Education, Springer.
- BRAVO Project (2024). Serious Games for ADHD Treatment. Information Systems Frontiers, Springer.
- arXiv:2405.01218 (2024). Attention and AR for ADHD.
- arXiv:2511.01248 (2025). FocusView: Video Customization for ADHD.
- arXiv:2602.20350 (2026). Misty Forest VR: Neurodiversity-Affirming Design.
- IEEE (2025). Attentive Visual Interfaces for ADHD Children.
- Marshall, P., et al. (2017). Design Framework for ADHD Assistive Technologies. UCL.

### AR/VR Systems
- FocusViz (2024). IEEE ISMAR 2024.
- Cogleap (2024). Hope Focus System Technical Documentation.
- vCAT (2024). USC Institute for Creative Technologies.
- FocusVR (2025). Springer.

### Commercial Apps
- Inflow (2024). CBT-based ADHD app.
- Bento Focus (2024). ADHD-specific design.
- Tiimo (2024). Visual planning for ADHD.
- Forest (2024). Gamified focus timer.

---

*Document synthesized from 5 comprehensive research areas: WCAG COGA, ADHD UX Patterns, Academic Learning Interfaces, AR/VR Interfaces, and Commercial App Patterns.*

**Last Updated:** May 2026