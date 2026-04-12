"""A/B Testing Framework — DEPRECATED, use packages.learning_engine.routing.ab_testing instead.

This module is kept for backwards compatibility only.
Import from learning_engine.routing.ab_testing for new code.
"""

# Re-export from single source of truth
from packages.learning_engine.routing.ab_testing import ABTest as _ABTest, ABTestingFramework as _ABTestingFramework

ABTest = _ABTest
ABTestingFramework = _ABTestingFramework

__all__ = ["ABTest", "ABTestingFramework"]