"""RecallSessionTool — Recall session context from session history."""

from src.orchestration.tool_factory import build_tool, ToolContext


@build_tool
class RecallSessionTool:
    name = "recall_session"
    description = "Recall session context from session history"
    input_schema = {
        "session_id": {"type": "string", "description": "Optional session ID", "optional": True},
        "lines": {"type": "integer", "description": "Number of lines", "default": 50}
    }

    def is_read_only(self, input) -> bool:
        return True

    def is_concurrency_safe(self, input) -> bool:
        return True

    async def execute(self, input, context: ToolContext):
        from src.memory.unified_memory import recall_session

        return await recall_session(
            session_id=input.get("session_id"),
            lines=input.get("lines", 50)
        )


from src.orchestration.tool_registry import registry

registry.register(RecallSessionTool)