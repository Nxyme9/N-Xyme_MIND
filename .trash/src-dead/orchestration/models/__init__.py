"""
Models — Model fallback management with circuit breakers.

Modules:
    - fallback: Model fallback manager with automatic routing
"""

from .fallback import ModelFallbackManager, FallbackRoute, ModelHealth

__all__ = [
    "ModelFallbackManager",
    "FallbackRoute",
    "ModelHealth",
]
