"""Context Injector — Integrate athena-context MCP with BMAD workflow executor.

This module provides context injection from Athena's memory bank into BMAD workflows.
It loads active, product, user, and constraint contexts when workflows start and
updates context as phases complete.

Usage:
    from packages.orchestration.bmad.context_injector import ContextInjector

    injector = ContextInjector()
    context = injector.get_initial_context()

    # Inject into workflow execution
    result = executor.execute(workflow, phase="create", context=context)

    # Update context after phase completes
    injector.on_phase_complete("create", result)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class WorkflowContext:
    """Context to inject into BMAD workflow execution."""

    active_context: str = ""
    product_context: str = ""
    user_context: str = ""
    constraints: str = ""
    injected_at: str = ""
    phase_history: list = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for workflow context."""
        return {
            "active_context": self.active_context,
            "product_context": self.product_context,
            "user_context": self.user_context,
            "constraints": self.constraints,
            "injected_at": self.injected_at,
            "phase_history": self.phase_history,
        }

    @classmethod
    def from_contexts(
        cls,
        active: Optional[dict] = None,
        product: Optional[dict] = None,
        user: Optional[dict] = None,
        constraints: Optional[dict] = None,
    ) -> WorkflowContext:
        """Create WorkflowContext from individual context dicts."""
        return cls(
            active_context=active.get("content", "") if active else "",
            product_context=product.get("content", "") if product else "",
            user_context=user.get("content", "") if user else "",
            constraints=constraints.get("content", "") if constraints else "",
            injected_at=datetime.now().isoformat(),
        )


