"""
The Catalyst - Core Orchestration Engine for N-Xyme Catalyst

This package provides the central orchestration engine that coordinates
all components of the N-Xyme Catalyst system.
"""

from .catalyst import (
    Catalyst,
    SystemState,
    ComponentStatus,
    ComponentHealth,
    SystemHealth,
    CatalystError,
    InitializationError,
    ComponentError,
    create_catalyst,
)

__version__ = "1.0.0"
__author__ = "N-Xyme"

__all__ = [
    "Catalyst",
    "SystemState",
    "ComponentStatus",
    "ComponentHealth",
    "SystemHealth",
    "CatalystError",
    "InitializationError",
    "ComponentError",
    "create_catalyst",
]
