"""RecordSkillOutcomeTool — Record a skill execution outcome for learning."""

from src.orchestration.tool_factory import build_tool, ToolContext


@build_tool
class RecordSkillOutcomeTool:
    name = "record_skill_outcome"
    description = "Record a skill execution outcome for learning"
    input_schema = {
        "skill_name": {"type": "string", "description": "Skill name"},
        "success": {"type": "boolean", "description": "Success status"},
        "latency_ms": {"type": "number", "description": "Execution latency", "default": 0},
        "feedback": {"type": "string", "description": "User feedback", "optional": True}
    }

    def is_read_only(self, input) -> bool:
        return False

    def is_concurrency_safe(self, input) -> bool:
        return True

    async def execute(self, input, context: ToolContext):
        from src.memory.unified_memory import record_skill_outcome

        return await record_skill_outcome(
            skill_name=input.get("skill_name", ""),
            success=input.get("success", False),
            latency_ms=input.get("latency_ms", 0),
            feedback=input.get("feedback", "")
        )


from src.orchestration.tool_registry import registry

registry.register(RecordSkillOutcomeTool)