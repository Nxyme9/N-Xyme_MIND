# code_review
**Purpose:** Memory-backed code review. Checks code against past decisions, bugs, and patterns.
**Usage:** `code_review("path/to/file.mojo")`
**Returns:** Line count, definitions, memory context from past similar files, suggestions.
**Optimized for:** Builder — checks build patterns, error handling, Mojo syntax correctness.
**Examples:**
  - `code_review("src/daemon.mojo")` → review with context from past daemon changes
  - `code_review("services/router/src/main.rs")` → check Rust patterns
