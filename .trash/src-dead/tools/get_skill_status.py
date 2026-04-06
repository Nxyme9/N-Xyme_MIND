"""GetSkillStatusTool — Get skill lifecycle status."""

from src.orchestration.tool_factory import build_tool, ToolContext


@build_tool
class GetSkillStatusTool:
    name = "get_skill_status"
    description = "Get skill lifecycle status"
    input_schema = {
        "skill_name": {"type": "string", "description": "Optional skill name", "optional": True}
    }

    def is_read_only(self, input) -> bool:
        return True

    def is_concurrency_safe(self, input) -> bool:
        return True

    async def execute(self, input, context: ToolContext):
        from src.memory.unified_memory import get_skill_status

        return await get_skill_status(skill_name=input.get("skill_name"))


from src.orchestration.tool_registry import registry

registry.register(GetSkillStatusTool)