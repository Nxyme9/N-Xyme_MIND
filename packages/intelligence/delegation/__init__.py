"""Delegation package — Task decomposition and context sharing."""

from .decomposer import TaskDecomposer, get_task_decomposer
from .context_sharing import ContextSharing, get_context_sharing
from .communication import AgentCommunication, get_agent_communication
from .logger import DelegationOutcomeLogger, get_outcome_logger

__all__ = [
    "TaskDecomposer",
    "get_task_decomposer",
    "ContextSharing",
    "get_context_sharing",
    "AgentCommunication",
    "get_agent_communication",
    "DelegationOutcomeLogger",
    "get_outcome_logger",
]
