# adversarial_review
**Purpose:** DEEP code review — find edge cases, failure modes, security issues, hidden assumptions.
**Usage:** `adversarial_review("path/to/file.mojo", context="check error handling")`
**Optimized for:** Critic — adversarial mindset, worst-case scenarios.
**What it checks:** Edge cases (null/empty/boundary), error handling gaps, race conditions, security holes, assumption violations.
**Returns:** List of issues with severity (critical/warning/info) and fix suggestions.
