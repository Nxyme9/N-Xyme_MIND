# AR/VR Interfaces for ADHD: Technical Research Document

**Document Type:** Technical Research Survey
**Date:** May 2026
**Status:** Complete

---

## Executive Summary

This document presents a comprehensive technical survey of augmented reality (AR) and virtual reality (VR) interfaces designed to support individuals with Attention Deficit Hyperactivity Disorder (ADHD). The research covers the theoretical foundation of the SEEV attention model, analyzes existing AR/VR ADHD solutions including FocusViz and related systems, examines the Understood.org platform ecosystem, and investigates cognitive assistance technologies from Cogleap. The document concludes with evidence-based design recommendations for ADHD-specific AR/VR interface development.

---

## 1. SEEV Model: Theoretical Foundation

### 1.1 Model Overview

The **Salience, Effort, Expectancy, Value (SEEV) model** is a computational model of visual attention allocation developed by Christopher D. Wickens and colleagues. The model provides a theoretically grounded method for predicting where individuals will allocate their visual attention in multi-source display environments. Originally developed for aviation and complex supervisory control tasks, the SEEV model has been validated across multiple domains including driving, air traffic control, and medical environments.

### 1.2 Core Components

The SEEV model integrates four factors that collectively predict attention allocation probability:

**Salience (S)** — The bottom-up perceptual attractiveness of an Area of Interest (AOI). Salient stimuli capture attention automatically through physical features such as contrast, size, motion, or color. High salience increases attention allocation.

**Effort (EF)** — The physical or mental exertion required to access information. This includes head movements, eye movements, and cognitive filtering processes required to extract meaning from stimuli. Effort acts as an **inhibitor** of attention — higher effort reduces the probability of attending.

**Expectancy (EX)** — The expected information bandwidth or rate of change within an AOI. This factor represents the top-down expectation about whether valuable information will appear in a particular location. Operators develop expectancies based on task models and prior experience.

**Value (V)** — The personal importance or relevance of an AOI to the primary task goal. Value is derived from the operator's training, task priorities, and motivational state. Like expectancy, value is a top-down factor.

### 1.3 Mathematical Formulation

The original SEEV equation:

```
P(A) = s·S − ef·EF + (ex·EX + v·V)
```

Where:
- `P(A)` = Probability of attending an AOI
- `s, ef, ex, v` = Scaling coefficients for each factor
- `S` = Salience score
- `EF` = Effort score  
- `EX` = Expectancy score
- `V` = Value score

In simplified applications, the bottom-up factors (salience, effort) and top-down factors (expectancy, value) are often weighted equally or reduced to the EV (Expectancy-Value) model for assessing "optimal" attention distribution.

### 1.4 SEEV in ADHD Applications

The SEEV model provides a valuable framework for designing AR/VR interfaces for ADHD populations:

| SEEV Factor | ADHD Challenge | Design Application |
|-------------|---------------|------------------|
| Salience | Difficulty filtering irrelevant stimuli | Maximize target salience; minimize distraction salience |
| Effort | Executive function demands reduce available cognitive resources | Minimize navigation effort; provide clear visual pathways |
| Expectancy | Time blindness and unpredictable task timelines | Provide clear temporal cues; predictable reward timing |
| Value | Motivation and reward sensitivity | High-value reinforcement; immediate feedback |

Recent research (arXiv:2405.01218) applied the SEEV model specifically to AR interfaces for ADHD, demonstrating how each factor can be optimized in pervasive AR (PAR) environments. The study identified four primary challenges for ADHD in AR: **distraction management**, **social presence**, **personalization**, and **accessibility requirements**.

---

## 2. FocusViz and Related AR Interfaces

### 2.1 FocusViz: Gaze-Based Attention Framework

**FocusViz** is an interactive gaze-based framework designed to enhance attention in pervasive augmented reality for individuals with ADHD. The system was presented at IEEE ISMAR 2024/2025.

#### Technical Approach
- Uses built-in eye-tracking technology (e.g., Apple Vision Pro)
- Collects real-time eye tracking data to analyze fixation and saccade patterns
- Distinguishes between top-down (goal-directed) and bottom-up (stimulus-driven) attention
- Implements the SEEV model within AR spatial interfaces

#### Design Principles
FocusViz addresses four ADHD-specific challenges in AR environments:

1. **Distraction Management** — The system provides cognitive support to filter irrelevant AR elements
2. **Social Presence** — Maintains awareness of real-world social cues while engaged with AR content
3. **Personalization** — Adapts to individual ADHD profiles (low, medium, high support needs)
4. **Accessibility** — Ensures AR interventions are usable across the ADHD spectrum

