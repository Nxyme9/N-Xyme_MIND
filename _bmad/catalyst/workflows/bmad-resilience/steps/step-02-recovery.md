# Step 2: Error Recovery

## MANDATORY EXECUTION RULES:
- Detect failure type
- Apply appropriate recovery strategy
- Log failure to Graphiti
- Continue pipeline if possible

## RECOVERY STRATEGIES:

### Agent Timeout
1. Retry with same agent (max 2 attempts)
2. Fallback to local model
3. Skip with warning

### Model Error (429, 500, etc.)
1. Rotate API key
2. Switch to different model tier (cloud → local)
3. Queue for later execution

### Invalid Output
1. Re-run with additional context
2. Try different agent
3. Flag for human review

### Pipeline Interruption
1. Save current state to Graphiti
2. Log checkpoint
3. Enable resume from last checkpoint

## EXECUTION:

### 1. Detect Failure
```python
if result["status"] == "failed":
    error_type = classify_error(result["error"])
```

### 2. Apply Strategy
```python
strategy = RECOVERY_STRATEGIES[error_type]
recovery_result = await strategy.execute(task, error)
```

### 3. Log to Graphiti
```
graphiti_add_episode(
    name=f"Failure: {task_id}",
    episode_body=f"Error: {error}\nRecovery: {strategy}\nOutcome: {result}",
    source="pipeline"
)
```

### 4. Continue or Halt
- If recovery successful → continue pipeline
- If recovery failed after 3 attempts → halt and notify
