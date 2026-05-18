# Agent Edit Tool — Design Specification

**Goal:** A single MCP tool optimized for editing agent files (agent.js, SKILL.md, workflow.md, tools.json) with maximum speed and zero quality loss.

**Key Insight:** Generic edit tools require read → find oldString → replace → validate (4 tool calls per edit). Agent Edit parses the file structure once, allows targeted section edits, and validates automatically (1 tool call per edit).

---

## TOOL DEFINITION

```json
{
  "name": "agent_edit",
  "description": "Surgical edit tool for agent files. Parses structure, edits sections, validates automatically. Handles agent.js, SKILL.md, workflow.md, tools.json. 1 call = read+edit+validate.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "operation": {
        "type": "string",
        "enum": [
          "read_agent",
          "edit_section",
          "add_section",
          "remove_section",
          "edit_prompt_section",
          "add_skill",
          "remove_skill",
          "edit_tools",
          "edit_config",
          "batch_edit",
          "validate_agent"
        ],
        "description": "Operation to perform"
      },
      "agent": {
        "type": "string",
        "description": "Agent name (e.g., 'Scalpel', 'Sisyphus')"
      },
      "file_type": {
        "type": "string",
        "enum": ["agent.js", "SKILL.md", "workflow.md", "tools.json"],
        "description": "File type to edit (auto-detected from operation)"
      },
      "skill_name": {
        "type": "string",
        "description": "Skill name for SKILL.md/workflow.md operations"
      },
      "section": {
        "type": "string",
        "description": "Section name for section-based edits (identity, protocol, rules, tools, quality_gate, classify, constraints, techniques)"
      },
      "content": {
        "type": "string",
        "description": "New content for the section or skill"
      },
      "skill_key": {
        "type": "string",
        "description": "Skill key to add/remove (e.g., 'bmad-code-review')"
      },
      "tools_allowed": {
        "type": "array",
        "items": {"type": "string"},
        "description": "New allowed tools list (for edit_tools operation)"
      },
      "tools_blocked": {
        "type": "array",
        "items": {"type": "string"},
        "description": "New blocked tools list (for edit_tools operation)"
      },
      "config_key": {
        "type": "string",
        "description": "Config key to edit (name, mode, model, description, color)"
      },
      "config_value": {
        "type": "string",
        "description": "New config value"
      },
      "batch": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "agent": {"type": "string"},
            "operation": {"type": "string"},
            "section": {"type": "string"},
            "content": {"type": "string"},
            "skill_key": {"type": "string"},
            "config_key": {"type": "string"},
            "config_value": {"type": "string"}
          }
        },
        "description": "Batch operations for batch_edit"
      },
      "validate": {
        "type": "boolean",
        "default": true,
        "description": "Auto-validate after edit (default: true)"
      }
    },
    "required": ["operation"]
  }
}
```

---

## OPERATIONS

### 1. `read_agent` — Parse agent structure (1 call)

```python
agent_edit(operation="read_agent", agent="Scalpel")
```

**Returns:**
```json
{
  "name": "Scalpel - Code Surgeon",
  "mode": "primary",
  "color": "#FF5722",
  "model": "opencode/qwen3.6-plus-free",
  "description": "Code surgeon...",
  "skills": ["scalpel-method", "bmad-create-architecture", ...],
  "sections": {
    "identity": "You are SCALPEL...",
    "context": "You operate in the N-Xyme ecosystem...",
    "mission": "When you dissect something...",
    "protocol": "PHASE 1 — MAP...",
    "anti_hallucination": "These are hard rules...",
    "decompiler": "When given something unknown...",
    "frankenstein": "Stitching code from multiple sources...",
    "quality_gate": "Before done:..."
  },
  "tools": {"allowed": ["bash", "write", "edit", "read", "glob", "grep"], "blocked": []},
  "format": "export_default",
  "line_count": 136
}
```

**Speed:** 1 tool call (reads agent.js + tools.json + config entry in parallel)

---

### 2. `edit_section` — Edit a specific section of agent.js prompt (1 call)

```python
agent_edit(
  operation="edit_section",
  agent="Scalpel",
  section="anti_hallucination",
  content="New anti-hallucination rules here...",
  validate=True
)
```

**What it does:**
1. Reads agent.js
2. Parses the prompt into sections (auto-detects section boundaries via markdown headings)
3. Replaces the target section content
4. Reconstructs the full agent.js with export default wrapper intact
5. Validates: JS syntax check, section count, anti-hallucination presence
6. Writes back

