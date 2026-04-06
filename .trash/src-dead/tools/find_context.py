"""FindContextTool — Find relevant context for a task."""

from src.orchestration.tool_factory import build_tool, ToolContext


@build_tool
class FindContextTool:
    name = "find_context"
    description = "Find relevant context for a specific task"
    input_schema = {
        "task": {"type": "string", "description": "Task description"},
        "context_type": {"type": "string", "description": "Context type", "default": "all"}
    }

    def is_read_only(self, input) -> bool:
        return True

    def is_concurrency_safe(self, input) -> bool:
        return True

    async def execute(self, input, context: ToolContext):
        from src.memory.unified_memory import find_context

        return await find_context(
            task=input.get("task", ""),
            context_type=input.get("context_type", "all")
        )


from src.orchestration.tool_registry import registry

registry.register(FindContextTool)