#### Evaluation Scenarios
The prototype implements three dual-task scenarios evaluating multitasking:
- Information retrieval (auditory lecture + AR information search)
- Navigation (physical traversal + virtual notifications)
- Collaboration (group discussion + text processing)

### 2.2 The Focus Field

**The Focus Field** was developed at Reality Hack 2020 as an AR system to help maintain focus in visually distracting environments.

#### Features
- Uses Microsoft HoloLens 2 with eye-tracking
- Radiating visual rings emanating from focus points to redirect attention
- Goal-setting and progress monitoring through mobile companion app
- Specifically designed for users with ADHD and autism

#### Design Insights from Testing
- Users with ADHD and autism showed discomfort with sustained eye contact
- Visual cues must be non-intrusive to avoid adding cognitive load
- Progressive disclosure of features improved engagement

### 2.3 Empowered Brain AR System

**Empowered Brain** is an augmented reality and artificial intelligence-based social-emotional communication aid using Google Glass.

#### Clinical Results
A study published in *Sustainability* (2019) demonstrated significant correlations between game performance and ADHD symptom severity:
- ABC-Hyperactivity scores correlated strongly (p = 0.0013)
- TRF ADHD scores showed significant correlation (p = 0.012)
- No adverse effects reported

The system used points and stars as in-game rewards based on performance, demonstrating how gamification can provide objective measures of ADHD symptoms in naturalistic settings.

### 2.4 FocusVR: VR Attention Game

**FocusVR** is a virtual reality video game designed to improve concentration in children with ADHD through sustained and selective attention techniques.

#### Intervention Design
- Uses Oculus Quest 3 VR headset
- 30-minute sessions with therapist/parent monitoring
- Targets sustained attention (finding objects) and selective attention (filtering irrelevant objects)

#### Results
- **Sustained attention:** 77.24% average improvement in correctly found objects
- **Selective attention:** 55.66% average correct filtering
- Individual improvements up to 44% for sustained attention, 24% for selective attention
- Best combined as complementary to CBT and medication

---

## 3. Understood Platform Analysis

### 3.1 Platform Overview

**Understood.org** is a nonprofit organization dedicated to empowering people with learning and thinking differences, including ADHD, dyslexia, and dyscalculia. The platform provides comprehensive resources for assistive technology (AT).

### 3.2 Core Components

| Component | Description |
|----------|------------|
| **Understood Assistant** | AI-powered expert system for ADHD, dyslexia, dyscalculia questions |
| **Resource Library** | Comprehensive AT guides for reading, writing, math |
| **Tool Recommendations** | Curated app and device recommendations |
| **Community Forums** | Peer support networks |

### 3.3 Assistive Technology Resources

Understood categorizes AT across functional domains:

**For Reading:**
- Text-to-speech (TTS) technology
- Audiobooks and digital text (Bookshare)
- Screen readers and literacy apps

**For Writing:**
- Speech-to-text dictation
- Word prediction technology
- Graphic organizers

**For Math:**
- Calculators and number manipulation tools
- Math learning center apps with virtual manipulatives

**For Organization and Focus:**
- Timers and reminders (built into devices)
- Calendar and task management apps
- AI assistant integration

### 3.4 AI Tools for ADHD

Understood's research on AI tools for ADHD identifies six key applications:

1. **Time Management** — AI can help with time blindness through contextual reminders
2. **Task Initiation** — Chatbots help break tasks into actionable steps
3. **Project Decomposition** — AI helps structure large projects into smaller steps
4. **Note Summarization** — AI tools summarize recorded content
5. **Focus cueing** — AI provides subtle environmental cues
6. **Executive Function Support** — AI adapts to individual cognitive patterns

### 3.5 Platform Accessibility Features

Understood emphasizes:
- Free trials and freemium models for AT tools
- Built-in accessibility features across platforms
- Device loan programs through state AT Act Programs
- Privacy and security considerations for free tools

---

## 4. CogLocus/Cogleap Cognitive Assistance

*Note: The system is named "Cogleap" (not "CogLocus"), doing business as "CogLAp" in some contexts.*

### 4.1 Cogleap Organization Overview

**Cogleap** is a technology company focused on transforming the lives of neurodiverse children using human-centered AI. The organization specifically targets children with ADHD and Autism Spectrum Disorder (ASD).

### 4.2 Hope Focus System (HFS)

The **Hope Focus System (HFS)** is Cogleap's core training program, combining three key elements:

#### Program Components

1. **Strength-Based Coaching** — Building on natural abilities
2. **Auditory Processing Activities** — Supporting cognitive and sensory development using bone-conduction headphones
3. **Skill-Building Exercises** — Promoting coordination and motor skills

