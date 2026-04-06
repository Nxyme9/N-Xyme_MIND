"""GetLearningStatsTool — Get learning statistics."""

from src.orchestration.tool_factory import build_tool, ToolContext


@build_tool
class GetLearningStatsTool:
    name = "get_learning_stats"
    description = "Get learning statistics from priority_engine, preference_model, procedural memory"
    input_schema = {}

    def is_read_only(self, input) -> bool:
        return True

    def is_concurrency_safe(self, input) -> bool:
        return True

    async def execute(self, input, context: ToolContext):
        from src.memory.unified_memory import get_learning_stats

        return await get_learning_stats()


from src.orchestration.tool_registry import registry

registry.register(GetLearningStatsTool)