---
description: Integrate NotebookLM as a dynamic research backend for Athena
created: 2026-02-27
last_updated: 2026-02-27
---

# /notebooklm-bridge — Dynamic Context Injection

> **Latency Profile**: HIGH (External Context Shift)
> **Philosophy**: Use NotebookLM as a pre-computed exocortex for thick context (resumes, project docs, massive PDFs).

## Trigger

User provides a NotebookLM project or asks to use NotebookLM context with a specific goal (e.g., "Build a portfolio using my NotebookLM info").

## The Pattern (Stolen from @ZinhoAutomates)

Instead of feeding raw, zero-context prompts to Athena, we use Google's NotebookLM to synthesize massive document dumps into structured data.

### Phase 1: Context Priming (The "Data Dump")

1. Create a new notebook in NotebookLM.
2. Upload all foundational documents:
   - Resumes / CVs
   - Project documentation / READMEs
   - Target audience profiles
   - Competitor references
3. Let NotebookLM index the corpus.

### Phase 2: The Direct Bridge Request

Prompt Athena with the active context connection:
> "Create a [deliverable type: e.g., detailed portfolio website] based on the [notebook name] notebook from NotebookLM."

*Why this works*: Athena pulls the *synthesized* reality from the Notebook instead of hallucinating.

### Phase 3: The Multi-Agent Split (Agent Manager)

Instead of linear execution, deploy parallel agents for complex builds:

- **Agent A (Research)**: "Create a new notebook in NotebookLM about the top 3 SaaS competitors."
- **Agent B (Execution)**: "Start scaffolding the SaaS landing page structure while Agent A completes the research."

### Phase 4: The Visual Ingestion Hack

When Athena needs to analyze video inputs (since it prefers image inputs for now):

1. Extract frames: Convert the target video into a `.jpg` sequence.
2. Feed the image sequence to Athena.
3. Prompt: "Add the hero image sequence, project thumbnails, and about section image. Match color scheme."

## Workflow Application

When a user requests a complex web build (portfolio, dashboard) but provides sparse local context:

1. **Instruct** the user to drop their life/project history into NotebookLM.
2. **Connect** Athena to the Notebook.
3. **Execute** the build using the pre-digested NotebookLM summary as the primary instruction source.

## Tagging

# workflow #notebooklm #integration #multi-agent #context-bridge