**Speed:** 1 tool call (read + parse + edit + validate + write)

---

### 3. `edit_prompt_section` — Edit a specific section within the prompt text

```python
agent_edit(
  operation="edit_prompt_section",
  agent="Scalpel",
  section="quality_gate",
  content="Before done:\n- Compiles clean\n- Tests pass\n- Sentinel verification passed"
)
```

**Difference from `edit_section`:** This edits the content WITHIN a section (replaces the entire section body), while `edit_section` can also add/remove sections.

---

### 4. `add_skill` — Add a skill to agent's skills array (1 call)

```python
agent_edit(operation="add_skill", agent="Sisyphus", skill_key="bmad-catalyst-orchestration")
```

**What it does:**
1. Reads agent.js
2. Parses skills array
3. Adds skill if not already present
4. Writes back
5. Validates: skills array is valid JSON, skill exists in bmad/core/skills or agents/*/skills

**Speed:** 1 tool call

---

### 5. `remove_skill` — Remove a skill from agent's skills array (1 call)

```python
agent_edit(operation="remove_skill", agent="Sisyphus", skill_key="bmad-retrospective")
```

---

### 6. `edit_tools` — Edit tools.json allowed/blocked lists (1 call)

```python
agent_edit(
  operation="edit_tools",
  agent="Explore",
  tools_allowed=["bash", "read", "glob", "grep"],
  tools_blocked=["write", "edit"]
)
```

**Validates:** Every tool in allowed exists in at least one MCP server. No tool in both allowed and blocked.

---

### 7. `edit_config` — Edit agent config entry in opencode.json (1 call)

```python
agent_edit(
  operation="edit_config",
  agent="Scalpel",
  config_key="model",
  config_value="opencode/qwen3.6-plus-free"
)
```

**What it does:**
1. Reads opencode.json
2. Finds agent entry by name
3. Updates the specified key
4. Writes back
5. Validates: config structure is valid

---

### 8. `batch_edit` — Multiple edits in 1 call (1 call for N edits)

```python
agent_edit(
  operation="batch_edit",
  batch=[
    {"agent": "Scalpel", "operation": "add_skill", "skill_key": "bmad-code-review"},
    {"agent": "Kairos", "operation": "add_skill", "skill_key": "nx-kairos-therapy"},
    {"agent": "Sisyphus", "operation": "add_skill", "skill_key": "bmad-brainstorming"},
    {"agent": "Sisyphus", "operation": "add_skill", "skill_key": "bmad-technical-research"},
  ],
  validate=True
)
```

**Speed:** 1 tool call for N edits. Reads all files, applies all changes, validates all, writes all.

---

### 9. `validate_agent` — Validate agent structure without editing (1 call)

```python
agent_edit(operation="validate_agent", agent="Scalpel")
```

**Returns:**
```json
{
  "agent": "Scalpel - Code Surgeon",
  "valid": true,
  "checks": {
    "js_syntax": "pass",
    "export_default_format": "pass",
    "has_identity": "pass",
    "has_rules": "pass",
    "has_anti_hallucination": "pass",
    "has_quality_gate": "pass",
    "has_classify": "pass",
    "tools_exist": "pass",
    "tools_disjoint": "pass",
    "config_matches": "pass",
    "skills_exist": "pass",
    "prompt_under_150_lines": "pass"
  },
  "warnings": ["Prompt is 136 lines, approaching 150 line limit"],
  "errors": []
}
```

---

## SECTION DETECTION ALGORITHM

For `agent.js` files, sections are detected by markdown headings within the prompt:

```python
def parse_agent_sections(prompt_text):
    """Parse agent.js prompt into sections based on markdown headings."""
    sections = {}
    current_section = "preamble"
    current_content = []
    
    for line in prompt_text.split('\n'):
        if line.startswith('## '):
            # Save previous section
            if current_content:
                sections[current_section] = '\n'.join(current_content).strip()
            # Start new section
            current_section = line[3:].lower().replace(' ', '_').replace('—', '_').replace('-', '_')
            current_content = []
        else:
            current_content.append(line)
    
    # Save last section
    if current_content:
        sections[current_section] = '\n'.join(current_content).strip()
    
    return sections
```

**Standard section names:**
- `preamble` — Opening paragraph (IDENTITY)
- `your_role` — Role definition
- `tools` — Tool descriptions
- `protocol` / `core_protocol` / `execution_protocol` — Phased methodology
- `rules` / `hard_rules` / `constraints` — Hard constraints
- `anti_hallucination` / `anti_hallucination_rules` — Anti-hallucination rules
- `classify` — Classification variants
- `techniques` — Domain-specific techniques
- `quality_gate` — Verification checklist
- `context` / `our_context` — Ecosystem context
- `mission` / `your_mission` — Mission statement

---

## VALIDATION CHECKS

After every edit, run these checks:

```python
def validate_agent_edit(agent_name, file_type, changes):
    """Validate agent structure after edit."""
    checks = {}
    
    if file_type == "agent.js":
        # 1. JS syntax check
        checks["js_syntax"] = check_js_syntax(agent_js_content)
        
        # 2. Export default format
        checks["export_default_format"] = "export default {" in agent_js_content and "}" at end
        
        # 3. Required sections
        checks["has_identity"] = "IDENTITY" in content or "You are" in content
        checks["has_rules"] = "RULES" in content or "CONSTRAINTS" in content
        checks["has_anti_hallucination"] = "hallucinat" in content.lower() or "don't invent" in content.lower()
        checks["has_quality_gate"] = "QUALITY GATE" in content or "Quality Gate" in content
        checks["has_classify"] = "CLASSIFY" in content or "[quick" in content
        
        # 4. Tools validation
        checks["tools_exist"] = all_tools_exist_in_mcp(tools_allowed)
        checks["tools_disjoint"] = len(set(tools_allowed) & set(tools_blocked)) == 0
        
        # 5. Config match
        checks["config_matches"] = agent_name_in_config(agent_name, opencode_config)
        
        # 6. Skills validation
        checks["skills_exist"] = all_skills_exist(skills_list)
        
        # 7. Prompt length
        checks["prompt_under_150_lines"] = prompt_line_count < 150
    
    elif file_type == "SKILL.md":
        checks["has_frontmatter"] = content.startswith("---")
        checks["has_name"] = "name:" in frontmatter
        checks["has_description"] = "description:" in frontmatter
        checks["has_workflow"] = "## " in content
    
    elif file_type == "tools.json":
        checks["valid_json"] = json.loads(content) is valid
        checks["tools_exist"] = all_tools_exist_in_mcp(allowed)
        checks["tools_disjoint"] = len(set(allowed) & set(blocked)) == 0
    
    return {
        "valid": all(checks.values()),
        "checks": checks,
        "warnings": [k for k, v in checks.items() if v == "warning"],
        "errors": [k for k, v in checks.items() if v == "fail"]
    }
```

---

## PERFORMANCE COMPARISON

| Task | Generic Tools | Agent Edit | Speedup |
|------|--------------|------------|---------|
| Read agent structure | 3 calls (read agent.js + read tools.json + read config) | 1 call | **3x** |
| Edit one section | 3 calls (read + edit + validate) | 1 call | **3x** |
| Add skill to 4 agents | 12 calls (4× read + 4× edit + 4× validate) | 1 call (batch) | **12x** |
| Validate agent | 2 calls (read + grep checks) | 1 call | **2x** |
| Edit tools.json + validate | 3 calls (read + edit + validate) | 1 call | **3x** |
| Full agent audit | 5+ calls | 1 call | **5x+** |

---

## IMPLEMENTATION

Add to `services/megatool-mcp/server.py`:

1. Add tool definition to `ALL_TOOLS`
2. Add handler function `handle_agent_edit`
3. Add to `ADMIN_DISPATCH`

The handler uses:
- `re` for parsing markdown sections
- `json` for tools.json and config
- `subprocess` for JS syntax validation (node -c)
- `os` for file existence checks

---

## EDGE CASES HANDLED

1. **Plain text agent.js** (no export default): Auto-detect format, handle accordingly
2. **Multiple sections with same name**: Use first match, warn about duplicates
3. **Section not found**: Return error with available section names
4. **Skill already exists**: No-op, return "already present"
5. **Tool doesn't exist in MCP**: Validation error, reject edit
6. **Batch edit partial failure**: Apply successful edits, report failures
7. **Concurrent edits**: File locking via atomic write (write to temp, rename)

---

## SAFETY

1. **Atomic writes**: Write to `.tmp` file, then `os.rename()` (atomic on Linux)
2. **Backup**: Copy original to `agents/<name>/.backup/<timestamp>.agent.js` before edit
3. **Rollback**: If validation fails after write, restore from backup
4. **Permission check**: Only allow edits to agents the calling agent has permission to modify
5. **No permanent deletes**: Backups are never auto-deleted
