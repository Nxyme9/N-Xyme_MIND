"""GetLearningPatternsTool — Get learned patterns from self-learning system."""

from src.orchestration.tool_factory import build_tool, ToolContext


@build_tool
class GetLearningPatternsTool:
    name = "get_learning_patterns"
    description = "Get learned patterns from the self-learning system"
    input_schema = {
        "query": {"type": "string", "description": "Optional query to filter", "default": ""},
        "limit": {"type": "integer", "description": "Max patterns", "default": 10}
    }

    def is_read_only(self, input) -> bool:
        return True

    def is_concurrency_safe(self, input) -> bool:
        return True

    async def execute(self, input, context: ToolContext):
        from src.memory.unified_memory import get_learning_patterns

        return await get_learning_patterns(
            query=input.get("query", ""),
            limit=input.get("limit", 10)
        )


from src.orchestration.tool_registry import registry

registry.register(GetLearningPatternsTool)