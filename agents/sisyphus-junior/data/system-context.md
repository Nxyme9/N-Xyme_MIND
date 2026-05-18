# Sisyphus Junior — System Context

## Delegation Flow
- Spawned by: Sisyphus (via delegate_task or call_omo_agent)
- Inherits session identity via parentID
- Parent session ID available in context

## Common Patterns
- Simple edits: file_read → file_edit → verify_code
- New files: file_write → bash("cargo check")
- Config changes: file_read → file_edit → validate

## Model Constraints
- minimax-m2.5-free: 204K context / 65K output
- For tasks exceeding 3 files or complex logic → delegate to Hephaestus
