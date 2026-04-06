"""SearchMemoriesTool — Search across all memory sources."""

from src.orchestration.tool_factory import build_tool, ToolContext, ToolResult


@build_tool
class SearchMemoriesTool:
    name = "search_memories"
    description = "Search across all memory sources using unified memory router"
    input_schema = {
        "query": {"type": "string", "description": "Search query string"},
        "limit": {"type": "integer", "description": "Max results", "default": 10},
        "sources": {
            "type": "array",
            "description": "Specific sources to query",
            "optional": True,
        },
    }

    def is_read_only(self, input) -> bool:
        return True

    def is_concurrency_safe(self, input) -> bool:
        return True

    async def execute(self, input, context: ToolContext):
        from src.memory.router import get_router
        from src.memory.router import UnifiedMemoryQuery

        router = get_router()
        query = input.get("query", "")
        limit = input.get("limit", 10)
        sources = input.get("sources")

        um_query = UnifiedMemoryQuery(
            query=query,
            max_results_per_source=limit,
            enabled_sources=sources,
        )

        result = router.search(um_query)

        return {
            "status": "ok",
            "query": query,
            "results": [
                {
                    "content": r.content[:500],
                    "source": r.source,
                    "score": r.score,
                    "id": r.id,
                }
                for r in result.results
            ],
            "sources_queried": result.sources_queried,
            "sources_failed": result.sources_failed,
            "total_results": result.total_results,
        }


from src.orchestration.tool_registry import registry

registry.register(SearchMemoriesTool)
