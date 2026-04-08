"""BMAD Workflow Executor — Load and execute BMAD workflows from _bmad/.

Public API:
    BMADExecutor        — Main executor class
    load_workflow()     — Load a workflow definition by name
    list_workflows()    — List available workflows
    execute_workflow()  — Execute a workflow by name
"""

__interface_version__ = "1.0.0"

from .executor import BMADExecutor, load_workflow, list_workflows, execute_workflow

__all__ = [
    "__interface_version__",
    "BMADExecutor",
    "load_workflow",
    "list_workflows",
    "execute_workflow",
]