#### Neurological Framework

HFS is designed around neurological differences common to ADHD and ASD:
- Fronto-striatal circuitry differences affecting attention, emotional regulation
- Sound and language processing differences impacting communication
- Targeted at brain regions involved in higher-order cognition

#### Observed Outcomes (After ~40 Sessions)
- Improved sensorimotor skills
- Enhanced social skills and memory
- Better emotional self-control
- Increased attention and sustained focus

#### Observed Outcomes (After ~50 Sessions)
- Improved attention accuracy
- Better activity regulation
- Enhanced physical control

### 4.3 vCAT: Virtual Classroom Attention Tracker

**vCAT** is an advanced VR-based attention assessment system developed in collaboration with Dr. Albert "Skip" Rizzo at USC Institute for Creative Technologies.

#### Technical Specifications
- Uses 13-minute Continuous Performance Test (CPT) paradigm
- Immersive VR classroom environment with realistic distractions
- Multi-dimensional data collection: head/hand movement, gaze range, reaction time, accuracy, stability

#### Clinical Validation
- Based on 20+ years of scientific research
- Normative database from 837 neurotypical children (ages 6-13)
- Validated against age and gender-specific norms
- Used in hospitals, clinics, and schools worldwide

#### Assessment Dimensions
- Sustained attention
- Active attention
- Impulse control
- Hyperactive behaviors
- Psychomotor regulation

#### Machine Learning Integration
- Compares individual performance to age/gender-matched norms
- Generates comprehensive assessment reports
- Identifies subtle behavioral patterns missed by traditional testing

### 4.4 FocusEDTx: CBT Intervention Program

**FocusEDTx** is a 12-week evidence-informed cognitive and social-emotional training program.

#### Program Structure
- Clinician-designed curriculum
- 35 animated video lessons (CBT concept translation)
- 25 interactive activities
- Parent/caregiver video tutorials
- Progress and growth tracking

#### Topics Covered
- ADHD psychoeducation
- Body awareness / sensory system
- Emotional state recognition
- Executive function and memory
- Attention / concentration
- Impulsivity control
- Problem-solving and decision-making
- Organizational skills
- Cognitive distortion / negative thinking
- Growth mindset / school skills

---

## 5. ADHD-Specific AR/VR Design Recommendations

### 5.1 Attention Architecture Principles

Based on the SEEV model and existing research, AR/VR interfaces for ADHD should optimization for the four attention types:

| Attention Type | Definition | Design Priority |
|----------------|------------|-----------------|
| **Selective** | Focus on relevant stimuli while ignoring distraction | High |
| **Sustained** | Maintain consistent focus over time | High |
| **Divided** | Handle multiple information streams | Moderate |
| **Alternating** | Shift focus between tasks | Moderate |

### 5.2 Design Guidelines

#### Salience Optimization
- Maximum target-to-distractor contrast ratio (minimum 3:1)
- Use motion sparingly — motion should indicate relevance, not novelty
- Implement peripheral cues that draw attention to targets without startling
- Provide visual anchoring points to reduce search complexity

#### Effort Reduction
- Minimize gaze shifts required for essential information
- Use spatial consistency (predictable information locations)
- Implement smooth pursuit rather than discrete gaze shifts
- Provide redundant cues (spatial + temporal + color)

#### Expectancy Enhancement
- Provide clear task onset signals
- Use predictable reward timing intervals (2-5 seconds for immediate feedback)
- Signal task transitions explicitly before they occur
- Maintain task continuity to reduce re-orienting overhead

#### Value Enhancement
- Implement immediate positive feedback for task-relevant behaviors
- Use varied reward modalities (visual, auditory, haptic)
- Connect in-context rewards to meaningful outcomes
- Avoid over-reliance on external rewards that reduce intrinsic motivation

### 5.3 Interface Specifications

#### Visual Design
- **Element sizing:** Minimum 1.5° visual angle for critical elements
- **Color coding:** Maximum 4 categories; avoid red/green as only distinguishers
- **Spacing:** Minimum 2x element width between interactive elements
- **Text:** Sans-serif, minimum 16pt equivalent at comfortable viewing distance

#### Temporal Design
- **Feedback latency:** <100ms for all interactions
- **Transition timing:** 500ms minimum for non-critical transitions, 1500ms for task changes
- **Session duration:** Maximum 20 minutes continuous use for AR, 30 minutes for VR
- **Break intervals:** Mandatory breaks every 20 minutes (matching attentional cycles)

