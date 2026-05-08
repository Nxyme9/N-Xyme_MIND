# Acceptance Tests for Orchestration Fixes

All tests follow Gherkin format (Given/When/Then) with clear acceptance criteria and edge cases.

---

## Feature 1: Zombie Task Protection

**Story**: Ensure failed tasks show error status instead of becoming zombies

### Scenario 1.1: Task fails and shows error status

```gherkin
Given a task is submitted to the orchestrator
When the task execution fails with an exception
Then the task status should be "error"
And the task should have an error message
And the task should not remain in "pending" or "running" state
```

### Scenario 1.2: Task timeout shows error status

```gherkin
Given a task is submitted to the orchestrator
When the task execution exceeds the timeout limit
Then the task status should be "error"
And the error message should indicate "timeout"
```

### Scenario 1.3: Zombie task detection - no heartbeat

```gherkin
Given a task is in "running" state
When the worker stops sending heartbeats for more than 60 seconds
Then the task should be marked as "error"
And a zombie task alert should be logged
```

### Edge Cases

```gherkin
# Edge Case 1.4: Task fails after partial completion
Given a task has completed 50% of its work
When the worker crashes unexpectedly
Then the task status should be "error"
And the partial progress should be recorded

# Edge Case 1.5: Network failure during task execution
Given a task is executing
When network connectivity is lost
Then the task status should be "error"
And the error should indicate "connection lost"

# Edge Case 1.6: Multiple rapid failures
Given multiple tasks are submitted simultaneously
When all of them fail due to a system issue
Then each failed task should have independent error status
And no task should block another from being marked as error
```

---

## Feature 2: Memory Injection Timeout

**Story**: Ensure memory injection times out after 5 seconds to prevent blocking

### Scenario 2.1: Memory injection times out at 5 seconds

```gherkin
Given a task requires memory injection
When the memory injection takes longer than 5 seconds
Then the injection should be cancelled
And the task should proceed without injected memory
And a warning should be logged about the timeout
```

### Scenario 2.2: Fast memory injection succeeds

```gherkin
Given a task requires memory injection
When the memory injection completes in under 5 seconds
Then the task should receive the injected context
And execution should continue normally
```

### Edge Cases

```gherkin
# Edge Case 2.3: Memory injection hangs at exactly 5 seconds
Given a memory injection is in progress
When 5 seconds elapse exactly
Then the injection should be cancelled at that moment
And no partial context should be injected

# Edge Case 2.4: Multiple concurrent memory injections
Given multiple tasks require memory injection
When one injection times out
Then other injections should continue independently
And the timed-out task should proceed without memory

# Edge Case 2.5: Memory injection retry after timeout
Given a memory injection timed out
When the same task is retried
Then the system should attempt injection again
And the timeout should apply to each attempt separately
```

---

## Feature 3: Empty Task Validation

**Story**: Ensure empty tasks are rejected before entering the queue

### Scenario 3.1: Empty string task rejected

```gherkin
Given an empty string task is submitted
When the task enters the validation phase
Then the task should be rejected
And an error "Task cannot be empty" should be returned
And the task should not enter the queue
```

### Scenario 3.2: Whitespace-only task rejected

```gherkin
Given a task containing only whitespace is submitted
When the task enters the validation phase
Then the task should be rejected
And an error "Task cannot be empty or whitespace only" should be returned
```

### Scenario 3.3: Valid task accepted

```gherkin
Given a task with actual content is submitted
When the task enters the validation phase
Then the task should be accepted
And the task should enter the queue
```

### Edge Cases

```gherkin
# Edge Case 3.4: None/null task submitted
Given a null task is submitted
Then it should be rejected with error "Task is required"

# Edge Case 3.5: Task with only newlines
Given a task with only "\n\n\n" is submitted
Then it should be rejected as whitespace-only

# Edge Case 3.6: Task with only special characters
Given a task with only "!!!@@@" is submitted
Then it should be accepted (non-whitespace content exists)

# Edge Case 3.7: Unicode whitespace characters
Given a task with only unicode whitespace (e.g., \u3000) is submitted
Then it should be rejected
```

