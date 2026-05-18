# Step 1: State Detection

**Goal:** Detect user state and classify as FLOW, FRICTION, or ADAPT

---

## User State Classification

Analyze the user's input to determine their current state:

### FLOW State
User is in a productive flow and wants to:
- Continue working on existing tasks
- Execute known operations
- Make progress without blockers

**Indicators:**
- Clear, direct requests
- Specific implementation tasks
- Known workflow patterns
- No expressed frustration or uncertainty

### FRICTION State
User is experiencing friction and needs:
- Problem diagnosis
- Debugging assistance
- Resolution of blockers
- Error handling guidance

**Indicators:**
- Error messages or exceptions
- Questions about failures
- "Why isn't this working?"
- Frustration indicators
- Stuck or blocked language

### ADAPT State
User needs to adapt or pivot:
- New feature requests
- Architecture changes
- Learning new patterns
- Exploring new approaches
- Refactoring or restructuring

**Indicators:**
- "How do I..."
- "What's the best way to..."
- New requirements
- Change requests
- Exploration language

---

## Execution

<step n="1.1" goal="Analyze user input">
<action>Analyze the user's message for state indicators</action>
<action>Classify as FLOW, FRICTION, or ADAPT</action>
<action>Store classification as {{user_state}}</action>
</step>

<step n="1.2" goal="Extract context factors">
<action>Identify relevant context from activeContext.md</action>
<action>Check session history for recent operations</action>
<action>Determine if state is mixed (e.g., FRICTION trying to do new feature)</action>
</step>

<step n="1.3" goal="Confirm state classification">
<action>Present classification to user for confirmation</action>
<action>If user corrects, update {{user_state}} accordingly</action>
</step>

---

## Output

- **user_state:** FLOW | FRICTION | ADAPT
- **confidence:** high | medium | low
- **factors:** [list of key factors that led to classification]