#### Sensory Design
- **Audio:** Non-speech sounds for feedback, speech for navigation
- **Haptic:** Proprioceptive feedback for state changes (ADHD may benefit from tactile cueing)
- **Multi-modal redundancy:** Critical alerts should use 2+ modalities

### 5.4 Personalization Requirements

#### ADHD Subtype Considerations
| Subtype | Primary Needs | Design Emphasis |
|---------|-------------|----------------|
| **Predominantly Inattentive** | Focus maintenance, working memory support | External attention cues, reduced memory demands |
| **Predominantly Hyperactive-Impulsive** | Inhibition support, self-monitoring | Response delay options, self-monitoring tools |
| **Combined** | Balanced support | Comprehensive approach addressing both domains |

#### Adaptive Difficulty
- Implement real-time difficulty adjustment based on performance metrics
- Allow clinician oversight of difficulty parameters
- Provide progression paths for extended engagement

### 5.5 Safety Considerations

#### Physical Safety (VR)
- Play space boundary systems required
- Maximum session durations enforced
- Comfort checks between sessions
- Seated play options for users prone to motion sensitivity

#### Cognitive Safety
- Avoid overwhelming sensory loads
- Provide calm/quiet modes with reduced stimulation
- Explicit consent for session start to prevent startling
- Clear exit mechanisms always visible

#### Privacy Considerations
- Minimally necessary data collection
- Transparent data usage policies
- Parental/guardian controls for minors
- Secure storage for sensitive assessment data

---

## 6. Additional AR/VR Systems for ADHD

### 6.1 AugmentedFocus

A mobile AR application for language learning designed specifically for children with ADHD. Uses AR elements to increase engagement and retention in educational activities.

### 6.2 AR-Therapist

Gamified AR paradigm using therapist competency levels to adapt game difficulty in real-time for ADHD children. Combines AR experiences with professional oversight.

### 6.3 BCI-Integrated AR Systems

Research has explored combining brain-computer interfaces (BCI) with AR for ADHD, using visually-evoked potentials through eye blinks and other physiological signals for therapeutic intervention.

### 6.4 Exergaming Systems

Xbox Kinect-based interventions combining physical exercise with game mechanics to improve executive functions in ADHD children. Demonstrated improvements in inhibition, switching, and updating.

---

## 7. Research Gaps and Future Directions

### 7.1 Identified Gaps

1. **Long-term efficacy data** — Most studies report short-term improvements; longitudinal data is limited
2. **Transfer effects** — Whether in-context gains transfer to daily functioning
3. **Individual difference moderators** — Understanding which ADHD subtypes benefit most from specific interventions
4. **Neural mechanisms** — Limited understanding of how AR/VR interventions produce their effects

### 7.2 Promising Directions

1. **AI-personalized interventions** — Real-time adaptation based on physiological and behavioral markers
2. **Multi-modal integration** — Combining AR/VR with other modalities (auditory, haptic)
3. **Ecological momentary assessment** — Using AR/VR for real-world monitoring
4. **Hybrid interventions** — Combining digital and human-delivered support

---

## 8. References

1. Wickens, C.D. (2015). Noticing events in the visual workplace: The SEEV and N-SEEV models. *Cambridge Handbook of Applied Perception Research*, 749-768.

2. Bzostek, J. (2009). N-SEEV: A Computational Model of Attention and Noticing. *Proceedings of the Human Factors and Ergonomics Society Annual Meeting*.

3. Happel, O. et al. (2021). The Effect of Effort on the Allocation of Visual Attention. *Proceedings of the Human Factors and Ergonomics Society*.

4. FocusViz Research Team. (2024). FocusViz: An Interactive Gaze-Based Framework to Enhance Attention in Pervasive Augmented Reality for Individuals with ADHD. *IEEE ISMAR 2024*.

5. Sahin, N.T. et al. (2019). Digital Attention-Related Augmented-Reality Game. *Sustainability*, 6(6), 72.

6. FocusVR Research Team. (2025). FocusVR: A Video Game Designed to Enhance Concentration in Children with ADHD. *New Challenges in Software Engineering*, Springer.

7. Cogleap Research Team. (2024). Hope Focus System (HFS) Research & Results. *Cogleap Technical Documentation*.

8. Rizzo, A.S. et al. (2024). vCAT Virtual Reality Attention and Self-Control Assessment System. *USC Institute for Creative Technologies*.

9. Understood.org. (2024). Assistive Technology Resources and AI Tools for ADHD. *Understood Technical Reports*.

10. arXiv:2405.01218. (2024). Attention and Sensory Processing in Augmented Reality: Empowering ADHD Population. *arXiv preprint*.

---

*Document compiled for research purposes. Last updated May 2026.*