"""CreateMemoryTool — Create a new memory entry."""

from src.orchestration.tool_factory import build_tool, ToolContext, ToolResult
from pathlib import Path
from datetime import datetime
import json
import uuid


@build_tool
class CreateMemoryTool:
    name = "create_memory"
    description = "Create a new memory entry in unified memory system"
    input_schema = {
        "content": {"type": "string", "description": "Memory content text"},
        "kind": {"type": "string", "description": "Memory type", "default": "note"},
        "scope": {"type": "string", "description": "Memory scope", "default": "global"},
        "tags": {"type": "array", "description": "Tags", "optional": True},
        "metadata": {"type": "object", "description": "Metadata", "optional": True},
    }

    def is_read_only(self, input) -> bool:
        return False

    def is_concurrency_safe(self, input) -> bool:
        return True

    async def execute(self, input, context: ToolContext):
        import sqlite3

        content = input.get("content", "")
        kind = input.get("kind", "note")
        scope = input.get("scope", "global")
        tags = input.get("tags")
        metadata = input.get("metadata")

        db_path = (
            Path(__file__).parent.parent.parent
            / "context"
            / "memory"
            / "mind_from_mind.db"
        )

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        memory_id = f"mem_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()
        tags_json = json.dumps(tags) if tags else None
        meta_json = json.dumps(metadata) if metadata else None

        cursor.execute(
            """INSERT INTO memories (id, kind, scope, content, created_at, updated_at, meta_json, text, tags, tier, archived)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'long_term', 0)""",
            (
                memory_id,
                kind,
                scope,
                content,
                now,
                now,
                meta_json,
                content[:5000],
                tags_json,
            ),
        )

        cursor.execute(
            "INSERT INTO memory_fts(rowid, content) VALUES ((SELECT rowid FROM memories WHERE id = ?), ?)",
            (memory_id, content),
        )

        conn.commit()
        conn.close()

        return {
            "status": "ok",
            "memory_id": memory_id,
            "kind": kind,
            "scope": scope,
            "timestamp": now,
        }


from src.orchestration.tool_registry import registry

registry.register(CreateMemoryTool)
