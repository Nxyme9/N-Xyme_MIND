"""DeleteMemoryTool — Delete or archive a memory entry."""

from src.orchestration.tool_factory import build_tool, ToolContext


@build_tool
class DeleteMemoryTool:
    name = "delete_memory"
    description = "Delete or archive a memory entry"
    input_schema = {
        "memory_id": {"type": "string", "description": "Memory ID"},
        "hard_delete": {"type": "boolean", "description": "Permanent delete", "default": False}
    }

    def is_read_only(self, input) -> bool:
        return False

    def is_concurrency_safe(self, input) -> bool:
        return True

    def is_destructive(self, input) -> bool:
        return input.get("hard_delete", False)

    async def execute(self, input, context: ToolContext):
        from src.memory.unified_memory import delete_memory

        return await delete_memory(
            memory_id=input.get("memory_id", ""),
            hard_delete=input.get("hard_delete", False)
        )


from src.orchestration.tool_registry import registry

registry.register(DeleteMemoryTool)