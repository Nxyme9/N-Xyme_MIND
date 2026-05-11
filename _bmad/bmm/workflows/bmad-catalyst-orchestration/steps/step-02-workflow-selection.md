# Step 2: Workflow Selection

**Goal:** Select BMAD workflow based on user intent and detected state

---

## Workflow Selection

Based on user state and intent, select appropriate BMAD workflow:

### For FLOW State
- **Implementation focus:** bmad-quick-flow/bmad-quick-dev
- **Code changes:** Hephaestus delegation
- **Testing:** bmad-qa-generate-e2e-tests

### For FRICTION State
- **Debugging:** recall-project-context or recall-agent-history
- **Investigation:** bmad-quick-flow for diagnosis
- **Resolution:** Hephaestus with focused fix scope

### For ADAPT State
- **New features:** 3-solutioning workflows
- **Architecture:** bmad-create-architecture
- **Planning:** bmad-create-epics-and-stories
- **Analysis:** bmad-document-project or bmad-create-product-brief

---

## Trigger Phrase Mapping

Map user intent to specific workflow triggers:

| User Says | Trigger Phrase | BMAD Workflow |
|-----------|---------------|----------------|
| "catalyst orchestrate" | catalyst | bmad-catalyst-orchestration |
| "delegate to agents" | orchestrate | Workflow selection based on task |
| "run multi-agent workflow" | delegate | Fractal delegation pattern |
| "document this project" | document | bmad-document-project |
| "create tests for..." | qa | bmad-qa-generate-e2e-tests |
| "plan this feature" | plan | bmad-create-epics-and-stories |
| "design architecture" | architecture | bmad-create-architecture |

---

## Execution

<step n="2.1" goal="Match user intent to workflow">
<action>Parse user request for trigger keywords</action>
<action>Match to appropriate BMAD workflow</action>
<action>Store workflow reference as {{selected_workflow}}</action>
</step>

<step n="2.2" goal="Validate workflow exists">
<action>Check {project-root}/_bmad/bmm/workflows/ for workflow existence</action>
<action>If workflow not found, suggest closest match or default to bmad-quick-flow</action>
</step>

<step n="2.3" goal="Extract workflow requirements">
<action>Read SKILL.md from selected workflow</action>
<action>Extract trigger phrases and store as {{trigger_phrases}}</action>
<action>Prepare workflow parameters</action>
</step>

---

## Output

- **selected_workflow:** path to BMAD workflow
- **trigger_phrases:** [list of phrases that trigger this workflow]
- **workflow_params:** {key-value pairs for workflow execution}