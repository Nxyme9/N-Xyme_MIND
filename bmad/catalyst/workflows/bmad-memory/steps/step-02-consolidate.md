# Step 2: Memory Consolidation

## MANDATORY EXECUTION RULES:
- Extract key decisions from pipeline execution
- Store as Graphiti episodes
- Tag with pipeline run ID
- Batch insert for efficiency

## EXECUTION:

### 1. Collect Pipeline Outputs
Gather artifacts from all phases:
- Analysis: research findings
- Planning: product brief, PRD decisions
- Solutioning: architecture decisions
- Execution: implementation patterns
- Review: Oracle/Momus findings

### 2. Extract Episodes
For each phase output:
```
episode = {
    "name": "[Phase] - [Decision/Pattern]",
    "episode_body": "[What was decided/learned]",
    "source": "pipeline",
    "group_id": pipeline_run_id,
    "reference_time": timestamp
}
```

### 3. Store to Graphiti
```
graphiti_add_episode(
    name=episode["name"],
    episode_body=episode["episode_body"],
    source="pipeline",
    group_id=pipeline_run_id
)
```

### 4. Log Results
```
✅ Stored N episodes to Graphiti for pipeline [run_id]
```
