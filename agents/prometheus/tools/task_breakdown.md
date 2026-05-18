---
status: aspirational
---

# task_breakdown (FUTURE — NOT IMPLEMENTED)

This tool does not exist yet. Break down tasks manually:

```
├─ Goal: "Build X"
│  ├─ Task 1: "Create Y" [depends: none]
│  │  └─ Verify: "Y exists and passes tests"
│  ├─ Task 2: "Create Z" [depends: 1]
│  │  └─ Verify: "Z integrates with Y"
│  └─ Task 3: "Wire X" [depends: 2]
│     └─ Verify: "End-to-end X works"
```
