"""TemprSearchTool — TEMPR multi-strategy retrieval with RRF fusion."""

from src.orchestration.tool_factory import build_tool, ToolContext


@build_tool
class TemprSearchTool:
    name = "tempr_search"
    description = "TEMPR multi-strategy retrieval with RRF fusion"
    input_schema = {
        "query": {"type": "string", "description": "Search query"},
        "top_k": {"type": "integer", "description": "Max results", "default": 10},
        "tier": {"type": "string", "description": "Memory tier", "optional": True},
        "strategies": {"type": "array", "description": "Search strategies", "optional": True}
    }

    def is_read_only(self, input) -> bool:
        return True

    def is_concurrency_safe(self, input) -> bool:
        return True

    async def execute(self, input, context: ToolContext):
        from src.memory.unified_memory import tempr_search

        return await tempr_search(
            query=input.get("query", ""),
            top_k=input.get("top_k", 10),
            tier=input.get("tier"),
            strategies=input.get("strategies")
        )


from src.orchestration.tool_registry import registry

registry.register(TemprSearchTool)