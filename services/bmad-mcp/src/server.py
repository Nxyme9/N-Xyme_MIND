#!/usr/bin/env python3
"""BMAD-MCP — Scans SKILL.md files, registers as callable MCP tools.
Each tool, when called, loads the SKILL.md and returns structured instructions.

Supports:
  - bmad/core/skills/*/SKILL.md (19 workflows)
  - bmad/bmm/workflows/*/*/SKILL.md (13 workflows)
  - agents/*/skills/*/SKILL.md (per-agent skills)
  - Keyword auto-trigger: "build" → bmad_dev_story()
"""
import json
import sys
import os
import glob
import re

PROJECT_ROOT = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND"
TEMPLATE_PLACEHOLDER = "{project-root}"

SKILL_ROOTS = [
    os.path.join(PROJECT_ROOT, "bmad/core/skills/*/SKILL.md"),
    os.path.join(PROJECT_ROOT, "bmad/bmm/workflows/*/*/SKILL.md"),
    os.path.join(PROJECT_ROOT, "bmad/tea/workflows/*/*/SKILL.md"),
    os.path.join(PROJECT_ROOT, "agents/*/skills/*/SKILL.md"),
    os.path.join(PROJECT_ROOT, "plugins/*/SKILL.md"),
]

# Keywords that auto-trigger skills
KEYWORD_MAP = {
    "build": "bmad_dev_story",
    "plan": "bmad_create_architecture",
    "brainstorm": "bmad_brainstorming",
    "review": "bmad_code_review",
    "research": "bmad_domain_research",
    "market": "bmad_market_research",
    "technical": "bmad_technical_research",
    "agent": "agent_builder",
    "builder": "agent_builder",
    "prd": "bmad_edit_prd",
    "validate": "bmad_validate_prd",
    "ux": "bmad_create_ux_design",
    "architecture": "bmad_create_architecture",
    "epic": "bmad_create_epics_and_stories",
    "readiness": "bmad_check_implementation_readiness",
    "sprint": "bmad_sprint_planning",
    "retro": "bmad_retrospective",
    "orchestrate": "nx_sisyphus_orchestrate",
    "delegate": "nx_sisyphus_orchestrate",
    "build_tool": "nx_hephaestus_build",
    "hotload": "nx_hephaestus_hotload",
    "quality": "nx_hephaestus_quality_gates",
    "memory": "bmad_memory_consolidate",
    "recall": "bmad_memory_recall",
    "search": "bmad_memory_search",
    "distill": "bmad_distillator",
    "shard": "bmad_shard_doc",
    "prose": "bmad_editorial_review_prose",
    "structure": "bmad_editorial_review_structure",
    "document": "bmad_document_project",
    "context": "bmad_generate_project_context",
    "test_plan": "bmad_testarch_test_design",
    "test_strategy": "bmad_testarch_test_design",
    "guide": "bmad_index_docs",
    "product_brief": "bmad_create_product_brief",
    "opgrade": "nx_total_opgrade",
    "upgrade": "nx_total_opgrade",
    "refit": "nx_total_opgrade",
    "gap": "nx_total_opgrade",
    "bleeding": "nx_total_opgrade",
}

# Cache for scanned skills
_skills_cache = None

def _parse_skill_md(path):
    """Parse a SKILL.md file to extract name, description, and content."""
    with open(path, encoding="utf-8") as f:
        content = f.read()

    # Extract YAML frontmatter
    name = os.path.basename(os.path.dirname(path))
    description = "Skill workflow"

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            body = parts[2]
            for line in frontmatter.split("\n"):
                if line.startswith("name:"):
                    name = line.split(":", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("description:"):
                    description = line.split(":", 1)[1].strip().strip('"').strip("'")
            content = body
        else:
            body = parts[1] if len(parts) > 1 else content
            content = body
    else:
        body = content
        content = body

    # Clean name for MCP tool format
    tool_name = name.lower().replace("-", "_").replace(" ", "_").replace("/", "_")
    return tool_name, description, content, path

def scan_skills(force=False):
    """Scan all SKILL.md files and build tool definitions."""
    global _skills_cache
    if _skills_cache is not None and not force:
        return _skills_cache

    tools = {}
    for pattern in SKILL_ROOTS:
        for skill_path in glob.glob(pattern):
            try:
                tool_name, description, content, path = _parse_skill_md(skill_path)
                content = content.replace(TEMPLATE_PLACEHOLDER, PROJECT_ROOT)
                description = description.replace(TEMPLATE_PLACEHOLDER, PROJECT_ROOT)
                tools[tool_name] = {
                    "name": tool_name,
                    "description": description[:200],
                    "path": path,
                    "content": content[:500],  # Content preview for tool definition
                }
            except Exception as e:
                print(f"[bmad-mcp] Error parsing {skill_path}: {e}", file=sys.stderr)

    _skills_cache = tools
    return tools

def handle_initialize():
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {"tools": {}},
        "serverInfo": {"name": "bmad-mcp", "version": "0.1.0"}
    }

def handle_tools_list():
    tools = scan_skills()
    return {
        "tools": [
            {
                "name": name,
                "description": info["description"],
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "description": f"Path: {info['path']}"
                }
            }
            for name, info in tools.items()
        ]
    }

def handle_tool_call(name, arguments):
    tools = scan_skills()
    tool = tools.get(name)
    if not tool:
        # Check keyword map
        for keyword, mapped_name in KEYWORD_MAP.items():
            if keyword in name or keyword in arguments.get("query", "").lower():
                mapped = tools.get(mapped_name)
                if mapped:
                    return {"content": [{"type": "text", "text": f"Auto-triggered: {mapped_name}\n\n{mapped['content'][:2000]}"}]}
        return {"content": [{"type": "text", "text": f"Unknown skill: {name}"}]}

    # Load full content
    with open(tool["path"], encoding="utf-8") as f:
        full_content = f.read()

    # Resolve {project-root} template variable
    full_content = full_content.replace(TEMPLATE_PLACEHOLDER, PROJECT_ROOT)

    return {
        "content": [{"type": "text", "text": f"# {tool['name']}\n\n{tool['description']}\n\n---\n\n{full_content}"}]
    }

def main():
    # Pre-scan skills on startup
    count = len(scan_skills(force=True))
    print(f"[bmad-mcp] Loaded {count} skills", file=sys.stderr)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            method = request.get("method", "")
            req_id = request.get("id", None)

            if method == "initialize":
                result = handle_initialize()
            elif method == "tools/list":
                result = handle_tools_list()
            elif method == "tools/call":
                params = request.get("params", {})
                result = handle_tool_call(params.get("name", ""), params.get("arguments", {}))
            else:
                result = {"error": f"Unknown method: {method}"}

            response = {"jsonrpc": "2.0", "id": req_id, "result": result}
            print(json.dumps(response), flush=True)
        except Exception as e:
            error_response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(e)}}
            print(json.dumps(error_response), flush=True)

if __name__ == "__main__":
    main()
