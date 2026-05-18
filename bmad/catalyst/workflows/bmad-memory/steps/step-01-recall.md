# Step 1: Memory Recall

## MANDATORY EXECUTION RULES:
- Search Graphiti for context relevant to the current planning phase
- Extract decisions, patterns, and past failures
- Inject context into the planning workflow
- If Graphiti is unavailable, skip gracefully (circuit breaker)

## EXECUTION:

### 1. Extract Keywords
From the user's request, extract 3-5 key terms for search.

### 2. Search Graphiti
```
graphiti_hybrid_search(query=keywords, max_results=5)
```

### 3. Format Context
For each result:
- Decision made
- Outcome (success/failure)
- Relevance to current request

### 4. Inject into Planning
Present context as:
```
📚 Relevant Past Context:

[Decision 1]: [Outcome]
[Decision 2]: [Outcome]

Consider these when planning.
```

### 5. Circuit Breaker
If Graphiti timeout > 5s or unavailable:
- Log warning
- Continue without context
- Do NOT block the pipeline
