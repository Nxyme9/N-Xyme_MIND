# quality_check
**Purpose:** Run fmt → lint → test → audit in one combined gate.
**Usage:** `quality_check("path/to/file.mojo")`
**Optimized for:** Builder — catches issues BEFORE commit.
**Returns:** Pass/fail per gate with fix suggestions.