class ContextInjector:
    """Integrates athena-context MCP with BMAD workflow executor.

    Loads context from Athena memory bank and injects into workflow execution.
    Gracefully handles cases where athena-context is unavailable.

    Usage:
        injector = ContextInjector()
        context = injector.get_initial_context()
        result = executor.execute(workflow, phase="create", context=context.to_dict())
        injector.on_phase_complete("create", result)
    """

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize the context injector.

        Args:
            project_root: Path to project root. Defaults to standard location.
        """
        self.project_root = project_root or Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
        self._athena_mcp_available: Optional[bool] = None
        self._current_context: Optional[WorkflowContext] = None

    def _check_athena_mcp_available(self) -> bool:
        """Check if athena-context MCP is available."""
        if self._athena_mcp_available is not None:
            return self._athena_mcp_available

        # Try importing the athena_context_mcp module
        try:
            # First check if package is installed
            import importlib.util

            spec = importlib.util.find_spec("athena_context_mcp")
            if spec is None:
                logger.debug("athena_context_mcp not installed")
                self._athena_mcp_available = False
                return False

            # Try importing to verify it works
            from athena_context_mcp import (
                get_active_context,
                get_product_context,
                get_user_context,
                get_constraints,
            )

            self._athena_mcp_available = True
            logger.info("athena-context MCP is available")
            return True

        except ImportError as e:
            logger.debug(f"Cannot import athena_context_mcp: {e}")
            self._athena_mcp_available = False
            return False
        except Exception as e:
            logger.warning(f"Error checking athena-context MCP: {e}")
            self._athena_mcp_available = False
            return False

    def _read_context_file(self, filename: str) -> dict:
        """Read a context file from the memory bank.

        Args:
            filename: Name of context file (e.g., "activeContext.md")

        Returns:
            Dict with content, exists, error keys
        """
        memory_bank = self.project_root / ".context" / "memory_bank"
        file_path = memory_bank / filename

        result = {
            "content": "",
            "exists": False,
            "error": None,
        }

        if not file_path.exists():
            result["error"] = f"File not found: {file_path}"
            return result

        try:
            result["content"] = file_path.read_text(encoding="utf-8")
            result["exists"] = True
        except Exception as e:
            result["error"] = str(e)

        return result

    def get_initial_context(self) -> WorkflowContext:
        """Get initial context for workflow execution.

        Loads active, product, user, and constraint contexts from Athena memory bank.
        If athena-context MCP is unavailable, falls back to reading files directly.

        Returns:
            WorkflowContext with all available contexts
        """
        logger.info("Loading initial context for BMAD workflow")

        # Try MCP first, then fallback to direct file reading
        if self._check_athena_mcp_available():
            try:
                from athena_context_mcp import (
                    get_active_context,
                    get_product_context,
                    get_user_context,
                    get_constraints,
                )

                active = get_active_context()
                product = get_product_context()
                user = get_user_context()
                constraints = get_constraints()

                context = WorkflowContext.from_contexts(
                    active=active,
                    product=product,
                    user=user,
                    constraints=constraints,
                )

                self._current_context = context
                logger.info(
                    f"Loaded context from MCP: active={bool(active.get('content'))}, "
                    f"product={bool(product.get('content'))}, "
                    f"user={bool(user.get('content'))}, "
                    f"constraints={bool(constraints.get('content'))}"
                )
                return context

            except Exception as e:
                logger.warning(f"Failed to load context from MCP, falling back to files: {e}")

        # Fallback: read files directly
        logger.info("Using fallback file-based context loading")

        active = self._read_context_file("activeContext.md")
        product = self._read_context_file("productContext.md")
        user = self._read_context_file("userContext.md")
        constraints = self._read_context_file("constraints.md")

        context = WorkflowContext.from_contexts(
            active=active if active["exists"] else None,
            product=product if product["exists"] else None,
            user=user if user["exists"] else None,
            constraints=constraints if constraints["exists"] else None,
        )

        self._current_context = context
        logger.info(
            f"Loaded context from files: active={active['exists']}, "
            f"product={product['exists']}, "
            f"user={user['exists']}, "
            f"constraints={constraints['exists']}"
        )

        return context

    def on_phase_complete(self, phase: str, result: Any) -> None:
        """Update context when a workflow phase completes.

        Args:
            phase: Name of completed phase ("create", "edit", "validate")
            result: WorkflowResult from phase execution
        """
        if self._current_context is None:
            logger.warning("No current context to update")
            return

        # Record phase completion
        phase_record = {
            "phase": phase,
            "completed_at": datetime.now().isoformat(),
            "success": result.success if hasattr(result, "success") else None,
            "steps_completed": result.steps_completed if hasattr(result, "steps_completed") else [],
            "steps_failed": result.steps_failed if hasattr(result, "steps_failed") else [],
        }

        self._current_context.phase_history.append(phase_record)
        logger.info(f"Phase '{phase}' completed: success={phase_record['success']}")

    def get_injected_context_block(self, context_type: str = "all") -> str:
        """Get a formatted context block for prompt injection.

        Args:
            context_type: Which contexts to include ("all", "active", "product", "user")

        Returns:
            Formatted context block string
        """
        if self._current_context is None:
            self.get_initial_context()

        context = self._current_context
        if context is None:
            return "# No context available"

        blocks = []
        blocks.append("# Athena Context Injection")
        blocks.append(f"# Generated: {datetime.now().isoformat()}")
        blocks.append("")

        if context_type in ["all", "active"] and context.active_context:
            blocks.append("## Active Context")
            blocks.append(context.active_context)
            blocks.append("")

        if context_type in ["all", "product"] and context.product_context:
            blocks.append("## Product Context (Identity)")
            blocks.append(context.product_context)
            blocks.append("")

        if context_type in ["all", "user"] and context.user_context:
            blocks.append("## User Context")
            blocks.append(context.user_context)
            blocks.append("")

        if context_type == "all" and context.constraints:
            blocks.append("## Constraints")
            blocks.append(context.constraints)
            blocks.append("")

        return "\n".join(blocks)

    def reset(self) -> None:
        """Reset the current context."""
        self._current_context = None
        logger.info("Context injector reset")


# Module-level convenience functions

_injector: Optional[ContextInjector] = None


def get_injector() -> ContextInjector:
    """Get the default context injector instance."""
    global _injector
    if _injector is None:
        _injector = ContextInjector()
    return _injector


def get_initial_context() -> WorkflowContext:
    """Get initial context for workflow execution."""
    return get_injector().get_initial_context()


def inject_into_workflow(context: WorkflowContext) -> Dict[str, Any]:
    """Get context dict for workflow execution.

    Args:
        context: WorkflowContext from get_initial_context()

    Returns:
        Dict ready for BMADExecutor.execute(context=...)
    """
    return context.to_dict()


def on_phase_complete(phase: str, result: Any) -> None:
    """Update context when a phase completes."""
    get_injector().on_phase_complete(phase, result)
