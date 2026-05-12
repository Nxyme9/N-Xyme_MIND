# BMAD Workflows

## Overview

BMAD (Build, Manage, Analyze, Deliver) workflows provide structured project execution phases. Located in `_bmad/` directory.

## Workflow Phases

| Phase | Purpose | Workflows |
|-------|---------|-----------|
| 1. Analysis | PRD validation, requirements | bmad-validate-prd, bmad-analyze-requirements |
| 2. Planning | UX design, architecture | bmad-design-ux, bmad-plan-architecture |
| 3. Solutioning | Epic creation, architecture | bmad-create-epics, bmad-solution-architecture |
| 4. Implementation | Sprint, dev, review | bmad-sprint-development, bmad-code-review |
| 5. Test | Test design, CI | bmad-test-architecture, bmad-setup-ci |

## Key Workflows

### bmad-catalyst-orchestration

Main orchestrator workflow that detects user state (FLOW, FRICTION, ADAPT) and routes to appropriate workflow.

### bmad-document-project

Generate project documentation based on current state.

### bmad-generate-project-context

Create context summary from project files.

## Workflow Execution

```python
from catalyst_mcp import execute_workflow

result = execute_workflow(
    workflow_name="bmad-catalyst-orchestration",
    phase="create",
    context={}
)
```

## Related Files

- [[orchestration/catalyst|Catalyst Orchestrator]] - Orchestrates workflow execution
- [[orchestration/bmad/phase_gate|Phase Gate]] - Validates phase transitions