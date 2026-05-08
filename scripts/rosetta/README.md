# Rosetta Negative Examples for LoRA Training

This directory contains negative examples for tool discrimination training, based on research from **ToolFormer**, **ToolLLM**, and **NexusRaven**.

## Research Background

### ToolFormer Methodology
- Include irrelevant candidate functions so model learns to discriminate
- Negative examples show tools that should NOT be called for given requests
- Helps model distinguish when tool calling is appropriate vs. direct answering

### NexusRaven Approach  
- Include distractor tools similar to correct tool
- Forces model to learn subtle differences between tool purposes
- Improves tool selection accuracy in ambiguous scenarios

### Why Negative Examples Matter
1. **Tool Discrimination**: Model learns to NOT call tools when unnecessary
2. **Error Prevention**: Reduces false positive tool calls
3. **Distractor Resistance**: Model ignores similar-but-wrong tools
4. **Appropriate Response**: Knows when to answer directly vs. use tools

## Files

### `negative_examples.json`
75 negative examples covering these categories:

| Category | Count | Description |
|----------|-------|-------------|
| Knowledge questions (no tool needed) | 7 | Questions model can answer directly |
| Wrong tool selected | 20+ | Similar but incorrect tool choice |
| Context required | 10+ | Can't execute without more info |
| Ambiguous requests | 5+ | Could mean multiple things |

**Structure:**
```json
{
  "negative_examples": [
    {
      "id": "neg_001",
      "user_request": "What is the weather today?",
      "correct_tool": null,
      "distractor_tools": ["read_file", "git_commit", "github_create_issue"],
      "reason": "This is a knowledge question..."
    }
  ]
}
```

### `generate_training_data.py`
Script to generate mixed positive/negative training data.

**Usage:**
```bash
# Generate default 1000 examples (70% positive, 30% negative)
python scripts/rosetta/generate_training_data.py

# Custom ratio
python scripts/rosetta/generate_training_data.py --ratio 0.8 --total 2000

# With JSON output for inspection
python scripts/rosetta/generate_training_data.py --json-output datasets/inspection.json
```

**Output Format:**
```json
{
  "input": "read README.md",
  "output": "[TOOL_CALL]{tool => \"read_file\", args => { --path \"README.md\" }}[/TOOL_CALL]",
  "tool": "read_file",
  "args": {"path": "README.md"},
  "type": "positive"
}
```

## Available Tool Names

The examples use real MCP tool names from `opencode.json`:

### Filesystem
- `read_file`, `write_file`, `glob`, `grep`, `edit`

### Git
- `git_status`, `git_log`, `git_diff`, `git_branch`, `git_commit`
- `git_merge`, `git_pull`, `git_push`, `git_reset`, `git_rebase`
- `git_stash`, `git_blame`, `git_bisect`

### GitHub
- `github_search_repositories`, `github_list_issues`, `github_search_code`
- `github_create_issue`, `github_create_pull_request`, `github_get_file_contents`

### Web
- `webfetch`, `websearch`, `context7_query-docs`

### Memory
- `unified-memory_search_memories`, `unified-memory_memory_write`
- `unified-memory_get_memory_stats`

### Sessions
- `session_list`, `session_search`, `session_info`

### Intelligence
- `intelligence_route`, `intelligence_score_complexity`, `intelligence_available_agents`

### Quality Gates
- `quality-gates_run_typecheck`, `quality-gates_run_lint`, `quality-gates_run_tests`
- `quality-gates_run_all_gates`, `quality-gates_run_secrets`

### Other
- `lsp_goto_definition`, `lsp_find_references`, `lsp_rename`, `lsp_diagnostics`, `lsp_symbols`
- `obsidian_get_file_contents`, `obsidian_simple_search`, `obsidian_append_content`
- `notion_API_post_search`, `notion_API_retrieve_a_page`
- `telegram_send_message`
- `sequential-thinking_sequentialthinking`

## Adding More Examples

To add new negative examples, add to `negative_examples.json`:

```json
{
  "id": "neg_076",
  "user_request": "Your request here",
  "correct_tool": "tool_name or null",
  "distractor_tools": ["distractor1", "distractor2"],
  "reason": "Why this is negative..."
}
```

## Best Practices

1. **Realistic Requests**: Use actual user query phrasings
2. **Clear Reasoning**: Explain WHY tool should/shouldn't be called
3. **Varied Distractors**: Include both obviously wrong and subtly wrong tools
4. **Cover Edge Cases**: Include ambiguous, multi-intent, and context-dependent cases
5. **Balance Categories**: Ensure good coverage of failure modes

## LoRA Training Notes

When training with this data:

1. **Label Format**: Use `type: "positive"` / `type: "negative"` labels
2. **Loss Weighting**: Consider weighting negative examples higher
3. **Batch Mix**: Ensure each batch has mix of positive/negative
4. **Evaluation**: Track tool selection accuracy separately for positive/negative
