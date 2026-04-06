"""UpdateMemoryTool — Update an existing memory entry."""

from src.orchestration.tool_factory import build_tool, ToolContext


@build_tool
class UpdateMemoryTool:
    name = "update_memory"
    description = "Update an existing memory entry"
    input_schema = {
        "memory_id": {"type": "string", "description": "Memory ID"},
        "content": {"type": "string", "description": "New content", "optional": True},
        "tags": {"type": "array", "description": "New tags", "optional": True},
        "metadata": {"type": "object", "description": "New metadata", "optional": True}
    }

    def is_read_only(self, input) -> bool:
        return False

    def is_concurrency_safe(self, input) -> bool:
        return True

    async def execute(self, input, context: ToolContext):
        from src.memory.unified_memory import update_memory

        return await update_memory(
            memory_id=input.get("memory_id", ""),
            content=input.get("content"),
            tags=input.get("tags"),
            metadata=input.get("metadata")
        )


from src.orchestration.tool_registry import registry

registry.register(UpdateMemoryTool)