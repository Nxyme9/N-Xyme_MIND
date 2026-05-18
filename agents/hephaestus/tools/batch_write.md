# batch_write
**Purpose:** Generate MULTIPLE code files from a single specification.
**Usage:** `batch_write("create a logger module with handler + formatter + config")`
**Returns:** Status per file — queued, written, verified.
**Optimized for:** Builder — generates production-ready Mojo/Python/Rust code.
**Workflow:** Spec → generate each file → code_review each → fix issues → done.