---

## Feature 4: Task Cleanup

**Story**: Ensure old completed tasks are removed after 1 hour

### Scenario 4.1: Old completed task cleaned up after 1 hour

```gherkin
Given a task completed more than 1 hour ago
When the cleanup job runs
Then the task should be removed from the system
And all associated metadata should be deleted
```

### Scenario 4.2: Recent task not cleaned up

```gherkin
Given a task completed less than 1 hour ago
When the cleanup job runs
Then the task should remain in the system
```

### Scenario 4.3: Failed task also cleaned up after 1 hour

```gherkin
Given a task failed more than 1 hour ago
When the cleanup job runs
Then the task should be removed from the system
```

### Edge Cases

```gherkin
# Edge Case 4.4: Task cleanup respects task-specific retention
Given a task has explicit retention of 24 hours
When 1 hour passes
Then the task should NOT be cleaned up
And cleanup should respect the 24-hour retention

# Edge Case 4.5: Running task never cleaned up
Given a task is still in "running" state
When the cleanup job runs
Then the running task should NOT be cleaned up
Even if it has been running for more than 1 hour

# Edge Case 4.6: Batch cleanup of multiple old tasks
Given 100 tasks completed more than 1 hour ago
When the cleanup job runs
Then all 100 tasks should be removed
And the cleanup should complete within reasonable time

# Edge Case 4.7: Cleanup should not affect tasks from today
Given a task completed 59 minutes ago
When the cleanup job runs
Then the task should remain (1 hour threshold not met)
```

---

## Feature 5: Retry Logic

**Story**: Ensure API failures retry up to 3 times before giving up

### Scenario 5.1: API call succeeds on first try

```gherkin
Given an API call is made
When the call succeeds on the first attempt
Then the result should be returned immediately
And no retries should occur
```

### Scenario 5.2: API call fails and retries 3 times then succeeds

```gherkin
Given an API call is made
When the first attempt fails with a transient error
Then the system should retry up to 3 times
And if one of the retries succeeds, return the result
And log that retry was successful
```

### Scenario 5.3: API call fails all 3 retries and returns error

```gherkin
Given an API call is made
When all 3 attempts fail with transient errors
Then the system should return a final error
And indicate "max retries exceeded"
And log the failure
```

### Edge Cases

```gherkin
# Edge Case 5.4: Non-transient error does not retry
Given an API call fails with a non-transient error (e.g., 400 Bad Request)
When the call is made
Then no retries should occur
And the error should be returned immediately

# Edge Case 5.5: Retry respects exponential backoff
Given an API call fails and needs retry
When the retry happens
Then the wait time should increase exponentially (1s, 2s, 4s)
And not retry immediately

# Edge Case 5.6: Retry on timeout errors
Given an API call times out
When the call is made
Then it should retry up to 3 times
And treat timeout as a transient error

# Edge Case 5.7: Retry on rate limit (429)
Given an API call returns 429 Too Many Requests
When the call is made
Then it should retry up to 3 times
And respect the Retry-After header if present

# Edge Case 5.8: Circuit breaker opens after repeated failures
Given an API has failed 5 times in a row
When the next API call is attempted
Then the circuit breaker should open
And fail immediately without retry
And return "circuit breaker open" error
```

---

## Test Implementation Notes

### Test Framework
- Use pytest with pytest-asyncio for async tests
- Fixtures provided by `tests/conftest.py`
- Mock external dependencies (APIs, databases)

### Running Tests

```bash
# Run all orchestration acceptance tests
pytest tests/acceptance/test_orchestration_fixes.py -v

# Run specific feature
pytest tests/acceptance/test_orchestration_fixes.py -k "zombie" -v
```

### Success Criteria
- All scenarios pass
- Edge cases pass
- No regressions in existing tests