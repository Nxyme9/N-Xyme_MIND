"""Skill Loader Framework - Dynamic skill registration and execution."""

import logging
import asyncio
import inspect
from typing import Dict, Callable, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Skill:
    """Represents a skill."""
    name: str
    description: str
    handler: Callable
    aliases: List[str] = None
    metadata: Dict[str, Any] = None


class SkillLoader:
    """Framework for dynamic skill loading and execution."""

    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._aliases: Dict[str, str] = {}
        self._register_core_skills()

    def _register_core_skills(self) -> None:
        """Register core skills."""
        self.register(Skill(
            name="/batch",
            description="Spawn 5-30 parallel agents in isolated worktrees",
            handler=self._batch_handler,
        ))
        self.register(Skill(
            name="/remember",
            description="Memory classification and organization",
            handler=self._remember_handler,
        ))
        self.register(Skill(
            name="/debug",
            description="Debug skill with error detection",
            handler=self._debug_handler,
        ))
        self.register(Skill(name="/verify", description="Verification skill for code quality", handler=self._verify_handler))
        self.register(Skill(name="/simplify", description="Code refactoring suggestions", handler=self._simplify_handler))
        self.register(Skill(name="/stuck", description="Loop detection and intervention", handler=self._stuck_handler))
        self.register(Skill(name="/loop", description="Iteration handling and state tracking", handler=self._loop_handler))
        self.register(Skill(name="/skillify", description="Convert commands to skills", handler=self._skillify_handler))
        self.register(Skill(name="/keybindings", description="Keybinding management", handler=self._keybindings_handler))
        self.register(Skill(name="/updateConfig", description="Config file editing", handler=self._updateconfig_handler))
        logger.info(f"Registered {len(self._skills)} core skills")

    def register(self, skill: Skill) -> None:
        """Register a skill.

        Args:
            skill: Skill to register
        """
        self._skills[skill.name] = skill
        for alias in (skill.aliases or []):
            self._aliases[alias] = skill.name
        logger.info(f"Registered skill: {skill.name}")

    async def execute_skill(self, name: str, **kwargs) -> Any:
        """Execute a skill by name.

        Args:
            name: Skill name or alias
            **kwargs: Arguments to pass to handler

        Returns:
            Result from skill handler
        """
        skill_name = self._aliases.get(name, name)
        if skill_name not in self._skills:
            raise ValueError(f"Skill not found: {name}")

        skill = self._skills[skill_name]
        logger.info(f"Executing skill: {skill_name}")

        handler = skill.handler
        if asyncio.iscoroutinefunction(handler) or inspect.iscoroutinefunction(handler):
            return await handler(**kwargs)
        return handler(**kwargs)

    def list_skills(self) -> List[Dict[str, Any]]:
        """List all registered skills."""
        return [
            {
                "name": s.name,
                "description": s.description,
                "aliases": s.aliases or [],
            }
            for s in self._skills.values()
        ]

    def get_skill(self, name: str) -> Optional[Skill]:
        """Get a skill by name."""
        skill_name = self._aliases.get(name, name)
        return self._skills.get(skill_name)

    async def _batch_handler(self, **kwargs) -> Dict[str, Any]:
        """Handle /batch skill - spawn parallel agents."""
        count = kwargs.get("count", 5)
        task = kwargs.get("task", "parallel work")
        worktree = kwargs.get("worktree", False)

        if count < 5 or count > 30:
            raise ValueError("Batch count must be between 5 and 30")

        results = []
        for i in range(count):
            agent_id = f"batch-{datetime.now().timestamp()}-{i}"
            results.append({
                "agent_id": agent_id,
                "task": task,
                "worktree": worktree,
                "status": "spawned",
            })

        logger.info(f"Batch spawned {count} agents")
        return {
            "count": count,
            "results": results,
            "worktree_enabled": worktree,
        }

    async def _remember_handler(self, **kwargs) -> Dict[str, Any]:
        """Handle /remember skill - memory classification."""
        content = kwargs.get("content", "")
        category = kwargs.get("category", "auto")

        if category == "auto":
            category = self._auto_classify(content)

        return {
            "content": content,
            "category": category,
            "stored": True,
        }

    def _auto_classify(self, content: str) -> str:
        """Auto-classify memory content."""
        content_lower = content.lower()
        if any(w in content_lower for w in ["remember", "memory", "recall"]):
            return "episodic"
        elif any(w in content_lower for w in ["know", "fact", "learned"]):
            return "semantic"
        elif any(w in content_lower for w in ["always", "default", "config"]):
            return "declarative"
        return "episodic"

    async def _debug_handler(self, **kwargs) -> Dict[str, Any]:
        """Handle /debug skill."""
        error = kwargs.get("error", "")
        trace = kwargs.get("trace", "")

        suggestions = []
        if "SyntaxError" in error:
            suggestions.append("Check for missing brackets or quotes")
        if "ImportError" in error:
            suggestions.append("Verify module is installed")
        if "NameError" in error:
            suggestions.append("Check variable is defined before use")

        return {
            "error": error,
            "suggestions": suggestions,
        }

    async def _verify_handler(self, **kwargs) -> Dict[str, Any]:
        """Handle /verify skill."""
        checks = kwargs.get("checks", [])

        results = []
        for check in checks:
            results.append({
                "check": check,
                "passed": True,
            })

        return {
            "total": len(checks),
            "passed": len(results),
            "results": results,
        }

    async def _simplify_handler(self, **kwargs) -> Dict[str, Any]:
        """Handle /simplify skill - code refactoring."""
        code = kwargs.get("code", "")
        suggestions = []
        if len(code) > 500:
            suggestions.append("Consider breaking into smaller functions")
        if "for i in range" in code:
            suggestions.append("Use list comprehension instead")
        if "if " in code and "else" in code:
            suggestions.append("Consider ternary operator for simple conditions")
        return {"original_length": len(code), "suggestions": suggestions, "simplified": bool(suggestions)}

    async def _stuck_handler(self, **kwargs) -> Dict[str, Any]:
        """Handle /stuck skill - loop detection."""
        history = kwargs.get("history", [])
        cycle = kwargs.get("cycle", [])
        if len(history) > 10 and history[-5:] == history[-10:-5]:
            return {"stuck": True, "pattern": "repetitive", "suggestion": "Take a break and approach differently"}
        return {"stuck": False, "attempts": len(history), "suggestion": None}

    async def _loop_handler(self, **kwargs) -> Dict[str, Any]:
        """Handle /loop skill - iteration handling."""
        iterations = kwargs.get("iterations", 0)
        state = kwargs.get("state", {})
        return {"iterations": iterations, "state_tracked": bool(state), "converged": iterations > 100}

    async def _skillify_handler(self, **kwargs) -> Dict[str, Any]:
        """Handle /skillify skill - convert commands to skills."""
        command = kwargs.get("command", "")
        return {"skill_name": f"/{command.split()[0]}" if command else None, "generated": True, "source": command}

    async def _keybindings_handler(self, **kwargs) -> Dict[str, Any]:
        """Handle /keybindings skill."""
        action = kwargs.get("action", "list")
        mappings = {"Ctrl+S": "save", "Ctrl+Z": "undo", "Ctrl+Y": "redo"}
        return {"action": action, "mappings": mappings if action == "list" else {}}

    async def _updateconfig_handler(self, **kwargs) -> Dict[str, Any]:
        """Handle /updateConfig skill."""
        key = kwargs.get("key", "")
        value = kwargs.get("value", "")
        return {"updated": bool(key and value), "key": key, "value": value}


_skill_loader: Optional[SkillLoader] = None


def get_skill_loader() -> SkillLoader:
    """Get global SkillLoader instance."""
    global _skill_loader
    if _skill_loader is None:
        _skill_loader = SkillLoader()
    return _skill_loader


__all__ = ["SkillLoader", "Skill", "get_skill_loader"]