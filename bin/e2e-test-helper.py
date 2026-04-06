"""E2E Test Helper Module.

Provides utility functions for end-to-end testing.
"""


def health_check() -> dict[str, str]:
    """Perform a health check for E2E tests.

    Returns:
        dict: A dictionary containing status and message.
    """
    return {"status": "ok", "message": "E2E test passed"}


def get_model_info() -> dict[str, str]:
    """Get model information for testing.

    Returns:
        dict: A dictionary containing model and provider details.
    """
    return {"model": "qwen3.6-plus-free", "provider": "opencode"}
