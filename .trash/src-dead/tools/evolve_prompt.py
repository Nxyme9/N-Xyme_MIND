"""EvolvePromptTool — Evolve a prompt using PromptWizard generate→critique→refine loop."""

from src.orchestration.tool_factory import build_tool, ToolContext


@build_tool
class EvolvePromptTool:
    name = "evolve_prompt"
    description = "Evolve a prompt using the PromptWizard generate→critique→refine loop"
    input_schema = {
        "original_prompt": {"type": "string", "description": "Original prompt"},
        "task_context": {"type": "string", "description": "Task context", "default": ""},
        "iterations": {"type": "integer", "description": "Evolution iterations", "default": 3}
    }

    def is_read_only(self, input) -> bool:
        return True

    def is_concurrency_safe(self, input) -> bool:
        return True

    async def execute(self, input, context: ToolContext):
        from src.memory.unified_memory import evolve_prompt

        return await evolve_prompt(
            original_prompt=input.get("original_prompt", ""),
            task_context=input.get("task_context", ""),
            iterations=input.get("iterations", 3)
        )


from src.orchestration.tool_registry import registry

registry.register(EvolvePromptTool)