"""N-Xyme Core — Interface definitions for plug-and-play modules."""

__version__ = "1.0.0"

from .interfaces import (
    NXymeModule,
    ModuleMetadata,
    ModuleState,
    ModuleStatus,
    HealthCheckResult,
)
from .registry import NXymeRegistry, get_registry
from .config import NXymeConfig, ModuleConfig, get_default_config, load_config

__all__ = [
    # Interfaces
    "NXymeModule",
    "ModuleMetadata",
    "ModuleState",
    "ModuleStatus",
    "HealthCheckResult",
    # Registry
    "NXymeRegistry",
    "get_registry",
    # Config
    "NXymeConfig",
    "ModuleConfig",
    "get_default_config",
    "load_config",
]
