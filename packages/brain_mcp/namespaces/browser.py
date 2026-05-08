"""
Browser namespace tools for nx-brain-mcp.

This module contains all browser/playwright-related MCP tools.
Functions are registered manually in __init__.py after MCP is available.
"""

from __future__ import annotations

from typing import Optional


# ============================================================================
# PLAYWRIGHT TOOLS (browser.*) - Personal Brain Browser Automation
# ============================================================================


async def browser_navigate(url: str) -> dict[str, any]:
    """Navigate to a URL and return page info."""
    try:
        from playwright_mcp import navigate as pw_navigate

        return await pw_navigate(url)
    except Exception as e:
        return {"error": str(e)}


async def browser_screenshot(
    path: Optional[str] = None, full_page: bool = False
) -> dict[str, any]:
    """Take a screenshot of the current page."""
    try:
        from playwright_mcp import screenshot as pw_screenshot

        return await pw_screenshot(path, full_page)
    except Exception as e:
        return {"error": str(e)}


async def browser_click(selector: str) -> dict[str, any]:
    """Click an element on the page."""
    try:
        from playwright_mcp import click as pw_click

        return await pw_click(selector)
    except Exception as e:
        return {"error": str(e)}


async def browser_fill(selector: str, value: str) -> dict[str, any]:
    """Fill an input field."""
    try:
        from playwright_mcp import fill as pw_fill

        return await pw_fill(selector, value)
    except Exception as e:
        return {"error": str(e)}


async def browser_get_text(selector: str) -> dict[str, any]:
    """Get text content from an element."""
    try:
        from playwright_mcp import get_text as pw_get_text

        return await pw_get_text(selector)
    except Exception as e:
        return {"error": str(e)}


async def browser_evaluate(script: str) -> dict[str, any]:
    """Execute JavaScript in page context."""
    try:
        from playwright_mcp import evaluate as pw_evaluate

        return await pw_evaluate(script)
    except Exception as e:
        return {"error": str(e)}
