"""SemanticSearchTool — Semantic search using embeddings."""

from src.orchestration.tool_factory import build_tool, ToolContext


@build_tool
class SemanticSearchTool:
    name = "semantic_search"
    description = "Semantic search using embeddings via Ollama"
    input_schema = {
        "query": {"type": "string", "description": "Search query"},
        "top_k": {"type": "integer", "description": "Number of results", "default": 5}
    }

    def is_read_only(self, input) -> bool:
        return True

    def is_concurrency_safe(self, input) -> bool:
        return True

    async def execute(self, input, context: ToolContext):
        from src.memory.unified_memory import semantic_search

        return await semantic_search(
            query=input.get("query", ""),
            top_k=input.get("top_k", 5)
        )


from src.orchestration.tool_registry import registry

registry.register(SemanticSearchTool)