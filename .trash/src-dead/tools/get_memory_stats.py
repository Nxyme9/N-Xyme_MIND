"""GetMemoryStatsTool — Get statistics about memory sources."""

from src.orchestration.tool_factory import build_tool, ToolContext, ToolResult


@build_tool
class GetMemoryStatsTool:
    name = "get_memory_stats"
    description = "Get statistics about all memory sources and their health"
    input_schema = {}

    def is_read_only(self, input) -> bool:
        return True

    def is_concurrency_safe(self, input) -> bool:
        return True

    async def execute(self, input, context: ToolContext):
        from src.memory.registry import get_registry, get_enabled_connectors

        registry = get_registry()
        connectors = get_enabled_connectors()

        sources = []
        for conn in connectors:
            try:
                health = conn.health_check()
                sources.append(
                    {
                        "name": conn.name,
                        "enabled": True,
                        "status": "healthy" if health.healthy else "error",
                        "message": health.error or "",
                        "latency_ms": round(health.latency_ms, 2),
                    }
                )
            except Exception as e:
                sources.append(
                    {
                        "name": conn.name,
                        "enabled": True,
                        "status": "error",
                        "message": str(e),
                    }
                )

        return {
            "status": "ok",
            "sources": sources,
            "total_sources": len(sources),
            "enabled_count": len([s for s in sources if s.get("enabled")]),
        }


from src.orchestration.tool_registry import registry

registry.register(GetMemoryStatsTool)
