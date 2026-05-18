# code_search
**Purpose:** Find relevant code files by MEANING, not just keywords.
**Usage:** `code_search("routing engine error handling")`
**Returns:** Ranked file paths with relevance scores and summaries.
**Optimized for:** Builder — focuses on `.mojo`, `.py`, `.rs` files, skips configs/docs.
**Examples:**
  - `code_search("pattern for handling errors in Mojo")` → files with error handling patterns
  - `code_search("batch processing implementation")` → files that process data in batches
  - `code_search("memory vector storage")` → files related to memory/embedding storage
